import unittest

from scripts.auditar_sercop import MODALIDAD
from scripts.preparar_piloto import preparar_corte


class PrepararPilotoTest(unittest.TestCase):
    def test_conserva_el_denominador_y_cuenta_un_proceso_con_varios_items(self):
        licitacion = {
            "procurementMethodDetails": MODALIDAD,
            "tenderPeriod": {"startDate": "2025-01-31T23:00:00-05:00"},
            "items": [
                {"classification": {"scheme": "CPC", "id": "871410018"}},
                {"classification": {"scheme": "CPC", "id": "871410011"}},
            ],
        }
        del_rubro = {"ocid": "A", "tender": licitacion, "buyer": {"id": "1", "name": "Entidad A"}}
        sin_cpc = {"ocid": "B", "tender": {**licitacion, "items": []}}
        paquetes = [{"releases": [fila]} for fila in (del_rubro, sin_cpc)]

        corte, procesos, ocids = preparar_corte("2025-01", paquetes, 2, "hash")

        self.assertEqual((corte["total"], corte["con_cpc"]), (2, 1))
        self.assertEqual(ocids, {"A", "B"})
        self.assertEqual(len(procesos), 1)
        self.assertEqual(procesos[0]["apertura"], "2025-01-31")
        self.assertEqual(procesos[0]["cpc"], ["871410011", "871410018"])

        with self.assertRaisesRegex(ValueError, "total distinto al portal"):
            preparar_corte("2025-01", paquetes, 3, "hash")
