"""Compara rangos de monto contractual en seis cortes mensuales del piloto."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import mean, quantiles

from scripts.auditar_sercop import filas_del_corte, leer_zip
from scripts.capturar_sercop import ANIO, leer_crudo
from scripts.cargar_postgres import fecha
from scripts.exportar_tableros import leer_piloto


MINIMO_CONTRATOS = 15


@dataclass(frozen=True)
class Observacion:
    apertura: date
    disponible: date
    cpc: str | None
    monto: Decimal


def leer_observaciones():
    datos = leer_piloto()
    procesos = {p["ocid"]: p for p in datos["procesos"]}
    contratos = [
        c for c in datos["contratos"]
        if c["firma"] and c["firma"] >= procesos[c["ocid"]]["apertura"]
    ]
    requeridos = {c["ocid"] for c in contratos}
    publicaciones = {}
    for corte in datos["cortes"]:
        crudo = {"mes": f"{ANIO}-{corte['mes']:02}", "sha256": corte["sha256_zip"]}
        for fila in filas_del_corte(leer_zip(leer_crudo(crudo))):
            if fila["ocid"] in requeridos and (publicacion := fecha(fila.get("date"))):
                publicaciones[fila["ocid"]] = publicacion

    if faltantes := requeridos - publicaciones.keys():
        raise ValueError(f"Falta la fecha de la entrega SERCOP para {len(faltantes)} procesos con contrato")

    observaciones = []
    for contrato in contratos:
        ocid = contrato["ocid"]
        proceso = procesos[ocid]
        codigos = proceso["cpc"]
        disponible = max(contrato["firma"], publicaciones[ocid])
        observaciones.append(Observacion(
            proceso["apertura"], disponible, codigos[0] if len(codigos) == 1 else None,
            contrato["monto"],
        ))
    return observaciones


def particion(observaciones, inicio):
    historial = [o for o in observaciones if o.apertura < inicio and o.disponible < inicio]
    evaluacion = [o for o in observaciones if o.apertura.replace(day=1) == inicio]
    return historial, evaluacion


def ajustar(historial):
    if len(historial) < MINIMO_CONTRATOS:
        raise ValueError(f"El modelo general requiere {MINIMO_CONTRATOS} contratos históricos")
    general = quantiles([o.monto for o in historial], n=4, method="inclusive")
    montos_por_cpc = defaultdict(list)
    for observacion in historial:
        if observacion.cpc:
            montos_por_cpc[observacion.cpc].append(observacion.monto)
    por_cpc = {
        cpc: quantiles(montos, n=4, method="inclusive")
        for cpc, montos in montos_por_cpc.items() if len(montos) >= MINIMO_CONTRATOS
    }
    return general, por_cpc


def medir(predicciones):
    errores, aciertos, anchuras, puntuaciones = [], [], [], []
    for monto, (inferior, mediana, superior) in predicciones:
        anchura = superior - inferior
        distancia = max(0, inferior - monto, monto - superior)
        errores.append(abs(monto - mediana))
        aciertos.append(inferior <= monto <= superior)
        anchuras.append(anchura)
        puntuaciones.append(anchura + 4 * distancia)
    return mean(errores), sum(aciertos), mean(anchuras), mean(puntuaciones)


def principal():
    observaciones = leer_observaciones()
    general_total, cpc_total = [], []
    print("| Mes de apertura | Historial disponible | Contratos evaluados | Con rango por CPC |")
    print("| --- | ---: | ---: | ---: |")
    for mes in range(7, 13):
        inicio = date(ANIO, mes, 1)
        historial, evaluacion = particion(observaciones, inicio)
        general, por_cpc = ajustar(historial)
        general_total.extend((o.monto, general) for o in evaluacion)
        cpc_total.extend((o.monto, por_cpc.get(o.cpc, general)) for o in evaluacion)
        print(f"| {inicio:%Y-%m} | {len(historial)} | {len(evaluacion)} | "
              f"{sum(o.cpc in por_cpc for o in evaluacion)} |")

    if not general_total:
        raise ValueError("No hay contratos evaluables entre julio y diciembre")
    print()
    print("| Modelo | Error absoluto medio (USD) | Dentro del rango | Anchura media (USD) | Puntuación media |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for nombre, predicciones in (("General", general_total), ("Por CPC con respaldo", cpc_total)):
        error, aciertos, anchura, puntuacion = medir(predicciones)
        print(f"| {nombre} | {error:.2f} | {aciertos}/{len(predicciones)} | {anchura:.2f} | {puntuacion:.2f} |")


if __name__ == "__main__":
    principal()
