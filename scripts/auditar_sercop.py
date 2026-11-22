"""Descarga cuatro cortes de SERCOP y muestra su cobertura en JSON."""

from decimal import Decimal
import hashlib
from http.client import IncompleteRead
import io
import json
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from zipfile import ZipFile


BASE_URL = "https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA"
MODALIDAD = "Subasta Inversa Electrónica"
CORTES = ((2024, 10), (2025, 3), (2025, 10), (2026, 10))
CPC_PILOTO = "87141"


def filas_del_corte(paquetes):
    if any(len(paquete["releases"]) != 1 for paquete in paquetes):
        raise ValueError("El corte requiere una entrega por paquete para este perfil")
    return [paquete["releases"][0] for paquete in paquetes]


def cpcs_del_proceso(licitacion):
    return {
        clase["id"]
        for item in licitacion.get("items") or []
        if (clase := item.get("classification"))
        and clase.get("scheme") == "CPC"
        and clase.get("id")
    }


def perfilar(paquetes, mes):
    filas = filas_del_corte(paquetes)
    ocids = {fila["ocid"] for fila in filas}
    compras = {
        "entidad_con_id": 0,
        "apertura_en_mes": 0,
        "fecha_de_entrega_en_mes": 0,
        "con_cpc": 0,
        "con_numero_de_oferentes": 0,
        "con_adjudicacion": 0,
    }
    piloto = set()
    entidades_piloto = set()
    for fila in filas:
        licitacion = fila["tender"]
        id_entidad = fila.get("buyer", {}).get("id")
        apertura = licitacion.get("tenderPeriod", {}).get("startDate") or ""
        cpcs = cpcs_del_proceso(licitacion)
        oferentes = licitacion.get("numberOfTenderers")
        compras["entidad_con_id"] += bool(id_entidad)
        compras["apertura_en_mes"] += apertura[:7] == mes
        compras["fecha_de_entrega_en_mes"] += (fila.get("date") or "")[:7] == mes
        compras["con_cpc"] += bool(cpcs)
        compras["con_numero_de_oferentes"] += type(oferentes) is int and oferentes >= 0
        compras["con_adjudicacion"] += bool(fila.get("awards"))

        if id_entidad and apertura[:7] == mes and any(cpc.startswith(CPC_PILOTO) for cpc in cpcs):
            piloto.add(fila["ocid"])
            entidades_piloto.add(id_entidad)

    perfil = {
        "entregas": len(filas),
        "procesos_unicos": len(ocids),
        **compras,
        "procesos_piloto": len(piloto),
        "entidades_piloto": len(entidades_piloto),
    }
    return perfil, ocids, entidades_piloto


def leer_respuesta(url):
    for intento in range(3):
        try:
            with urlopen(url, timeout=30) as respuesta:
                return respuesta.read()
        except (URLError, TimeoutError, IncompleteRead) as error:
            if intento == 2 or (isinstance(error, HTTPError) and error.code not in (408, 429, 500, 502, 503, 504)):
                raise
            sleep(2 ** intento)


def descargar_zip(anio, mes):
    consulta = urlencode({"year": anio, "month": mes, "method": MODALIDAD})
    return leer_respuesta(f"{BASE_URL}/download?type=json&{consulta}")


def leer_zip(archivo):
    with ZipFile(io.BytesIO(archivo)) as zip_sercop:
        nombre_json, = zip_sercop.namelist()
        return json.loads(zip_sercop.read(nombre_json), parse_float=Decimal)


def total_portal(anio, mes):
    consulta = urlencode({"year": anio, "month": mes, "method": MODALIDAD})
    return json.loads(leer_respuesta(f"{BASE_URL}/get-totals?{consulta}"))["count"]


def descargar_corte(anio, mes):
    archivo = descargar_zip(anio, mes)
    return leer_zip(archivo), total_portal(anio, mes), hashlib.sha256(archivo).hexdigest()


def auditar_corte(anio, mes):
    periodo = f"{anio}-{mes:02}"
    paquetes, total_portal, sha256_zip = descargar_corte(anio, mes)
    perfil, ocids, entidades_piloto = perfilar(paquetes, periodo)
    corte = {
        "periodo": periodo,
        "total_portal": total_portal,
        "sha256_zip": sha256_zip,
        **perfil,
    }
    return corte, ocids, entidades_piloto


if __name__ == "__main__":
    cortes, procesos, entidades = zip(*(auditar_corte(*periodo) for periodo in CORTES))
    informe = {
        "procesos_unicos": len(set.union(*procesos)),
        "entidades_piloto": len(set.union(*entidades)),
        "cortes": cortes,
    }
    print(json.dumps(informe, indent=2))
