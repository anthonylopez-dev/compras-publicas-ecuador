CREATE SCHEMA IF NOT EXISTS limpio;
CREATE SCHEMA IF NOT EXISTS analitico;

CREATE TABLE IF NOT EXISTS limpio.corte (
    mes date PRIMARY KEY CHECK (extract(day FROM mes) = 1),
    total_portal integer NOT NULL CHECK (total_portal >= 0),
    sha256_zip text NOT NULL CHECK (sha256_zip ~ '^[0-9a-f]{64}$'),
    cargado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS limpio.proceso (
    ocid text PRIMARY KEY CHECK (ocid <> ''),
    mes date NOT NULL REFERENCES limpio.corte (mes) ON DELETE CASCADE,
    codigo text NOT NULL,
    apertura date NOT NULL CHECK (apertura >= mes AND apertura < mes + interval '1 month'),
    modalidad text NOT NULL,
    entidad_id text,
    entidad_nombre text,
    objeto text,
    estado text,
    numero_oferentes integer CHECK (numero_oferentes >= 0)
);

CREATE INDEX IF NOT EXISTS proceso_mes_idx ON limpio.proceso (mes);
CREATE INDEX IF NOT EXISTS proceso_entidad_apertura_idx ON limpio.proceso (entidad_id, apertura DESC);

CREATE TABLE IF NOT EXISTS limpio.proceso_cpc (
    ocid text NOT NULL REFERENCES limpio.proceso (ocid) ON DELETE CASCADE,
    cpc text NOT NULL CHECK (cpc ~ '^[0-9]+$'),
    PRIMARY KEY (ocid, cpc)
);

CREATE TABLE IF NOT EXISTS limpio.adjudicacion (
    ocid text NOT NULL REFERENCES limpio.proceso (ocid) ON DELETE CASCADE,
    adjudicacion_id text NOT NULL CHECK (adjudicacion_id <> ''),
    fecha date,
    estado text,
    monto numeric,
    moneda text CHECK (moneda ~ '^[A-Z]{3}$'),
    PRIMARY KEY (ocid, adjudicacion_id)
);

CREATE TABLE IF NOT EXISTS limpio.adjudicacion_proveedor (
    ocid text NOT NULL,
    adjudicacion_id text NOT NULL,
    proveedor_id text NOT NULL CHECK (proveedor_id <> ''),
    proveedor_nombre text,
    PRIMARY KEY (ocid, adjudicacion_id, proveedor_id),
    FOREIGN KEY (ocid, adjudicacion_id)
        REFERENCES limpio.adjudicacion (ocid, adjudicacion_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS limpio.contrato (
    ocid text NOT NULL REFERENCES limpio.proceso (ocid) ON DELETE CASCADE,
    contrato_id text NOT NULL CHECK (contrato_id <> ''),
    adjudicacion_id text,
    firma date,
    estado text,
    monto numeric,
    moneda text CHECK (moneda ~ '^[A-Z]{3}$'),
    PRIMARY KEY (ocid, contrato_id)
);

CREATE OR REPLACE VIEW analitico.dim_fecha AS
WITH fechas AS (
    SELECT dia::date AS fecha
    FROM limpio.corte AS c
    CROSS JOIN LATERAL generate_series(
        c.mes::timestamp, c.mes + interval '1 month - 1 day', interval '1 day'
    ) AS serie(dia)
    UNION
    SELECT fecha FROM limpio.adjudicacion WHERE fecha IS NOT NULL
    UNION
    SELECT firma FROM limpio.contrato WHERE firma IS NOT NULL
)
SELECT fecha, extract(year FROM fecha)::int AS anio, extract(month FROM fecha)::int AS mes
FROM fechas;

CREATE OR REPLACE VIEW analitico.dim_entidad AS
SELECT DISTINCT ON (entidad_id) entidad_id, entidad_nombre
FROM limpio.proceso
WHERE entidad_id IS NOT NULL
ORDER BY entidad_id, (entidad_nombre IS NULL), apertura DESC, ocid DESC;

CREATE OR REPLACE VIEW analitico.dim_proveedor AS
SELECT DISTINCT ON (ap.proveedor_id) ap.proveedor_id, ap.proveedor_nombre
FROM limpio.adjudicacion_proveedor AS ap
JOIN limpio.adjudicacion AS a USING (ocid, adjudicacion_id)
ORDER BY ap.proveedor_id, (ap.proveedor_nombre IS NULL), a.fecha DESC NULLS LAST, ap.ocid DESC, ap.adjudicacion_id DESC;

CREATE OR REPLACE VIEW analitico.dim_rubro AS
SELECT DISTINCT cpc, left(cpc, 5) AS grupo_cpc FROM limpio.proceso_cpc;

CREATE OR REPLACE VIEW analitico.dim_procedimiento AS
SELECT DISTINCT modalidad FROM limpio.proceso;

CREATE OR REPLACE VIEW analitico.hecho_proceso AS
SELECT p.ocid, p.mes, p.codigo, p.apertura, p.modalidad, p.entidad_id, p.objeto, p.estado, p.numero_oferentes
FROM limpio.proceso AS p;

CREATE OR REPLACE VIEW analitico.hecho_adjudicacion AS
SELECT a.ocid, a.adjudicacion_id, p.entidad_id, p.modalidad, a.fecha, a.estado, a.monto, a.moneda
FROM limpio.adjudicacion AS a
JOIN limpio.proceso AS p USING (ocid);

CREATE OR REPLACE VIEW analitico.hecho_contrato AS
SELECT c.ocid, c.contrato_id, c.adjudicacion_id, p.entidad_id, p.modalidad, p.apertura,
       c.firma, c.estado, c.monto, c.moneda
FROM limpio.contrato AS c
JOIN limpio.proceso AS p USING (ocid);

CREATE OR REPLACE VIEW analitico.proceso_rubro AS
SELECT ocid, cpc FROM limpio.proceso_cpc;

CREATE OR REPLACE VIEW analitico.contrato_proveedor AS
SELECT c.ocid, c.contrato_id, ap.proveedor_id
FROM limpio.contrato AS c
JOIN limpio.adjudicacion_proveedor AS ap USING (ocid, adjudicacion_id);

CREATE OR REPLACE VIEW analitico.piloto_87141 AS
SELECT p.ocid, p.mes, p.codigo, p.apertura, p.entidad_id, e.entidad_nombre, p.objeto
FROM limpio.proceso AS p
JOIN analitico.dim_entidad AS e USING (entidad_id)
WHERE EXISTS (
    SELECT 1 FROM limpio.proceso_cpc AS pc WHERE pc.ocid = p.ocid AND left(pc.cpc, 5) = '87141'
);

CREATE OR REPLACE VIEW analitico.calidad_mensual AS
SELECT c.mes, c.total_portal, count(p.ocid) AS procesos,
       count(p.ocid) FILTER (WHERE NOT indicadores.con_cpc) AS sin_cpc,
       count(p.ocid) FILTER (WHERE p.entidad_id IS NULL OR p.entidad_nombre IS NULL) AS sin_entidad,
       count(p.ocid) FILTER (WHERE indicadores.piloto) AS procesos_piloto
FROM limpio.corte AS c
LEFT JOIN limpio.proceso AS p USING (mes)
LEFT JOIN LATERAL (
    SELECT count(*) > 0 AS con_cpc, coalesce(bool_or(left(pc.cpc, 5) = '87141'), false) AS piloto
    FROM limpio.proceso_cpc AS pc WHERE pc.ocid = p.ocid
) AS indicadores ON true
GROUP BY c.mes, c.total_portal;

CREATE OR REPLACE VIEW analitico.calidad_contratos AS
SELECT p.mes, count(*) AS contratos,
       count(*) FILTER (WHERE a.adjudicacion_id IS NULL) AS sin_adjudicacion_vinculada,
       count(*) FILTER (WHERE c.firma IS NULL) AS sin_firma,
       count(*) FILTER (WHERE c.monto IS NULL OR c.moneda IS NULL) AS sin_valor_completo,
       count(*) FILTER (WHERE c.monto < 0) AS monto_negativo
FROM limpio.contrato AS c
JOIN limpio.proceso AS p USING (ocid)
LEFT JOIN limpio.adjudicacion AS a ON a.ocid = c.ocid AND a.adjudicacion_id = c.adjudicacion_id
GROUP BY p.mes;
