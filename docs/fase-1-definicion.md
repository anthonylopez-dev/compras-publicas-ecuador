# Fase 1. Definición del tablero piloto

## Usuario y decisión

Una pyme ecuatoriana que ofrece mantenimiento vehicular al Estado necesita decidir **qué compradores seguir y cuándo revisar sus procesos**. El tablero muestra el historial de aperturas por entidad, permite filtrar por mes y enlaza cada proceso con su ficha de SERCOP.

## Alcance y unidad de análisis

Enero a diciembre de 2025 · Ecuador · Subasta Inversa Electrónica · CPC `87141`.

Cada observación es un OCID distinto con al menos un ítem de la convocatoria cuyo esquema de clasificación es `CPC` y cuyo código empieza por `87141`. El mes corresponde a la fecha registrada en `tender.tenderPeriod.startDate`, conservando el día que publica la fuente. Se agrupa por `buyer.id` y se muestra el último nombre observado para ese identificador. [SERCOP](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/datos-abiertos/) · [CPC 87141](https://aplicaciones2.ecuadorencifras.gob.ec/SIN/resul_correspondencia.php?ciiu=9&id=87141) · [Referencia OCDS](https://standard.open-contracting.org/latest/en/schema/reference/)

| Pregunta | Cálculo y campos |
| --- | --- |
| ¿Cuántos procesos encuentro con mis filtros? | Conteo de `ocid` distintos del rubro, filtrado por `buyer.id` y mes de `tender.tenderPeriod.startDate`. |
| ¿Cuántas entidades publicaron procesos del rubro? | Conteo de `buyer.id` distintos en los procesos filtrados. |
| ¿Qué entidades tuvieron más aperturas? | Conteo de OCID distintos por `buyer.id` en el mes seleccionado o en todo el año. El ranking muestra las primeras cinco entidades, con desempate alfabético. |
| ¿En qué meses abrió procesos una entidad? | Serie de doce conteos de OCID distintos por mes para la entidad seleccionada, con cero en meses sin procesos identificados. El indicador de meses activos cuenta meses con al menos un proceso entre los resultados filtrados. |
| ¿Qué procesos respaldan cada conteo? | Listado del nombre de entidad, `tender.description`, `tender.id` y fecha de apertura de los resultados filtrados. Cada fila enlaza a la ficha oficial por `ocid`. |
| ¿Qué parte de la fuente se pudo clasificar por rubro? | Para cada mes, OCID de la modalidad con al menos un ítem de esquema CPC y código informado ÷ todos los OCID de la modalidad. El tablero muestra también la diferencia en cantidad. Esta cobertura es nacional. |

## Verificación y entrega

Los doce ZIP coinciden con los conteos mensuales del portal y su suma coincide con el total anual. Se comprobaron **18.333 OCID distintos** en la modalidad. **239 procesos de 181 entidades** cumplen la regla del piloto. **1.014 procesos** de la modalidad carecen de CPC, lo que puede subestimar el conteo del rubro. Las cifras describen aperturas de 2025. Una evaluación de estacionalidad requiere más años y cobertura comparable.

La [demo local](../demo/index.html) incluye filtros, ranking, gráfico, fichas y cobertura por mes. Abre `demo/index.html` en el navegador con los archivos de la carpeta `demo`. Para regenerar sus datos desde la raíz del proyecto, ejecuta `python -m scripts.preparar_piloto`. El archivo generado conserva el total del portal y el hash de cada ZIP.

La hipótesis comercial es que el historial ahorra tiempo al priorizar compradores. Queda por probar con dos o tres proveedores del rubro usando la [guía de entrevistas de la Fase 0](fase-0-auditoria.md#primera-versión).
