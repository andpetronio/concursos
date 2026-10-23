from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from concursos.tests.test_concursos import DATOS


ANTERIOR = [("concursos", "0002_alter_concurso_funciones")]


class CatalogosMigrationTests(TransactionTestCase):
    def setUp(self):
        executor = MigrationExecutor(connection)
        self.destinos = executor.loader.graph.leaf_nodes()
        executor.migrate(ANTERIOR)
        self.apps = executor.loader.project_state(ANTERIOR).apps
        self.Concurso = self.apps.get_model("concursos", "Concurso")
        self.usuario = self.apps.get_model("auth", "User").objects.create(username="migracion_catalogo_sintetica")

    def tearDown(self):
        # Si un preflight falló, retirar solo los casos sintéticos antes de restaurar el esquema.
        if not connection.introspection.table_names():
            return
        self.apps.get_model("concursos", "CambioEstado").objects.all().delete()
        self.Concurso.objects.all().delete()
        MigrationExecutor(connection).migrate(self.destinos)
        super().tearDown()

    def registro(self, **cambios):
        return self.Concurso.objects.create(
            **{**DATOS, "modalidad": "Cerrado Interno",
               "agrupamiento": "Mantenimiento, Producción y Servicios Generales", **cambios},
            creado_por_id=self.usuario.pk, actualizado_por_id=self.usuario.pk,
        )

    def migrar(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.destinos)
        return executor.loader.project_state(self.destinos).apps

    def test_conversion_inequivoca_conserva_originales_auditoria_y_otros_datos(self):
        anterior = self.registro()
        historial = self.apps.get_model("concursos", "CambioEstado").objects.create(
            concurso_id=anterior.pk, usuario_id=self.usuario.pk,
            estado_nuevo="preparacion", situacion_nueva="normal",
        )
        original = {campo: getattr(anterior, campo) for campo in ("modalidad", "agrupamiento", "categoria", "tramo")}
        apps = self.migrar()
        nuevo = apps.get_model("concursos", "Concurso").objects.get(pk=anterior.pk)
        self.assertEqual((nuevo.modalidad, nuevo.agrupamiento, nuevo.categoria, nuevo.tramo),
                         ("cerrado_interno", "03", "5", "Intermedio"))
        self.assertEqual(nuevo.clasificacion_anterior, original)
        for campo in ("codigo_presupuestario", "denominacion", "funciones", "unidad", "dependencia", "cadena_jerarquica",
                      "creado_en", "actualizado_en", "creado_por_id", "actualizado_por_id", "version"):
            self.assertEqual(getattr(nuevo, campo), getattr(anterior, campo))
        self.assertTrue(apps.get_model("concursos", "CambioEstado").objects.filter(pk=historial.pk, fecha=historial.fecha).exists())
        MigrationExecutor(connection).migrate(ANTERIOR)
        restaurado = self.Concurso.objects.get(pk=anterior.pk)
        self.assertEqual({campo: getattr(restaurado, campo) for campo in original}, original)

    def test_valor_desconocido_o_nombre_ambiguo_detiene_toda_conversion(self):
        primero = self.registro()
        problema = self.registro(agrupamiento="Técnico-profesional")  # 2A o 2B: no inferir.
        with self.assertRaisesMessage(RuntimeError, "No se convirtió ningún concurso"):
            self.migrar()
        primero.refresh_from_db()
        problema.refresh_from_db()
        self.assertEqual(primero.modalidad, "Cerrado Interno")
        self.assertEqual(problema.agrupamiento, "Técnico-profesional")
        self.Concurso.objects.filter(pk=problema.pk).update(agrupamiento="03", modalidad="Valor desconocido")
        with self.assertRaisesMessage(RuntimeError, "pendiente de revisión administrativa"):
            self.migrar()
        self.assertEqual(self.Concurso.objects.get(pk=problema.pk).modalidad, "Valor desconocido")

    def test_tramo_previo_inconsistente_no_se_sobrescribe(self):
        anterior = self.registro(tramo="Mayor")
        with self.assertRaisesMessage(RuntimeError, "categoría o tramo inconsistente"):
            self.migrar()
        anterior.refresh_from_db()
        self.assertEqual(anterior.tramo, "Mayor")

    def test_reversion_no_pisa_una_correccion_posterior(self):
        anterior = self.registro()
        apps = self.migrar()
        apps.get_model("concursos", "Concurso").objects.filter(pk=anterior.pk).update(
            modalidad="acotado", agrupamiento="2A", categoria="3", tramo="Mayor",
        )
        MigrationExecutor(connection).migrate(ANTERIOR)
        anterior.refresh_from_db()
        self.assertEqual((anterior.modalidad, anterior.agrupamiento, anterior.categoria, anterior.tramo),
                         ("acotado", "2A", "3", "Mayor"))
