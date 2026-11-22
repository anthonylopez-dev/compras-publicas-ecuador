"""Versiona los ZIP originales del piloto y los conteos de SERCOP."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile

from scripts.auditar_sercop import MODALIDAD, descargar_zip, total_portal
from scripts.preparar_piloto import ANIO


RAIZ = Path(__file__).resolve().parents[1]
CRUDO = RAIZ / "data" / "raw"
MESES = tuple(f"{ANIO}-{mes:02}" for mes in range(1, 13))


def guardar_crudo(ruta, contenido):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if ruta.exists() and ruta.read_bytes() == contenido:
        return
    with NamedTemporaryFile(dir=ruta.parent, delete=False) as temporal:
        temporal.write(contenido)
        pendiente = Path(temporal.name)
    try:
        pendiente.replace(ruta)
    finally:
        pendiente.unlink(missing_ok=True)


def capturar_mes(mes):
    archivo = descargar_zip(ANIO, mes)
    huella = sha256(archivo).hexdigest()
    periodo = f"{ANIO}-{mes:02}"
    guardar_crudo(CRUDO / periodo / f"{huella}.zip", archivo)
    return {"mes": periodo, "total": total_portal(ANIO, mes), "sha256": huella}


def capturar():
    with ThreadPoolExecutor(max_workers=3) as descargas:
        cortes = list(descargas.map(capturar_mes, range(1, 13)))
    manifiesto = {
        "anio": ANIO,
        "modalidad": MODALIDAD,
        "total_anual": total_portal(ANIO, 0),
        "cortes": cortes,
    }
    validar_manifiesto(manifiesto)
    contenido = json.dumps(manifiesto, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    ruta = CRUDO / f"{ANIO}-{sha256(contenido).hexdigest()}.json"
    guardar_crudo(ruta, contenido)
    return ruta


def validar_manifiesto(manifiesto):
    cortes = manifiesto["cortes"]
    if (
        manifiesto["anio"] != ANIO
        or manifiesto["modalidad"] != MODALIDAD
        or tuple(corte["mes"] for corte in cortes) != MESES
    ):
        raise ValueError("El manifiesto debe incluir los doce cortes del piloto de 2025")
    if any(type(corte["total"]) is not int or corte["total"] < 0 for corte in cortes):
        raise ValueError("El manifiesto contiene un total mensual inválido")
    if sum(corte["total"] for corte in cortes) != manifiesto["total_anual"]:
        raise ValueError("La suma de cortes mensuales difiere del total anual de SERCOP")


def leer_crudo(corte):
    huella = corte["sha256"]
    if corte["mes"] not in MESES or not re.fullmatch(r"[0-9a-f]{64}", huella):
        raise ValueError("Mes o SHA-256 inválido en el manifiesto")
    archivo = (CRUDO / corte["mes"] / f"{huella}.zip").read_bytes()
    if sha256(archivo).hexdigest() != huella:
        raise ValueError(f"{corte['mes']}: el ZIP crudo difiere del SHA-256 del manifiesto")
    return archivo


if __name__ == "__main__":
    print(capturar())
