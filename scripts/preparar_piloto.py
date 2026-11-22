"""Prepara los datos de la demo local con los doce cortes de 2025."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from scripts.auditar_sercop import (
    CPC_PILOTO,
    MODALIDAD,
    cpcs_del_proceso,
    descargar_corte,
    filas_del_corte,
)


ANIO = 2025
ARCHIVO_DEMO = Path(__file__).resolve().parents[1] / "demo" / "datos.js"


def preparar_corte(mes, paquetes, total_portal, sha256_zip):
    filas = filas_del_corte(paquetes)
    ocids = {fila["ocid"] for fila in filas}
    if len(filas) != total_portal or len(ocids) != len(filas) or not all(ocids):
        raise ValueError(f"{mes}: OCID faltantes, repetidos o total distinto al portal")

    con_cpc = 0
    procesos = []
    for fila in filas:
        licitacion = fila["tender"]
        inicio = licitacion.get("tenderPeriod", {}).get("startDate") or ""
        apertura = date.fromisoformat(inicio[:10]).isoformat()
        if apertura[:7] != mes or licitacion["procurementMethodDetails"] != MODALIDAD:
            raise ValueError(f"{fila['ocid']}: fecha o modalidad fuera del corte {mes}")

        cpcs = cpcs_del_proceso(licitacion)
        con_cpc += bool(cpcs)
        codigos = sorted(cpc for cpc in cpcs if cpc.startswith(CPC_PILOTO))
        if codigos:
            entidad = fila["buyer"]
            if not entidad.get("id") or not entidad.get("name", "").strip():
                raise ValueError(f"{fila['ocid']}: entidad del piloto sin ID o nombre")
            objeto = " ".join((licitacion.get("description") or "").split())
            procesos.append({
                "ocid": fila["ocid"],
                "codigo": licitacion.get("id") or fila["ocid"],
                "entidad_id": entidad["id"],
                "entidad": " ".join(entidad["name"].split()),
                "objeto": objeto,
                "apertura": apertura,
                "cpc": codigos,
            })

    corte = {"mes": mes, "total": total_portal, "con_cpc": con_cpc, "sha256_zip": sha256_zip}
    return corte, procesos, ocids


def cargar_mes(mes):
    return preparar_corte(f"{ANIO}-{mes:02}", *descargar_corte(ANIO, mes))


def construir_demo():
    with ThreadPoolExecutor(max_workers=3) as descargas:
        resultados = list(descargas.map(cargar_mes, range(1, 13)))

    cortes, grupos, ocids = zip(*resultados)
    if len(set.union(*ocids)) != sum(map(len, ocids)):
        raise ValueError("Hay OCID repetidos entre meses")

    procesos = sorted(
        (proceso for grupo in grupos for proceso in grupo),
        key=lambda proceso: (proceso["apertura"], proceso["ocid"]),
        reverse=True,
    )
    datos = {"anio": ANIO, "cpc": CPC_PILOTO, "cortes": cortes, "procesos": procesos}
    ARCHIVO_DEMO.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=ARCHIVO_DEMO.parent, delete=False
    ) as temporal:
        temporal.write("const DATOS = " + json.dumps(datos, separators=(",", ":")) + ";\n")
        ruta_temporal = Path(temporal.name)
    ruta_temporal.replace(ARCHIVO_DEMO)
    print(f"{len(cortes)} meses · {sum(corte['total'] for corte in cortes)} procesos en la fuente")
    print(f"{len(procesos)} procesos del rubro · {len({p['entidad_id'] for p in procesos})} entidades")


if __name__ == "__main__":
    construir_demo()
