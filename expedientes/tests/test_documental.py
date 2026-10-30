from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from concursos import services as concursos_services
from concursos.choices import EstadoConcurso, SituacionAdministrativa
from concursos.tests.test_concursos import DATOS, PASSWORD, START
from core.models import SessionActivity
from participantes.models import Aspirante, Jurado, Persona

from expedientes.catalogo import REQUISITOS
from expedientes.models import CambioControlDocumental, CambioEtapaDocumental, ControlDocumental, SeguimientoDocumental
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

    def test_avance_automatico_solo_al_completar_quinto_previo_sin_convocar(self):
        for requisito in REQUISITOS[:4]:
            respuesta = self.guardar(requisito.codigo, fojas="12/15" if requisito.requiere_foja else "")
            self.assertEqual(respuesta.status_code, 302)
            self.assertEqual(self.concurso.seguimiento_documental.etapa, "preparacion")
        seguimiento = SeguimientoDocumental.objects.get(concurso=self.concurso)
        self.assertEqual((seguimiento.etapa, seguimiento.version), ("preparacion", 1))
        self.assertFalse(seguimiento.historial.exists())

        self.assertEqual(self.guardar("vacancia").status_code, 302)
        seguimiento.refresh_from_db()
        evento = seguimiento.historial.get()
        self.assertEqual((seguimiento.etapa, seguimiento.version), ("convocatoria", 2))
        self.assertEqual((evento.origen, evento.anterior, evento.nueva, evento.usuario),
                         (CambioEtapaDocumental.Origen.AUTOMATICO, "preparacion", "convocatoria", self.editor))
        self.assertEqual(CambioControlDocumental.objects.count(), 5)
        self.assertEqual(len(consultar_documentacion(self.concurso).pendientes_exigibles), 3)
        self.concurso.refresh_from_db()
        self.assertEqual((self.concurso.estado, self.concurso.version, self.concurso.historial.count()),
                         ("preparacion", 1, 1))
        self.assertFalse(habilitacion_convocatoria(self.concurso).habilitado)  # Todavía faltan los jurados.
        historial = self.client.get(reverse("concursos:etapa_historial", args=[self.concurso.pk]))
        self.assertContains(historial, "Automático")

    def test_autoguardado_actualiza_etapa_contadores_y_estados_sin_refrescar(self):
        for requisito in REQUISITOS[:4]:
            self.guardar(requisito.codigo, fojas="5" if requisito.requiere_foja else "")
        control = self.control("vacancia")
        respuesta = self.client.post(
            self.url(control), {
                f"control-{control.pk}-version_esperada": control.version,
                f"control-{control.pk}-verificado": "on",
            }, HTTP_X_REQUESTED_WITH="XMLHttpRequest", HTTP_ACCEPT="application/json",
        )
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos["etapa_documental"], {
            "codigo": "convocatoria", "nombre": "Convocatoria", "version": 2,
        })
        self.assertEqual(datos["totales"]["pendientes"], 3)
        siguiente = self.control("publicacion_convocatoria")
        self.assertEqual(datos["estados_controles"][str(siguiente.pk)]["estado"], "Pendiente exigible")
        self.assertEqual(datos["totales"]["secciones"]["preparacion"]["completos"], 5)
        self.assertIn('data-document-stage-name', self.client.get(self.concurso.get_absolute_url()).content.decode())
        self.assertIn("Documentación previa completa", datos["habilitacion_html"])
        self.assertIn("Todavía faltan otros datos o jurados", datos["habilitacion_html"])

    def test_rollback_manual_respeta_decision_sin_reavance_ni_retroceso_automatico(self):
        self.completar_preparacion()
        seguimiento = SeguimientoDocumental.objects.get(concurso=self.concurso)
        self.assertEqual(seguimiento.etapa, "convocatoria")
        actualizar_etapa(concurso_id=self.concurso.pk, etapa="preparacion", usuario=self.editor,
                         version_esperada=seguimiento.version)
        control = self.control("vacancia")
        self.guardar("vacancia", verificado=False)
        self.guardar("vacancia")
        seguimiento.refresh_from_db()
        self.assertEqual((seguimiento.etapa, seguimiento.version), ("preparacion", 3))
        self.assertEqual(list(seguimiento.historial.values_list("origen", flat=True)),
                         [CambioEtapaDocumental.Origen.MANUAL, CambioEtapaDocumental.Origen.AUTOMATICO])
        # No retroceder al faltar requisitos de etapas ya alcanzadas.
        actualizar_etapa(concurso_id=self.concurso.pk, etapa="convocatoria", usuario=self.editor,
                         version_esperada=seguimiento.version)
        self.guardar("vacancia", verificado=False)
        seguimiento.refresh_from_db()
        self.assertEqual(seguimiento.etapa, "convocatoria")

    def test_historicos_completos_no_avanzan_por_editar_observaciones(self):
        for requisito in REQUISITOS[:5]:
            ControlDocumental.objects.filter(concurso=self.concurso, requisito=requisito.codigo).update(
                verificado=True, fojas="9" if requisito.requiere_foja else "",
            )
        self.guardar("vacancia", observaciones="Corrección posterior")
        seguimiento = SeguimientoDocumental.objects.get(concurso=self.concurso)
        self.assertEqual((seguimiento.etapa, seguimiento.version, seguimiento.historial.count()),
                         ("preparacion", 1, 0))

    def test_si_falla_historial_de_avance_se_revierte_el_quinto_documento(self):
        for requisito in REQUISITOS[:4]:
            self.guardar(requisito.codigo, fojas="5" if requisito.requiere_foja else "")
        control = self.control("vacancia")
        with patch("expedientes.services.CambioEtapaDocumental.objects.create",
                   side_effect=RuntimeError("Falla de bitácora de etapa")):
            with self.assertRaisesMessage(RuntimeError, "Falla de bitácora de etapa"):
                actualizar_control(
                    concurso_id=self.concurso.pk, control_id=control.pk,
                    datos={"verificado": True}, usuario=self.editor, version_esperada=control.version,
                )
        control.refresh_from_db()
        seguimiento = SeguimientoDocumental.objects.get(concurso=self.concurso)
        self.assertEqual((control.verificado, control.version), (False, 1))
        self.assertFalse(control.historial.exists())
        self.assertEqual((seguimiento.etapa, seguimiento.version, seguimiento.historial.count()),
                         ("preparacion", 1, 0))

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
        historial = self.client.get(self.url(control, historial=True))
        self.assertContains(historial, "Antes · PPAL Sin registrar / ACTIV Sin registrar")
        self.assertContains(historial, "Después · PPAL 01 / ACTIV 02")
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
        self.assertEqual(consultar_documentacion(self.concurso).sugerencia, EstadoConcurso.CONVOCADO)
        self.guardar("dictamen")
        self.assertEqual(consultar_documentacion(self.concurso).sugerencia, EstadoConcurso.CONVOCADO)
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

    def crear_aspirante_sintetico(self):
        persona = Persona.objects.create(
            apellido="Prueba", nombre="Inscriptor", dni="30123456",
            creado_por=self.editor, actualizado_por=self.editor,
        )
        return Aspirante.objects.create(
            concurso=self.concurso, persona=persona,
            creado_por=self.editor, actualizado_por=self.editor,
        )

    def test_cuatro_actuaciones_sugieren_estados_sin_guardarlos(self):
        self.crear_aspirante_sintetico()
        for codigo, fojas, esperado in (
            ("publicacion_convocatoria", "", EstadoConcurso.CONVOCADO),
            ("acta_inscriptos", "12/14", EstadoConcurso.EN_CURSO),
            ("dictamen", "20", EstadoConcurso.CON_DICTAMEN),
            ("designacion", "40/42", EstadoConcurso.FINALIZADO),
        ):
            with self.subTest(codigo=codigo):
                respuesta = self.guardar(codigo, fojas=fojas)
                self.assertEqual(respuesta.status_code, 302)
                documentacion = consultar_documentacion(self.concurso)
                self.assertEqual(documentacion.sugerencia, esperado)
                self.assertEqual(documentacion.detalle_sugerencia.requisito, codigo)
                self.concurso.refresh_from_db()
                self.assertEqual(self.concurso.estado, EstadoConcurso.PREPARACION)
                self.assertEqual(self.concurso.historial.count(), 1)
                self.login(self.estadista)
                form = self.client.get(reverse("concursos:estado", args=[self.concurso.pk]),
                                       {"sugerencia": codigo}).context["form"]
                self.assertEqual(form.initial["estado"], esperado)
                self.assertIn(fojas or documentacion.detalle_sugerencia.nombre_documento,
                              form.initial["justificacion"])
                self.login(self.editor)

    def test_sin_inscriptos_no_infiere_desierto_ni_sugiere_en_curso(self):
        self.guardar("acta_inscriptos", fojas="4/5")
        documentacion = consultar_documentacion(self.concurso)
        self.assertIsNone(documentacion.sugerencia)
        response = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(response, "Acta de inscriptos verificada, sin aspirantes cargados")
        self.assertContains(response, "tramitá la declaración de concurso desierto")
        self.crear_aspirante_sintetico()
        self.assertEqual(consultar_documentacion(self.concurso).sugerencia, EstadoConcurso.EN_CURSO)

    def test_foja_incompleta_no_habilita_sugerencia_y_estado_manual_se_respeta(self):
        self.crear_aspirante_sintetico()
        self.guardar("dictamen")
        self.assertIsNone(consultar_documentacion(self.concurso).sugerencia)
        self.guardar("dictamen", fojas="5")
        self.assertEqual(consultar_documentacion(self.concurso).sugerencia, EstadoConcurso.CON_DICTAMEN)
        concursos_services.cambiar_estado(
            pk=self.concurso.pk, estado=EstadoConcurso.FINALIZADO,
            situacion=SituacionAdministrativa.NORMAL,
            justificacion="Finalización manual", usuario=self.estadista, version_esperada=1,
        )
        self.concurso.refresh_from_db()
        self.assertIsNone(consultar_documentacion(self.concurso).sugerencia)
        self.login(self.estadista)
        estado = self.client.get(reverse("concursos:estado", args=[self.concurso.pk]),
                                {"sugerencia": "dictamen"})
        self.assertEqual(estado.context["form"].initial["estado"], EstadoConcurso.FINALIZADO)
        self.assertNotIn("justificacion", estado.context["form"].initial)

    def test_impugnado_o_suspendido_no_recibe_sugerencia_y_conserva_cambios_manuales(self):
        self.guardar("publicacion_convocatoria")
        for situacion in (SituacionAdministrativa.IMPUGNADO, SituacionAdministrativa.SUSPENDIDO):
            self.concurso.refresh_from_db()
            concursos_services.cambiar_estado(
                pk=self.concurso.pk, estado=self.concurso.estado,
                situacion=situacion, justificacion="Revisión manual",
                usuario=self.estadista, version_esperada=self.concurso.version,
            )
            self.concurso.refresh_from_db()
            self.assertIsNone(consultar_documentacion(self.concurso).sugerencia)
        concursos_services.cambiar_estado(
            pk=self.concurso.pk, estado=EstadoConcurso.PREPARACION,
            situacion=SituacionAdministrativa.NORMAL, justificacion="Se levantó la suspensión",
            usuario=self.estadista, version_esperada=self.concurso.version,
        )
        self.concurso.refresh_from_db()
        self.assertEqual(consultar_documentacion(self.concurso).sugerencia, EstadoConcurso.CONVOCADO)

    def test_ajax_muestra_sugerencia_tras_guardar_y_respeta_permiso(self):
        control = self.control("publicacion_convocatoria")
        prefijo = f"control-{control.pk}-"
        respuesta = self.client.post(self.url(control), {
            prefijo + "version_esperada": control.version,
            prefijo + "verificado": "on",
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest", HTTP_ACCEPT="application/json")
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.json()["sugerencia_html"]
        self.assertEqual(respuesta.json()["sugerencia"]["requisito"], "publicacion_convocatoria")
        self.assertIsNone(respuesta.json()["sugerencia"]["url"])
        self.assertIn("Convocado", html)
        self.assertNotIn("Revisar y confirmar sugerencia de estado", html)
        self.concurso.refresh_from_db()
        self.assertEqual(self.concurso.estado, EstadoConcurso.PREPARACION)
        self.login(self.estadista)
        detalle = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(detalle, "?sugerencia=publicacion_convocatoria")
        self.assertContains(detalle, "Revisar y confirmar sugerencia de estado")
        estado = self.client.get(reverse("concursos:estado", args=[self.concurso.pk]),
                                {"sugerencia": "publicacion_convocatoria"})
        self.assertEqual(estado.context["form"].initial["estado"], EstadoConcurso.CONVOCADO)
        self.assertIn("Constancia de publicación", estado.context["form"].initial["justificacion"])
        confirmado = self.client.post(reverse("concursos:estado", args=[self.concurso.pk]), {
            "estado": EstadoConcurso.CONVOCADO, "situacion": SituacionAdministrativa.NORMAL,
            "version_esperada": self.concurso.version,
            "justificacion": estado.context["form"].initial["justificacion"],
        })
        self.assertEqual(confirmado.status_code, 302)
        self.concurso.refresh_from_db()
        self.assertEqual(self.concurso.estado, EstadoConcurso.CONVOCADO)
        self.assertIn("Constancia de publicación", self.concurso.historial.first().justificacion)
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
        self.assertContains(response, "<span data-document-complete-count>0</span> de 21 requisitos completos")
        self.assertContains(response, 'aria-label="Verificado: Certificación de vacancia del cargo"')
        self.assertContains(response, '/control-documental/etapa/#control-documental')
        self.assertContains(response, 'class="document-control-status document-control-status--no-registrado"', count=16)
        self.assertContains(response, "Pendiente exigible", count=5)
        self.assertNotContains(response, "Control documental · No disponible")
        self.guardar("vacancia", observaciones="<script>prueba</script>")
        self.assertContains(self.client.get(self.concurso.get_absolute_url()), "&lt;script&gt;prueba&lt;/script&gt;")

    def test_requisitos_se_verifican_con_interruptor_y_campo_fojas_condicional(self):
        response = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(response, 'class="document-toggle-form"', count=21)
        self.assertContains(response, 'class="document-verification-toggle"', count=21)
        self.assertContains(response, 'data-document-auto-feedback', count=21)
        self.assertContains(response, 'data-document-fallback-save', count=21)
        self.assertContains(response, 'js/document-autosave.js')
        self.assertContains(response, 'Guardar cambios', count=21)
        self.assertNotContains(response, 'document-toggle-save">Guardar</button>')
        self.assertContains(response, 'class="document-control-revealed"', count=12)
        self.assertContains(response, 'class="document-control-notes"', count=21)
        self.assertNotContains(response, '<summary>Editar requisito</summary>')
        self.assertContains(response, '0/5 completos')
        self.assertContains(response, '0/3 completos')
        self.assertContains(response, '0/4 completos')
        self.assertContains(response, '0/6 completos')
        self.assertContains(response, '<span data-document-complete-count>0</span> de 21 requisitos completos')
        self.assertContains(response, 'id="panel-control-documental"')
        self.assertContains(response, 'name="control-')

    def test_guardado_automatico_ajax_sin_foja_y_resumen_real(self):
        control = self.control("vacancia")
        datos = {f"control-{control.pk}-version_esperada": control.version,
                 f"control-{control.pk}-verificado": "on"}
        respuesta = self.client.post(self.url(control), datos,
                                    HTTP_X_REQUESTED_WITH="XMLHttpRequest", HTTP_ACCEPT="application/json")
        self.assertEqual(respuesta.status_code, 200)
        body = respuesta.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["version"], 2)
        self.assertEqual(body["estado"], "Verificado")
        self.assertEqual(body["totales"]["completos"], 1)
        self.assertEqual(body["totales"]["secciones"]["preparacion"], {"completos": 1, "total": 5})
        self.assertIn("Documentación previa pendiente", body["habilitacion_html"])
        control.refresh_from_db()
        self.assertTrue(control.verificado)
        self.assertEqual(control.historial.count(), 1)
        # No-op: no inventa una segunda verificación ni un nuevo evento.
        datos[f"control-{control.pk}-version_esperada"] = 2
        otra = self.client.post(self.url(control), datos,
                               HTTP_X_REQUESTED_WITH="XMLHttpRequest", HTTP_ACCEPT="application/json")
        self.assertEqual(otra.status_code, 200)
        self.assertEqual(otra.json()["version"], 2)
        self.assertEqual(control.historial.count(), 1)

    def test_guardado_automatico_ajax_fojas_presupuesto_y_error(self):
        control = self.control("afectacion_presupuestaria")
        prefix = f"control-{control.pk}-"
        datos = {prefix + "version_esperada": 1, prefix + "verificado": "on",
                 prefix + "fojas": "9/2", prefix + "partida_principal": "1",
                 prefix + "actividad_presupuestaria": "02"}
        invalida = self.client.post(self.url(control), datos,
                                    HTTP_X_REQUESTED_WITH="XMLHttpRequest", HTTP_ACCEPT="application/json")
        self.assertEqual(invalida.status_code, 400)
        self.assertIn("fojas", invalida.json()["errores"])
        control.refresh_from_db()
        self.assertEqual(control.version, 1)
        self.assertEqual(control.historial.count(), 0)
        datos[prefix + "fojas"] = "12/15"
        correcta = self.client.post(self.url(control), datos,
                                    HTTP_X_REQUESTED_WITH="XMLHttpRequest", HTTP_ACCEPT="application/json")
        self.assertEqual(correcta.status_code, 200)
        self.assertEqual(correcta.json()["partida_principal"], "01")
        self.assertEqual(correcta.json()["version"], 2)
        control.refresh_from_db()
        self.assertTrue(control.completo)
        self.assertEqual(control.historial.count(), 1)
        conflicto = self.client.post(self.url(control), datos,
                                     HTTP_X_REQUESTED_WITH="XMLHttpRequest", HTTP_ACCEPT="application/json")
        self.assertEqual(conflicto.status_code, 409)
        self.assertIn("Otro operador", str(conflicto.json()))
        self.assertEqual(control.historial.count(), 1)

    def test_guardado_automatico_respeta_permiso_y_fallback_clasico(self):
        control = self.control("vacancia")
        datos = {f"control-{control.pk}-version_esperada": 1,
                 f"control-{control.pk}-verificado": "on"}
        normal = self.client.post(self.url(control), datos)
        self.assertEqual(normal.status_code, 302)
        self.login(self.lector)
        respuesta = self.client.post(self.url(control), datos,
                                    HTTP_X_REQUESTED_WITH="XMLHttpRequest", HTTP_ACCEPT="application/json")
        self.assertEqual(respuesta.status_code, 403)

    def test_error_documental_revela_fojas_y_conserva_valores(self):
        control = self.control('afectacion_presupuestaria')
        response = self.guardar('afectacion_presupuestaria', fojas='9/2', observaciones='Dato pendiente de corrección')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dato pendiente de corrección')
        self.assertContains(response, 'id="documental-%s"' % control.pk)
        self.assertContains(response, 'class="document-toggle-form document-toggle-form--errors"', count=1)
        self.assertContains(response, 'class="document-verification-toggle"', count=21)
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
        self.assertNotContains(response, 'class="document-verification-toggle"')
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
        for etapa in ["convocatoria", "inscripciones", "oposicion", "finalizacion"]:
            seguimiento = SeguimientoDocumental.objects.get(concurso=self.concurso)
            if seguimiento.etapa != etapa:
                actualizar_etapa(concurso_id=self.concurso.pk, etapa=etapa, usuario=self.editor,
                                 version_esperada=seguimiento.version)
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
