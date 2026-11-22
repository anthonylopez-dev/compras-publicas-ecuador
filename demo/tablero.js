"use strict";

const estado = document.querySelector("#estado");

if (typeof DATOS === "undefined") {
  estado.textContent = "No se cargaron los datos. Abre este tablero con los archivos de su carpeta demo.";
} else {
  iniciarTablero(DATOS);
}

function iniciarTablero({ cortes, procesos }) {
  const entidad = document.querySelector("#entidad");
  const mes = document.querySelector("#mes");
  const limpiar = document.querySelector("#limpiar");
  const grafico = document.querySelector("#grafico");
  const ranking = document.querySelector("#ranking");
  const tabla = document.querySelector("#procesos");
  const botonMas = document.querySelector("#mas");
  const tamanoPagina = 12;
  const formatoMes = new Intl.DateTimeFormat("es-EC", { month: "long", timeZone: "UTC" });
  const formatoFecha = new Intl.DateTimeFormat("es-EC", { dateStyle: "medium", timeZone: "UTC" });
  const formatoNumero = new Intl.NumberFormat("es-EC");
  const formatoPorcentaje = new Intl.NumberFormat("es-EC", { style: "percent", maximumFractionDigits: 1 });
  const ordenarTexto = new Intl.Collator("es-EC").compare;
  const nombres = new Map();
  let visibles = tamanoPagina;

  for (const proceso of procesos) {
    if (!nombres.has(proceso.entidad_id)) nombres.set(proceso.entidad_id, proceso.entidad);
  }
  for (const [id, nombre] of [...nombres].sort((a, b) => ordenarTexto(a[1], b[1]))) {
    entidad.add(new Option(nombre, id));
  }
  for (const corte of cortes) mes.add(new Option(nombreMes(corte.mes), corte.mes));

  entidad.addEventListener("change", aplicarFiltros);
  mes.addEventListener("change", aplicarFiltros);
  limpiar.addEventListener("click", () => {
    entidad.value = "";
    mes.value = "";
    aplicarFiltros();
    entidad.focus();
  });
  botonMas.addEventListener("click", () => {
    const primerNuevo = visibles;
    visibles += tamanoPagina;
    renderizarProcesos(filtrarProcesos());
    tabla.rows[primerNuevo]?.querySelector("a").focus();
  });

  renderizarCobertura();
  aplicarFiltros();
  document.querySelector("#tablero").hidden = false;
  estado.hidden = true;

  function nombreMes(valor) {
    return formatoMes.format(new Date(`${valor}-01T12:00:00Z`));
  }

  function contarPor(lista, clave) {
    const conteos = new Map();
    for (const proceso of lista) {
      const valor = clave(proceso);
      conteos.set(valor, (conteos.get(valor) ?? 0) + 1);
    }
    return conteos;
  }

  function filtrarProcesos() {
    return procesos.filter(proceso =>
      (!entidad.value || proceso.entidad_id === entidad.value) &&
      (!mes.value || proceso.apertura.startsWith(mes.value))
    );
  }

  function aplicarFiltros() {
    visibles = tamanoPagina;
    const filtrados = filtrarProcesos();
    document.querySelector("#total-procesos").textContent = formatoNumero.format(filtrados.length);
    document.querySelector("#total-entidades").textContent = contarPor(filtrados, p => p.entidad_id).size;
    document.querySelector("#total-meses").textContent = contarPor(filtrados, p => p.apertura.slice(0, 7)).size;
    limpiar.disabled = !entidad.value && !mes.value;
    renderizarGrafico();
    renderizarRanking();
    renderizarProcesos(filtrados);
  }

  function configurarFiltro(boton, control, valor, contenedor) {
    boton.type = "button";
    boton.value = valor;
    boton.setAttribute("aria-pressed", String(control.value === valor));
    boton.addEventListener("click", () => {
      control.value = control.value === valor ? "" : valor;
      aplicarFiltros();
      [...contenedor.querySelectorAll("button")].find(opcion => opcion.value === valor)?.focus();
    });
  }

  function renderizarGrafico() {
    const deEntidad = procesos.filter(p => !entidad.value || p.entidad_id === entidad.value);
    const porMes = contarPor(deEntidad, p => p.apertura.slice(0, 7));
    const maximo = Math.max(1, ...porMes.values());
    grafico.replaceChildren(...cortes.map(({ mes: periodo }) => {
      const valor = porMes.get(periodo) ?? 0;
      const nombre = nombreMes(periodo);
      const boton = document.createElement("button");
      boton.className = "columna";
      configurarFiltro(boton, mes, periodo, grafico);
      boton.setAttribute("aria-label", `${nombre}, ${valor} ${valor === 1 ? "proceso" : "procesos"}`);

      const marca = document.createElement("span");
      marca.className = "marca";
      const cifra = document.createElement("span");
      cifra.className = "valor";
      cifra.textContent = valor;
      const barra = document.createElement("span");
      barra.className = "barra";
      barra.style.setProperty("--altura", `${valor / maximo * 78}%`);
      marca.append(cifra, barra);

      const etiqueta = document.createElement("span");
      etiqueta.className = "mes";
      etiqueta.textContent = nombre.slice(0, 3);
      boton.append(marca, etiqueta);
      return boton;
    }));
  }

  function renderizarRanking() {
    const deMes = procesos.filter(p => !mes.value || p.apertura.startsWith(mes.value));
    const porEntidad = contarPor(deMes, p => p.entidad_id);
    const principales = [...porEntidad].sort((a, b) => b[1] - a[1] || ordenarTexto(nombres.get(a[0]), nombres.get(b[0])));
    document.querySelector("#periodo-ranking").textContent = mes.value
      ? `Procesos abiertos en ${nombreMes(mes.value)} de 2025`
      : "Procesos abiertos en 2025";
    document.querySelector("#ranking-vacio").hidden = principales.length > 0;
    ranking.replaceChildren(...principales.slice(0, 5).map(([id, cantidad]) => {
      const fila = document.createElement("li");
      const boton = document.createElement("button");
      configurarFiltro(boton, entidad, id, ranking);

      const nombre = document.createElement("span");
      nombre.className = "nombre-entidad";
      nombre.textContent = nombres.get(id);
      nombre.title = nombre.textContent;
      const cifra = document.createElement("span");
      cifra.className = "conteo-entidad";
      cifra.textContent = cantidad;
      boton.setAttribute("aria-label", `${nombre.textContent}, ${cantidad} ${cantidad === 1 ? "proceso" : "procesos"}`);
      boton.append(nombre, cifra);
      fila.append(boton);
      return fila;
    }));
  }

  function renderizarProcesos(filtrados) {
    tabla.replaceChildren();
    for (const proceso of filtrados.slice(0, visibles)) {
      const fila = tabla.insertRow();
      fila.insertCell().textContent = formatoFecha.format(new Date(`${proceso.apertura}T12:00:00Z`));
      fila.insertCell().textContent = nombres.get(proceso.entidad_id);
      const objeto = fila.insertCell();
      objeto.textContent = proceso.objeto || "Objeto no informado";
      const codigo = document.createElement("span");
      codigo.className = "codigo";
      codigo.textContent = proceso.codigo;
      objeto.append(codigo);

      const enlace = document.createElement("a");
      enlace.href = `https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/ocds/${encodeURIComponent(proceso.ocid)}`;
      enlace.target = "_blank";
      enlace.rel = "noopener";
      enlace.textContent = "Ver en SERCOP";
      enlace.setAttribute("aria-label", `Ver ${proceso.codigo} en SERCOP (nueva pestaña)`);
      fila.insertCell().append(enlace);
    }

    document.querySelector("#resumen-resultados").textContent = filtrados.length
      ? `${Math.min(visibles, filtrados.length)} de ${formatoNumero.format(filtrados.length)} procesos, del más reciente al más antiguo.`
      : "No hay procesos del rubro para los filtros seleccionados.";
    botonMas.hidden = filtrados.length <= visibles;
    document.querySelector("#tabla-procesos").hidden = filtrados.length === 0;
  }

  function renderizarCobertura() {
    const filas = document.querySelector("#filas-cobertura");
    let total = 0;
    let sinCodigo = 0;
    for (const corte of cortes) {
      const faltantes = corte.total - corte.con_cpc;
      total += corte.total;
      sinCodigo += faltantes;
      const fila = filas.insertRow();
      const titulo = document.createElement("th");
      titulo.scope = "row";
      titulo.textContent = nombreMes(corte.mes);
      fila.append(titulo);
      fila.insertCell().textContent = formatoNumero.format(corte.total);
      fila.insertCell().textContent = formatoNumero.format(faltantes);
      fila.insertCell().textContent = corte.total ? formatoPorcentaje.format(corte.con_cpc / corte.total) : "—";
    }
    document.querySelector("#resumen-cobertura").textContent =
      `${formatoNumero.format(sinCodigo)} de ${formatoNumero.format(total)} sin código en 2025`;
  }
}
