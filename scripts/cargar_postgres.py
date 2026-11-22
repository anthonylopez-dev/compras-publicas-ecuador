"""Concilia los cortes de SERCOP y publica el piloto en PostgreSQL."""

import argparse
from datetime import date
from decimal import Decimal
import json
import os
from pathlib import Path

import psycopg
from psycopg import sql

from scripts.auditar_sercop import (
    CPC_PILOTO, MODALIDAD, cpcs_del_proceso, filas_del_corte, leer_zip,
)
from scripts.capturar_sercop import ANIO, RAIZ, capturar, leer_crudo, validar_manifiesto


COLUMNAS = {
    "corte": ("mes", "total_portal", "sha256_zip"),
    "proceso": (
        "ocid", "mes", "codigo", "apertura", "modalidad", "entidad_id", "entidad_nombre",
        "objeto", "estado", "numero_oferentes",
    ),
    "proceso_cpc": ("ocid", "cpc"),
    "adjudicacion": ("ocid", "adjudicacion_id", "fecha", "estado", "monto", "moneda"),
    "adjudicacion_proveedor": ("ocid", "adjudicacion_id", "proveedor_id", "proveedor_nombre"),
    "contrato": ("ocid", "contrato_id", "adjudicacion_id", "firma", "estado", "monto", "moneda"),
}


def texto(valor):
    if not valor:
        return None
    return " ".join(valor.split()) or None


def fecha(valor):
    return date.fromisoformat(valor[:10]) if valor else None


def valor_monetario(objeto):
    valor = objeto.get("value") or {}
    monto = valor.get("amount")
    moneda = texto(valor.get("currency"))
    if monto is not None:
        monto = Decimal(str(monto))
        if not monto.is_finite():
            raise ValueError("Se encontró un monto no finito")
    return monto, moneda.upper() if moneda else None


def agregar(registros, clave, fila):
    if registros.setdefault(clave, fila) != fila:
        raise ValueError(f"Registros incompatibles para la clave {clave}")


def transformar_corte(corte, paquetes, tablas):
    mes = date.fromisoformat(f"{corte['mes']}-01")
    filas = filas_del_corte(paquetes)
    if len(filas) != corte["total"]:
        raise ValueError(f"{mes}: el conteo del ZIP difiere del portal")

    sin_cpc = sin_entidad = piloto = 0
    tablas["corte"][mes] = (mes, corte["total"], corte["sha256"])
    for fila in filas:
        ocid = fila["ocid"]
        if not ocid or ocid in tablas["proceso"]:
            raise ValueError(f"{mes}: OCID ausente o repetido: {ocid}")

        oferta = fila["tender"]
        apertura = fecha((oferta.get("tenderPeriod") or {}).get("startDate"))
        if apertura is None or apertura.replace(day=1) != mes or oferta["procurementMethodDetails"] != MODALIDAD:
            raise ValueError(f"{ocid}: apertura o modalidad fuera del corte {mes}")

        entidad = fila.get("buyer") or {}
        entidad_id = texto(entidad.get("id"))
        entidad_nombre = texto(entidad.get("name"))
        cpcs = cpcs_del_proceso(oferta)
        es_piloto = any(cpc.startswith(CPC_PILOTO) for cpc in cpcs)
        falta_entidad = entidad_id is None or entidad_nombre is None
        if es_piloto and falta_entidad:
            raise ValueError(f"{ocid}: entidad del piloto sin identificador o nombre")
        sin_cpc += not cpcs
        sin_entidad += falta_entidad
        piloto += es_piloto

        tablas["proceso"][ocid] = (
            ocid, mes, texto(oferta.get("id")) or ocid, apertura, MODALIDAD,
            entidad_id, entidad_nombre, texto(oferta.get("description")),
            texto(oferta.get("status")), oferta.get("numberOfTenderers"),
        )
        for cpc in sorted(cpcs):
            tablas["proceso_cpc"][ocid, cpc] = (ocid, cpc)

        for adjudicacion in fila.get("awards") or []:
            clave = (ocid, adjudicacion["id"])
            agregar(tablas["adjudicacion"], clave, (
                *clave, fecha(adjudicacion.get("date")), texto(adjudicacion.get("status")),
                *valor_monetario(adjudicacion),
            ))
            for proveedor in adjudicacion.get("suppliers") or []:
                proveedor_id = proveedor["id"]
                agregar(tablas["adjudicacion_proveedor"], (*clave, proveedor_id), (
                    *clave, proveedor_id, texto(proveedor.get("name")),
                ))

        for contrato in fila.get("contracts") or []:
            clave = (ocid, contrato["id"])
            agregar(tablas["contrato"], clave, (
                *clave, texto(contrato.get("awardID")), fecha(contrato.get("dateSigned")),
                texto(contrato.get("status")), *valor_monetario(contrato),
            ))

    return mes, corte["total"], len(filas), sin_cpc, sin_entidad, piloto


def preparar_tablas(manifiesto):
    validar_manifiesto(manifiesto)
    tablas = {nombre: {} for nombre in COLUMNAS}
    conciliacion = [
        transformar_corte(corte, leer_zip(leer_crudo(corte)), tablas)
        for corte in manifiesto["cortes"]
    ]
    return tablas, conciliacion


def cargar(conexion, tablas, conciliacion):
    with conexion.transaction(), conexion.cursor() as cursor:
        cursor.execute((RAIZ / "sql" / "modelo.sql").read_text(encoding="utf-8"))
        cursor.execute(
            "DELETE FROM limpio.corte WHERE mes >= %s AND mes < %s",
            (date(ANIO, 1, 1), date(ANIO + 1, 1, 1)),
        )
        for tabla, columnas in COLUMNAS.items():
            consulta = sql.SQL("COPY {} ({}) FROM STDIN").format(
                sql.Identifier("limpio", tabla), sql.SQL(", ").join(map(sql.Identifier, columnas)),
            )
            with cursor.copy(consulta) as copia:
                for fila in tablas[tabla].values():
                    copia.write_row(fila)

        cursor.execute(
            """SELECT mes, total_portal, procesos, sin_cpc, sin_entidad, procesos_piloto
               FROM analitico.calidad_mensual WHERE mes >= %s AND mes < %s ORDER BY mes""",
            (date(ANIO, 1, 1), date(ANIO + 1, 1, 1)),
        )
        if cursor.fetchall() != conciliacion:
            raise ValueError("Las vistas de PostgreSQL difieren de la conciliación por mes")


def principal():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desde-crudo", type=Path, metavar="MANIFIESTO")
    argumentos = parser.parse_args()
    if not os.environ.get("PGDATABASE"):
        parser.error("Define PGDATABASE y los datos de acceso de PostgreSQL antes de cargar")

    with psycopg.connect(autocommit=True, connect_timeout=5, application_name="compras_publicas") as conexion:
        if not conexion.execute("SELECT pg_try_advisory_lock(87141, %s)", (ANIO,)).fetchone()[0]:
            raise SystemExit("Ya hay una carga del piloto en ejecución")
        ruta = argumentos.desde_crudo or capturar()
        print(f"Manifiesto: {ruta}", flush=True)
        tablas, conciliacion = preparar_tablas(json.loads(ruta.read_text(encoding="utf-8")))
        cargar(conexion, tablas, conciliacion)

    print(json.dumps({
        "anio": ANIO,
        "filas": {tabla: len(filas) for tabla, filas in tablas.items()},
        "sin_cpc": sum(fila[3] for fila in conciliacion),
        "sin_entidad": sum(fila[4] for fila in conciliacion),
        "procesos_piloto": sum(fila[5] for fila in conciliacion),
    }, indent=2))


if __name__ == "__main__":
    principal()
