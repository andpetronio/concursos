from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from concursos.tests.test_concursos import DATOS


class UnidadJuradoMigrationTests(TransactionTestCase):
    def test_unidad_vacia_sin_inferencias_conserva_todos_los_datos_del_jurado(self):
        executor = MigrationExecutor(connection)
        destinos = executor.loader.graph.leaf_nodes()
        anterior = [
            ("participantes", "0002_aspirante_email_aspirante_expediente_inscripcion_and_more"),
            ("concursos", "0003_concurso_clasificacion_anterior_and_more"),
        ]
        executor.migrate(anterior)
        try:
            apps = executor.loader.project_state(anterior).apps
            usuario = apps.get_model("auth", "User").objects.create(username="migracion_unidad_sintetica")
            concurso = apps.get_model("concursos", "Concurso").objects.create(
                **DATOS, creado_por_id=usuario.pk, actualizado_por_id=usuario.pk,
            )
            persona = apps.get_model("participantes", "Persona").objects.create(
                apellido="Ficticio", nombre="Prueba", dni="00123456",
                creado_por_id=usuario.pk, actualizado_por_id=usuario.pk,
            )
            Modelo = apps.get_model("participantes", "Jurado")
            jurado = Modelo.objects.create(
                concurso_id=concurso.pk, persona_id=persona.pk,
                titulo="Título sintético", cargo="Cargo histórico sintético", representacion="rectorado",
                calidad="suplente", email="jurado@example.invalid", telefono="0000-0000", version=7,
                creado_por_id=usuario.pk, actualizado_por_id=usuario.pk,
            )
            original = Modelo.objects.values().get(pk=jurado.pk)
            executor = MigrationExecutor(connection)
            executor.migrate(destinos)
            apps = executor.loader.project_state(destinos).apps
            migrado = apps.get_model("participantes", "Jurado").objects.values().get(pk=jurado.pk)
            self.assertEqual(migrado.pop("unidad"), "")
            self.assertIs(migrado.pop("vigente"), True)
            self.assertEqual(migrado, original)
            MigrationExecutor(connection).migrate(anterior)
            self.assertEqual(Modelo.objects.values().get(pk=jurado.pk), original)
        finally:
            MigrationExecutor(connection).migrate(destinos)


class AjustesMigrationTests(TransactionTestCase):
    def test_migrar_registros_anteriores_conserva_identidad_vinculos_funciones_e_historial(self):
        executor = MigrationExecutor(connection)
        destinos = executor.loader.graph.leaf_nodes()
        anterior = [("participantes", "0001_initial"), ("concursos", "0001_initial")]
        executor.migrate(anterior)
        try:
            apps = executor.loader.project_state(anterior).apps
            usuario = apps.get_model("auth", "User").objects.create(username="migracion_ficticia")
            concurso = apps.get_model("concursos", "Concurso").objects.create(
                **{**DATOS, "expediente": "EXP-HISTORICO"}, creado_por_id=usuario.pk, actualizado_por_id=usuario.pk,
            )
            persona = apps.get_model("participantes", "Persona").objects.create(
                apellido="Ficticio", nombre="Histórico", dni="1234567", version=3,
                creado_por_id=usuario.pk, actualizado_por_id=usuario.pk,
            )
            aspirante = apps.get_model("participantes", "Aspirante").objects.create(
                concurso_id=concurso.pk, persona_id=persona.pk,
                creado_por_id=usuario.pk, actualizado_por_id=usuario.pk,
            )
            cambio = apps.get_model("concursos", "CambioEstado").objects.create(
                concurso_id=concurso.pk, usuario_id=usuario.pk,
                estado_nuevo="preparacion", situacion_nueva="normal",
            )
            instantanea = (concurso.creado_en, aspirante.creado_en, persona.actualizado_en, cambio.fecha)
            executor = MigrationExecutor(connection)
            executor.migrate(destinos)
            apps = executor.loader.project_state(destinos).apps
            nuevo = apps.get_model("participantes", "Aspirante").objects.get(pk=aspirante.pk)
            conservada = apps.get_model("participantes", "Persona").objects.get(pk=persona.pk)
            cargo = apps.get_model("concursos", "Concurso").objects.get(pk=concurso.pk)
            evento = apps.get_model("concursos", "CambioEstado").objects.get(pk=cambio.pk)
            self.assertEqual((nuevo.persona_id, nuevo.concurso_id), (persona.pk, concurso.pk))
            self.assertEqual((nuevo.email, nuevo.expediente_inscripcion, nuevo.version), ("", "", 1))
            self.assertEqual((conservada.dni, conservada.version), ("1234567", 3))
            self.assertEqual((cargo.expediente, cargo.funciones), ("EXP-HISTORICO", DATOS["funciones"]))
            self.assertEqual((cargo.creado_en, nuevo.creado_en, conservada.actualizado_en, evento.fecha), instantanea)
        finally:
            MigrationExecutor(connection).migrate(destinos)
