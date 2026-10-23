from importlib import import_module

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.exceptions import IrreversibleError
from django.test import TransactionTestCase

from concursos.tests.test_concursos import DATOS


class InicializacionDocumentalMigrationTests(TransactionTestCase):
    def test_existentes_reciben_21_y_etapa_sin_alterar_concurso_participantes_historial(self):
        executor = MigrationExecutor(connection)
        destinos = executor.loader.graph.leaf_nodes()
        anteriores = [("concursos", "0003_concurso_clasificacion_anterior_and_more"),
                      ("participantes", "0003_jurado_unidad_alter_jurado_cargo")]
        executor.migrate([*anteriores, ("expedientes", None)])
        try:
            apps = executor.loader.project_state(anteriores).apps
            usuario = apps.get_model("auth", "User").objects.create(username="migracion_documental")
            Concurso = apps.get_model("concursos", "Concurso")
            concurso = Concurso.objects.create(**DATOS, creado_por_id=usuario.pk, actualizado_por_id=usuario.pk, version=7)
            Persona = apps.get_model("participantes", "Persona")
            persona = Persona.objects.create(nombre="Sintético", apellido="Migración", dni="00123456",
                                             creado_por_id=usuario.pk, actualizado_por_id=usuario.pk)
            Aspirante = apps.get_model("participantes", "Aspirante")
            aspirante = Aspirante.objects.create(concurso_id=concurso.pk, persona_id=persona.pk,
                email="sintetico@example.invalid", expediente_inscripcion="01-758-2026",
                creado_por_id=usuario.pk, actualizado_por_id=usuario.pk)
            Historial = apps.get_model("concursos", "CambioEstado")
            historial = Historial.objects.create(concurso_id=concurso.pk, usuario_id=usuario.pk,
                estado_nuevo="preparacion", situacion_nueva="normal")
            muestras = [(modelo._meta.app_label, modelo._meta.model_name, pk, modelo.objects.values().get(pk=pk))
                        for modelo, pk in [(Concurso, concurso.pk), (Persona, persona.pk), (Aspirante, aspirante.pk), (Historial, historial.pk)]]
            executor = MigrationExecutor(connection)
            executor.migrate(destinos)
            nuevas = executor.loader.project_state(destinos).apps
            for app, modelo, pk, original in muestras:
                self.assertEqual(nuevas.get_model(app, modelo).objects.values().get(pk=pk), original)
            Control = nuevas.get_model("expedientes", "ControlDocumental")
            controles = Control.objects.filter(concurso_id=concurso.pk)
            self.assertEqual(controles.count(), 21)
            self.assertFalse(controles.filter(verificado=True).exists())
            self.assertFalse(controles.exclude(responsable_id=None).exists())
            self.assertFalse(nuevas.get_model("expedientes", "CambioControlDocumental").objects.exists())
            seguimiento = nuevas.get_model("expedientes", "SeguimientoDocumental").objects.get(concurso_id=concurso.pk)
            self.assertEqual((seguimiento.etapa, seguimiento.version), ("preparacion", 1))
            self.assertFalse(nuevas.get_model("expedientes", "CambioEtapaDocumental").objects.exists())
        finally:
            MigrationExecutor(connection).migrate(destinos)

    def test_ampliacion_conserva_19_controles_checks_fojas_observaciones_y_bitacoras(self):
        executor = MigrationExecutor(connection)
        destinos = executor.loader.graph.leaf_nodes()
        anterior = [("expedientes", "0002_etapa_documental")]
        executor.migrate(anterior)
        try:
            apps = executor.loader.project_state(anterior).apps
            usuario = apps.get_model("auth", "User").objects.create(username="ampliacion_documental")
            concurso = apps.get_model("concursos", "Concurso").objects.create(
                **DATOS, creado_por_id=usuario.pk, actualizado_por_id=usuario.pk)
            Control = apps.get_model("expedientes", "ControlDocumental")
            Control.objects.bulk_create([Control(concurso_id=concurso.pk, requisito=c)
                                         for c, _ in Control._meta.get_field("requisito").choices])
            control = Control.objects.get(concurso_id=concurso.pk, requisito="acta_inscriptos")
            control.verificado, control.fojas, control.observaciones = True, "12/15", "Referencia histórica"
            control.version, control.responsable_id, control.actualizado_por_id = 4, usuario.pk, usuario.pk
            control.verificado_en = control.actualizado_en
            control.save()
            apps.get_model("expedientes", "CambioControlDocumental").objects.create(
                control_id=control.pk, usuario_id=usuario.pk, version=4,
                anterior={"verificado": False, "fojas": "5"}, nuevo={"verificado": True, "fojas": "12/15"})
            seguimiento = apps.get_model("expedientes", "SeguimientoDocumental").objects.create(
                concurso_id=concurso.pk, etapa="oposicion", version=2)
            apps.get_model("expedientes", "CambioEtapaDocumental").objects.create(
                seguimiento_id=seguimiento.pk, usuario_id=usuario.pk, anterior="preparacion", nueva="oposicion", version=2)
            muestras = {nombre: list(apps.get_model("expedientes", nombre).objects.order_by("pk").values())
                        for nombre in ["ControlDocumental", "CambioControlDocumental", "SeguimientoDocumental", "CambioEtapaDocumental"]}
            executor = MigrationExecutor(connection)
            executor.migrate(destinos)
            nuevas = executor.loader.project_state(destinos).apps
            for nombre, original in muestras.items():
                self.assertEqual(list(nuevas.get_model("expedientes", nombre).objects.filter(
                    pk__in=[o["id"] for o in original]).order_by("pk").values()), original)
            Control = nuevas.get_model("expedientes", "ControlDocumental")
            nuevos = Control.objects.filter(requisito__in=["oficio_apunsj", "notificacion_jurados"])
            self.assertEqual(Control.objects.count(), 21)
            self.assertEqual(nuevos.count(), 2)
            for nuevo in nuevos:
                self.assertEqual((nuevo.verificado, nuevo.fojas, nuevo.observaciones, nuevo.version,
                                  nuevo.responsable_id, nuevo.verificado_en, nuevo.actualizado_por_id),
                                 (False, "", "", 1, None, None, None))
            # Reversión de semillas intactas: restaura los 19 anteriores sin tocar sus datos.
            MigrationExecutor(connection).migrate(anterior)
            self.assertEqual(list(apps.get_model("expedientes", "ControlDocumental").objects.order_by("pk").values()),
                             muestras["ControlDocumental"])
            MigrationExecutor(connection).migrate(destinos)
            nuevo = Control.objects.get(requisito="notificacion_jurados")
            nuevo.verificado, nuevo.observaciones, nuevo.version = True, "Notificaciones comprobadas", 2
            nuevo.save()
            self.assertEqual(Control.objects.count(), 21)
            antes = list(Control.objects.order_by("pk").values())
            # Reejecutar la carga es idempotente y no reinicia siquiera los controles nuevos.
            migracion = import_module("expedientes.migrations.0004_incorporar_controles_convocatoria")
            with connection.schema_editor() as editor:
                migracion.agregar_controles(nuevas, editor)
            self.assertEqual(list(Control.objects.order_by("pk").values()), antes)
            with self.assertRaisesMessage(IrreversibleError, "tienen datos o historial"):
                MigrationExecutor(connection).migrate(anterior)
            self.assertEqual(list(Control.objects.order_by("pk").values()), antes)
        finally:
            MigrationExecutor(connection).migrate(destinos)
