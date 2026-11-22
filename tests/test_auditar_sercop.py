import unittest

from scripts.auditar_sercop import perfilar


class PerfilSercopTest(unittest.TestCase):
    def test_piloto_usa_fecha_de_apertura_y_cuenta_el_ocid_una_vez(self):
        item = {"classification": {"scheme": "CPC", "id": "871410018"}}
        fila = {
            "ocid": "ocds-ejemplo-A",
            "date": "2025-11-15T00:00:00-05:00",
            "buyer": {"id": "ENTIDAD-A"},
            "tender": {
                "tenderPeriod": {"startDate": "2025-10-01T00:00:00-05:00"},
                "items": [item, item],
                "numberOfTenderers": 0,
            },
        }
        paquete = {"releases": [fila]}
        perfil, ocids, entidades = perfilar([paquete, paquete], "2025-10")

        self.assertEqual(perfil["entregas"], 2)
        self.assertEqual(perfil["procesos_unicos"], 1)
        self.assertEqual(perfil["fecha_de_entrega_en_mes"], 0)
        self.assertEqual(perfil["con_numero_de_oferentes"], 2)
        self.assertEqual(perfil["procesos_piloto"], 1)
        self.assertEqual(ocids, {"ocds-ejemplo-A"})
        self.assertEqual(entidades, {"ENTIDAD-A"})

        perfil_otro_mes, _, _ = perfilar([paquete], "2025-11")
        self.assertEqual(perfil_otro_mes["procesos_piloto"], 0)
