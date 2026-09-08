import os
import json
import html
import unicodedata

import gspread
from google.oauth2.service_account import Credentials


# ============================================================
# 1. GOOGLE SHEETS
# ============================================================

def conectar_spreadsheet(directorio_superior, google_credentials_json, google_sheet_url):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    ruta_credenciales = os.path.join(
        directorio_superior,
        google_credentials_json
    )

    print("Usando credenciales:", ruta_credenciales)

    credenciales = Credentials.from_service_account_file(
        ruta_credenciales,
        scopes=scopes
    )

    cliente = gspread.authorize(credenciales)
    spreadsheet = cliente.open_by_url(google_sheet_url)

    return spreadsheet


def leer_hoja_empresas(spreadsheet, nombre_hoja):
    try:
        hoja = spreadsheet.worksheet(nombre_hoja)
    except gspread.WorksheetNotFound:
        print(f"ERROR: No existe la hoja: {nombre_hoja}")
        return []

    datos = hoja.get_all_values()

    if not datos:
        print(f"La hoja {nombre_hoja} está vacía.")
        return []

    return datos


# ============================================================
# 2. UTILIDADES GENERALES
# ============================================================

def escapar(texto):
    if texto is None:
        return ""

    return html.escape(str(texto), quote=True)


def normalizar_texto(texto):
    texto = str(texto).strip().lower()

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )

    return texto


def tiene_valor(texto):
    if texto is None:
        return False

    texto = str(texto).strip()

    if texto == "":
        return False

    if texto.lower() in [
        "none",
        "null",
        "nan",
        "no_encontrado",
        "no encontrado",
        "sin datos",
        "sin descripcion",
        "sin descripción"
    ]:
        return False

    return True


def convertir_float(valor):
    if valor is None:
        return None

    valor = str(valor).strip().replace(",", ".")

    if valor == "":
        return None

    try:
        return float(valor)
    except ValueError:
        return None


def coordenadas_validas(latitud, longitud):
    lat = convertir_float(latitud)
    lon = convertir_float(longitud)

    if lat is None or lon is None:
        return False

    if lat < -90 or lat > 90:
        return False

    if lon < -180 or lon > 180:
        return False

    return True


def normalizar_cabecera(texto):
    return normalizar_texto(texto)


def obtener_valor_por_alias(fila, cabecera, alias):
    """
    Busca un campo usando varios posibles nombres de columna.

    Si hay cabeceras duplicadas, por ejemplo:
    Nombre ... nombre
    devuelve la primera columna que tenga valor real.
    """

    alias_normalizados = [
        normalizar_cabecera(a)
        for a in alias
    ]

    valores_encontrados = []

    for idx, nombre_columna in enumerate(cabecera):
        nombre_normalizado = normalizar_cabecera(nombre_columna)

        if nombre_normalizado in alias_normalizados:
            if idx < len(fila):
                valor = str(fila[idx]).strip()

                if tiene_valor(valor):
                    valores_encontrados.append(valor)

    if valores_encontrados:
        return valores_encontrados[0]

    return ""


# ============================================================
# 3. TAGS
# ============================================================

def convertir_tags_a_lista(valor):
    if valor is None:
        return []

    if isinstance(valor, list):
        partes = valor
    else:
        texto = str(valor).strip()
        texto = texto.replace(";", ",")
        partes = texto.split(",")

    tags = []

    for parte in partes:
        tag = str(parte).strip().lower()

        if tag.startswith("#"):
            tag = tag[1:]

        if tag and tag not in tags:
            tags.append(tag)

    return tags


def obtener_todos_los_tags(empresas):
    tags = []

    for empresa in empresas:
        for tag in empresa.get("tags", []):
            tag = str(tag).strip().lower()

            if tag and tag not in tags:
                tags.append(tag)

    return sorted(tags)


def generar_tags_html_empresa(empresa):
    tags = empresa.get("tags", [])

    html_tags = ""

    for tag in tags:
        html_tags += (
            f'<span class="tag-empresa" '
            f'data-tag="{escapar(tag)}">'
            f'{escapar(tag)}</span>'
        )

    return html_tags


def generar_filtro_tags_global(empresas):
    tags = obtener_todos_los_tags(empresas)

    html_tags = ""

    for tag in tags:
        html_tags += (
            f'<button class="tag-filtro" '
            f'data-tag="{escapar(tag)}">'
            f'{escapar(tag)}</button>'
        )

    return html_tags


# ============================================================
# 4. CONVERSIÓN DE FILAS A EMPRESAS
# ============================================================

def fila_a_empresa(fila, cabecera, numero_fila):
    nombre = obtener_valor_por_alias(
        fila,
        cabecera,
        ["Nombre", "nombre", "empresa", "Empresa", "title", "name"]
    )

    latitud = obtener_valor_por_alias(
        fila,
        cabecera,
        ["Latitud", "latitud", "lat", "latitude"]
    )

    longitud = obtener_valor_por_alias(
        fila,
        cabecera,
        ["Longitud", "longitud", "lon", "lng", "longitude"]
    )

    direccion = obtener_valor_por_alias(
        fila,
        cabecera,
        ["Dirección", "direccion", "dirección", "address", "streetAddress"]
    )

    descripcion = obtener_valor_por_alias(
        fila,
        cabecera,
        ["Descripción", "descripcion", "descripción", "description"]
    )

    tags_texto = obtener_valor_por_alias(
        fila,
        cabecera,
        ["Tags", "tags", "etiquetas", "keywords", "palabras_clave"]
    )

    ciclo = obtener_valor_por_alias(
        fila,
        cabecera,
        ["Ciclo Asignado", "ciclo", "Ciclo", "ciclo asignado"]
    )

    estado_agente = obtener_valor_por_alias(
        fila,
        cabecera,
        ["estado_agente", "Estado Agente", "estado"]
    )

    fuentes = obtener_valor_por_alias(
        fila,
        cabecera,
        ["fuentes", "Fuentes", "source", "sources"]
    )

    fecha_inclusion = obtener_valor_por_alias(
        fila,
        cabecera,
        ["fecha_inclusion", "Fecha inclusión", "fecha_alta", "fecha"]
    )

    if not tiene_valor(nombre):
        print(f"Fila {numero_fila} descartada: no tiene nombre.")
        return None

    if not coordenadas_validas(latitud, longitud):
        print(f"Fila {numero_fila} descartada: coordenadas no válidas para {nombre}.")
        return None

    empresa = {
        "nombre": nombre,
        "latitud": str(latitud).replace(",", "."),
        "longitud": str(longitud).replace(",", "."),
        "direccion": direccion,
        "descripcion": descripcion,
        "tags": convertir_tags_a_lista(tags_texto),
        "ciclo": ciclo,
        "estado_agente": estado_agente,
        "fuentes": fuentes,
        "fecha_inclusion": fecha_inclusion
    }

    return empresa


def convertir_filas_a_empresas(datos):
    if not datos:
        return []

    cabecera = datos[0]
    filas = datos[1:]

    print("\nCabecera detectada:")
    print(cabecera)

    empresas = []

    for numero_fila, fila in enumerate(filas, start=2):
        empresa = fila_a_empresa(
            fila=fila,
            cabecera=cabecera,
            numero_fila=numero_fila
        )

        if empresa:
            empresas.append(empresa)

    return empresas


def leer_empresas_desde_sheets(
    directorio_superior,
    google_credentials_json,
    google_sheet_url,
    nombre_hoja
):
    spreadsheet = conectar_spreadsheet(
        directorio_superior=directorio_superior,
        google_credentials_json=google_credentials_json,
        google_sheet_url=google_sheet_url
    )

    datos = leer_hoja_empresas(
        spreadsheet=spreadsheet,
        nombre_hoja=nombre_hoja
    )

    empresas = convertir_filas_a_empresas(datos)

    return empresas


# ============================================================
# 5. GENERACIÓN JSON
# ============================================================

def generar_json(empresas, ruta_json):
    carpeta = os.path.dirname(ruta_json)

    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(
            empresas,
            f,
            ensure_ascii=False,
            indent=4
        )

    print(f"JSON generado: {ruta_json}")


# ============================================================
# 6. HTML DE TARJETAS
# ============================================================

def generar_tarjeta_empresa(empresa):
    nombre = empresa.get("nombre", "")
    descripcion = empresa.get("descripcion", "")
    direccion = empresa.get("direccion", "")
    ciclo = empresa.get("ciclo", "")
    tags = empresa.get("tags", [])

    data_tags = ",".join(tags)

    return f"""
    <article
        class="tarjeta-empresa"
        data-nombre="{escapar(nombre.lower())}"
        data-tags="{escapar(data_tags.lower())}"
    >
        <h3>{escapar(nombre)}</h3>

        <p class="linea-ciclo">
            <strong>Ciclo:</strong> {escapar(ciclo)}
        </p>

        <p class="linea-direccion">
            <strong>Dirección:</strong> {escapar(direccion)}
        </p>

        <p class="descripcion">
            {escapar(descripcion)}
        </p>

        <div class="tags-empresa">
            {generar_tags_html_empresa(empresa)}
        </div>
    </article>
    """


# ============================================================
# 7. CSS
# ============================================================

def generar_css():
    return """
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: #f3f4f6;
    color: #111827;
}

.cabecera {
    background: #111827;
    color: white;
    padding: 18px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 24px;
}

.cabecera h1 {
    margin: 0;
    font-size: 26px;
}

.cabecera p {
    margin: 6px 0 0 0;
    color: #d1d5db;
}

.resumen-superior {
    display: flex;
    gap: 12px;
}

.dato-resumen {
    min-width: 90px;
    background: #1f2937;
    border: 1px solid #374151;
    border-radius: 14px;
    padding: 12px;
    text-align: center;
}

.dato-resumen span {
    display: block;
    font-size: 28px;
    font-weight: bold;
}

.dato-resumen small {
    color: #d1d5db;
    font-size: 13px;
}

.tabs-vista {
    display: flex;
    gap: 8px;
    background: #111827;
    padding: 0 24px 14px 24px;
}

.tab-vista {
    border: 1px solid #374151;
    background: #1f2937;
    color: #d1d5db;
    padding: 9px 16px;
    border-radius: 999px;
    font-size: 14px;
    cursor: pointer;
}

.tab-vista:hover {
    background: #374151;
}

.tab-vista.activo {
    background: #2563eb;
    border-color: #2563eb;
    color: white;
}

.vista-oculta {
    display: none !important;
}

.layout {
    height: calc(100vh - 96px);
    display: grid;
    grid-template-columns: 390px 1fr;
    grid-template-areas: "panel mapa";
}

.vista-fecha {
    height: calc(100vh - 96px);
    overflow-y: auto;
    padding: 24px;
    background: #f3f4f6;
}

.vista-fecha .contenedor-fecha {
    max-width: 900px;
    margin: 0 auto;
}

.vista-fecha h2 {
    margin: 0 0 4px 0;
}

.vista-fecha .subtitulo-fecha {
    margin: 0 0 20px 0;
    color: #6b7280;
    font-size: 14px;
}

.grupo-fecha {
    margin-bottom: 26px;
}

.grupo-fecha h3 {
    position: sticky;
    top: 0;
    background: #f3f4f6;
    margin: 0 0 10px 0;
    padding: 6px 0;
    font-size: 15px;
    color: #374151;
    border-bottom: 1px solid #e5e7eb;
}

.lista-por-fecha {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.tarjeta-fecha {
    border: 1px solid #e5e7eb;
    background: white;
    border-radius: 14px;
    padding: 14px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    transition: all 0.2s ease;
}

.tarjeta-fecha:hover {
    border-color: #2563eb;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
}

.tarjeta-fecha .info-empresa-fecha h4 {
    margin: 0 0 4px 0;
    font-size: 16px;
}

.tarjeta-fecha .info-empresa-fecha p {
    margin: 0;
    font-size: 13px;
    color: #6b7280;
}

.tarjeta-fecha .badge-ciclo {
    flex-shrink: 0;
    background: #eff6ff;
    color: #1d4ed8;
    border-radius: 999px;
    padding: 6px 12px;
    font-size: 12px;
    white-space: nowrap;
}

.panel-lateral {
    grid-area: panel;
    background: white;
    border-right: 1px solid #e5e7eb;
    overflow-y: auto;
    padding: 18px;
}

.zona-mapa {
    grid-area: mapa;
    min-height: 400px;
}

#map {
    width: 100%;
    height: 100%;
}

.bloque-filtros,
.bloque-tags,
.bloque-empresas {
    margin-bottom: 22px;
}

.bloque-filtros h2,
.bloque-tags h2,
.bloque-empresas h2 {
    margin: 0 0 10px 0;
    font-size: 18px;
}

#buscador {
    width: 100%;
    padding: 12px;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    font-size: 15px;
}

.acciones-filtro {
    margin-top: 10px;
}

#btnLimpiar {
    width: 100%;
    padding: 10px;
    border: none;
    border-radius: 10px;
    background: #374151;
    color: white;
    cursor: pointer;
}

#btnLimpiar:hover {
    background: #111827;
}

.contenedor-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.tag-filtro {
    border: 1px solid #d1d5db;
    background: #f9fafb;
    color: #374151;
    padding: 7px 10px;
    border-radius: 999px;
    font-size: 13px;
    cursor: pointer;
}

.tag-filtro:hover {
    background: #e5e7eb;
}

.tag-filtro.activo {
    color: white;
    border-color: transparent;
}

.contador-resultados {
    margin: 0 0 12px 0;
    color: #6b7280;
    font-size: 14px;
}

.lista-empresas {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.tarjeta-empresa {
    border: 1px solid #e5e7eb;
    background: white;
    border-radius: 14px;
    padding: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.tarjeta-empresa:hover {
    border-color: #2563eb;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
}

.tarjeta-empresa.destacada {
    border-width: 2px;
    background: #fff;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.16);
}

.tarjeta-empresa.oculta {
    display: none;
}

.tarjeta-empresa h3 {
    margin: 0 0 6px 0;
    font-size: 17px;
}

.tarjeta-empresa p {
    margin: 4px 0;
    font-size: 14px;
    color: #374151;
}

.descripcion {
    line-height: 1.35;
}

.tags-empresa {
    margin-top: 10px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.tag-empresa {
    background: #f9fafb;
    color: #075985;
    border-radius: 999px;
    padding: 4px 8px;
    font-size: 12px;
}

.tag-empresa.destacado {
    color: white;
}

.marker-normal {
    width: 16px;
    height: 16px;
    background: #2563eb;
    border: 3px solid white;
    border-radius: 50%;
    box-shadow: 0 2px 8px rgba(0,0,0,0.35);
}

.marker-color {
    width: 24px;
    height: 24px;
    border: 4px solid white;
    border-radius: 50%;
    box-shadow: 0 3px 12px rgba(0,0,0,0.45);
}

/* ============================= */
/* VERSIÓN MÓVIL */
/* ============================= */

@media (max-width: 768px) {

    body {
        background: #f3f4f6;
    }

    .cabecera {
        position: sticky;
        top: 0;
        z-index: 1000;
        padding: 12px;
        flex-direction: row;
        align-items: center;
    }

    .cabecera h1 {
        font-size: 18px;
        line-height: 1.2;
    }

    .cabecera p {
        display: none;
    }

    .tabs-vista {
        position: sticky;
        top: 0;
        z-index: 1000;
        padding: 10px 12px;
        overflow-x: auto;
    }

    .vista-fecha {
        height: auto;
        padding: 14px;
    }

    .resumen-superior {
        gap: 6px;
    }

    .dato-resumen {
        min-width: 66px;
        padding: 8px;
        border-radius: 10px;
    }

    .dato-resumen span {
        font-size: 20px;
    }

    .dato-resumen small {
        font-size: 11px;
    }

    .layout {
        height: auto;
        display: flex;
        flex-direction: column;
    }

    .zona-mapa {
        order: 1;
        width: 100%;
        height: 48vh;
        min-height: 320px;
        border-bottom: 1px solid #d1d5db;
    }

    #map {
        height: 100%;
    }

    .panel-lateral {
        order: 2;
        width: 100%;
        border-right: none;
        padding: 14px;
        overflow: visible;
    }

    .bloque-filtros {
        position: sticky;
        top: 68px;
        z-index: 900;
        background: #f3f4f6;
        padding: 10px 0;
    }

    .bloque-tags {
        background: white;
        padding: 14px;
        border-radius: 14px;
        border: 1px solid #e5e7eb;
    }

    .bloque-empresas {
        background: white;
        padding: 14px;
        border-radius: 14px;
        border: 1px solid #e5e7eb;
    }

    .contenedor-tags {
        max-height: 170px;
        overflow-y: auto;
        padding-bottom: 4px;
    }

    .tag-filtro {
        font-size: 12px;
        padding: 7px 9px;
    }

    .lista-empresas {
        gap: 10px;
    }

    .tarjeta-empresa {
        padding: 12px;
    }

    .tarjeta-empresa h3 {
        font-size: 16px;
    }

    .tarjeta-empresa p {
        font-size: 13px;
    }
}
"""


# ============================================================
# 8. JAVASCRIPT
# ============================================================

def generar_javascript():
    return """
const CENTRO_ZARAGOZA = [41.6488, -0.8891];
const ZOOM_ZARAGOZA_CIUDAD = 12;

let mapa = L.map('map').setView(CENTRO_ZARAGOZA, ZOOM_ZARAGOZA_CIUDAD);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap'
}).addTo(mapa);

let marcadores = [];

// Ahora permitimos varios tags activos
let tagsActivos = [];

const PALETA_TAGS = [
    '#7f1d1d',
    '#1d4ed8',
    '#047857',
    '#6d28d9',
    '#c2410c',
    '#0f766e',
    '#be123c',
    '#4338ca',
    '#a16207',
    '#15803d',
    '#0369a1',
    '#9333ea',
    '#b45309',
    '#0e7490',
    '#4d7c0f'
];

const iconoNormal = L.divIcon({
    className: '',
    html: '<div class="marker-normal"></div>',
    iconSize: [22, 22],
    iconAnchor: [11, 11]
});

function normalizarTexto(texto) {
    return String(texto || '')
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\\u0300-\\u036f]/g, '')
        .trim();
}

function obtenerTagsEmpresa(empresa) {
    if (Array.isArray(empresa.tags)) {
        return empresa.tags;
    }

    return String(empresa.tags || '')
        .split(',')
        .map(t => t.trim())
        .filter(t => t.length > 0);
}

function obtenerTodosLosTags() {
    const tags = [];

    empresas.forEach(empresa => {
        obtenerTagsEmpresa(empresa).forEach(tag => {
            const tagNorm = normalizarTexto(tag);

            if (tagNorm && !tags.some(t => normalizarTexto(t) === tagNorm)) {
                tags.push(tag);
            }
        });
    });

    return tags.sort((a, b) => normalizarTexto(a).localeCompare(normalizarTexto(b)));
}

const TAGS_GLOBALES = obtenerTodosLosTags();

function obtenerColorTag(tag) {
    const tagNorm = normalizarTexto(tag);

    let indice = TAGS_GLOBALES.findIndex(
        t => normalizarTexto(t) === tagNorm
    );

    if (indice < 0) {
        indice = 0;
    }

    return PALETA_TAGS[indice % PALETA_TAGS.length];
}

function crearIconoColor(color) {
    return L.divIcon({
        className: '',
        html: `<div class="marker-color" style="background:${color};"></div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
    });
}

function empresaTieneTag(empresa, tag) {
    if (!tag) {
        return false;
    }

    const tagNorm = normalizarTexto(tag);
    const tagsEmpresa = obtenerTagsEmpresa(empresa);

    return tagsEmpresa.some(t => normalizarTexto(t) === tagNorm);
}

function empresaTieneAlgunTagActivo(empresa) {
    if (tagsActivos.length === 0) {
        return true;
    }

    return tagsActivos.some(tag => empresaTieneTag(empresa, tag));
}

function obtenerPrimerTagActivoDeEmpresa(empresa) {
    for (const tag of tagsActivos) {
        if (empresaTieneTag(empresa, tag)) {
            return tag;
        }
    }

    return null;
}

function empresaCoincideTexto(empresa, texto) {
    if (!texto) {
        return true;
    }

    const t = normalizarTexto(texto);

    const campos = [
        empresa.nombre,
        empresa.descripcion,
        empresa.direccion,
        empresa.ciclo,
        obtenerTagsEmpresa(empresa).join(', ')
    ].join(' ');

    return normalizarTexto(campos).includes(t);
}

function limpiarMarcadores() {
    marcadores.forEach(m => mapa.removeLayer(m));
    marcadores = [];
}

function pintarMarcadores(empresasVisibles) {
    limpiarMarcadores();

    empresasVisibles.forEach(empresa => {
        const lat = parseFloat(empresa.latitud);
        const lon = parseFloat(empresa.longitud);

        if (isNaN(lat) || isNaN(lon)) {
            return;
        }

        let icono = iconoNormal;

        const primerTagActivo = obtenerPrimerTagActivoDeEmpresa(empresa);

        if (primerTagActivo) {
            const color = obtenerColorTag(primerTagActivo);
            icono = crearIconoColor(color);
        }

        const marcador = L.marker(
            [lat, lon],
            {
                icon: icono
            }
        ).addTo(mapa);

        marcador.bindPopup(`
            <strong>${empresa.nombre || ''}</strong><br>
            ${empresa.direccion || ''}<br>
            <small>${obtenerTagsEmpresa(empresa).join(', ')}</small>
        `);

        marcadores.push(marcador);
    });

    // No hacemos fitBounds.
    // El mapa no se mueve al seleccionar tags.
}

function tagEstaActivo(tag) {
    const tagNorm = normalizarTexto(tag);

    return tagsActivos.some(
        t => normalizarTexto(t) === tagNorm
    );
}

function activarODesactivarTag(tag) {
    const tagNorm = normalizarTexto(tag);

    const yaExiste = tagsActivos.some(
        t => normalizarTexto(t) === tagNorm
    );

    if (yaExiste) {
        tagsActivos = tagsActivos.filter(
            t => normalizarTexto(t) !== tagNorm
        );
    } else {
        tagsActivos.push(tag);
    }
}

function colorearTagsGlobales() {
    const botones = document.querySelectorAll('.tag-filtro');

    botones.forEach(boton => {
        const tag = boton.dataset.tag || boton.textContent;
        const color = obtenerColorTag(tag);

        boton.style.borderColor = color;

        if (tagEstaActivo(tag)) {
            boton.classList.add('activo');
            boton.style.backgroundColor = color;
            boton.style.color = 'white';
        } else {
            boton.classList.remove('activo');
            boton.style.backgroundColor = '';
            boton.style.color = color;
        }
    });
}

function colorearTagsEmpresa(tarjeta) {
    const tags = tarjeta.querySelectorAll('.tag-empresa');

    tags.forEach(tagElemento => {
        tagElemento.classList.remove('destacado');
        tagElemento.style.backgroundColor = '';
        tagElemento.style.color = '';

        const tagTexto = tagElemento.dataset.tag || tagElemento.textContent;
        const color = obtenerColorTag(tagTexto);

        tagElemento.style.border = `1px solid ${color}`;
        tagElemento.style.color = color;

        if (tagEstaActivo(tagTexto)) {
            tagElemento.classList.add('destacado');
            tagElemento.style.backgroundColor = color;
            tagElemento.style.color = 'white';
        }
    });
}

function aplicarFiltros() {
    const texto = document.getElementById('buscador').value || '';
    const tarjetas = document.querySelectorAll('.tarjeta-empresa');

    const empresasVisibles = [];

    tarjetas.forEach((tarjeta, index) => {
        const empresa = empresas[index];

        const coincideTexto = empresaCoincideTexto(empresa, texto);
        const coincideTags = empresaTieneAlgunTagActivo(empresa);

        const visible = coincideTexto && coincideTags;

        tarjeta.classList.toggle('oculta', !visible);
        tarjeta.classList.remove('destacada');
        tarjeta.style.borderColor = '';
        tarjeta.style.boxShadow = '';

        colorearTagsEmpresa(tarjeta);

        if (visible) {
            empresasVisibles.push(empresa);

            const primerTagActivo = obtenerPrimerTagActivoDeEmpresa(empresa);

            if (primerTagActivo) {
                const color = obtenerColorTag(primerTagActivo);

                tarjeta.classList.add('destacada');
                tarjeta.style.borderColor = color;
                tarjeta.style.boxShadow = `0 4px 16px ${color}44`;
            }
        }
    });

    pintarMarcadores(empresasVisibles);
    colorearTagsGlobales();

    const contador = document.getElementById('contadorResultados');

    if (contador) {
        if (tagsActivos.length === 0) {
            contador.textContent = `${empresasVisibles.length} empresas encontradas`;
        } else {
            contador.textContent = `${empresasVisibles.length} empresas encontradas con: ${tagsActivos.join(', ')}`;
        }
    }
}

function activarTags() {
    const botones = document.querySelectorAll('.tag-filtro');

    botones.forEach(boton => {
        boton.addEventListener('click', () => {
            const tag = boton.dataset.tag || boton.textContent;

            activarODesactivarTag(tag);

            aplicarFiltros();
        });
    });
}

function activarBuscador() {
    const buscador = document.getElementById('buscador');

    if (!buscador) {
        return;
    }

    buscador.addEventListener('input', () => {
        aplicarFiltros();
    });
}

function activarLimpiar() {
    const boton = document.getElementById('btnLimpiar');

    if (!boton) {
        return;
    }

    boton.addEventListener('click', () => {
        tagsActivos = [];

        const buscador = document.getElementById('buscador');

        if (buscador) {
            buscador.value = '';
        }

        document.querySelectorAll('.tag-filtro').forEach(b => {
            b.classList.remove('activo');
            b.style.backgroundColor = '';
        });

        document.querySelectorAll('.tag-empresa').forEach(t => {
            t.classList.remove('destacado');
            t.style.backgroundColor = '';
        });

        aplicarFiltros();

        mapa.setView(CENTRO_ZARAGOZA, ZOOM_ZARAGOZA_CIUDAD);
    });
}

function activarClickTarjetas() {
    const tarjetas = document.querySelectorAll('.tarjeta-empresa');

    tarjetas.forEach((tarjeta, index) => {
        tarjeta.addEventListener('click', () => {
            const empresa = empresas[index];

            const lat = parseFloat(empresa.latitud);
            const lon = parseFloat(empresa.longitud);

            if (!isNaN(lat) && !isNaN(lon)) {
                mapa.setView([lat, lon], 16);
            }

            tarjeta.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
        });
    });
}

const NOMBRES_MES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
];

function formatearFechaLarga(fechaTexto) {
    const partes = String(fechaTexto || '').split('-');

    if (partes.length !== 3) {
        return 'Sin fecha';
    }

    const [anio, mes, dia] = partes;
    const indiceMes = parseInt(mes, 10) - 1;
    const nombreMes = NOMBRES_MES[indiceMes] || mes;

    return `${parseInt(dia, 10)} de ${nombreMes} de ${anio}`;
}

function empresasOrdenadasPorFecha() {
    return [...empresas].sort((a, b) => {
        const fechaA = a.fecha_inclusion || '';
        const fechaB = b.fecha_inclusion || '';

        if (fechaA === fechaB) {
            return normalizarTexto(a.nombre).localeCompare(normalizarTexto(b.nombre));
        }

        // Sin fecha va al final
        if (!fechaA) return 1;
        if (!fechaB) return -1;

        return fechaB.localeCompare(fechaA);
    });
}

function centrarEnEmpresa(empresa) {
    const lat = parseFloat(empresa.latitud);
    const lon = parseFloat(empresa.longitud);

    cambiarVista('mapa');

    setTimeout(() => {
        if (!isNaN(lat) && !isNaN(lon)) {
            mapa.setView([lat, lon], 16);
        }
    }, 50);
}

function renderizarListaPorFecha() {
    const contenedor = document.getElementById('listaPorFecha');

    if (!contenedor) {
        return;
    }

    const ordenadas = empresasOrdenadasPorFecha();

    let fechaActualGrupo = null;
    let html = '';

    ordenadas.forEach(empresa => {
        const fecha = empresa.fecha_inclusion || '';

        if (fecha !== fechaActualGrupo) {
            if (fechaActualGrupo !== null) {
                html += '</div></div>';
            }

            html += `
                <div class="grupo-fecha">
                    <h3>${formatearFechaLarga(fecha)}</h3>
                    <div class="lista-por-fecha">
            `;

            fechaActualGrupo = fecha;
        }

        html += `
            <article class="tarjeta-fecha" data-nombre="${escaparHtml(empresa.nombre || '')}">
                <div class="info-empresa-fecha">
                    <h4>${escaparHtml(empresa.nombre || '')}</h4>
                    <p>${escaparHtml(empresa.direccion || '')}</p>
                </div>
                <span class="badge-ciclo">${escaparHtml(empresa.ciclo || '')}</span>
            </article>
        `;
    });

    if (fechaActualGrupo !== null) {
        html += '</div></div>';
    }

    contenedor.innerHTML = html;

    contenedor.querySelectorAll('.tarjeta-fecha').forEach((tarjeta, index) => {
        tarjeta.addEventListener('click', () => {
            centrarEnEmpresa(ordenadas[index]);
        });
    });
}

function escaparHtml(texto) {
    const div = document.createElement('div');
    div.textContent = String(texto || '');
    return div.innerHTML;
}

function cambiarVista(vista) {
    const vistaMapa = document.getElementById('vistaMapa');
    const vistaFecha = document.getElementById('vistaFecha');

    document.querySelectorAll('.tab-vista').forEach(boton => {
        boton.classList.toggle('activo', boton.dataset.vista === vista);
    });

    if (vista === 'mapa') {
        vistaMapa.classList.remove('vista-oculta');
        vistaFecha.classList.add('vista-oculta');

        setTimeout(() => {
            mapa.invalidateSize();
        }, 50);
    } else {
        vistaMapa.classList.add('vista-oculta');
        vistaFecha.classList.remove('vista-oculta');
    }
}

function activarTabsVista() {
    document.querySelectorAll('.tab-vista').forEach(boton => {
        boton.addEventListener('click', () => {
            cambiarVista(boton.dataset.vista);
        });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    activarTags();
    activarBuscador();
    activarLimpiar();
    activarClickTarjetas();
    activarTabsVista();
    aplicarFiltros();
    renderizarListaPorFecha();

    setTimeout(() => {
        mapa.invalidateSize();
    }, 300);
});
"""


# ============================================================
# 9. HTML COMPLETO
# ============================================================

def generar_html_completo(empresas):
    total_empresas = len(empresas)
    total_tags = len(obtener_todos_los_tags(empresas))

    tarjetas_html = "".join(
        generar_tarjeta_empresa(empresa)
        for empresa in empresas
    )

    tags_html = generar_filtro_tags_global(empresas)

    empresas_json = json.dumps(
        empresas,
        ensure_ascii=False
    )

    html_completo = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">

    <title>Mapa de empresas tecnológicas de Zaragoza</title>

    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    />

    <style>
        {generar_css()}
    </style>
</head>

<body>

    <header class="cabecera">
        <div>
            <h1>Empresas tecnológicas de Zaragoza</h1>
            <p>Mapa interactivo de empresas, ciclos y tecnologías.</p>
        </div>

        <div class="resumen-superior">
            <div class="dato-resumen">
                <span id="totalEmpresas">{total_empresas}</span>
                <small>empresas</small>
            </div>

            <div class="dato-resumen">
                <span id="totalTags">{total_tags}</span>
                <small>tags</small>
            </div>
        </div>
    </header>

    <nav class="tabs-vista">
        <button class="tab-vista activo" data-vista="mapa">🗺️ Mapa</button>
        <button class="tab-vista" data-vista="fecha">🕒 Por fecha de inclusión</button>
    </nav>

    <main class="layout" id="vistaMapa">

        <section class="zona-mapa">
            <div id="map"></div>
        </section>

        <aside class="panel-lateral">

            <div class="bloque-filtros">
                <h2>Filtros</h2>

                <input
                    type="text"
                    id="buscador"
                    placeholder="Buscar empresa o tag..."
                >

                <div class="acciones-filtro">
                    <button id="btnLimpiar">Limpiar filtros</button>
                </div>
            </div>

            <div class="bloque-tags">
                <h2>Tags</h2>

                <div id="contenedorTags" class="contenedor-tags">
                    {tags_html}
                </div>
            </div>

            <div class="bloque-empresas">
                <h2>Empresas</h2>

                <p id="contadorResultados" class="contador-resultados"></p>

                <div id="listaEmpresas" class="lista-empresas">
                    {tarjetas_html}
                </div>
            </div>

        </aside>

    </main>

    <main class="vista-fecha vista-oculta" id="vistaFecha">
        <div class="contenedor-fecha">
            <h2>Empresas por fecha de inclusión</h2>
            <p class="subtitulo-fecha">Orden cronológico, de la más reciente a la más antigua.</p>

            <div id="listaPorFecha"></div>
        </div>
    </main>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

    <script>
        const empresas = {empresas_json};

        {generar_javascript()}
    </script>

</body>
</html>
"""

    return html_completo


def guardar_html(html_completo, ruta_html):
    carpeta = os.path.dirname(ruta_html)

    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(html_completo)

    print(f"HTML generado: {ruta_html}")