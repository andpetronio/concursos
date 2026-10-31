"""Los nombres de descarga deben describir el documento sin depender de datos vivos."""
from types import SimpleNamespace
from django.test import SimpleTestCase

from .views import nombre_descarga


class NombresDescargaTests(SimpleTestCase):
    @staticmethod
    def registro(tipo='designacion', expediente='17-697-2024', pk=22):
        return SimpleNamespace(tipo=tipo, pk=pk, concurso_id=7,
                               instantanea={'concurso': {'expediente': expediente}})

    def test_nombres_por_tipo_y_expediente(self):
        for tipo, esperado in (
            ('convocatoria', 'proyecto-resolucion-convocatoria'),
            ('designacion', 'proyecto-resolucion-designacion'),
            ('dictamen', 'proyecto-resolucion-aprobacion-dictamen'),
            ('sorteo_acta', 'acta-sorteo-temas'),
            ('apunsj', 'oficio-solicitud-veedor-apunsj'),
            ('elecciones', 'nota-eleccion-representantes-personal'),
            ('desierto_inscriptos', 'proyecto-resolucion-concurso-desierto'),
        ):
            with self.subTest(tipo=tipo):
                self.assertEqual(
                    nombre_descarga(self.registro(tipo)),
                    f'{esperado}-exp-17-697-2024-borrador-22.docx',
                )

    def test_zip_notificaciones_y_descarga_individual(self):
        registro = self.registro('jurados')
        self.assertEqual(nombre_descarga(registro),
                         'notificaciones-jurados-exp-17-697-2024-borrador-22.zip')
        self.assertEqual(nombre_descarga(registro, indice=3),
                         'notificaciones-jurados-exp-17-697-2024-borrador-22-jurado-3.docx')

    def test_nombre_jurado_con_rol_y_calidad_del_registro_historico(self):
        registro = self.registro('jurados')
        registro.instantanea['archivos'] = [
            {'indice': 3, 'nombre': 'notificacion-jurado-3-personal-suplente-exp-17-697-2024.docx',
             'representacion': 'personal', 'calidad': 'suplente'}]
        self.assertEqual(nombre_descarga(registro, indice=3),
                         'notificaciones-jurados-exp-17-697-2024-borrador-22-personal-suplente.docx')

    def test_snapshot_inmutable_y_nombre_sanitizado(self):
        registro = self.registro(expediente=' ../../EXp 01/23; \r\n documento \"')
        nombre = nombre_descarga(registro)
        self.assertTrue(nombre.startswith('proyecto-resolucion-designacion-exp-'))
        self.assertNotIn('..', nombre)
        self.assertNotIn('/', nombre)
        self.assertNotIn('\r', nombre)
        self.assertNotIn('\n', nombre)
        self.assertNotIn('\"', nombre)

    def test_registros_historicos_sin_codigo_o_expediente(self):
        self.assertEqual(nombre_descarga(self.registro('solicitud_jurados_rectorado')),
                         'oficio-solicitud-jurados-rectorado-exp-17-697-2024-borrador-22.docx')
        registro = self.registro('tipo_retirado', expediente='')
        self.assertEqual(nombre_descarga(registro),
                         'documento-historico-exp-concurso-7-borrador-22.docx')
