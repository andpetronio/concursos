"""La migración unifica estados vigentes sin reescribir asientos de auditoría."""
from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from concursos.tests.test_concursos import DATOS


class UnificacionExclusionMigrationTests(TransactionTestCase):
    def test_migra_ambas_causas_y_conserva_historial_original(self):
        executor = MigrationExecutor(connection)
        destino = executor.loader.graph.leaf_nodes()
        origen = [
            (app, name) if app != "participantes" else (app, "0007_evaluaciones_parciales")
            for app, name in destino
        ]
        executor.migrate(origen)
        try:
            apps = executor.loader.project_state(origen).apps
            Usuario = apps.get_model("auth", "User")
            Concurso = apps.get_model("concursos", "Concurso")
            Persona = apps.get_model("participantes", "Persona")
            Aspirante = apps.get_model("participantes", "Aspirante")
            Cambio = apps.get_model("participantes", "CambioSituacionAspirante")
            usuario = Usuario.objects.create(username="operador_unificacion")
            concurso = Concurso.objects.create(
                **DATOS, creado_por_id=usuario.pk, actualizado_por_id=usuario.pk,
            )
            casos = [
                ("no_habilitado", "no_habilitacion", "acta", "requisitos"),
                ("excluido", "exclusion", "resolucion", "impugnacion_aceptada"),
            ]
            referencia = []
            for i, (estado, tipo, clase, motivo) in enumerate(casos):
                persona = Persona.objects.create(
                    apellido=f"Histórico {i}", nombre="Prueba", dni=f"2999910{i}",
                    creado_por_id=usuario.pk, actualizado_por_id=usuario.pk,
                )
                aspirante = Aspirante.objects.create(
                    concurso_id=concurso.pk, persona_id=persona.pk, situacion=estado, version=2,
                    creado_por_id=usuario.pk, actualizado_por_id=usuario.pk,
                )
                cambio = Cambio.objects.create(
                    aspirante_id=aspirante.pk, tipo=tipo, anterior="inscripto", nueva=estado,
                    fecha_decision=date(2026, 10, 30), clase_documento=clase,
                    documento="Documento histórico", fojas="45/46", fundamento="Constancia histórica",
                    version=2, usuario_id=usuario.pk,
                )
                referencia.append((aspirante.pk, cambio.pk, estado, tipo, motivo))
            MigrationExecutor(connection).migrate(destino)
            apps = MigrationExecutor(connection).loader.project_state(destino).apps
            AspiranteNuevo = apps.get_model("participantes", "Aspirante")
            CambioNuevo = apps.get_model("participantes", "CambioSituacionAspirante")
            for aspirante_id, cambio_id, estado_original, tipo, motivo in referencia:
                a = AspiranteNuevo.objects.get(pk=aspirante_id)
                c = CambioNuevo.objects.get(pk=cambio_id)
                self.assertEqual((a.situacion, a.motivo_exclusion), ("excluido", motivo))
                self.assertEqual((c.tipo, c.anterior, c.nueva), (tipo, "inscripto", estado_original))
                self.assertEqual((c.motivo_exclusion, c.fojas), (motivo, "45/46"))
        finally:
            MigrationExecutor(connection).migrate(destino)
