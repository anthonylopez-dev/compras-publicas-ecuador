"""Construye el proyecto PBIP con un corte portátil y opción de refresco PostgreSQL."""

import base64
import hashlib
import json
from uuid import NAMESPACE_URL, uuid5
import zlib

from scripts.exportar_tableros import MESES, RAIZ, convertir, leer_piloto


BASE = RAIZ / "dashboards" / "powerbi"
NOMBRE = "Mantenimiento vehicular"
DEFINICION = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
FUENTE = "https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/ocds/"
TEMA = {
    "name": "Compras públicas Ecuador",
    "dataColors": ["#246A54", "#84AA99", "#406274", "#AA7850", "#9A704D"],
    "background": "#FFFFFF", "foreground": "#183C30", "tableAccent": "#246A54",
    "textClasses": {"label": {"fontFace": "Segoe UI", "color": "#4A6458", "fontSize": 10}},
}
PERIODO = "p.mes >= DATE '2025-01-01' AND p.mes < DATE '2026-01-01'"
PILOTO = f"""WITH piloto AS (
    SELECT p.*, dense_rank() OVER (ORDER BY entidad_id) AS entidad_clave
    FROM analitico.piloto_87141 p WHERE {PERIODO}
)"""
FORMATOS = {
    "int64": "Int64.Type", "string": "type text", "dateTime": "type date",
    "boolean": "type logical", "decimal": "Currency.Type",
}


def guardar(ruta, data):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def literal(valor):
    return '"' + valor.replace('"', '""') + '"'


def tabla(nombre, columnas, filas, sql):
    origen = json.dumps(filas, default=convertir, ensure_ascii=False, separators=(",", ":")).encode()
    compresor = zlib.compressobj(wbits=-15)
    datos = base64.b64encode(compresor.compress(origen) + compresor.flush()).decode()
    nombres = ", ".join(literal(c[0]) for c in columnas)
    tipos = ", ".join("{" + literal(c[0]) + ", " + FORMATOS[c[1]] + "}" for c in columnas)
    exp = [
        "let",
        "    Origen = if UsarPostgreSQL then",
        "        PostgreSQL.Database(ServidorPostgreSQL, \"compras_publicas\", [Query = " + literal(" ".join(sql.split())) + "])",
        "    else",
        '        Table.FromRows(Json.Document(Binary.Decompress(Binary.FromText("' + datos + '", BinaryEncoding.Base64), Compression.Deflate)), {' + nombres + "}),",
        '    Tipos = Table.TransformColumnTypes(Origen, {' + tipos + '}, "en-US")',
        "in",
        "    Tipos",
    ]
    return {
        "name": nombre,
        "lineageTag": str(uuid5(NAMESPACE_URL, nombre)),
        "columns": [
            {"name": clave, "dataType": tipo, "sourceColumn": clave,
             "summarizeBy": "none", **opciones}
            for clave, tipo, opciones in columnas
        ],
        "partitions": [{"name": nombre, "mode": "import", "source": {"type": "m", "expression": exp}}],
    }


def construir_modelo(datos):
    procesos = datos["procesos"]
    contratos = datos["contratos"]
    indices = {p["ocid"]: p for p in procesos}
    dim_mes = tabla(
        "Mes", [("Id", "int64", {"isHidden": True}), ("Mes", "string", {"sortByColumn": "Id"})],
        [(c["mes"], c["nombre"]) for c in datos["cortes"]],
        "SELECT mes AS \"Id\", (ARRAY[" + ", ".join("'" + m + "'" for m in MESES)
        + "])[mes] AS \"Mes\" FROM generate_series(1, 12) AS serie(mes)",
    )
    dim_entidad = tabla(
        "Entidad", [("Id", "int64", {"isHidden": True}), ("Entidad", "string", {})],
        [(e["id"], e["nombre"]) for e in datos["entidades"]],
        PILOTO + ' SELECT DISTINCT entidad_clave AS "Id", entidad_nombre AS "Entidad" FROM piloto',
    )
    proceso = tabla(
        "Procesos", [
            ("OCID", "string", {"isHidden": True}), ("MesId", "int64", {"isHidden": True}),
            ("EntidadId", "int64", {"isHidden": True}), ("Código", "string", {}),
            ("Apertura", "dateTime", {"formatString": "dd/MM/yyyy"}), ("Objeto", "string", {}),
            ("Oferentes", "int64", {}), ("Adjudicado", "boolean", {}),
            ("Días a la firma", "int64", {}), ("Ficha SERCOP", "string", {"dataCategory": "WebUrl"}),
        ],
        [(p["ocid"], p["mes"], p["entidad"], p["codigo"], p["apertura"], p["objeto"],
          p["oferentes"], p["adjudicado"], p["dias_firma"], FUENTE + p["ocid"]) for p in procesos],
        PILOTO + f'''
        SELECT p.ocid AS "OCID", extract(month FROM p.mes)::int AS "MesId", p.entidad_clave AS "EntidadId",
               p.codigo AS "Código", p.apertura AS "Apertura", p.objeto AS "Objeto",
               h.numero_oferentes AS "Oferentes",
               EXISTS (SELECT 1 FROM analitico.hecho_adjudicacion a WHERE a.ocid = p.ocid) AS "Adjudicado",
               (SELECT min(c.firma) - p.apertura FROM analitico.hecho_contrato c
                WHERE c.ocid = p.ocid AND c.firma >= p.apertura) AS "Días a la firma",
               '{FUENTE}' || p.ocid AS "Ficha SERCOP"
        FROM piloto p JOIN analitico.hecho_proceso h USING (ocid)
        ''',
    )
    contrato = tabla(
        "Contratos", [
            ("OCID", "string", {"isHidden": True}), ("MesId", "int64", {"isHidden": True}),
            ("EntidadId", "int64", {"isHidden": True}), ("Monto USD", "decimal", {}),
            ("Proveedor vinculado", "boolean", {}),
        ],
        [(c["ocid"], indices[c["ocid"]]["mes"], indices[c["ocid"]]["entidad"],
          c["monto"], c["proveedor_vinculado"]) for c in contratos],
        PILOTO + '''
        SELECT c.ocid AS "OCID", extract(month FROM p.mes)::int AS "MesId", p.entidad_clave AS "EntidadId",
               c.monto AS "Monto USD",
               EXISTS (SELECT 1 FROM analitico.contrato_proveedor cp
               WHERE cp.ocid = c.ocid AND cp.contrato_id = c.contrato_id) AS "Proveedor vinculado"
        FROM analitico.hecho_contrato c JOIN piloto p USING (ocid)
        WHERE c.moneda = 'USD' AND c.monto > 0
        ''',
    )
    cobertura = tabla(
        "Cobertura", [("MesId", "int64", {"isHidden": True}), ("Total", "int64", {}), ("Sin CPC", "int64", {})],
        [(c["mes"], c["total"], c["sin_cpc"]) for c in datos["cortes"]],
        f'''SELECT extract(month FROM p.mes)::int AS "MesId", p.procesos AS "Total", p.sin_cpc AS "Sin CPC"
        FROM analitico.calidad_mensual p WHERE {PERIODO}''',
    )
    medidas = {
        "Aperturas": ("COUNTROWS(Procesos)", "#,0"),
        "Entidades": ("DISTINCTCOUNT(Procesos[EntidadId])", "#,0"),
        "Meses activos": ("DISTINCTCOUNT(Procesos[MesId])", "#,0"),
        "Adjudicados con conteo": (
            "CALCULATE([Aperturas], KEEPFILTERS(Procesos[Adjudicado] = TRUE()), KEEPFILTERS(NOT ISBLANK(Procesos[Oferentes])))", "#,0"),
        "Adjudicados con 1 o 2": (
            "CALCULATE([Adjudicados con conteo], KEEPFILTERS(Procesos[Oferentes] IN {1, 2}))", "#,0"),
        "Proporción con 1 o 2 oferentes": ("DIVIDE([Adjudicados con 1 o 2], [Adjudicados con conteo])", "0.0%"),
        "Contratos en USD": ("COUNTROWS(Contratos)", "#,0"),
        "Contratos con proveedor": (
            "CALCULATE([Contratos en USD], Contratos[Proveedor vinculado] = TRUE())", "#,0"),
        "Mediana de contrato": ("MEDIAN(Contratos[Monto USD])", '"$"#,0'),
        "P25 de contrato": ("PERCENTILE.INC(Contratos[Monto USD], 0.25)", '"$"#,0'),
        "P75 de contrato": ("PERCENTILE.INC(Contratos[Monto USD], 0.75)", '"$"#,0'),
        "Días hasta la firma": ("MEDIAN(Procesos[Días a la firma])", '0" días"'),
        "Con firma": ("COUNT(Procesos[Días a la firma])", "#,0"),
        "Cobertura CPC": ("1 - DIVIDE(SUM(Cobertura[Sin CPC]), SUM(Cobertura[Total]))", "0.0%"),
    }
    proceso["measures"] = [
        {"name": nombre, "expression": formula, "formatString": formato}
        for nombre, (formula, formato) in medidas.items()
    ]
    relaciones = [(f, "MesId", "Mes") for f in ("Procesos", "Contratos", "Cobertura")]
    relaciones += [(f, "EntidadId", "Entidad") for f in ("Procesos", "Contratos")]
    return {"name": "Model", "compatibilityLevel": 1601, "model": {
        "culture": "es-EC", "sourceQueryCulture": "es-EC", "defaultPowerBIDataSourceVersion": "powerBI_V3",
        "tables": [dim_mes, dim_entidad, proceso, contrato, cobertura],
        "relationships": [
            {"name": str(uuid5(NAMESPACE_URL, desde + "." + campo)),
             "fromTable": desde, "fromColumn": campo, "toTable": hacia, "toColumn": "Id"}
            for desde, campo, hacia in relaciones
        ],
        "expressions": [
            {"name": "UsarPostgreSQL", "kind": "m",
             "expression": 'false meta [IsParameterQuery=true, Type="Logical", IsParameterQueryRequired=true]'},
            {"name": "ServidorPostgreSQL", "kind": "m",
             "expression": '"127.0.0.1:55432" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'},
        ],
    }}


def expr(valor):
    return {"expr": {"Literal": {"Value": valor}}}


def campo(tabla, propiedad, medida=False):
    return {"field": {"Measure" if medida else "Column": {
        "Expression": {"SourceRef": {"Entity": tabla}}, "Property": propiedad,
    }}, "queryRef": f"{tabla}.{propiedad}", "nativeQueryRef": propiedad}


def construir_informe(carpeta):
    definicion = carpeta / "definition"
    guardar(definicion / "version.json", {"$schema": DEFINICION + "versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    versiones = {"visual": "1.8.89", "report": "2.0.89", "page": "1.3.89"}
    guardar(definicion / "report.json", {
        "$schema": DEFINICION + "report/3.0.0/schema.json",
        "themeCollection": {
            "baseTheme": {"name": "CY24SU02", "reportVersionAtImport": versiones, "type": "SharedResources"},
            "customTheme": {"name": "Compras.json", "reportVersionAtImport": versiones, "type": "RegisteredResources"},
        },
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": "CY24SU02", "path": "BaseThemes/CY24SU02.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": "Compras.json", "path": "Compras.json", "type": "CustomTheme"}]},
        ],
    })
    guardar(carpeta / "StaticResources" / "RegisteredResources" / "Compras.json", TEMA)

    etiquetas = ["Resumen", "Compradores", "Competencia", "Montos y plazos", "Procesos"]
    ids = [hashlib.sha256(e.encode()).hexdigest()[:20] for e in etiquetas]
    guardar(definicion / "pages" / "pages.json", {
        "$schema": DEFINICION + "pagesMetadata/1.0.0/schema.json", "pageOrder": ids, "activePageName": ids[0],
    })
    marcas = []
    for nombre, ident in zip(etiquetas, ids):
        pagina = definicion / "pages" / ident
        guardar(pagina / "page.json", {
            "$schema": DEFINICION + "page/2.0.0/schema.json", "name": ident,
            "displayName": nombre, "displayOption": "FitToPage", "width": 1280, "height": 720,
            "objects": {"background": [{"properties": {
                "color": {"solid": {"color": expr("'#F4F6F2'")}}, "transparency": expr("0D"),
            }}]},
        })
        construir_pagina(pagina, nombre)
        marca = "Bookmark" + ident
        marcas.append({"name": marca})
        guardar(definicion / "bookmarks" / f"{marca}.bookmark.json", {
            "$schema": DEFINICION + "bookmark/1.4.0/schema.json", "name": marca, "displayName": nombre,
            "options": {"targetVisualNames": []},
            "explorationState": {"version": "1.3", "activeSection": ident, "sections": {ident: {"visualContainers": {}}}},
        })
    guardar(definicion / "bookmarks" / "bookmarks.json", {
        "$schema": DEFINICION + "bookmarksMetadata/1.0.0/schema.json", "items": marcas,
    })


def construir_pagina(pagina, nombre):
    contador = 0

    def visual(tipo, posicion, roles=None, titulo=None, orden=None, objetos=None):
        nonlocal contador
        contador += 1
        ident = hashlib.sha256(f"{nombre}.{contador}".encode()).hexdigest()[:20]
        x, y, ancho, alto = posicion
        propiedad = {"visualType": tipo, "drillFilterOtherVisuals": True}
        if roles:
            propiedad["query"] = {"queryState": {k: {"projections": v} for k, v in roles.items()}}
        if orden:
            propiedad["query"]["sortDefinition"] = {
                "sort": [{"field": c["field"], "direction": direccion} for c, direccion in orden],
            }
        if objetos:
            propiedad["objects"] = objetos
        if titulo:
            propiedad["visualContainerObjects"] = {"title": [{"properties": {
                "show": expr("true"), "text": expr("'" + titulo + "'"),
            }}]}
        guardar(pagina / "visuals" / ident / "visual.json", {
            "$schema": DEFINICION + "visualContainer/2.7.0/schema.json", "name": ident,
            "position": {"x": x, "y": y, "z": contador * 100, "width": ancho, "height": alto, "tabOrder": contador * 100},
            "visual": propiedad,
        })

    def texto(contenido, posicion, tamano, color="#183C30", negrita=False):
        estilo = {"fontSize": f"{tamano}pt", "fontFamily": "Segoe UI", "color": color}
        if negrita:
            estilo["fontWeight"] = "bold"
        visual("textbox", posicion, objetos={"general": [{"properties": {
            "paragraphs": [{"textRuns": [{"value": contenido, "textStyle": estilo}]}],
        }}]})

    def indicador(medida, x, y=176):
        visual("card", (x, y, 288, 105), {"Values": [m(medida)]})

    def m(nombre_medida):
        return campo("Procesos", nombre_medida, True)

    mes = campo("Mes", "Mes")
    entidad = campo("Entidad", "Entidad")
    cabeceras = {
        "Resumen": "Mantenimiento vehicular",
        "Compradores": "Quién abre procesos en distintos meses",
        "Competencia": "Cuántos oferentes participaron",
        "Montos y plazos": "Tamaño de contrato y tiempo hasta la firma",
        "Procesos": "Fichas de los procesos históricos",
    }
    texto(cabeceras[nombre], (32, 22, 1195, 59), 27, negrita=True)
    texto("Ecuador · Subasta Inversa Electrónica · CPC 87141 · Aperturas de 2025",
          (32, 85, 1216, 33), 13)
    for campo_filtro, caja in [(mes, (32, 121, 250, 52)), (entidad, (304, 121, 640, 52))]:
        visual("slicer", caja, {"Values": [{**campo_filtro, "active": True}]},
               objetos={"data": [{"properties": {"mode": expr("'Dropdown'")}}]})
    texto("Fuente  SERCOP, Contrataciones Abiertas Ecuador · CC BY 3.0 Ecuador",
          (32, 678, 1195, 36), 10, "#50695C")

    if nombre == "Resumen":
        for x, medida in zip((32, 340, 648, 956), ("Aperturas", "Entidades", "Contratos en USD", "Cobertura CPC")):
            indicador(medida, x)
        visual("columnChart", (32, 295, 800, 365), {"Category": [mes], "Y": [m("Aperturas")]},
               "Aperturas por mes", [(mes, "Ascending")])
        texto("Prioriza por meses activos y conserva una búsqueda por rubro para las entidades con aperturas puntuales. La cobertura CPC corresponde a todas las subastas inversas del mes.",
              (859, 320, 360, 245), 17)
    elif nombre == "Compradores":
        visual("tableEx", (32, 193, 1210, 462), {"Values": [entidad, m("Meses activos"), m("Aperturas")]},
               "Compradores ordenados por meses activos y aperturas", [(m("Meses activos"), "Descending"), (m("Aperturas"), "Descending")])
    elif nombre == "Competencia":
        for x, medida in zip((32, 340, 648, 956), ("Adjudicados con conteo", "Adjudicados con 1 o 2", "Proporción con 1 o 2 oferentes", "Contratos con proveedor")):
            indicador(medida, x)
        oferentes = campo("Procesos", "Oferentes")
        visual("columnChart", (32, 295, 820, 365), {"Category": [oferentes], "Y": [m("Adjudicados con conteo")]},
               "Adjudicados por número de oferentes", [(oferentes, "Ascending")])
        texto("La participación histórica se calcula entre procesos adjudicados con conteo publicado. El vínculo con proveedores se obtiene a través de la adjudicación.",
              (879, 320, 340, 245), 17)
    elif nombre == "Montos y plazos":
        for x, medida in zip((32, 340, 648, 956), ("Mediana de contrato", "P25 de contrato", "P75 de contrato", "Días hasta la firma")):
            indicador(medida, x)
        visual("lineChart", (32, 295, 820, 365), {"Category": [mes], "Y": [m("Días hasta la firma")]},
               "Mediana de días por mes de apertura", [(mes, "Ascending")])
        texto("Los montos representan el valor total del contrato. Para comparar precios se requiere revisar flota, cantidades, repuestos y duración.",
              (879, 320, 340, 245), 17)
    else:
        columnas = [campo("Procesos", c) for c in ("Apertura", "Código", "Oferentes", "Días a la firma", "Ficha SERCOP")]
        visual("tableEx", (32, 193, 1210, 462), {"Values": [*columnas[:1], entidad, *columnas[1:]]},
               "Procesos con enlace a la ficha oficial", [(columnas[0], "Descending")])


def construir():
    modelo = BASE / (NOMBRE + ".SemanticModel")
    informe = BASE / (NOMBRE + ".Report")
    guardar(BASE / (NOMBRE + ".pbip"), {
        "version": "1.0", "artifacts": [{"report": {"path": informe.name}}],
        "settings": {"enableAutoRecovery": True},
    })
    guardar(informe / "definition.pbir", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": "../" + modelo.name}},
    })
    guardar(modelo / "definition.pbism", {"version": "4.0", "settings": {}})
    guardar(modelo / "model.bim", construir_modelo(leer_piloto()))
    construir_informe(informe)
    print(BASE / (NOMBRE + ".pbip"))


if __name__ == "__main__":
    construir()
