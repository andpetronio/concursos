from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature

from concursos import services
from concursos.choices import EstadoConcurso, SituacionAdministrativa
from concursos.tests.test_concursos import DATOS, PASSWORD


@skipUnlessDBFeature("has_select_for_update")
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ConcurrentConcursoTests(TransactionTestCase):
    def test_dos_operadores_no_sobrescriben_estado_ni_duplican_historial(self):
        usuario = get_user_model().objects.create_user(username="concurrencia_ficticia", password=PASSWORD)
        concurso = services.crear_concurso(datos=DATOS, usuario=usuario)
        barrier = Barrier(2)

        def cambiar_desde_otra_conexion(estado):
            close_old_connections()
            try:
                actor = get_user_model().objects.get(pk=usuario.pk)
                barrier.wait(timeout=5)
                try:
                    services.cambiar_estado(pk=concurso.pk, estado=estado,
                                             situacion=SituacionAdministrativa.NORMAL, justificacion="",
                                             usuario=actor, version_esperada=1)
                    return "guardado"
                except ValidationError:
                    return "conflicto"
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(cambiar_desde_otra_conexion, [EstadoConcurso.CONVOCADO, EstadoConcurso.EN_CURSO]))
        self.assertCountEqual(results, ["guardado", "conflicto"])
        concurso.refresh_from_db()
        self.assertEqual(concurso.version, 2)
        self.assertEqual(concurso.historial.count(), 2)
        cambio = concurso.historial.first()
        self.assertEqual(cambio.estado_anterior, EstadoConcurso.PREPARACION)
        self.assertEqual(cambio.estado_nuevo, concurso.estado)
