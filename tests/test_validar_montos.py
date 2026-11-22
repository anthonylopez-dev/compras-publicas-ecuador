from datetime import date
from decimal import Decimal
import unittest

from scripts.validar_montos import Observacion, ajustar, medir, particion


class ValidacionMontosTest(unittest.TestCase):
    def test_corte_respeta_disponibilidad_y_separa_mes_objetivo(self):
        corte = date(2025, 7, 1)
        junio = date(2025, 6, 1)
        agosto = date(2025, 8, 1)
        disponible = Observacion(junio, date(2025, 6, 30), "871410011", Decimal(10))
        publicado_en_el_corte = Observacion(junio, corte, "871410011", Decimal(20))
        abierto_en_el_mes = Observacion(corte, agosto, None, Decimal(30))
        abierto_el_mes_siguiente = Observacion(agosto, agosto, None, Decimal(40))

        historial, evaluacion = particion(
            [publicado_en_el_corte, abierto_en_el_mes, disponible, abierto_el_mes_siguiente], corte,
        )

        self.assertEqual(historial, [disponible])
        self.assertEqual(evaluacion, [abierto_en_el_mes])

    def test_rango_por_cpc_requiere_quince_contratos_del_mismo_codigo(self):
        dia = date(2025, 6, 1)
        historial = (
            [Observacion(dia, dia, "871410011", Decimal(10))] * 15
            + [Observacion(dia, dia, "871410018", Decimal(20))] * 14
            + [Observacion(dia, dia, None, Decimal(30))]
        )

        general, por_cpc = ajustar(historial)

        self.assertEqual(por_cpc, {"871410011": [10, 10, 10]})
        self.assertEqual(por_cpc.get("871410018", general), general)
        self.assertEqual(por_cpc.get(None, general), general)

    def test_puntuacion_penaliza_anchura_y_distancia_fuera_del_rango(self):
        rango = (Decimal(10), Decimal(20), Decimal(30))

        resultado = medir([(Decimal(10), rango), (Decimal(35), rango), (Decimal(5), rango)])

        self.assertEqual(resultado, (Decimal(40) / 3, 1, 20, Decimal(100) / 3))
