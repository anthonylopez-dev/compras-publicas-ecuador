# Fase 4. Tableros de mantenimiento vehicular

Los dos tableros presentan las subastas inversas con apertura en 2025 del grupo CPC `87141`. Parten del mismo corte de PostgreSQL. El resumen muestra **239 procesos de 181 entidades y 201 contratos con monto positivo en USD**. Las otras páginas permiten comparar compradores por meses activos, consultar el número de oferentes, dimensionar contratos y abrir las fichas de SERCOP. [Análisis de la Fase 3](fase-3-hallazgos.md) · [Fuente de SERCOP](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/datos-abiertos/)

## Power BI Desktop

- [Informe PBIX con datos](../dashboards/powerbi/Mantenimiento%20vehicular.pbix)
- [Proyecto editable PBIP](../dashboards/powerbi/Mantenimiento%20vehicular.pbip)
- [Tema](../dashboards/powerbi/Mantenimiento%20vehicular.Report/StaticResources/RegisteredResources/Compras.json)
- [Capturas](../dashboards/capturas/) · [Recorrido narrado](../dashboards/recorrido.mp4)

El modelo relaciona las dimensiones Mes y Entidad con los hechos de procesos y contratos. La cobertura se relaciona solo con el mes y conserva el denominador nacional de la modalidad. Las medidas DAX distinguen aperturas, adjudicados con conteo, contratos y firmas. El informe incluye cinco páginas y sus marcadores.

El PBIX abre con los datos importados. Para refrescar la importación desde PostgreSQL, activa `UsarPostgreSQL`, configura `ServidorPostgreSQL` y autentícate en el conector de Power BI con un usuario autorizado para leer las vistas del proyecto. [Conector PostgreSQL de Power Query](https://learn.microsoft.com/en-us/power-query/connectors/postgresql) · [Base de la Fase 2](fase-2-datos.md)

El 22 de noviembre de 2026 se comprobó el refresco autenticado en una copia del PBIX en Power BI Desktop. Las cinco consultas a PostgreSQL coincidieron fila por fila con los datos incluidos en el proyecto. Tras autorizar las consultas y conectar a la instancia local, el resumen mostró **239 aperturas, 181 entidades, 201 contratos en USD y 94,5 % de cobertura CPC**. La instancia de prueba escuchaba solo en `127.0.0.1:55432` y la sesión local se realizó sin TLS.

## Web pública e incrustación

La [versión pública](https://compras-publicas-ecuador-vehicular.anthonyxm15.chatgpt.site) incluye filtros por entidad, mes y código CPC. Se comprobó la navegación en escritorio, móvil y dentro de un iframe desde otro origen mediante una sesión anónima.

Metabase ofrece enlaces e iframes públicos, con un servicio que hay que operar. Superset también admite incrustación, con configuración de acceso y, en su modalidad de SDK, un servicio que emita tokens. Para este corte histórico se publicó una web estática en Sites. Los filtros calculan resultados en el navegador a partir del extracto público. Los nombres de proveedores, contactos, credenciales y ZIP crudos quedan fuera de la publicación. [Metabase](https://www.metabase.com/docs/latest/embedding/public-links) · [Apache Superset](https://superset.apache.org/user-docs/using-superset/embedding/)

```html
<iframe
  title="Compras públicas de Ecuador · Mantenimiento vehicular"
  src="https://compras-publicas-ecuador-vehicular.anthonyxm15.chatgpt.site/?incrustado=1"
  width="100%"
  height="950"
  loading="lazy"
  style="border:0"
></iframe>
```

## Reproducir el corte

Desde el proyecto, con el entorno de Python y PostgreSQL de la Fase 2 activos:

```powershell
python -m scripts.exportar_tableros --salida dashboards/sitio
python -m scripts.construir_powerbi
```

El primer comando escribe los datos de la copia estática que acompaña al repositorio. Para preparar una nueva versión para Sites, exporta a `dashboards/web/dist` en el repositorio de despliegue independiente y publica desde allí. El segundo comando reconstruye el PBIP. Power BI Desktop permite refrescar la importación y guardar de nuevo como PBIX.

Queda por observar con una persona ajena al proyecto si el mensaje del resumen se entiende en 30 segundos.
