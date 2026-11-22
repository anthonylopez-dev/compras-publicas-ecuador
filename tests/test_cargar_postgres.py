from datetime import date
from decimal import Decimal
import unittest

from scripts.auditar_sercop import MODALIDAD
from scripts.cargar_postgres import COLUMNAS, transformar_corte


class TransformarPostgresTest(unittest.TestCase):
    def test_contrato_y_proveedor_mantienen_sus_propias_claves(self):
        proceso = {
            "ocid": "ocds-ejemplo",
            "buyer": {"id": "E1", "name": "  Entidad   A "},
            "tender": {
                "procurementMethodDetails": MODALIDAD,
                "tenderPeriod": {"startDate": "2025-12-31T23:00:00-05:00"},
                "items": [{"classification": {"scheme": "CPC", "id": "871410011"}}],
            },
            "awards": [{
                "id": "A1",
                "date": "2026-01-10T12:00:00-05:00",
                "suppliers": [{"id": "P1", "name": "Taller A"}, {"id": "P2", "name": "Taller B"}],
            }],
            "contracts": [{
                "id": "C1", "awardID": "A1", "dateSigned": "2026-02-05",
                "value": {"amount": Decimal("18700.151"), "currency": "USD"},
            }],
        }
        tablas = {nombre: {} for nombre in COLUMNAS}
        corte = {"mes": "2025-12", "total": 1, "sha256": "a" * 64}

        calidad = transformar_corte(corte, [{"releases": [proceso]}], tablas)

        self.assertEqual(calidad, (date(2025, 12, 1), 1, 1, 0, 0, 1))
        self.assertEqual(tablas["proceso"]["ocds-ejemplo"][6], "Entidad A")
        self.assertEqual(len(tablas["adjudicacion_proveedor"]), 2)
        contrato, = tablas["contrato"].values()
        self.assertEqual(contrato[2:4], ("A1", date(2026, 2, 5)))
        self.assertEqual(contrato[-2:], (Decimal("18700.151"), "USD"))

        with self.assertRaisesRegex(ValueError, "repetido"):
            transformar_corte(corte, [{"releases": [proceso]}], tablas)
