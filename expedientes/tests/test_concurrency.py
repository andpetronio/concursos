from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature

from concursos.services import crear_concurso
from concursos.tests.test_concursos import DATOS
from expedientes.services import actualizar_control, actualizar_etapa


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
@skipUnlessDBFeature("has_select_for_update")
class ConcurrenciaDocumentalTests(TransactionTestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="concurrencia_documental")
        self.usuario.user_permissions.set(Permission.objects.filter(codename__in=["view_concurso", "change_controldocumental"]))
        self.concurso = crear_concurso(datos=DATOS, usuario=self.usuario)

    def competir(self, operaciones):
        barrier = Barrier(2)

        def guardar(operacion):
            close_old_connections()
            try:
                actor = get_user_model().objects.get(pk=self.usuario.pk)
                barrier.wait(timeout=5)
                try:
                    operacion(actor)
                    return "guardado"
                except ValidationError:
                    return "conflicto"
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(guardar, operaciones))

    def test_mismo_control_solo_guarda_una_version_con_historial_atomico(self):
        control = self.concurso.controles_documentales.get(requisito="vacancia")
        def editar(texto):
            return lambda actor: actualizar_control(concurso_id=self.concurso.pk, control_id=control.pk,
                datos={"verificado": True, "observaciones": texto}, usuario=actor, version_esperada=1)
        self.assertCountEqual(self.competir([editar("Uno"), editar("Dos")]), ["guardado", "conflicto"])
        control.refresh_from_db()
        self.assertEqual((control.version, control.historial.count()), (2, 1))
        self.assertEqual(control.historial.get().nuevo["observaciones"], control.observaciones)

    def test_distintos_controles_no_descartan_cambios_independientes(self):
        controles = list(self.concurso.controles_documentales.filter(requisito__in=["vacancia", "tres_temas"]))
        def editar(control):
            return lambda actor: actualizar_control(concurso_id=self.concurso.pk, control_id=control.pk,
                datos={"verificado": True}, usuario=actor, version_esperada=1)
        self.assertEqual(self.competir([editar(c) for c in controles]), ["guardado", "guardado"])
        self.assertEqual(self.concurso.controles_documentales.filter(verificado=True, version=2).count(), 2)

    def test_dos_ultimos_controles_concurrentes_generan_un_solo_avance_automatico(self):
        from expedientes.catalogo import REQUISITOS
        from expedientes.models import CambioEtapaDocumental, SeguimientoDocumental

        for requisito in REQUISITOS[:3]:
            control = self.concurso.controles_documentales.get(requisito=requisito.codigo)
            actualizar_control(concurso_id=self.concurso.pk, control_id=control.pk,
                datos={"verificado": True, "fojas": "12"}, usuario=self.usuario,
                version_esperada=control.version)
        presup = self.concurso.controles_documentales.get(requisito="afectacion_presupuestaria")
        vacancia = self.concurso.controles_documentales.get(requisito="vacancia")

        def guardar(control, datos):
            return lambda actor: actualizar_control(concurso_id=self.concurso.pk,
                control_id=control.pk, datos=datos, usuario=actor, version_esperada=1)

        self.assertEqual(self.competir([
            guardar(presup, {"verificado": True, "fojas": "14",
                            "partida_principal": "01", "actividad_presupuestaria": "02"}),
            guardar(vacancia, {"verificado": True}),
        ]), ["guardado", "guardado"])
        seguimiento = SeguimientoDocumental.objects.get(concurso=self.concurso)
        self.assertEqual((seguimiento.etapa, seguimiento.version, seguimiento.historial.count()),
                         ("convocatoria", 2, 1))
        self.assertEqual(seguimiento.historial.get().origen, CambioEtapaDocumental.Origen.AUTOMATICO)
        self.assertEqual(presup.historial.count(), 1)
        self.assertEqual(vacancia.historial.count(), 1)

    def test_etapa_concurrente_no_sobrescribe_otro_operador(self):
        def editar(etapa):
            return lambda actor: actualizar_etapa(concurso_id=self.concurso.pk, etapa=etapa, usuario=actor, version_esperada=1)
        self.assertCountEqual(self.competir([editar("oposicion"), editar("inscripciones")]), ["guardado", "conflicto"])
        seguimiento = self.concurso.seguimiento_documental
        seguimiento.refresh_from_db()
        self.assertEqual((seguimiento.version, seguimiento.historial.count()), (2, 1))
