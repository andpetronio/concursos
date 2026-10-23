from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature

from concursos import services as concurso_services
from concursos.tests.test_concursos import DATOS, PASSWORD
from participantes import services as participante_services
from participantes.forms import VeedorAltaForm
from participantes.models import Aspirante, Persona, Veedor


@skipUnlessDBFeature("has_select_for_update")
class ConcurrentPersonaTests(TransactionTestCase):
    def test_dos_ediciones_de_inscripcion_solo_guardan_una_version(self):
        usuario = get_user_model().objects.create_user(username="concurrencia_aspirante", password=PASSWORD)
        concurso = concurso_services.crear_concurso(datos=DATOS, usuario=usuario)
        aspirante = participante_services.crear_participacion(
            modelo=Aspirante, concurso=concurso,
            datos={"apellido": "Ficticio", "nombre": "Prueba", "dni": "00123456"}, usuario=usuario,
        )
        barrier = Barrier(2)

        def editar(email):
            close_old_connections()
            try:
                actor = get_user_model().objects.get(pk=usuario.pk)
                registro = Aspirante.objects.get(pk=aspirante.pk)
                barrier.wait(timeout=5)
                try:
                    participante_services.editar_participacion(
                        participacion=registro, datos={"email": email, "expediente_inscripcion": "01-1-2026"},
                        usuario=actor, version_esperada=1,
                    )
                    return "guardado"
                except ValidationError:
                    return "conflicto"
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(editar, ["uno@example.invalid", "dos@example.invalid"]))
        self.assertCountEqual(results, ["guardado", "conflicto"])
        aspirante.refresh_from_db()
        self.assertEqual(aspirante.version, 2)
        self.assertEqual(aspirante.expediente_inscripcion, "01-1-2026")

    def test_dni_cambiado_mientras_espera_lock_no_vincula_persona_equivocada(self):
        usuario = get_user_model().objects.create_user(username="concurrencia_persona", password=PASSWORD)
        concurso = concurso_services.crear_concurso(datos=DATOS, usuario=usuario)
        datos = {"apellido": "Apellido Ficticio", "nombre": "Nombre Ficticio", "dni": "12.345.678"}
        participante_services.crear_participacion(
            modelo=Aspirante, concurso=concurso, datos={**datos, "dni": "12345678"}, usuario=usuario,
        )
        persona = Persona.objects.get()
        formulario = VeedorAltaForm(data=datos)
        self.assertTrue(formulario.is_valid())
        self.assertEqual(formulario.persona_id, persona.pk)
        intentando_lock = Event()

        def observar_select(execute, sql, params, many, context):
            if "FOR UPDATE" in sql and "participantes_persona" in sql:
                intentando_lock.set()
            return execute(sql, params, many, context)

        def vincular_desde_otra_conexion():
            close_old_connections()
            try:
                actor = get_user_model().objects.get(pk=usuario.pk)
                otro_concurso = type(concurso).objects.get(pk=concurso.pk)
                with connection.execute_wrapper(observar_select):
                    try:
                        participante_services.crear_participacion(
                            modelo=Veedor, concurso=otro_concurso, datos=formulario.cleaned_data,
                            usuario=actor, persona_id=formulario.persona_id,
                        )
                    except ValidationError:
                        return "conflicto"
                return "vinculado"
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                bloqueada = Persona.objects.select_for_update().get(pk=persona.pk)
                future = pool.submit(vincular_desde_otra_conexion)
                self.assertTrue(intentando_lock.wait(timeout=5))
                self.assertFalse(future.done())
                bloqueada.dni = "87654321"
                bloqueada.version += 1
                bloqueada.save()
            self.assertEqual(future.result(timeout=10), "conflicto")

        self.assertEqual(Persona.objects.count(), 1)
        self.assertEqual(Persona.objects.get().dni, "87654321")
        self.assertEqual(Veedor.objects.count(), 0)
