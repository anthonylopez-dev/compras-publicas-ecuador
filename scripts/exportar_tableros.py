"""Lee el piloto en una sola captura y exporta los datos que usa el tablero web."""

import argparse
from datetime import date
from decimal import Decimal
import json
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "dashboards" / "web" / "dist"
PERIODO = (date(2025, 1, 1), date(2026, 1, 1))
MESES = "Ene Feb Mar Abr May Jun Jul Ago Sep Oct Nov Dic".split()


def leer_piloto():
    config = {}
    if not os.getenv("PGDATABASE"):
        runtime = Path(os.environ["LOCALAPPDATA"]) / "compras-publicas-ecuador"
        config = dict(host="127.0.0.1", port=55432, dbname="compras_publicas",
                      user="compras_pipeline", passfile=str(runtime / "pgpass.conf"))
    with psycopg.connect(**config, row_factory=dict_row, connect_timeout=5) as conexion:
        conexion.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        cortes = conexion.execute("""
            SELECT q.mes, q.procesos AS total, q.sin_cpc, q.procesos_piloto, c.sha256_zip
            FROM analitico.calidad_mensual q JOIN limpio.corte c USING (mes)
            WHERE q.mes >= %s AND q.mes < %s ORDER BY q.mes
        """, PERIODO).fetchall()
        procesos = conexion.execute("""
            SELECT p.ocid, p.codigo, p.apertura, p.entidad_id, p.entidad_nombre, p.objeto,
                   h.numero_oferentes AS oferentes,
                   EXISTS (SELECT 1 FROM analitico.hecho_adjudicacion a WHERE a.ocid = p.ocid) AS adjudicado,
                   (SELECT min(c.firma) - p.apertura FROM analitico.hecho_contrato c
                    WHERE c.ocid = p.ocid AND c.firma >= p.apertura) AS dias_firma,
                   ARRAY(SELECT r.cpc FROM analitico.proceso_rubro r WHERE r.ocid = p.ocid
                         AND left(r.cpc, 5) = '87141' ORDER BY r.cpc) AS cpc
            FROM analitico.piloto_87141 p
            JOIN analitico.hecho_proceso h USING (ocid)
            WHERE p.mes >= %s AND p.mes < %s ORDER BY p.apertura DESC, p.ocid
        """, PERIODO).fetchall()
        contratos = conexion.execute("""
            SELECT c.ocid, c.contrato_id, c.monto, c.firma,
                   EXISTS (SELECT 1 FROM analitico.contrato_proveedor cp
                           WHERE cp.ocid = c.ocid AND cp.contrato_id = c.contrato_id) AS proveedor_vinculado
            FROM analitico.hecho_contrato c JOIN analitico.piloto_87141 p USING (ocid)
            WHERE p.mes >= %s AND p.mes < %s AND c.moneda = 'USD' AND c.monto > 0
            ORDER BY c.ocid, c.contrato_id
        """, PERIODO).fetchall()

    if [c["mes"].month for c in cortes] != list(range(1, 13)):
        raise ValueError("El tablero requiere los doce cortes de 2025")
    if len(procesos) != sum(c["procesos_piloto"] for c in cortes):
        raise ValueError("El conteo de procesos no coincide con la vista mensual")

    nombres = {p["entidad_id"]: p["entidad_nombre"] for p in procesos}
    claves = {codigo: indice for indice, codigo in enumerate(sorted(nombres), 1)}
    entidades = [{"id": claves[codigo], "nombre": nombres[codigo]} for codigo in claves]
    for p in procesos:
        p["entidad"] = claves[p.pop("entidad_id")]
        p.pop("entidad_nombre")
        p["mes"] = p["apertura"].month
    for c in cortes:
        c["mes"] = c["mes"].month
        c["nombre"] = MESES[c["mes"] - 1]

    return {"cortes": cortes, "entidades": entidades, "procesos": procesos, "contratos": contratos}


def convertir(valor):
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    raise TypeError(type(valor).__name__)


def escribir_web(datos, salida=WEB):
    campos = ("ocid", "codigo", "entidad", "apertura", "mes", "cpc", "oferentes", "adjudicado", "dias_firma")
    publico = {
        "entidades": datos["entidades"],
        "cortes": [{k: c[k] for k in ("mes", "nombre", "total", "sin_cpc")} for c in datos["cortes"]],
        "procesos": [{k: p[k] for k in campos} for p in datos["procesos"]],
        "contratos": [{k: c[k] for k in ("ocid", "monto", "proveedor_vinculado")} for c in datos["contratos"]],
    }
    salida.mkdir(parents=True, exist_ok=True)
    contenido = json.dumps(publico, default=convertir, separators=(",", ":"))
    (salida / "datos.js").write_text(f"const DATOS = {contenido};\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path,
                        default=WEB if WEB.is_dir() else RAIZ / "dashboards" / "sitio",
                        help="Carpeta que recibirá datos.js")
    argumentos = parser.parse_args()
    datos = leer_piloto()
    escribir_web(datos, argumentos.salida)
    print(f"{len(datos['procesos'])} procesos de {len(datos['entidades'])} entidades")
