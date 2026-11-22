# Fase 0. Auditoría de datos

22 de noviembre de 2026 · Ecuador

## Decisión

**Avanzar con compras públicas de Ecuador.** La primera versión ayudará a una pyme de mantenimiento vehicular a identificar qué entidades abren procesos de su rubro y en qué meses. El piloto se acota a Subasta Inversa Electrónica y al grupo CPC `87141`. En cuatro cortes hay **92 procesos del rubro de 79 entidades**. El clasificador oficial confirma el alcance del código. [Clasificador del INEC](https://aplicaciones2.ecuadorencifras.gob.ec/SIN/resul_correspondencia.php?ciiu=9&id=87141)

## Compras públicas · SERCOP

SERCOP publica datos en OCDS desde enero de 2015. Al revisar el selector, el último mes disponible era noviembre de 2026, que estaba en curso. La fuente ofrece descargas JSON, CSV y XLSX y una API de consultas. Las notas metodológicas indican que las descargas masivas se actualizan a diario. La política identifica la licencia **CC BY 3.0 Ecuador**, que permite la reutilización comercial con atribución. En el tablero se acreditará al SERCOP, se enlazarán la fuente y la licencia y se describirán las transformaciones. [Descargas](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/datos-abiertos/) · [API](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/datos-abiertos/api) · [Notas metodológicas](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/notas-metodologicas) · [Política de publicación](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/documentos/politica-publicacion-SERCOP-OCDS.pdf) · [Licencia](https://creativecommons.org/licenses/by/3.0/ec/)

Se descargaron cuatro ZIP del mismo procedimiento, comparando octubre en tres años y añadiendo marzo de 2025 como otro mes del calendario. Se contaron procesos por OCID y se comparó cada ZIP con el contador que usa el portal para los mismos filtros. [Portal de descargas de SERCOP](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/datos-abiertos/)

| Corte | Procesos únicos | Con CPC en al menos un ítem | Con número de oferentes | Con adjudicación | Procesos CPC `87141` |
| --- | ---: | ---: | ---: | ---: | ---: |
| Oct. 2024 | 2.553 | 2.397 (93,9 %) | 2.498 | 2.194 | 37 |
| Mar. 2025 | 1.661 | 1.573 (94,7 %) | 1.641 | 1.450 | 16 |
| Oct. 2025 | 1.462 | 1.391 (95,1 %) | 1.440 | 1.261 | 18 |
| Oct. 2026 | 1.232 | 1.040 (84,4 %) | 1.202 | 619 | 21 |
| **Total** | **6.908** | **6.401 (92,7 %)** | **6.781** | **5.524** | **92** |

- Los cuatro conteos coincidieron con el portal. Cada proceso tenía identificador de entidad y fecha de inicio de presentación de ofertas dentro del mes del corte. El OCID fue único dentro de cada corte y entre los cuatro cortes.
- Usar `tender.tenderPeriod.startDate` para agrupar por mes. En octubre de 2026, 1.140 de 1.232 entregas llevan fecha de noviembre en `release.date`. Esa diferencia cambia el mes asignado al proceso. [Referencia OCDS](https://standard.open-contracting.org/latest/en/schema/reference/)
- Mostrar la cobertura mensual de CPC junto a los conteos del rubro. En el corte más reciente faltó CPC en 192 de 1.232 procesos. Ese faltante deja una parte de la muestra sin rubro identificable y puede afectar las comparaciones.
- El campo de número de oferentes permite explorar competencia después de comprobar su significado y cobertura en procesos cerrados. El alcance de cada servicio, su unidad y los ajustes de valores publicados requieren una revisión adicional antes de comparar precios. Los cortes recientes pueden incorporar adjudicaciones con el tiempo. [Política de publicación y ajustes de valores de SERCOP](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/documentos/politica-publicacion-SERCOP-OCDS.pdf)

## Alternativa · Importaciones de régimen general

El catálogo del SENAE ofrece CSV con registros de salida autorizada, archivos desde 2013 con huecos entre semestres y un corte reciente de enero a octubre de 2026. El catálogo declara Creative Commons Attribution y enlaza una referencia genérica a CC BY. El archivo más reciente pesa unos 423 MB. El servidor respondió con el archivo completo a una solicitud de rango, así que la prueba leyó los primeros 256 KiB y cerró la conexión. [Catálogo del SENAE](https://www.datosabiertos.gob.ec/dataset/datos-de-declaraciones-aduaneras-de-importacion-regimen-general) · [Metadatos del catálogo](https://www.datosabiertos.gob.ec/api/3/action/package_show?id=datos-de-declaraciones-aduaneras-de-importacion-regimen-general)

El fragmento contiene 763 filas completas y 484 subpartidas distintas. Se validaron la fecha de ingreso, el código de subpartida de diez dígitos y los valores numéricos FOB y CIF en las 763 filas. La muestra sirve para verificar el esquema y ensayar una serie por producto y país de origen. Queda pendiente medir faltantes y duplicados en el archivo completo.

## Matriz comparativa

Escala de 1 a 5 por criterio técnico. Las puntuaciones son un juicio preliminar basado en las fuentes y muestras anteriores. El dolor del cliente y la disposición a pagar quedan pendientes de entrevistas.

| Criterio | Compras públicas | Importaciones |
| --- | --- | --- |
| Cobertura temporal | 5 · Desde 2015 | 4 · Desde 2013, con huecos |
| Volumen | 5 · 6.908 procesos en cuatro cortes de un procedimiento | 5 · El último archivo ocupa unos 423 MB |
| Calidad para el piloto | 4 · Entidad y fecha completas, CPC variable | 3 · Esquema verificable, calidad global pendiente |
| Facilidad de acceso | 5 · ZIP por mes y modalidad, API documentada | 3 · CSV voluminoso, servidor sin rango en la prueba |
| Licencia | 5 · CC BY 3.0 EC en la política de SERCOP | 4 · CC BY en el catálogo, versión sin precisar |
| Actualización | 5 · Diaria según la fuente | 4 · Cortes acumulados recientes |
| Potencial para ciencia de datos | 4 · Series por comprador y rubro, sujeto a cobertura | 4 · Series por subpartida y origen, sujeto a continuidad |
| **Total técnico** | **33/35** | **27/35** |
| Dolor del cliente | Pendiente de entrevistas | Pendiente de entrevistas |
| Posibilidad de monetización | Pendiente de entrevistas | Pendiente de entrevistas |

## Primera versión

Una vista con los principales compradores y un conteo mensual de OCID distintos por fecha de apertura. Empezar con enero a diciembre de 2025 para cubrir un año completo. Mostrar los procesos sin CPC por mes y vincular cada proceso a su ficha oficial. Ampliar el historial antes de hablar de estacionalidad. SERCOP ya ofrece búsqueda por palabra clave y entidad, así que la hipótesis de valor es ahorrar tiempo al identificar compradores recurrentes y planificar cuándo revisar sus procesos. [Buscador oficial de SERCOP](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/procedimientos)

Guía para las primeras conversaciones con dos o tres proveedores del rubro.

1. ¿Cómo encontraste el último proceso que te interesó y cuánto tiempo te tomó revisarlo?
2. ¿Qué información del historial de la entidad habría cambiado tu decisión de participar?
3. Al ver una lista de compradores con su historial mensual, ¿qué acción concreta tomarías esta semana?

## Reproducir la auditoría de SERCOP

Ejecutar desde la carpeta del proyecto con Python 3.8 o posterior.

```powershell
python scripts/auditar_sercop.py
python -m unittest discover -s tests
```

El script descarga los cuatro cortes, consulta los totales del portal e imprime los conteos y el SHA-256 de cada ZIP. Los conteos de esta auditoría corresponden a las descargas del día de revisión. SERCOP actualiza también los cortes históricos.
