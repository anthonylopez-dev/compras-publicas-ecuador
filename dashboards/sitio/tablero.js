"use strict";

const $ = (id) => document.getElementById(id);

if (typeof DATOS === "undefined") {
  $("estado").textContent = "Los datos del tablero no están disponibles. Recarga la página.";
} else {
  iniciar(DATOS);
}

function iniciar({ cortes, entidades, procesos, contratos }) {
  const opciones = document.querySelectorAll("[data-vista]");
  const filtros = [$("entidad"), $("mes"), $("cpc")];
  const nombres = new Map(entidades.map(({ id, nombre }) => [id, nombre]));
  const colacion = new Intl.Collator("es-EC");
  const formatoNumero = new Intl.NumberFormat("es-EC");
  const formatoUSD = new Intl.NumberFormat("es-EC", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const formatoPct = new Intl.NumberFormat("es-EC", { style: "percent", maximumFractionDigits: 1 });
  const pagina = 15;
  let vista = "resumen";
  let visibles = pagina;

  document.documentElement.classList.toggle("incrustado", new URLSearchParams(location.search).get("incrustado") === "1");
  for (const e of [...entidades].sort((a, b) => colacion.compare(a.nombre, b.nombre))) {
    $("entidad").add(new Option(e.nombre, e.id));
  }
  for (const c of cortes) $("mes").add(new Option(c.nombre, c.mes));
  const codigos = [...new Set(procesos.flatMap(p => p.cpc))].sort();
  for (const c of codigos) $("cpc").add(new Option(c, c));

  function numero(n) { return formatoNumero.format(n); }
  function porcentaje(n, total) { return total ? formatoPct.format(n / total) : "Sin datos"; }
  function usd(n) { return "USD " + formatoUSD.format(n); }
  function nodo(tipo, texto, clase) {
    const el = document.createElement(tipo);
    if (texto != null) el.textContent = texto;
    if (clase) el.className = clase;
    return el;
  }

  function tabla(destino, titulos, filas, vacio = "No hay resultados para estos filtros.") {
    if (!filas.length) {
      $(destino).replaceChildren(nodo("p", vacio, "ayuda"));
      return;
    }
    const t = nodo("table");
    const cabecera = t.createTHead().insertRow();
    for (const titulo of titulos) {
      const th = nodo("th", titulo);
      th.scope = "col";
      cabecera.append(th);
    }
    const cuerpo = t.createTBody();
    for (const columnas of filas) {
      const fila = cuerpo.insertRow();
      for (const contenido of columnas) {
        const td = fila.insertCell();
        td.append(contenido);
      }
    }
    $(destino).replaceChildren(t);
  }

  function indicadores(id, filas, clase) {
    const lista = clase ? nodo("dl", null, clase) : $(id);
    lista.replaceChildren(...filas.map(([etiqueta, valor]) => {
      const casilla = nodo("div");
      casilla.append(nodo("dt", etiqueta), nodo("dd", valor));
      return casilla;
    }));
    if (clase) $(id).replaceChildren(lista);
  }

  function baseAnual() {
    return procesos.filter(p => (!$("entidad").value || p.entidad === Number($("entidad").value))
      && (!$("cpc").value || p.cpc.includes($("cpc").value)));
  }

  function percentil(ordenados, p) {
    const posicion = (ordenados.length - 1) * p;
    const inicio = Math.floor(posicion);
    return ordenados[inicio] + (ordenados[Math.ceil(posicion)] - ordenados[inicio]) * (posicion - inicio);
  }

  function activar(valor, enfocar = false) {
    vista = valor;
    for (const opcion of opciones) {
      const activa = opcion.dataset.vista === vista;
      opcion.setAttribute("aria-pressed", String(activa));
      $(opcion.dataset.vista).hidden = !activa;
      if (activa && enfocar) opcion.focus();
    }
    dibujar();
  }

  function dibujar() {
    const anual = baseAnual();
    const seleccionado = Number($("mes").value);
    const lista = anual.filter(p => !seleccionado || p.mes === seleccionado);
    const ids = new Set(lista.map(p => p.ocid));
    const firmados = contratos.filter(c => ids.has(c.ocid));
    $("limpiar").disabled = filtros.every(f => !f.value) && !$("buscar").value;
    $("seleccion").textContent = numero(lista.length) + " procesos para los filtros seleccionados.";
    if (vista === "resumen") resumen(lista, anual, firmados, seleccionado);
    if (vista === "compradores") compradores(lista);
    if (vista === "competencia") competencia(lista, firmados);
    if (vista === "montos") montos(lista, firmados);
    if (vista === "procesos") listado(lista);
  }

  function resumen(lista, anual, firmados, seleccionado) {
    const adjudicados = lista.filter(p => p.adjudicado && p.oferentes != null);
    const unoDos = adjudicados.filter(p => p.oferentes >= 1 && p.oferentes <= 2).length;
    indicadores("indicadores", [
      ["Procesos del rubro", numero(lista.length)], ["Entidades", numero(new Set(lista.map(p => p.entidad)).size)],
      ["Contratos en USD", numero(firmados.length)], ["Adjudicados con 1–2 oferentes", porcentaje(unoDos, adjudicados.length)],
    ]);

    const conteos = cortes.map(c => anual.filter(p => p.mes === c.mes).length);
    const maximo = Math.max(...conteos, 1);
    $("calendario").replaceChildren(...cortes.map((c, i) => {
      const boton = nodo("button", null, "columna");
      boton.type = "button";
      boton.dataset.mes = c.mes;
      boton.setAttribute("aria-label", c.nombre + ", " + conteos[i] + " procesos");
      boton.setAttribute("aria-pressed", String(seleccionado === c.mes));
      const pista = nodo("span", null, "pista");
      const barra = nodo("span", null, "barra");
      barra.style.setProperty("--alto", (conteos[i] / maximo * 78) + "%");
      pista.append(nodo("strong", conteos[i]), barra);
      boton.append(pista, nodo("span", c.nombre, "mes"));
      boton.addEventListener("click", () => {
        $("mes").value = seleccionado === c.mes ? "" : String(c.mes);
        dibujar();
        $("calendario").querySelector('[data-mes="' + c.mes + '"]').focus();
      });
      return boton;
    }));
  }

  function compradores(lista) {
    const porEntidad = new Map();
    for (const p of lista) {
      if (!porEntidad.has(p.entidad)) porEntidad.set(p.entidad, []);
      porEntidad.get(p.entidad).push(p);
    }
    const datos = [...porEntidad].map(([id, grupo]) => ({
      id, nombre: nombres.get(id), cantidad: grupo.length,
      meses: [...new Set(grupo.map(p => p.mes))].sort((a, b) => a - b),
    }));
    datos.sort((a, b) => b.meses.length - a.meses.length || b.cantidad - a.cantidad || colacion.compare(a.nombre, b.nombre));
    $("bajada-compradores").textContent = "Ordenado por meses activos en la selección. Puedes abrir los procesos de cada entidad.";
    tabla("ranking", ["Entidad", "Procesos", "Meses activos", "Meses observados"], datos.map(e => {
      const enlace = nodo("button", e.nombre, "enlace-entidad");
      enlace.type = "button";
      enlace.addEventListener("click", () => {
        $("entidad").value = String(e.id);
        $("buscar").value = "";
        visibles = pagina;
        activar("procesos", true);
      });
      return [enlace, numero(e.cantidad), numero(e.meses.length), e.meses.map(m => cortes[m - 1].nombre).join(", ")];
    }));
  }

  function competencia(lista, firmados) {
    const conocidos = lista.filter(p => p.adjudicado && p.oferentes != null);
    const frecuencias = new Map();
    for (const { oferentes: n } of conocidos) frecuencias.set(n, (frecuencias.get(n) ?? 0) + 1);
    const maximo = Math.max(...frecuencias.values(), 1);
    const pocos = conocidos.filter(p => p.oferentes >= 1 && p.oferentes <= 2).length;
    $("bajada-competencia").textContent = conocidos.length
      ? numero(pocos) + " de " + numero(conocidos.length) + " adjudicados con conteo tuvieron 1 o 2 oferentes."
      : "La selección carece de adjudicados con conteo publicado.";
    $("oferentes").replaceChildren(...[...frecuencias].sort((a, b) => a[0] - b[0]).map(([n, total]) => {
      const fila = nodo("div", null, "barra-fila");
      const barra = nodo("span", null, "barra-horizontal");
      barra.style.setProperty("--ancho", (100 * total / maximo) + "%");
      barra.setAttribute("aria-hidden", "true");
      fila.append(nodo("span", n + (n === 1 ? " oferente" : " oferentes")), barra, nodo("strong", numero(total)));
      return fila;
    }));
    const vinculados = firmados.filter(c => c.proveedor_vinculado).length;
    $("proveedores").textContent = numero(vinculados) + " de " + numero(firmados.length) + " contratos en USD tienen un proveedor enlazado.";
  }

  function montos(lista, firmados) {
    const valores = firmados.map(c => c.monto).sort((a, b) => a - b);
    const dias = lista.filter(p => p.dias_firma != null).map(p => p.dias_firma).sort((a, b) => a - b);
    indicadores("importes", [
      ["Contratos con monto positivo en USD", numero(valores.length)],
      ["Mediana", valores.length ? usd(percentil(valores, .5)) : "Sin datos"],
      ["Mitad central", valores.length ? usd(percentil(valores, .25)) + " a " + usd(percentil(valores, .75)) : "Sin datos"],
    ], "estadisticas");
    indicadores("firmas", [
      ["Procesos con fecha de firma", numero(dias.length)],
      ["Mediana", dias.length ? numero(percentil(dias, .5)) + " días" : "Sin datos"],
      ["Más de 60 días", numero(dias.filter(d => d > 60).length)],
      ["Sin una firma registrada", numero(lista.length - dias.length)],
    ], "estadisticas");
  }

  function listado(lista) {
    const consulta = $("buscar").value.trim().toLocaleLowerCase("es-EC");
    const filas = lista.filter(p => (p.codigo + " " + nombres.get(p.entidad)).toLocaleLowerCase("es-EC").includes(consulta));
    const fecha = new Intl.DateTimeFormat("es-EC", { dateStyle: "medium", timeZone: "UTC" });
    tabla("listado", ["Apertura", "Entidad", "Código del proceso", "CPC", "Ficha oficial"], filas.slice(0, visibles).map(p => {
      const enlace = nodo("a", "Ver en SERCOP");
      enlace.href = "https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/ocds/" + encodeURIComponent(p.ocid);
      enlace.target = "_blank";
      enlace.rel = "noopener";
      enlace.setAttribute("aria-label", "Ver " + p.codigo + " en SERCOP (nueva pestaña)");
      return [fecha.format(new Date(p.apertura + "T12:00:00Z")), nombres.get(p.entidad), p.codigo, p.cpc.join(", "), enlace];
    }));
    $("conteo-procesos").textContent = numero(Math.min(visibles, filas.length)) + " de " + numero(filas.length) + " procesos.";
    $("mas").hidden = visibles >= filas.length;
  }

  const apariciones = new Map();
  for (const p of procesos) apariciones.set(p.entidad, (apariciones.get(p.entidad) ?? 0) + 1);
  const unicos = [...apariciones.values()].filter(n => n === 1).length;
  $("lectura").textContent = numero(unicos) + " de " + numero(entidades.length) +
    " entidades abrieron un solo proceso. Juntas aportaron el " + porcentaje(unicos, procesos.length) + " de las aperturas.";
  const total = cortes.reduce((s, c) => s + c.total, 0);
  const faltan = cortes.reduce((s, c) => s + c.sin_cpc, 0);
  $("resumen-cobertura").textContent = numero(faltan) + " de " + numero(total) + " sin CPC";
  tabla("cobertura", ["Mes", "Total", "Sin CPC", "Cobertura"], cortes.map(c => [
    c.nombre, numero(c.total), numero(c.sin_cpc), porcentaje(c.total - c.sin_cpc, c.total),
  ]));
  for (const opcion of opciones) opcion.addEventListener("click", () => activar(opcion.dataset.vista));
  for (const boton of document.querySelectorAll("[data-ir]")) boton.addEventListener("click", () => activar(boton.dataset.ir, true));
  for (const filtro of filtros) filtro.addEventListener("change", () => { visibles = pagina; dibujar(); });
  $("buscar").addEventListener("input", () => { visibles = pagina; dibujar(); });
  $("limpiar").addEventListener("click", () => {
    for (const filtro of filtros) filtro.value = "";
    $("buscar").value = "";
    visibles = pagina;
    dibujar();
    $("entidad").focus();
  });
  $("mas").addEventListener("click", () => {
    const siguiente = visibles;
    visibles += pagina;
    dibujar();
    $("listado").querySelectorAll("tbody tr")[siguiente]?.querySelector("a")?.focus();
  });
  dibujar();
  $("estado").hidden = true;
  $("tablero").hidden = false;
}
