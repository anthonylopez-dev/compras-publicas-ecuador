# Fase 2. Ingesta, limpieza y modelo de datos

La carga cubre las subastas inversas electrónicas de Ecuador con apertura de ofertas entre enero y diciembre de 2025. El modelo conserva todas las filas de esa modalidad para medir cobertura. La vista `analitico.piloto_87141` reproduce el alcance del tablero de mantenimiento vehicular. [Descargas de SERCOP](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/datos-abiertos/) · [Ficha del piloto](fase-1-definicion.md)

## Capas y actualización

| Capa | Ubicación | Contenido |
| --- | --- | --- |
| Cruda | `data/raw/<mes>/<sha256>.zip` | ZIP originales. El manifiesto `data/raw/2025-<sha256>.json` registra los totales oficiales y el hash de cada corte. Puedes reproducir una captura a partir de su manifiesto. |
| Limpia | Esquema `limpio` en PostgreSQL | Tablas con fechas, montos y claves normalizadas. Cada corte guarda su total oficial, el hash de su ZIP y la fecha de carga. |
| Analítica | Esquema `analitico` en PostgreSQL | Hechos de procesos, adjudicaciones y contratos, dimensiones para consultas y vistas de cobertura. |

La carga verifica el SHA-256 de cada ZIP, los totales de los doce meses y el total anual. Rechaza OCID duplicados, fechas de apertura fuera del corte y modalidades inesperadas. PostgreSQL reemplaza el año en una transacción y compara las vistas con el resultado de Python antes de confirmar los cambios. Si una validación falla, sigue disponible la última carga confirmada. El bloqueo de sesión evita que se ejecuten dos cargas simultáneas. [Transacciones](https://www.psycopg.org/psycopg3/docs/basic/transactions.html) · [Bloqueos advisory](https://www.postgresql.org/docs/18/explicit-locking.html#ADVISORY-LOCKS)

## Diccionario de datos

| Tabla limpia y grano | Campos y origen OCDS |
| --- | --- |
| `corte` · un mes | `mes` es el primer día del corte. `total_portal` proviene del contador oficial. `sha256_zip` identifica el archivo de origen. `cargado_en` registra la carga en PostgreSQL. |
| `proceso` · un OCID | `ocid` identifica el proceso. `codigo` proviene de `tender.id`. `apertura` usa `tender.tenderPeriod.startDate`. `modalidad` usa `tender.procurementMethodDetails`. `entidad_id` y `entidad_nombre` vienen de `buyer`. `objeto`, `estado` y `numero_oferentes` vienen de `tender`. |
| `proceso_cpc` · un OCID y un código | `cpc` es `tender.items[].classification.id` si el esquema es `CPC`. |
| `adjudicacion` · un OCID y una adjudicación | `adjudicacion_id`, `fecha`, `estado`, `monto` y `moneda` vienen de `awards[]` y su objeto `value`. |
| `adjudicacion_proveedor` · un proveedor por adjudicación | `proveedor_id` y `proveedor_nombre` vienen de `awards[].suppliers[]`. |
| `contrato` · un OCID y un contrato | `contrato_id`, `adjudicacion_id`, `firma`, `estado`, `monto` y `moneda` vienen de `contracts[]`, incluidos `awardID`, `dateSigned` y `value`. |

Las dimensiones `dim_fecha`, `dim_entidad`, `dim_proveedor`, `dim_rubro` y `dim_procedimiento` sirven a los tres hechos. `proceso_rubro` y `contrato_proveedor` mantienen las relaciones que pueden tener más de una fila. Para sumar un monto tras unir una de esas relaciones, agrupa primero por la clave original de adjudicación o contrato. [Esquema OCDS](https://standard.open-contracting.org/latest/en/schema/reference/)

## Decisiones de limpieza

- Las fechas conservan el día que publica SERCOP y se tipan como `date`. La dimensión incluye todos los días del período de apertura y las fechas de adjudicación o firma fuera de ese período.
- Los montos usan `numeric` y conservan la precisión y moneda de origen. Los faltantes se representan con `NULL`. El valor de una adjudicación y el de un contrato son medidas distintas. [Política de publicación de SERCOP](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/documentos/politica-publicacion-SERCOP-OCDS.pdf)
- Se normalizan espacios en los nombres y se conserva el identificador publicado. La dimensión muestra el nombre informado más reciente por identificador. Las referencias entre contratos y adjudicaciones usan OCID e ID de adjudicación.
- Las filas hijas idénticas con la misma clave se guardan una vez. Una discrepancia bajo la misma clave aborta la carga. Los códigos CPC se mantienen como texto y los procesos sin código siguen en el denominador.

## Conciliación de la primera carga

| Control | Resultado |
| --- | ---: |
| Meses conciliados | 12 de 12 |
| Procesos de la modalidad | 18.333, igual al total de SERCOP |
| Procesos sin CPC | 1.014 |
| Procesos sin identificador o nombre de entidad | 0 |
| Procesos del piloto | 239 de 181 entidades, con los mismos OCID que la demo |
| Adjudicaciones | 15.722, incluidas 4 sin monto |
| Contratos | 14.683, incluidos 21 sin adjudicación vinculable por clave |

Los 21 contratos permanecen en `hecho_contrato` y se cuentan en `calidad_contratos`. El puente de proveedores incluye los vínculos verificables a través de la adjudicación. El portal oficial permite conciliar el total de procesos de esta modalidad. Los conteos de contratos y adjudicaciones se derivan de los archivos, con grano y fecha propios. [Fuente de SERCOP](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/datos-abiertos/)

## Ejecutar y consultar

En este equipo la base `compras_publicas` está en PostgreSQL 18.7, disponible en `127.0.0.1:55432` con el usuario `compras_pipeline`. El archivo `pgpass.conf` vive bajo `%LOCALAPPDATA%\compras-publicas-ecuador`. Desde la raíz del proyecto:

```powershell
.\scripts\actualizar_windows.ps1
.\scripts\actualizar_windows.ps1 -SoloServidor
.\scripts\actualizar_windows.ps1 -DesdeCrudo 'data\raw\2025-e31ff7d74a688ab16ddf0a4c00dc38c7750e70aa1c220d392b494e7df3fd0730.json'
```

La primera forma actualiza los doce cortes, la segunda inicia PostgreSQL para consultar la base y la tercera reproduce una captura sin acceder a SERCOP. En otro equipo, instala `requirements.txt` con Python 3.10 o posterior, crea una base PostgreSQL dedicada, configura `PGDATABASE`, `PGHOST`, `PGPORT`, `PGUSER` y `PGPASSFILE` según tu instancia y ejecuta `python -m scripts.cargar_postgres`. [Distribución de PostgreSQL para Windows](https://www.postgresql.org/download/windows/) · [Variables de conexión](https://www.postgresql.org/docs/18/libpq-envars.html)

```sql
SELECT * FROM analitico.calidad_mensual ORDER BY mes;
SELECT * FROM analitico.calidad_contratos ORDER BY mes;
SELECT mes, count(*) FROM analitico.piloto_87141 GROUP BY mes ORDER BY mes;
```

La actualización semanal usa `scripts/programar_windows.ps1` y se ejecuta los lunes a las 08:00, hora de Ecuador, con la sesión de Windows iniciada. Refresca los cortes de 2025 para incorporar correcciones que publique SERCOP. La última ejecución escribe en `actualizacion.log` bajo `%LOCALAPPDATA%\compras-publicas-ecuador`. [Programador de tareas de Windows](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/register-scheduledtask)
