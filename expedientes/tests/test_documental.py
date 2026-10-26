from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from concursos import services as concursos_services
from concursos.choices import EstadoConcurso
from concursos.tests.test_concursos import DATOS, PASSWORD, START
from core.models import SessionActivity
from participantes.models import Jurado, Persona

from expedientes.catalogo import REQUISITOS
from expedientes.models import CambioControlDocumental, ControlDocumental, SeguimientoDocumental
from expedientes.services import actualizar_control, actualizar_etapa, consultar_documentacion, habilitacion_convocatoria
from expedientes.validators import normalizar_fojas


class FojasTests(SimpleTestCase):
    def test_individual_rangos_espacios_y_normalizacion(self):
        for entrada, salida in (("5", "5"), ("5/8", "5/8"), ("12/15", "12/15"), ("105/109", "105/109"),
                                (" 005 / 008 ", "5/8"), ("7/7", "7/7"), ("", "")):
            with self.subTest(entrada=entrada):
                self.assertEqual(normalizar_fojas(entrada), salida)

    def test_fojas_invalidas(self):
        for valor in ("0", "-1", "0/5", "5/0", "8/5", "1/2/3", "1 2", "1.5", "1-3", "abc", "１２", "1" * 51):
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                normalizar_fojas(valor)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DocumentalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = get_user_model().objects.create_user(username="documental_sintetico", password=PASSWORD)
        cls.lector = get_user_model().objects.create_user(username="consulta_documental", password=PASSWORD)
        cls.estadista = get_user_model().objects.create_user(username="cambios_estado", password=PASSWORD)
        cls.sin_permiso = get_user_model().objects.create_user(username="sin_acceso_documental", password=PASSWORD)
        ver = Permission.objects.get(content_type__app_label="concursos", codename="view_concurso")
        cls.editor.user_permissions.set([ver, Permission.objects.get(codename="change_controldocumental")])
        cls.lector.user_permissions.set([ver])
        cls.estadista.user_permissions.set([ver, Permission.objects.get(codename="cambiar_estado_concurso")])

    def setUp(self):
        reloj = patch("django.utils.timezone.now", return_value=START)
        self.now = reloj.start()
        self.addCleanup(reloj.stop)
        self.login(self.editor)
        self.concurso = concursos_services.crear_concurso(datos=DATOS, usuario=self.editor)

    def login(self, usuario, client=None):
        client = client or self.client
        client.logout()
        return client.post(reverse("login"), {"username": usuario.username, "password": PASSWORD})

    def control(self, codigo):
        return self.concurso.controles_documentales.get(requisito=codigo)

    def url(self, control, *, concurso=None, historial=False):
        return reverse("concursos:control_historial" if historial else "concursos:control_documental",
                       args=[(concurso or self.concurso).pk, control.pk])

    def guardar(self, codigo, *, verificado=True, fojas="", observaciones="", version=None, client=None):
        control = self.control(codigo)
        prefix = f"control-{control.pk}-"
        datos = {prefix + "fojas": fojas, prefix + "observaciones": observaciones,
                 prefix + "version_esperada": control.version if version is None else version}
        if verificado:
            datos[prefix + "verificado"] = "on"
        return (client or self.client).post(self.url(control), datos)

    def completar_preparacion(self):
        for requisito in reversed(REQUISITOS[:5]):
            self.assertEqual(self.guardar(requisito.codigo, fojas="5/8" if requisito.requiere_foja else "").status_code, 302)

    def crear_jurado(self):
        for numero, (representacion, calidad) in enumerate(
                (r, c) for r in Jurado.Representacion.values for c in Jurado.Calidad.values):
            persona = Persona.objects.create(apellido="Sintético", nombre=f"Prueba {numero}", dni=str(30000000 + numero),
                                              creado_por=self.editor, actualizado_por=self.editor)
            Jurado.objects.create(concurso=self.concurso, persona=persona, representacion=representacion,
                                   calidad=calidad, titulo="Título de prueba", unidad="Unidad de servicio",
                                   creado_por=self.editor, actualizado_por=self.editor)

    def test_inicializa_21_sin_verificaciones_ni_historial_ficticio(self):
        self.assertEqual(self.concurso.controles_documentales.count(), 21)
        self.assertEqual(set(self.concurso.controles_documentales.values_list("requisito", flat=True)),
                         {r.codigo for r in REQUISITOS})
        self.assertFalse(self.concurso.controles_documentales.filter(verificado=True).exists())
        self.assertFalse(self.concurso.controles_documentales.exclude(responsable=None).exists())
        self.assertFalse(CambioControlDocumental.objects.exists())
        with self.assertRaises(IntegrityError), transaction.atomic():
            ControlDocumental.objects.create(concurso=self.concurso, requisito="vacancia")
        with self.assertRaises(IntegrityError), transaction.atomic():
            ControlDocumental.objects.create(concurso=self.concurso, requisito="inventado")

    def test_registro_fojas_y_correcciones_con_historia_antes_despues(self):
        self.assertEqual(self.guardar("jurado_dependencia", fojas=" 005 / 008 ", observaciones="Primera referencia").status_code, 302)
        control = self.control("jurado_dependencia")
        self.assertTrue(control.completo)
        self.assertEqual((control.fojas, control.version, control.responsable, control.verificado_en),
                         ("5/8", 2, self.editor, START))
        primero = control.historial.get()
        self.assertEqual(primero.anterior["fojas"], "")
        self.assertEqual(primero.nuevo["fojas"], "5/8")
        self.now.return_value = START + timedelta(minutes=1)
        self.guardar("jurado_dependencia", fojas="12/15", observaciones="Referencia corregida")
        self.guardar("jurado_dependencia", verificado=False, fojas="12/15", observaciones="Se retiró la verificación")
        control.refresh_from_db()
        self.assertFalse(control.completo)
        self.assertEqual(control.historial.count(), 3)
        self.assertEqual(control.fojas, "12/15")
        self.assertIsNotNone(control.verificado_en)
        historial = self.client.get(self.url(control, historial=True))
        self.assertContains(historial, "Primera referencia")
        self.assertContains(historial, "Referencia corregida")
        self.assertContains(historial, self.editor.username)

    def test_codigos_afectacion_dos_digitos_y_conservacion_historica(self):
        from expedientes.validators import normalizar_codigo_dos_digitos
        self.assertEqual(normalizar_codigo_dos_digitos("1"), "01")
        self.assertEqual(normalizar_codigo_dos_digitos("02"), "02")
        for invalido in ("-1", "123", "1.1", "ab"):
            with self.subTest(invalido=invalido), self.assertRaises(ValidationError):
                normalizar_codigo_dos_digitos(invalido)
        control = self.control("afectacion_presupuestaria")
        datos = {"verificado": True, "fojas": "12/15", "partida_principal": "1",
                 "actividad_presupuestaria": "02", "observaciones": "Afectación ficticia"}
        actualizar_control(concurso_id=self.concurso.pk, control_id=control.pk, datos=datos,
                           usuario=self.editor, version_esperada=control.version)
        control.refresh_from_db()
        self.assertEqual((control.partida_principal, control.actividad_presupuestaria), ("01", "02"))
        self.assertEqual(control.historial.first().nuevo["partida_principal"], "01")
        self.assertEqual(control.historial.first().nuevo["actividad_presupuestaria"], "02")
        with self.assertRaises(ValidationError):
            actualizar_control(concurso_id=self.concurso.pk, control_id=control.pk,
                datos={**datos, "partida_principal": "1.1"},
                usuario=self.editor, version_esperada=control.version)
        control.refresh_from_db()
        self.assertEqual(control.partida_principal, "01")

    def test_foja_invalida_se_rechaza_sin_cambios_y_conserva_formulario(self):
        response = self.guardar("afectacion_presupuestaria", fojas="8/5", observaciones="Conservar entrada")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Conservar entrada")
        self.assertContains(response, "el inicio no puede superar")
        self.assertContains(response, f'/control-documental/{self.control("afectacion_presupuestaria").pk}/#documental-')
        control = self.control("afectacion_presupuestaria")
        self.assertEqual((control.version, control.verificado, control.fojas), (1, False, ""))
        self.assertFalse(control.historial.exists())

    def test_check_sin_foja_y_foja_sin_check_no_completan(self):
        self.assertEqual(self.guardar("acta_inscriptos", verificado=True).status_code, 302)
        self.assertFalse(self.control("acta_inscriptos").completo)
        self.assertEqual(self.guardar("acta_inscriptos", verificado=False, fojas="12/15").status_code, 302)
        self.assertFalse(self.control("acta_inscriptos").completo)
        self.assertContains(self.client.get(self.concurso.get_absolute_url()), "Sin verificar")

    def test_requisitos_sin_foja_no_tienen_campo_y_no_exigen_referencia(self):
        control = self.control("vacancia")
        self.assertNotContains(self.client.get(self.concurso.get_absolute_url()), f'name="control-{control.pk}-fojas"')
        # Una foja agregada al POST no introduce un campo que el catálogo no pide.
        self.assertEqual(self.guardar("vacancia", fojas="injected").status_code, 302)
        control.refresh_from_db()
        self.assertTrue(control.completo)
        self.assertEqual(control.fojas, "")
        control.fojas = "5"
        with self.assertRaises(ValidationError):
            control.full_clean()

    def test_servicio_rechaza_fojas_invalidas_sin_depender_del_formulario(self):
        control = self.control("acta_inscriptos")
        with self.assertRaises(ValidationError):
            actualizar_control(concurso_id=self.concurso.pk, control_id=control.pk,
                               datos={"fojas": "0", "verificado": True}, usuario=self.editor, version_esperada=1)
        control.refresh_from_db()
        self.assertEqual(control.version, 1)

    def test_habilitacion_cinco_cualquier_orden_y_seis_plazas_identificadas(self):
        inicial = habilitacion_convocatoria(self.concurso)
        self.assertEqual(len(inicial.pendientes_documentales), 5)
        self.assertEqual(len(inicial.pendientes_jurado), 6)
        self.assertFalse(inicial.habilitado)
        self.completar_preparacion()
        self.assertFalse(habilitacion_convocatoria(self.concurso).habilitado)
        self.crear_jurado()
        self.assertTrue(habilitacion_convocatoria(self.concurso).habilitado)
        Jurado.objects.filter(concurso=self.concurso, representacion="rectorado", calidad="suplente").delete()
        resultado = habilitacion_convocatoria(self.concurso)
        self.assertFalse(resultado.habilitado)
        self.assertIn("falta suplente", resultado.pendientes_jurado[0])

    def test_habilitacion_valida_datos_generales_y_jurado_anteriores_incompletos(self):
        self.completar_preparacion()
        self.crear_jurado()
        Jurado.objects.filter(concurso=self.concurso, representacion="rectorado", calidad="titular").update(unidad="")
        self.assertFalse(habilitacion_convocatoria(self.concurso).habilitado)
        self.assertIn("unidad", habilitacion_convocatoria(self.concurso).pendientes_jurado[0])
        Jurado.objects.filter(concurso=self.concurso).update(unidad="Unidad declarada")
        self.concurso.codigo_presupuestario = " "
        self.assertTrue(habilitacion_convocatoria(self.concurso).pendientes_datos)
        self.concurso.codigo_presupuestario = DATOS["codigo_presupuestario"]
        self.concurso.categoria = "1"  # No habilitada para 03.
        self.assertTrue(habilitacion_convocatoria(self.concurso).pendientes_datos)

    def test_habilitacion_no_confia_en_check_con_fojas_invalidas_o_vacias(self):
        self.completar_preparacion()
        self.crear_jurado()
        control = self.control("jurado_personal")
        for referencia in ("", "0", "9/5"):
            ControlDocumental.objects.filter(pk=control.pk).update(fojas=referencia)
            self.assertFalse(habilitacion_convocatoria(self.concurso).habilitado)

    def test_consulta_reutilizable_sin_escrituras_con_fojas_y_pendientes(self):
        self.guardar("acta_inscriptos", fojas="5/8")
        resultado = consultar_documentacion(self.concurso)
        self.assertEqual(resultado.total, 21)
        self.assertEqual([c.requisito for c in resultado.verificados], ["acta_inscriptos"])
        self.assertEqual(resultado.fojas, {"acta_inscriptos": "5/8"})
        self.assertEqual(len(resultado.pendientes), 20)
        self.assertFalse(resultado.habilitacion.habilitado)

    def test_fuera_de_orden_permitido_y_aviso_comunicacion_antes_de_aprobacion(self):
        self.assertEqual(self.guardar("aprobacion_dictamen", fojas="15/18").status_code, 302)
        resultado = consultar_documentacion(self.concurso)
        self.assertTrue(any("comunicación del dictamen" in aviso for aviso in resultado.advertencias))
        self.assertEqual(self.guardar("comunicacion_dictamen").status_code, 302)
        aprobacion = next(aviso for aviso in consultar_documentacion(self.concurso).advertencias
                          if aviso.startswith("Resolución de aprobación"))
        self.assertNotIn("comunicación del dictamen", aprobacion)
        self.concurso.refresh_from_db()
        self.assertEqual((self.concurso.estado, self.concurso.historial.count()), ("preparacion", 1))

    def test_sugerencia_solo_dictamen_valido_sin_cambio_automatico_y_permiso_independiente(self):
        self.guardar("publicacion_convocatoria")
        self.assertIsNone(consultar_documentacion(self.concurso).sugerencia)
        self.guardar("dictamen")
        self.assertIsNone(consultar_documentacion(self.concurso).sugerencia)
        self.guardar("dictamen", fojas="20/22")
        self.assertEqual(consultar_documentacion(self.concurso).sugerencia, EstadoConcurso.CON_DICTAMEN)
        self.concurso.refresh_from_db()
        self.assertEqual(self.concurso.version, 1)
        self.assertEqual(self.concurso.historial.count(), 1)
        self.assertNotContains(self.client.get(self.concurso.get_absolute_url()), "Revisar y confirmar sugerencia de estado")
        url = reverse("concursos:estado", args=[self.concurso.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.login(self.estadista)
        response = self.client.get(url + "?sugerencia=dictamen")
        self.assertEqual(response.context["form"].initial["estado"], EstadoConcurso.CON_DICTAMEN)
        self.concurso.refresh_from_db()
        self.assertEqual(self.concurso.estado, EstadoConcurso.PREPARACION)
        response = self.client.post(url, {"estado": "con_dictamen", "situacion": "normal", "version_esperada": 1,
                                          "justificacion": "Confirmación de prueba"})
        self.assertEqual(response.status_code, 302)
        self.concurso.refresh_from_db()
        self.assertEqual(self.concurso.estado, EstadoConcurso.CON_DICTAMEN)
        self.assertEqual(self.concurso.historial.first().usuario, self.estadista)
        self.assertIsNone(consultar_documentacion(self.concurso).sugerencia)

    def test_permisos_consulta_escritura_y_estado_son_independientes(self):
        control = self.control("vacancia")
        for actor in (self.lector, self.estadista):
            self.login(actor)
            response = self.client.get(self.concurso.get_absolute_url())
            self.assertContains(response, "Control documental")
            self.assertNotContains(response, f'name="control-{control.pk}-verificado"')
            self.assertEqual(self.guardar("vacancia").status_code, 403)
            with self.assertRaises(PermissionDenied):
                actualizar_control(concurso_id=self.concurso.pk, control_id=control.pk,
                                   datos={"verificado": True}, usuario=actor, version_esperada=1)
        self.login(self.sin_permiso)
        self.assertEqual(self.client.get(self.url(control, historial=True)).status_code, 403)
        self.assertEqual(self.guardar("vacancia").status_code, 403)
        self.client.logout()
        self.assertEqual(self.guardar("vacancia").status_code, 302)
        self.assertFalse(self.control("vacancia").verificado)

    def test_acceso_anidado_sin_eliminacion_o_historial_editable(self):
        otro = concursos_services.crear_concurso(datos=DATOS, usuario=self.editor)
        control = self.control("vacancia")
        self.assertEqual(self.client.post(self.url(control, concurso=otro)).status_code, 404)
        self.assertEqual(self.client.get(self.url(control, concurso=otro, historial=True)).status_code, 404)
        self.assertEqual(self.client.delete(self.url(control)).status_code, 405)
        self.assertEqual(self.client.post(self.url(control, historial=True)).status_code, 405)
        self.assertEqual(CambioControlDocumental._meta.default_permissions, ())

    def test_version_obligatoria_y_envios_desactualizados_no_sobrescriben(self):
        control = self.control("vacancia")
        self.assertEqual(self.client.post(self.url(control), {f"control-{control.pk}-verificado": "on"}).status_code, 200)
        self.guardar("vacancia", observaciones="Primera edición")
        response = self.guardar("vacancia", observaciones="Edición vieja", version=1)
        self.assertContains(response, "Otro operador modificó este control")
        self.assertContains(response, "Edición vieja")
        control.refresh_from_db()
        self.assertEqual((control.observaciones, control.version, control.historial.count()), ("Primera edición", 2, 1))

    def test_rollback_si_falla_historial_y_noop_sin_evento_falso(self):
        self.guardar("vacancia", verificado=False)
        self.assertFalse(CambioControlDocumental.objects.exists())
        control = self.control("vacancia")
        with patch("expedientes.services.CambioControlDocumental.objects.create", side_effect=RuntimeError("Falla sintética")):
            with self.assertRaises(RuntimeError):
                actualizar_control(concurso_id=self.concurso.pk, control_id=control.pk,
                                   datos={"verificado": True}, usuario=self.editor, version_esperada=1)
        control.refresh_from_db()
        self.assertFalse(control.verificado)
        self.assertEqual(control.version, 1)

    def test_csrf_sesion_vencida_y_requests_automaticas_no_guardan(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("login"))
        token = client.cookies["csrftoken"].value
        client.post(reverse("login"), {"username": self.editor.username, "password": PASSWORD, "csrfmiddlewaretoken": token})
        self.assertEqual(self.guardar("vacancia", client=client).status_code, 403)
        session_key = self.client.session.session_key
        self.now.return_value = START + timedelta(seconds=1799)
        self.client.get(self.concurso.get_absolute_url())
        self.assertEqual(SessionActivity.objects.get(session_id=session_key).last_activity, START)
        self.now.return_value = START + timedelta(seconds=1800)
        response = self.guardar("vacancia")
        self.assertEqual(response.url, "/ingresar/?expired=1")
        self.assertFalse(self.control("vacancia").verificado)
        self.assertFalse(CambioControlDocumental.objects.exists())

    def test_ui_agrupa_catalogo_y_no_imputa_incumplimiento_a_etapas_futuras(self):
        response = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(response, "Documentación previa pendiente")
        self.assertContains(response, "0 de 21 requisitos completos")
        self.assertContains(response, 'aria-label="Verificado: Certificación de vacancia del cargo"')
        self.assertContains(response, '/control-documental/etapa/#control-documental')
        self.assertContains(response, "No registrado", count=16)
        self.assertContains(response, "Pendiente exigible", count=5)
        self.assertNotContains(response, "Control documental · No disponible")
        self.guardar("vacancia", observaciones="<script>prueba</script>")
        self.assertContains(self.client.get(self.concurso.get_absolute_url()), "&lt;script&gt;prueba&lt;/script&gt;")

    def test_requisitos_se_consultan_compactos_y_se_editan_con_details_nativo(self):
        response = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(response, '<summary>Editar requisito</summary>', count=21)
        self.assertContains(response, 'class="document-control-editor"', count=21)
        self.assertNotContains(response, 'class="document-control-editor" open')
        self.assertContains(response, '0/5 completos')
        self.assertContains(response, '0/3 completos')
        self.assertContains(response, '0/4 completos')
        self.assertContains(response, '0/6 completos')
        self.assertContains(response, '0 de 21 requisitos completos')
        self.assertContains(response, 'id="panel-control-documental"')
        self.assertContains(response, 'name="control-')

    def test_error_documental_reabre_solo_el_requisito_y_conserva_valores(self):
        control = self.control('afectacion_presupuestaria')
        response = self.guardar('afectacion_presupuestaria', fojas='9/2', observaciones='Dato pendiente de corrección')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dato pendiente de corrección')
        self.assertContains(response, 'id="documental-%s"' % control.pk)
        self.assertContains(response, 'class="document-control-editor" open', count=1)
        self.assertContains(response, '<summary>Editar requisito</summary>', count=21)
        self.assertContains(response, 'el inicio no puede superar')
        control.refresh_from_db()
        self.assertEqual(control.version, 1)

    def test_resumen_compacto_fojas_presupuesto_historial_y_solo_lectura(self):
        control = self.control('afectacion_presupuestaria')
        self.guardar('afectacion_presupuestaria', fojas='12/15', observaciones='Afectación registrada')
        response = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(response, 'Fojas:')
        self.assertContains(response, '12/15')
        self.assertContains(response, 'PPAL:')
        self.assertContains(response, 'ACTIV:')
        self.assertContains(response, 'Observaciones registradas')
        self.assertContains(response, reverse('concursos:control_historial', args=[self.concurso.pk, control.pk]))
        self.login(self.lector)
        response = self.client.get(self.concurso.get_absolute_url())
        self.assertNotContains(response, '<summary>Editar requisito</summary>')
        self.assertNotContains(response, f'name="control-{control.pk}-version_esperada"')
        self.assertContains(response, 'Ver información adicional')
        self.assertContains(response, 'Afectación registrada')
        self.assertContains(response, '12/15')

    def test_etapa_manual_exigibilidad_historia_y_retroceso_sin_borrar_controles(self):
        resultado = consultar_documentacion(self.concurso)
        self.assertEqual(len(resultado.pendientes_exigibles), 5)
        self.assertEqual(len(resultado.no_registrados_futuros), 16)
        self.guardar("dictamen", fojas="25/29", observaciones="Registrado anticipadamente")
        url = reverse("concursos:etapa_documental", args=[self.concurso.pk])
        self.assertEqual(self.client.post(url, {"etapa-etapa": "inscripciones", "etapa-version_esperada": 1}).status_code, 302)
        resultado = consultar_documentacion(self.concurso)
        self.assertEqual(len(resultado.pendientes_exigibles), 11)
        self.assertEqual(len(resultado.no_registrados_futuros), 9)
        self.assertContains(self.client.get(self.concurso.get_absolute_url()), "Pendiente exigible", count=11)
        cambio = resultado.seguimiento.historial.get()
        self.assertEqual((cambio.anterior, cambio.nueva, cambio.usuario, cambio.version),
                         ("preparacion", "inscripciones", self.editor, 2))
        actualizar_etapa(concurso_id=self.concurso.pk, etapa="preparacion", usuario=self.editor, version_esperada=2)
        self.assertTrue(self.control("dictamen").completo)
        self.concurso.refresh_from_db()
        self.assertEqual((self.concurso.estado, self.concurso.version, self.concurso.historial.count()), ("preparacion", 1, 1))
        historial = self.client.get(reverse("concursos:etapa_historial", args=[self.concurso.pk]))
        self.assertContains(historial, "Inscripciones")
        self.assertContains(historial, self.editor.username)

    def test_etapa_permiso_validacion_y_version_sin_cambios_silenciosos(self):
        url = reverse("concursos:etapa_documental", args=[self.concurso.pk])
        for entrada in ({"etapa-etapa": "inventada", "etapa-version_esperada": 1}, {"etapa-etapa": "oposicion"}):
            self.assertEqual(self.client.post(url, entrada).status_code, 200)
        seguimiento = SeguimientoDocumental.objects.get(concurso=self.concurso)
        self.assertFalse(seguimiento.historial.exists())
        with self.assertRaises(ValidationError):
            actualizar_etapa(concurso_id=self.concurso.pk, etapa="inventada", usuario=self.editor, version_esperada=1)
        actualizar_etapa(concurso_id=self.concurso.pk, etapa="oposicion", usuario=self.editor, version_esperada=1)
        response = self.client.post(url, {"etapa-etapa": "finalizacion", "etapa-version_esperada": 1})
        self.assertContains(response, "Otro operador modificó la etapa documental")
        self.assertContains(response, 'value="finalizacion" selected')
        seguimiento.refresh_from_db()
        self.assertEqual((seguimiento.etapa, seguimiento.version, seguimiento.historial.count()), ("oposicion", 2, 1))
        for actor in (self.lector, self.estadista):
            self.login(actor)
            self.assertEqual(self.client.post(url, {"etapa-etapa": "finalizacion", "etapa-version_esperada": 2}).status_code, 403)
            self.assertNotContains(self.client.get(self.concurso.get_absolute_url()), 'name="etapa-etapa"')
            with self.assertRaises(PermissionDenied):
                actualizar_etapa(concurso_id=self.concurso.pk, etapa="finalizacion", usuario=actor, version_esperada=2)

    def test_etapa_csrf_vencimiento_y_rollback_historial(self):
        url = reverse("concursos:etapa_documental", args=[self.concurso.pk])
        client = Client(enforce_csrf_checks=True)
        self.login(self.editor, client)
        self.assertEqual(client.post(url, {"etapa-etapa": "finalizacion", "etapa-version_esperada": 1}).status_code, 403)
        with patch("expedientes.services.CambioEtapaDocumental.objects.create", side_effect=RuntimeError("Falla sintética")):
            with self.assertRaises(RuntimeError):
                actualizar_etapa(concurso_id=self.concurso.pk, etapa="oposicion", usuario=self.editor, version_esperada=1)
        seguimiento = SeguimientoDocumental.objects.get(concurso=self.concurso)
        self.assertEqual((seguimiento.etapa, seguimiento.version), ("preparacion", 1))
        self.now.return_value = START + timedelta(seconds=1800)
        self.assertEqual(self.client.post(url, {"etapa-etapa": "finalizacion", "etapa-version_esperada": 1}).url,
                         "/ingresar/?expired=1")
        seguimiento.refresh_from_db()
        self.assertEqual(seguimiento.etapa, "preparacion")

    def test_convocatoria_21_orden_y_notificacion_general_sin_seis_checks_individuales(self):
        response = self.client.get(self.concurso.get_absolute_url())
        grupos = response.context["secciones_documentales"]
        self.assertEqual(len(grupos), 5)
        convocatoria = next(g for g in grupos if g["codigo"] == "convocatoria")
        self.assertEqual([(f["numero"], f["requisito"].codigo) for f in convocatoria["filas"]],
                         [(6, "publicacion_convocatoria"), (7, "oficio_apunsj"), (8, "notificacion_jurados")])
        filas = [f for g in grupos for f in g["filas"]]
        self.assertEqual([f["numero"] for f in filas], list(range(1, 22)))
        self.assertEqual([f["requisito"].codigo for f in filas], [r.codigo for r in REQUISITOS])
        self.assertContains(response, "Este único check acredita las notificaciones correspondientes a los seis jurados titulares y suplentes.")
        self.assertEqual(self.concurso.controles_documentales.filter(requisito="notificacion_jurados").count(), 1)

    def test_nuevos_controles_exigibles_desde_convocatoria_sin_bloquear_proyecto_o_exigir_veedor(self):
        nuevos = {"oficio_apunsj", "notificacion_jurados"}
        resultado = consultar_documentacion(self.concurso)
        self.assertTrue(nuevos <= {r.codigo for r in resultado.no_registrados_futuros})
        self.completar_preparacion()
        self.crear_jurado()
        self.assertFalse(self.concurso.veedors.exists())
        self.assertTrue(habilitacion_convocatoria(self.concurso).habilitado)
        for version, etapa in enumerate(["convocatoria", "inscripciones", "oposicion", "finalizacion"], start=1):
            actualizar_etapa(concurso_id=self.concurso.pk, etapa=etapa, usuario=self.editor, version_esperada=version)
            resultado = consultar_documentacion(self.concurso)
            self.assertTrue(nuevos <= {r.codigo for r in resultado.pendientes_exigibles})
            self.assertFalse(nuevos & {r.codigo for r in resultado.no_registrados_futuros})
            self.assertTrue(resultado.habilitacion.habilitado)
        self.assertFalse(self.control("oficio_apunsj").verificado)
        self.assertFalse(self.control("notificacion_jurados").verificado)

    def test_convocatoria_cualquier_orden_sin_fojas_ni_advertencias_de_secuencia(self):
        for codigo in ("notificacion_jurados", "oficio_apunsj", "publicacion_convocatoria"):
            control = self.control(codigo)
            response = self.client.get(self.concurso.get_absolute_url())
            self.assertNotContains(response, f'name="control-{control.pk}-fojas"')
            self.assertEqual(self.guardar(codigo, observaciones="Control documental manual").status_code, 302)
            control.refresh_from_db()
            self.assertTrue(control.completo)
            self.assertEqual(control.fojas, "")
            self.assertEqual(consultar_documentacion(self.concurso).advertencias, ())
            control.fojas = "5"
            with self.assertRaises(ValidationError):
                control.full_clean()
        self.assertEqual(self.guardar("acta_inscriptos", fojas="20").status_code, 302)
        self.assertEqual(consultar_documentacion(self.concurso).advertencias, ())
        self.assertEqual(self.guardar("envio_acta").status_code, 302)
        self.assertEqual(consultar_documentacion(self.concurso).advertencias, ())
