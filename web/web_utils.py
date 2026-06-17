import os
import json
import html

import gspread
from google.oauth2.service_account import Credentials


# ==================================================
# CONFIGURACIÓN INTERNA
# ==================================================

LAT_ZARAGOZA = 41.6488
LON_ZARAGOZA = -0.8891
ZOOM_ZARAGOZA = 12


# ==================================================
# GOOGLE SHEETS
# ==================================================

def conectar_spreadsheet(directorio_superior, google_credentials_json, google_sheet_url):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    ruta_credenciales = os.path.join(
        directorio_superior,
        google_credentials_json
    )

    print("🔐 Usando credenciales:", ruta_credenciales)

    credenciales = Credentials.from_service_account_file(
        ruta_credenciales,
        scopes=scopes
    )

    cliente = gspread.authorize(credenciales)
    spreadsheet = cliente.open_by_url(google_sheet_url)

    return spreadsheet


def leer_hoja_empresas(directorio_superior, google_credentials_json, google_sheet_url, nombre_hoja):
    spreadsheet = conectar_spreadsheet(
        directorio_superior,
        google_credentials_json,
        google_sheet_url
    )

    print("\n📚 Hojas disponibles:")
    for ws in spreadsheet.worksheets():
        print("-", ws.title)

    hoja = spreadsheet.worksheet(nombre_hoja)
    datos = hoja.get_all_values()

    print(f"\n📄 Hoja leída: {nombre_hoja}")
    print(f"Filas totales encontradas: {len(datos)}")

    if not datos:
        return [], []

    cabecera = datos[0]
    filas = datos[1:]

    print("\n📌 Cabecera detectada:")
    print(cabecera)

    return cabecera, filas


# ==================================================
# UTILIDADES DE TEXTO Y DATOS
# ==================================================

def normalizar_campo(campo):
    campo = str(campo).strip().lower()

    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n"
    }

    for origen, destino in reemplazos.items():
        campo = campo.replace(origen, destino)

    return campo


def obtener_valor(diccionario, posibles_campos, defecto=""):
    mapa = {}

    for clave, valor in diccionario.items():
        mapa[normalizar_campo(clave)] = valor

    for campo in posibles_campos:
        campo_normalizado = normalizar_campo(campo)

        if campo_normalizado in mapa:
            return mapa[campo_normalizado]

    return defecto


def limpiar_texto(valor):
    if valor is None:
        return ""

    return str(valor).strip()


def tiene_valor(valor):
    valor = limpiar_texto(valor)

    if valor == "":
        return False

    if valor.lower() in [
        "none",
        "null",
        "nan",
        "no encontrado",
        "no_encontrado",
        "sin datos"
    ]:
        return False

    return True


def convertir_float(valor):
    try:
        texto = str(valor).replace(",", ".").strip()

        if texto == "":
            return None

        return float(texto)

    except Exception:
        return None


def coordenadas_validas(latitud, longitud):
    if latitud is None or longitud is None:
        return False

    try:
        lat = float(latitud)
        lon = float(longitud)

        return -90 <= lat <= 90 and -180 <= lon <= 180

    except Exception:
        return False


def escapar(valor):
    return html.escape(str(valor), quote=True)


def convertir_tags_a_lista(tags):
    if tags is None:
        return []

    if isinstance(tags, list):
        return [limpiar_texto(t) for t in tags if limpiar_texto(t)]

    texto = limpiar_texto(tags)

    if texto == "":
        return []

    partes = texto.replace(";", ",").split(",")

    tags_limpios = []

    for parte in partes:
        tag = parte.strip()

        if tag.startswith("#"):
            tag = tag[1:]

        if tag and tag.lower() not in [t.lower() for t in tags_limpios]:
            tags_limpios.append(tag)

    return tags_limpios


def normalizar_tag(tag):
    tag = limpiar_texto(tag).lower()

    if tag.startswith("#"):
        tag = tag[1:]

    return tag.strip()


# ==================================================
# CONVERSIÓN DE FILAS A EMPRESAS
# ==================================================

def fila_a_empresa(cabecera, fila, numero_fila):
    empresa_raw = {}

    for i, campo in enumerate(cabecera):
        valor = fila[i] if i < len(fila) else ""
        empresa_raw[campo] = valor

    nombre = limpiar_texto(
        obtener_valor(
            empresa_raw,
            ["Nombre", "nombre", "empresa", "nombre_empresa", "name", "title"]
        )
    )

    latitud = convertir_float(
        obtener_valor(
            empresa_raw,
            ["Latitud", "latitud", "lat", "latitude"]
        )
    )

    longitud = convertir_float(
        obtener_valor(
            empresa_raw,
            ["Longitud", "longitud", "longtud", "lng", "lon", "longitude"]
        )
    )

    direccion = limpiar_texto(
        obtener_valor(
            empresa_raw,
            ["Dirección", "direccion", "dirección", "address"]
        )
    )

    descripcion = limpiar_texto(
        obtener_valor(
            empresa_raw,
            ["Descripción", "descripcion", "descripción", "description"]
        )
    )

    tags = limpiar_texto(
        obtener_valor(
            empresa_raw,
            ["Tags", "tags", "etiquetas", "keywords", "palabras_clave"]
        )
    )

    ciclo = limpiar_texto(
        obtener_valor(
            empresa_raw,
            [
                "Ciclo Asignado",
                "ciclo asignado",
                "ciclo",
                "familia",
                "fp",
                "ciclo_formativo"
            ]
        )
    )

    alumnos = limpiar_texto(
        obtener_valor(
            empresa_raw,
            ["NAlumnos", "nalumnos", "alumnos", "num_alumnos", "numero_alumnos"],
            "0"
        )
    )

    estado_agente = limpiar_texto(
        obtener_valor(
            empresa_raw,
            ["estado_agente", "Estado Agente", "estado"]
        )
    )

    fuentes = limpiar_texto(
        obtener_valor(
            empresa_raw,
            ["fuentes", "Fuentes", "source", "sources"]
        )
    )

    if not tiene_valor(nombre):
        print(f"⚠️ Fila {numero_fila} descartada: no tiene nombre.")
        return None

    if not coordenadas_validas(latitud, longitud):
        print(f"⚠️ {nombre}: sin coordenadas válidas. Se publicará tarjeta, pero no marcador.")

    return {
        "nombre": nombre,
        "latitud": latitud,
        "longitud": longitud,
        "direccion": direccion,
        "descripcion": descripcion,
        "tags": tags,
        "tags_lista": convertir_tags_a_lista(tags),
        "ciclo": ciclo if ciclo else "Otro",
        "alumnos": alumnos if alumnos else "0",
        "estado_agente": estado_agente if estado_agente else "Sin estado",
        "fuentes": fuentes
    }


def convertir_filas_a_empresas(cabecera, filas):
    empresas = []

    for numero_fila, fila in enumerate(filas, start=2):
        empresa = fila_a_empresa(cabecera, fila, numero_fila)

        if empresa is not None:
            empresas.append(empresa)

    print(f"\n✅ Empresas preparadas para publicar: {len(empresas)}")

    return empresas


def leer_empresas_desde_sheets(
    directorio_superior,
    google_credentials_json,
    google_sheet_url,
    nombre_hoja
):
    cabecera, filas = leer_hoja_empresas(
        directorio_superior,
        google_credentials_json,
        google_sheet_url,
        nombre_hoja
    )

    if not cabecera:
        print("⚠️ La hoja está vacía.")
        return []

    return convertir_filas_a_empresas(cabecera, filas)


# ==================================================
# JSON
# ==================================================

def generar_json(empresas, ruta_json):
    os.makedirs(os.path.dirname(ruta_json), exist_ok=True)

    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(empresas, f, ensure_ascii=False, indent=2)

    print(f"✅ JSON generado: {ruta_json}")


# ==================================================
# GENERACIÓN DE TARJETAS Y TAGS
# ==================================================

def generar_tags_html_empresa(empresa):
    tags = empresa.get("tags_lista", [])

    if not tags:
        return '<button class="tag tag-boton" data-tag="sintags">#SinTags</button>'

    partes = []

    for tag in tags:
        tag_visible = "#" + escapar(tag)
        tag_data = escapar(normalizar_tag(tag))

        partes.append(
            f'<button class="tag tag-boton" data-tag="{tag_data}">{tag_visible}</button>'
        )

    return "".join(partes)


def generar_tarjeta_empresa(empresa):
    nombre = escapar(empresa["nombre"])
    descripcion = escapar(empresa["descripcion"]) or "Sin descripción disponible."
    direccion = escapar(empresa["direccion"]) or "Dirección no disponible."
    ciclo = escapar(empresa["ciclo"])
    alumnos = escapar(empresa["alumnos"])
    estado_agente = escapar(empresa["estado_agente"])
    fuentes = escapar(empresa["fuentes"])

    tags_data = "|".join(
        normalizar_tag(tag)
        for tag in empresa.get("tags_lista", [])
    )

    texto_busqueda = " ".join([
        empresa["nombre"],
        empresa["descripcion"],
        empresa["direccion"],
        empresa["tags"],
        empresa["ciclo"],
        empresa["estado_agente"],
        empresa["fuentes"]
    ])

    texto_busqueda = escapar(texto_busqueda.lower())

    tiene_coords = coordenadas_validas(
        empresa["latitud"],
        empresa["longitud"]
    )

    if tiene_coords:
        latitud = empresa["latitud"]
        longitud = empresa["longitud"]
        clase_extra = " tarjeta-clicable"
        data_coords = f'data-lat="{latitud}" data-lng="{longitud}" data-nombre="{nombre}"'
    else:
        latitud = "Sin latitud"
        longitud = "Sin longitud"
        clase_extra = ""
        data_coords = f'data-nombre="{nombre}"'

    tags_html = generar_tags_html_empresa(empresa)

    if fuentes:
        fuentes_html = f'<p class="fuentes">🔗 Fuentes: {fuentes}</p>'
    else:
        fuentes_html = ""

    return f"""
            <div class="card{clase_extra}" 
                 {data_coords}
                 data-tags="{escapar(tags_data)}"
                 data-search="{texto_busqueda}">
                <div>
                    <h2>{nombre}</h2>
                    <span class="badge-ciclo">{ciclo}</span>
                    <p class="descripcion">{descripcion}</p>
                    <p class="direccion">📍 {direccion}</p>
                    {fuentes_html}
                </div>

                <div>
                    <div class="tags">{tags_html}</div>

                    <div class="info-footer">
                        <span>Lat: {latitud}, Lng: {longitud}</span>
                        <span>👥 Alumnos: <strong>{alumnos}</strong></span>
                    </div>

                    <div class="estado-footer">
                        Estado agente: <strong>{estado_agente}</strong>
                    </div>
                </div>
            </div>
"""


def obtener_todos_los_tags(empresas):
    tags = set()

    for empresa in empresas:
        for tag in empresa.get("tags_lista", []):
            tags.add(normalizar_tag(tag))

    return sorted(tags)


def generar_filtro_tags_global(empresas):
    tags = obtener_todos_los_tags(empresas)

    if not tags:
        return ""

    botones = []

    for tag in tags:
        botones.append(
            f'<button class="filtro-tag" data-tag="{escapar(tag)}">#{escapar(tag)}</button>'
        )

    return "\n".join(botones)


def generar_marcadores(empresas):
    marcadores = []

    for empresa in empresas:
        if not coordenadas_validas(empresa["latitud"], empresa["longitud"]):
            continue

        marcadores.append({
            "nombre": empresa["nombre"],
            "lat": empresa["latitud"],
            "lng": empresa["longitud"],
            "ciclo": empresa["ciclo"],
            "descripcion": empresa["descripcion"],
            "direccion": empresa["direccion"],
            "tags": empresa["tags"],
            "tags_lista": empresa["tags_lista"],
            "alumnos": empresa["alumnos"]
        })

    return marcadores


# ==================================================
# CSS
# ==================================================

def generar_css():
    return """
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background-color: #f4f7f6;
            margin: 0;
            padding: 0;
            color: #333;
        }

        header {
            background-color: #1e293b;
            color: white;
            text-align: center;
            padding: 1.5rem 1rem;
        }

        header h1 {
            margin: 0;
            font-size: 2rem;
        }

        header p {
            margin: 0.5rem 0 0 0;
            color: #cbd5e1;
        }

        .barra-info {
            max-width: 1200px;
            margin: 1rem auto 0 auto;
            padding: 0 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
        }

        .contador {
            background: white;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            font-weight: bold;
            color: #1e293b;
        }

        .buscador {
            flex: 1;
            min-width: 260px;
        }

        .buscador input {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            font-size: 1rem;
        }

        .panel-tags {
            max-width: 1200px;
            margin: 1rem auto 0 auto;
            padding: 0 1rem;
        }

        .panel-tags h3 {
            margin: 0 0 0.5rem 0;
            color: #1e293b;
            font-size: 1rem;
        }

        .filtros-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        .filtro-tag,
        .tag-boton {
            border: none;
            cursor: pointer;
            font-family: inherit;
        }

        .filtro-tag {
            background: #e2e8f0;
            color: #334155;
            padding: 0.4rem 0.7rem;
            border-radius: 999px;
            font-size: 0.85rem;
            transition: 0.2s;
        }

        .filtro-tag:hover {
            background: #fecaca;
            color: #7f1d1d;
        }

        .filtro-tag.activo {
            background: #7f1d1d;
            color: white;
        }

        .limpiar-filtros {
            background: #fee2e2;
            color: #991b1b;
        }

        #mapa-seccion {
            max-width: 1200px;
            margin: 1.5rem auto;
            padding: 0 1rem;
        }

        #map {
            height: 450px;
            width: 100%;
            border-radius: 8px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }

        main {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 1rem;
        }

        .grid-empresas {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
        }

        .card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border-left: 5px solid #3b82f6;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: 0.2s ease;
        }

        .card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 14px rgba(0,0,0,0.08);
        }

        .card.seleccionada {
            border-left-color: #7f1d1d;
            background-color: #fef2f2;
            box-shadow: 0 8px 18px rgba(127,29,29,0.20);
        }

        .card.coincide-busqueda {
            border-left-color: #0ea5e9;
            background-color: #f0f9ff;
        }

        .tarjeta-clicable {
            cursor: pointer;
        }

        .tarjeta-clicable:hover {
            border-left-color: #0ea5e9;
            background-color: #f8fafc;
        }

        .card h2 {
            margin-top: 0;
            color: #1e293b;
            font-size: 1.25rem;
        }

        .badge-ciclo {
            background-color: #e0f2fe;
            color: #0369a1;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.85rem;
            font-weight: bold;
            display: inline-block;
            margin-bottom: 1rem;
            align-self: flex-start;
        }

        .descripcion {
            font-size: 0.95rem;
            color: #4b5563;
            line-height: 1.4;
            margin-bottom: 1rem;
        }

        .direccion {
            font-size: 0.85rem;
            color: #64748b;
            line-height: 1.4;
        }

        .fuentes {
            font-size: 0.8rem;
            color: #64748b;
            word-break: break-word;
        }

        .tags {
            margin: 1rem 0;
        }

        .tag {
            background: #f1f5f9;
            color: #475569;
            padding: 0.25rem 0.55rem;
            border-radius: 4px;
            font-size: 0.8rem;
            margin-right: 0.5rem;
            display: inline-block;
            margin-bottom: 0.25rem;
        }

        .tag:hover {
            background: #fecaca;
            color: #7f1d1d;
        }

        .tag.activo {
            background: #7f1d1d;
            color: white;
        }

        .info-footer {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            font-size: 0.8rem;
            color: #64748b;
            border-top: 1px solid #f1f5f9;
            padding-top: 0.75rem;
            margin-top: auto;
            flex-wrap: wrap;
        }

        .estado-footer {
            margin-top: 0.5rem;
            font-size: 0.78rem;
            color: #64748b;
        }

        .popup h3 {
            margin: 0 0 0.5rem 0;
            color: #1e293b;
        }

        .popup p {
            margin: 0.25rem 0;
        }

        .marker-normal {
            width: 16px;
            height: 16px;
            background: #2563eb;
            border: 3px solid white;
            border-radius: 50%;
            box-shadow: 0 2px 8px rgba(0,0,0,0.35);
        }

        .marker-destacado {
            width: 22px;
            height: 22px;
            background: #7f1d1d;
            border: 4px solid white;
            border-radius: 50%;
            box-shadow: 0 3px 12px rgba(127,29,29,0.6);
        }

        footer {
            text-align: center;
            color: #64748b;
            padding: 2rem 1rem;
            font-size: 0.9rem;
        }

        @media (max-width: 700px) {
            header h1 {
                font-size: 1.5rem;
            }

            #map {
                height: 360px;
            }

            .grid-empresas {
                grid-template-columns: 1fr;
            }
        }
"""


# ==================================================
# JAVASCRIPT
# ==================================================

def generar_javascript(marcadores):
    marcadores_json = json.dumps(marcadores, ensure_ascii=False)

    return f"""
        const empresas = {marcadores_json};

        const map = L.map('map').setView([{LAT_ZARAGOZA}, {LON_ZARAGOZA}], {ZOOM_ZARAGOZA});

        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; OpenStreetMap contributors'
        }}).addTo(map);

        let marcadoresLeaflet = [];
        let marcadoresPorNombre = {{}};
        let tagActivo = null;

        const iconoNormal = L.divIcon({{
            className: "",
            html: '<div class="marker-normal"></div>',
            iconSize: [22, 22],
            iconAnchor: [11, 11],
            popupAnchor: [0, -10]
        }});

        const iconoDestacado = L.divIcon({{
            className: "",
            html: '<div class="marker-destacado"></div>',
            iconSize: [30, 30],
            iconAnchor: [15, 15],
            popupAnchor: [0, -14]
        }});

        function normalizarTag(tag) {{
            if (!tag) return "";
            return tag.toLowerCase().replace(/^#/, "").trim();
        }}

        function crearPopup(empresa) {{
            return `
                <div class="popup">
                    <h3>${{empresa.nombre}}</h3>
                    <p><strong>Ciclo:</strong> ${{empresa.ciclo || "Otro"}}</p>
                    <p><strong>Descripción:</strong> ${{empresa.descripcion || ""}}</p>
                    <p><strong>Dirección:</strong> ${{empresa.direccion || ""}}</p>
                    <p><strong>Tags:</strong> ${{empresa.tags || ""}}</p>
                    <p><strong>Alumnos:</strong> ${{empresa.alumnos || "0"}}</p>
                </div>
            `;
        }}

        function empresaTieneTag(empresa, tag) {{
            if (!tag) return false;

            const tags = empresa.tags_lista || [];

            return tags
                .map(t => normalizarTag(t))
                .includes(normalizarTag(tag));
        }}

        function obtenerTagsGlobales() {{
            const tags = new Set();

            empresas.forEach(empresa => {{
                (empresa.tags_lista || []).forEach(tag => {{
                    tags.add(normalizarTag(tag));
                }});
            }});

            return Array.from(tags).sort();
        }}

        function detectarTagDesdeTexto(texto) {{
            const t = normalizarTag(texto);

            if (t.length === 0) {{
                return null;
            }}

            const tags = obtenerTagsGlobales();
            const tagEncontrado = tags.find(tag => tag.startsWith(t));

            return tagEncontrado || null;
        }}

        function obtenerTagDeResaltado() {{
            const texto = document.getElementById("busqueda").value.toLowerCase().trim();

            if (tagActivo !== null) {{
                return tagActivo;
            }}

            return detectarTagDesdeTexto(texto);
        }}

        function pintarMarcadores(lista) {{
            marcadoresLeaflet.forEach(m => map.removeLayer(m));
            marcadoresLeaflet = [];
            marcadoresPorNombre = {{}};

            const tagResaltado = obtenerTagDeResaltado();

            lista.forEach(empresa => {{
                const destacar = tagResaltado !== null && empresaTieneTag(empresa, tagResaltado);

                const marker = L.marker(
                    [empresa.lat, empresa.lng],
                    {{
                        icon: destacar ? iconoDestacado : iconoNormal
                    }}
                )
                .addTo(map)
                .bindPopup(crearPopup(empresa));

                marcadoresLeaflet.push(marker);
                marcadoresPorNombre[empresa.nombre] = marker;
            }});

            map.setView([{LAT_ZARAGOZA}, {LON_ZARAGOZA}], {ZOOM_ZARAGOZA});
        }}

        function obtenerEmpresasVisiblesPorTarjetas() {{
            const tarjetas = document.querySelectorAll(".card");
            const visibles = [];

            tarjetas.forEach(tarjeta => {{
                if (tarjeta.style.display !== "none") {{
                    const nombre = tarjeta.dataset.nombre;
                    const empresa = empresas.find(e => e.nombre === nombre);

                    if (empresa) {{
                        visibles.push(empresa);
                    }}
                }}
            }});

            return visibles;
        }}

        function actualizarMarcadoresDesdeTarjetas() {{
            const visibles = obtenerEmpresasVisiblesPorTarjetas();
            pintarMarcadores(visibles);
        }}

        function aplicarFiltros() {{
            const texto = document.getElementById("busqueda").value.toLowerCase().trim();
            const tarjetas = document.querySelectorAll(".card");

            const tagDetectadoPorTexto = detectarTagDesdeTexto(texto);
            const tagFiltroEfectivo = tagActivo !== null ? tagActivo : null;
            const tagParaResaltar = tagActivo !== null ? tagActivo : tagDetectadoPorTexto;

            let visibles = 0;

            tarjetas.forEach(tarjeta => {{
                const contenido = tarjeta.dataset.search || "";
                const tags = tarjeta.dataset.tags || "";
                const listaTags = tags.split("|");

                const coincideTexto = texto === "" || contenido.includes(texto);
                const coincideTagActivo = tagFiltroEfectivo === null || listaTags.includes(tagFiltroEfectivo);

                if (coincideTexto && coincideTagActivo) {{
                    tarjeta.style.display = "flex";
                    visibles++;

                    tarjeta.classList.remove("seleccionada");
                    tarjeta.classList.remove("coincide-busqueda");

                    if (tagParaResaltar !== null && listaTags.includes(tagParaResaltar)) {{
                        tarjeta.classList.add("seleccionada");
                    }} else if (texto !== "") {{
                        tarjeta.classList.add("coincide-busqueda");
                    }}

                }} else {{
                    tarjeta.style.display = "none";
                    tarjeta.classList.remove("coincide-busqueda");
                    tarjeta.classList.remove("seleccionada");
                }}
            }});

            document.getElementById("contador-empresas").textContent = visibles;
            actualizarMarcadoresDesdeTarjetas();
            actualizarTagsActivos(tagParaResaltar);
        }}

        function actualizarTagsActivos(tagParaResaltar = null) {{
            document.querySelectorAll(".tag, .filtro-tag").forEach(boton => {{
                const tag = normalizarTag(boton.dataset.tag);

                if (tagParaResaltar !== null && tag === tagParaResaltar) {{
                    boton.classList.add("activo");
                }} else {{
                    boton.classList.remove("activo");
                }}
            }});
        }}

        function seleccionarTag(tag) {{
            const tagNormalizado = normalizarTag(tag);

            if (tagActivo === tagNormalizado) {{
                tagActivo = null;
            }} else {{
                tagActivo = tagNormalizado;
            }}

            aplicarFiltros();
        }}

        function limpiarFiltros() {{
            tagActivo = null;
            document.getElementById("busqueda").value = "";

            document.querySelectorAll(".card").forEach(tarjeta => {{
                tarjeta.style.display = "flex";
                tarjeta.classList.remove("seleccionada");
                tarjeta.classList.remove("coincide-busqueda");
            }});

            document.querySelectorAll(".tag, .filtro-tag").forEach(tag => {{
                tag.classList.remove("activo");
            }});

            document.getElementById("contador-empresas").textContent = document.querySelectorAll(".card").length;
            pintarMarcadores(empresas);
        }}

        function activarClickTags() {{
            document.querySelectorAll(".tag-boton, .filtro-tag").forEach(boton => {{
                boton.addEventListener("click", (event) => {{
                    event.stopPropagation();
                    seleccionarTag(boton.dataset.tag);
                }});
            }});

            const botonLimpiar = document.getElementById("limpiar-filtros");

            if (botonLimpiar) {{
                botonLimpiar.addEventListener("click", limpiarFiltros);
            }}
        }}

        function activarClickTarjetas() {{
            const tarjetas = document.querySelectorAll(".tarjeta-clicable");

            tarjetas.forEach(tarjeta => {{
                tarjeta.addEventListener("click", () => {{
                    const lat = Number(tarjeta.dataset.lat);
                    const lng = Number(tarjeta.dataset.lng);
                    const nombre = tarjeta.dataset.nombre;

                    if (!isNaN(lat) && !isNaN(lng)) {{
                        map.setView([lat, lng], 17);

                        const marcador = marcadoresPorNombre[nombre];

                        if (marcador) {{
                            marcador.openPopup();
                        }}
                    }}
                }});
            }});
        }}

        document.getElementById("busqueda").addEventListener("input", aplicarFiltros);

        pintarMarcadores(empresas);
        activarClickTarjetas();
        activarClickTags();
"""


# ==================================================
# HTML COMPLETO
# ==================================================

def generar_html_completo(empresas):
    tarjetas_html = "\n".join(
        generar_tarjeta_empresa(empresa)
        for empresa in empresas
    )

    filtros_tags_html = generar_filtro_tags_global(empresas)
    marcadores = generar_marcadores(empresas)

    total_empresas = len(empresas)
    total_marcadores = len(marcadores)

    css = generar_css()
    javascript = generar_javascript(marcadores)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IAProspector - Mapa de Empresas</title>

    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />

    <style>
{css}
    </style>
</head>
<body>

    <header>
        <h1>IAProspector: Mapa Tecnológico</h1>
        <p>Empresas sincronizadas automáticamente desde Google Sheets</p>
    </header>

    <section class="barra-info">
        <div class="contador">
            <span id="contador-empresas">{total_empresas}</span> empresas publicadas · {total_marcadores} con marcador
        </div>

        <div class="buscador">
            <input type="text" id="busqueda" placeholder="Escribe una empresa o las primeras letras de un tag...">
        </div>
    </section>

    <section class="panel-tags">
        <h3>Tags disponibles</h3>
        <div class="filtros-tags">
            {filtros_tags_html}
            <button class="filtro-tag limpiar-filtros" id="limpiar-filtros">Limpiar filtros</button>
        </div>
    </section>

    <section id="mapa-seccion">
        <div id="map"></div>
    </section>

    <main>
        <div class="grid-empresas" id="grid-empresas">
{tarjetas_html}
        </div>
    </main>

    <footer>
        IAProspector · Datos generados desde Google Sheets
    </footer>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

    <script>
{javascript}
    </script>
</body>
</html>
"""


def guardar_html(html_completo, ruta_html):
    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(html_completo)

    print(f"✅ HTML generado: {ruta_html}")