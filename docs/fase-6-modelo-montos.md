# Fase 6. Rangos de monto contractual para mantenimiento vehicular

La prueba evaluó si conocer el código CPC permite estimar mejor el **monto total de un contrato** de mantenimiento vehicular. En aperturas de julio a diciembre de 2025, el rango general incluyó **43 de 99 contratos** y el modelo por CPC incluyó **36 de 99**. Ambos tuvieron un error medio cercano a **USD 40.000** al estimar el monto central. Con estos resultados se mantienen las referencias históricas del tablero. [Caso de estudio](fase-5-caso-de-estudio.md).

## Datos y validación temporal

Se usó el corte del 22 de noviembre de 2026 con **201 contratos** en USD, de monto positivo y con firma utilizable. Cada contrato se vincula con la fecha de apertura y los códigos del grupo CPC 87141 de su convocatoria. La prueba abarcó **99 contratos de 120 aperturas** del segundo semestre. En este corte cada proceso evaluado aportó un contrato. [Manifiesto del corte](corte-2025.json) · [Datos de SERCOP](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/datos-abiertos/).

Se ajustaron los modelos al inicio de cada mes de julio a diciembre. El ajuste usó contratos cuya apertura, firma y fecha de la entrega de SERCOP precedían al mes evaluado. La prueba usó los montos de los contratos de las convocatorias abiertas durante ese mes, incluidas las firmas de 2026 cuando correspondía. La fecha de la entrega es la que figura en `release.date` del ZIP. En 200 de los 201 contratos, esa fecha fue posterior a la firma. [Referencia OCDS](https://standard.open-contracting.org/latest/en/schema/reference/).

- **Modelo general.** Calcula la mediana y el intervalo del percentil 25 al 75 de todo el historial disponible.
- **Modelo por CPC.** Calcula los mismos valores para convocatorias con un único código del grupo 87141 y al menos 15 contratos históricos de ese código. Usa el rango general para los demás casos.

| Mes de apertura | Contratos en el historial disponible | Contratos evaluados | Casos con rango por CPC |
| --- | ---: | ---: | ---: |
| Julio | 29 | 23 | 0 |
| Agosto | 42 | 14 | 9 |
| Septiembre | 59 | 18 | 7 |
| Octubre | 76 | 16 | 6 |
| Noviembre | 87 | 12 | 9 |
| Diciembre | 95 | 16 | 6 |
| **Total evaluado** | | **99** | **37** |

## Resultados

| Modelo | Error absoluto medio de la mediana | Contratos dentro del rango | Anchura media | Puntuación media del intervalo |
| --- | ---: | ---: | ---: | ---: |
| General | USD 39.956,35 | 43/99 (43,4 %) | USD 29.279,27 | 139.003,26 |
| Por CPC con respaldo general | USD 39.941,84 | 36/99 (36,4 %) | USD 25.421,58 | 140.878,04 |

El error absoluto medio mide cuánto se apartó el monto estimado del monto contractual, en dólares. La cobertura indica cuántos montos entraron en el rango. La puntuación del intervalo suma su anchura y cuatro veces la distancia del monto al límite más cercano cuando cae fuera. Una puntuación menor indica mejor equilibrio entre anchura y cobertura para este intervalo central del 50 %.

El código permitió dar un rango específico en **37 de 99 casos**, todos del código `871410011`. El modelo por CPC redujo el error medio de la mediana en **USD 14,51**. Sus rangos más estrechos dejaron fuera siete contratos adicionales y empeoraron la puntuación del intervalo.

## Uso y límites

Una pyme puede seguir usando los montos históricos para elegir fichas comparables y revisar qué incluyen en flota, duración y repuestos. La estimación se refiere al contrato completo y se evalúa solo en procesos que llegaron a tener un contrato utilizable. El universo cubre una modalidad y un año de aperturas.

Las fechas proceden de una captura posterior. El filtro temporal reduce el uso anticipado de montos, pero la captura por sí sola no permite reconstruir todas las versiones de las convocatorias y los contratos tal como se veían cada mes. Para evaluar un uso predictivo harían falta capturas fechadas de un período posterior y datos de alcance comparables.

## Reproducir la prueba

Desde la raíz, con la base de PostgreSQL cargada y los ZIP de `data/raw/` correspondientes a sus hashes. El script lee la base y los ZIP y genera las tablas de resultados. Usa las dependencias ya fijadas en `requirements.txt`. [Guía de carga](fase-2-datos.md) · [Repetir el corte original](../README.md#repetir-el-corte-del-caso).

```powershell
python -m scripts.validar_montos
python -m unittest discover -s tests
```
