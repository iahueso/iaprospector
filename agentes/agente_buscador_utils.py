import os
import sys
import json
import time
import random
import requests
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

from ddgs import DDGS

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic


# ==================================================
# 0. IMPORTAR CONFIG DESDE DIRECTORIO SUPERIOR
# ==================================================

DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
DIRECTORIO_SUPERIOR = os.path.dirname(DIRECTORIO_ACTUAL)

if DIRECTORIO_SUPERIOR not in sys.path:
    sys.path.append(DIRECTORIO_SUPERIOR)

try:
    from config import (
        ANTHROPIC_API_KEY,
        GOOGLE_SHEET_URL,
        GOOGLE_CREDENTIALS_JSON,
        GEOAPIFY_API_KEY
    )

    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY

except ImportError as e:
    print("❌ Error importando config.py")
    print(e)
    exit(1)


# ==================================================
# 1. CONFIGURACIÓN GENERAL
# ==================================================

HOJA_BASE = "empresas_base"
HOJA_FINALES = "empresas_finales"
HOJA_NODATA = "empresas_nodata"
HOJA_TAGS = "tags"

CIUDAD = "Zaragoza"
REGION = "Aragón"
PAIS = "España"

MAX_EMPRESAS_WEB = 5

CABECERA_BASE = [
    "nombre",
    "procesada"
]

CABECERA_FINALES = [
    "Nombre",
    "Latitud",
    "Longitud",
    "Dirección",
    "Descripción",
    "Tags",
    "Ciclo Asignado",
    "NAlumnos",
    "estado_agente",
    "fuentes",
    "fecha_inclusion"
]

CABECERA_NODATA = [
    "Nombre",
    "Descripción",
    "Tags",
    "Ciclo Asignado",
    "Dirección Intentada",
    "motivo_error",
    "estado_agente",
    "origen",
    "fuentes",
    "fecha"
]

CABECERA_TAGS = [
    "tags"
]

CICLOS_VALIDOS = [
    "DAM",
    "DAW",
    "ASIR",
    "IA y Big Data",
    "Transporte y Logística",
    "Administración",
    "Marketing",
    "Otro"
]


# ==================================================
# 2. TAGS BASE Y PLANTILLAS DE BÚSQUEDA
# ==================================================

TAGS_BUSQUEDA_WEB = [
    "software",
    "desarrollo web",
    "desarrollo de aplicaciones",
    "inteligencia artificial",
    "machine learning",
    "big data",
    "datos",
    "cloud",
    "ciberseguridad",
    "redes",
    "sistemas",
    "automatización",
    "robótica",
    "industria 4.0",
    "consultoría tecnológica",
    "transformación digital",
    "ERP",
    "CRM",
    "ecommerce",
    "marketing digital",
    "logística",
    "IoT",
    "realidad aumentada",
    "videojuegos",
    "diseño 3D",
    "hardware",
    "soporte informático"
]

PLANTILLAS_CONSULTA_WEB = [
    "empresas tecnológicas Zaragoza {tags}",
    "startups Zaragoza {tags}",
    "empresas TIC Zaragoza {tags}",
    "consultoras tecnológicas Zaragoza {tags}",
    "empresas de software en Zaragoza {tags}",
    "empresas digitales Zaragoza {tags}",
    "empresas innovación tecnológica Zaragoza {tags}",
    "empresas informática Zaragoza {tags}",
    "empresas desarrollo aplicaciones Zaragoza {tags}",
    "empresas transformación digital Zaragoza {tags}",
    "empresas tecnológicas Aragón Zaragoza {tags}",
    "empresas IA Zaragoza {tags}",
    "empresas cloud Zaragoza {tags}",
    "empresas ciberseguridad Zaragoza {tags}"
]

NUM_CONSULTAS_WEB_POR_PASADA = 5
NUM_TAGS_POR_CONSULTA_MIN = 3
NUM_TAGS_POR_CONSULTA_MAX = 4


# ==================================================
# 3. GOOGLE SHEETS
# ==================================================

def conectar_spreadsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    ruta_credenciales = os.path.join(
        DIRECTORIO_SUPERIOR,
        GOOGLE_CREDENTIALS_JSON
    )

    print("🔐 Usando credenciales:", ruta_credenciales)

    credenciales = Credentials.from_service_account_file(
        ruta_credenciales,
        scopes=scopes
    )

    cliente = gspread.authorize(credenciales)
    spreadsheet = cliente.open_by_url(GOOGLE_SHEET_URL)

    return spreadsheet


def obtener_o_crear_hoja(spreadsheet, nombre_hoja, cabecera):
    try:
        hoja = spreadsheet.worksheet(nombre_hoja)

    except gspread.WorksheetNotFound:
        hoja = spreadsheet.add_worksheet(
            title=nombre_hoja,
            rows=1000,
            cols=max(20, len(cabecera))
        )
        hoja.append_row(cabecera)
        print(f"✅ Hoja creada: {nombre_hoja}")
        return hoja

    datos = hoja.get_all_values()

    if not datos:
        hoja.append_row(cabecera)

    asegurar_cabecera(hoja, cabecera)

    return hoja


def asegurar_cabecera(hoja, cabecera_deseada):
    datos = hoja.get_all_values()

    if not datos:
        hoja.append_row(cabecera_deseada)
        return cabecera_deseada

    cabecera_actual = datos[0]
    cambios = False

    for campo in cabecera_deseada:
        if campo not in cabecera_actual:
            cabecera_actual.append(campo)
            cambios = True

    if cambios:
        hoja.update("1:1", [cabecera_actual])
        print(f"✅ Cabecera actualizada en {hoja.title}")

    return cabecera_actual


def preparar_hojas():
    spreadsheet = conectar_spreadsheet()

    hoja_base = obtener_o_crear_hoja(
        spreadsheet,
        HOJA_BASE,
        CABECERA_BASE
    )

    hoja_finales = obtener_o_crear_hoja(
        spreadsheet,
        HOJA_FINALES,
        CABECERA_FINALES
    )

    hoja_nodata = obtener_o_crear_hoja(
        spreadsheet,
        HOJA_NODATA,
        CABECERA_NODATA
    )

    hoja_tags = obtener_o_crear_hoja(
        spreadsheet,
        HOJA_TAGS,
        CABECERA_TAGS
    )

    return hoja_base, hoja_finales, hoja_nodata, hoja_tags


def buscar_indice_columna(cabecera, posibles_nombres):
    cabecera_normalizada = [
        str(c).strip().lower()
        for c in cabecera
    ]

    for nombre in posibles_nombres:
        nombre = nombre.lower()

        if nombre in cabecera_normalizada:
            return cabecera_normalizada.index(nombre)

    return None


def valor_columna(fila, idx):
    if idx is None:
        return ""

    if idx >= len(fila):
        return ""

    return str(fila[idx]).strip()


def celda_a1(fila_google, columna_python):
    return gspread.utils.rowcol_to_a1(
        fila_google,
        columna_python + 1
    )


# ==================================================
# 4. UTILIDADES
# ==================================================

def fecha_actual():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fecha_hoy():
    return datetime.now().strftime("%Y-%m-%d")


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
        "sin descripción",
        "sin descripcion",
        "sin tags",
        "sin datos"
    ]:
        return False

    return True


def normalizar_nombre(nombre):
    nombre = str(nombre).strip().lower()

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
        nombre = nombre.replace(origen, destino)

    quitar = [
        " s.l.",
        " s.l",
        " sl",
        " s.a.",
        " s.a",
        " sa",
        " sociedad limitada",
        " sociedad anonima",
        " sociedad anónima",
        ",",
        ".",
        ";",
        ":",
        "-",
        "_"
    ]

    for q in quitar:
        nombre = nombre.replace(q, " ")

    nombre = " ".join(nombre.split())

    return nombre


def es_procesada(valor):
    valor = str(valor).strip().lower()

    return valor in [
        "sí",
        "si",
        "s",
        "yes",
        "true",
        "1",
        "procesada",
        "ok"
    ]


def contenido_a_texto(contenido):
    # Con ChatAnthropic, content puede ser una lista de bloques
    # [{"type": "text", "text": "..."}, ...] en lugar de un string.
    if isinstance(contenido, list):
        partes = []

        for bloque in contenido:
            if isinstance(bloque, dict):
                if bloque.get("type", "text") == "text":
                    partes.append(str(bloque.get("text", "")))
            else:
                partes.append(str(bloque))

        return "\n".join(partes)

    return str(contenido)


def limpiar_json_respuesta(texto):
    texto = contenido_a_texto(texto).strip()

    if texto.startswith("```json"):
        texto = texto.replace("```json", "", 1).strip()

    if texto.startswith("```"):
        texto = texto.replace("```", "", 1).strip()

    if texto.endswith("```"):
        texto = texto[:-3].strip()

    inicio = texto.find("{")
    fin = texto.rfind("}")

    if inicio != -1 and fin != -1 and fin > inicio:
        texto = texto[inicio:fin + 1]

    return texto


def lista_a_texto(valor):
    if valor is None:
        return ""

    if isinstance(valor, list):
        limpios = []

        for item in valor:
            item = str(item).strip()

            if item and item.lower() not in [x.lower() for x in limpios]:
                limpios.append(item)

        return ", ".join(limpios)

    return str(valor).strip()


def convertir_texto_tags_a_lista(texto_tags):
    if texto_tags is None:
        return []

    texto = str(texto_tags).strip()

    if texto == "":
        return []

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


def normalizar_tags(valor):
    texto = lista_a_texto(valor)

    tags = convertir_texto_tags_a_lista(texto)

    return ", ".join(tags)


def normalizar_ciclo(ciclo):
    ciclo = str(ciclo).strip()

    if ciclo not in CICLOS_VALIDOS:
        return "Otro"

    return ciclo


# ==================================================
# 5. GESTIÓN DE TAGS
# ==================================================

def leer_tags_hoja(hoja_tags):
    datos = hoja_tags.get_all_values()

    if len(datos) < 2:
        return []

    texto_tags = datos[1][0] if datos[1] else ""

    return convertir_texto_tags_a_lista(texto_tags)


def guardar_tags_hoja(hoja_tags, tags):
    tags_limpios = []

    for tag in tags:
        tag = str(tag).strip().lower()

        if tag.startswith("#"):
            tag = tag[1:]

        if tag and tag not in tags_limpios:
            tags_limpios.append(tag)

    tags_limpios = sorted(tags_limpios)

    texto = ", ".join(tags_limpios)

    datos = hoja_tags.get_all_values()

    if not datos:
        hoja_tags.append_row(["tags"])

    if len(datos) < 2:
        hoja_tags.append_row([texto])
    else:
        hoja_tags.update_cell(2, 1, texto)

    print(f"✅ Hoja tags actualizada con {len(tags_limpios)} tags.")


def extraer_tags_desde_empresas_finales(hoja_finales):
    datos = hoja_finales.get_all_values()

    if not datos:
        return []

    cabecera = datos[0]
    filas = datos[1:]

    idx_tags = buscar_indice_columna(
        cabecera,
        ["Tags", "tags", "etiquetas", "keywords", "palabras_clave"]
    )

    if idx_tags is None:
        print("⚠️ No se encontró columna Tags en empresas_finales.")
        return []

    todos_los_tags = []

    for fila in filas:
        texto_tags = valor_columna(fila, idx_tags)
        tags = convertir_texto_tags_a_lista(texto_tags)

        for tag in tags:
            if tag not in todos_los_tags:
                todos_los_tags.append(tag)

    return todos_los_tags


def asegurar_tags_disponibles(hoja_tags, hoja_finales):
    tags_actuales = leer_tags_hoja(hoja_tags)

    if tags_actuales:
        print(f"🏷️ Tags leídos desde hoja tags: {len(tags_actuales)}")
        return tags_actuales

    print("⚠️ La hoja tags está vacía.")
    print("🔎 Revisando empresas_finales para extraer tags existentes...")

    tags_desde_finales = extraer_tags_desde_empresas_finales(hoja_finales)

    if tags_desde_finales:
        guardar_tags_hoja(hoja_tags, tags_desde_finales)
        return tags_desde_finales

    print("⚠️ No se encontraron tags en empresas_finales.")
    print("🏷️ Usando tags base por defecto.")

    guardar_tags_hoja(hoja_tags, TAGS_BUSQUEDA_WEB)

    return TAGS_BUSQUEDA_WEB


def actualizar_tags_con_empresa(hoja_tags, empresa):
    tags_actuales = leer_tags_hoja(hoja_tags)

    tags_empresa = convertir_texto_tags_a_lista(
        empresa.get("tags", "")
    )

    hubo_cambios = False

    for tag in tags_empresa:
        if tag not in tags_actuales:
            tags_actuales.append(tag)
            hubo_cambios = True

    if hubo_cambios:
        guardar_tags_hoja(hoja_tags, tags_actuales)
        print(f"🏷️ Nuevos tags añadidos desde empresa: {empresa.get('nombre', '')}")
    else:
        print("ℹ️ La empresa no aporta tags nuevos.")


# ==================================================
# 6. EMPRESAS EXISTENTES
# ==================================================

def obtener_nombres_empresas_de_hoja(hoja):
    datos = hoja.get_all_values()

    if not datos:
        return set()

    cabecera = datos[0]
    filas = datos[1:]

    idx_nombre = buscar_indice_columna(
        cabecera,
        ["Nombre", "nombre", "empresa", "nombre_empresa", "title", "name"]
    )

    if idx_nombre is None:
        idx_nombre = 0

    nombres = set()

    for fila in filas:
        nombre = valor_columna(fila, idx_nombre)

        if tiene_valor(nombre):
            nombres.add(normalizar_nombre(nombre))

    return nombres


def obtener_nombres_finales_y_globales(hoja_finales, hoja_nodata):
    nombres_finales = obtener_nombres_empresas_de_hoja(hoja_finales)
    nombres_nodata = obtener_nombres_empresas_de_hoja(hoja_nodata)

    nombres_globales = set()
    nombres_globales.update(nombres_finales)
    nombres_globales.update(nombres_nodata)

    return nombres_finales, nombres_nodata, nombres_globales


# ==================================================
# 7. TOOL DE BÚSQUEDA WEB
# ==================================================

@tool
def buscar_en_internet(consulta: str) -> dict:
    """
    Busca información en internet.
    Devuelve los 5 primeros resultados con título, enlace y descripción.
    """

    resultados_limpios = []

    try:
        with DDGS() as ddgs:
            resultados = ddgs.text(
                consulta,
                region="es-es",
                max_results=5
            )

            for r in resultados:
                resultados_limpios.append({
                    "titulo": str(r.get("title", "")).strip(),
                    "enlace": str(r.get("href", "")).strip(),
                    "descripcion": str(r.get("body", "")).strip()
                })

        return {
            "consulta": consulta,
            "resultados": resultados_limpios
        }

    except Exception as e:
        return {
            "consulta": consulta,
            "error": str(e),
            "resultados": []
        }


# ==================================================
# 8. GEOAPIFY
# ==================================================

TIPOS_RESULTADO_GENERICOS = {
    "country", "state", "county", "city", "postcode",
    "suburb", "district", "locality"
}


def geolocalizar_empresa_geoapify(nombre_empresa):
    consulta = f"{nombre_empresa}, {CIUDAD}, {REGION}, {PAIS}"

    url = "https://api.geoapify.com/v1/geocode/search"

    params = {
        "text": consulta,
        "format": "json",
        "limit": 1,
        "lang": "es",
        "filter": "countrycode:es",
        "bias": "proximity:-0.8891,41.6488",
        "apiKey": GEOAPIFY_API_KEY
    }

    try:
        respuesta = requests.get(
            url,
            params=params,
            timeout=15
        )

        try:
            datos = respuesta.json()
        except Exception:
            datos = {}

        if respuesta.status_code != 200:
            return {
                "estado_geo": "ERROR",
                "consulta": consulta,
                "latitud": "",
                "longitud": "",
                "direccion": "",
                "mensaje": f"Código HTTP {respuesta.status_code}: {datos}"
            }

        resultados = datos.get("results", [])

        if not resultados:
            return {
                "estado_geo": "NO_ENCONTRADO",
                "consulta": consulta,
                "latitud": "",
                "longitud": "",
                "direccion": "",
                "mensaje": "Sin resultados"
            }

        resultado = resultados[0]

        latitud = str(resultado.get("lat", "")).strip()
        longitud = str(resultado.get("lon", "")).strip()
        direccion = str(resultado.get("formatted", "")).strip()

        if not tiene_valor(latitud) or not tiene_valor(longitud):
            return {
                "estado_geo": "NO_ENCONTRADO",
                "consulta": consulta,
                "latitud": "",
                "longitud": "",
                "direccion": direccion,
                "mensaje": "Geoapify no devolvió latitud o longitud"
            }

        # Resultado genérico (solo ciudad/zona): no es la sede de la empresa.
        # Cae en un punto de Juslibol, así que se deja sin ubicación.
        tipo_resultado = str(resultado.get("result_type", "")).strip().lower()
        es_punto_generico = (
            abs(float(latitud) - 41.6915847) < 0.0001
            and abs(float(longitud) + 0.9101268) < 0.0001
        )

        if es_punto_generico or tipo_resultado in TIPOS_RESULTADO_GENERICOS:
            return {
                "estado_geo": "SIN_UBICACION",
                "consulta": consulta,
                "latitud": "",
                "longitud": "",
                "direccion": "",
                "mensaje": f"Resultado genérico ({tipo_resultado or 'punto de Zaragoza'}), sin sede exacta"
            }

        return {
            "estado_geo": "OK",
            "consulta": consulta,
            "latitud": latitud,
            "longitud": longitud,
            "direccion": direccion,
            "mensaje": ""
        }

    except Exception as e:
        return {
            "estado_geo": "ERROR",
            "consulta": consulta,
            "latitud": "",
            "longitud": "",
            "direccion": "",
            "mensaje": str(e)
        }


# ==================================================
# 9. AGENTE CLAUDE
# ==================================================

def crear_agente_buscador():
    llm = ChatAnthropic(
        model="claude-sonnet-5"
    )

    system_prompt = """
Eres un agente buscador de empresas tecnológicas de Zaragoza y Aragón.

Tienes una herramienta llamada buscar_en_internet.

Tu trabajo:
1. Buscar empresas tecnológicas reales de Zaragoza o Aragón.
2. Obtener información pública de una empresa concreta.
3. Generar una descripción breve y objetiva.
4. Generar tags.
5. Proponer un ciclo formativo relacionado.
6. Incluir fuentes cuando las conozcas.

Reglas:
- No inventes empresas.
- No inventes datos.
- Usa buscar_en_internet cuando necesites información.
- Devuelve siempre JSON válido.
- No uses Markdown.
- No escribas ```json.
- No añadas explicación fuera del JSON.
- Los tags deben ser cortos y útiles.
- El ciclo debe ser uno de estos:
  DAM, DAW, ASIR, IA y Big Data, Transporte y Logística, Administración, Marketing, Otro.
- No incluyas universidades, institutos, administraciones públicas, medios de comunicación ni noticias.

Formato obligatorio:

{
  "empresas": [
    {
      "nombre": "Nombre empresa",
      "descripcion": "Descripción breve",
      "tags": ["tag1", "tag2", "tag3"],
      "ciclo": "DAW",
      "fuentes": "URLs o referencias usadas"
    }
  ]
}
"""

    agente = create_agent(
        model=llm,
        tools=[buscar_en_internet],
        system_prompt=system_prompt
    )

    return agente


def agente_buscar_datos_empresa(agente, nombre_empresa):
    mensaje = f"""
Busca información pública sobre esta empresa:

{nombre_empresa}

Instrucciones:
- Usa buscar_en_internet con esta consulta:
  "{nombre_empresa} Zaragoza Aragón empresa tecnología actividad dirección web"
- Analiza los 5 primeros resultados.
- Genera descripción, tags, ciclo y fuentes.
- Devuelve una sola empresa dentro de la lista empresas.
- No inventes datos.
- Devuelve únicamente JSON válido.

Formato obligatorio:

{{
  "empresas": [
    {{
      "nombre": "{nombre_empresa}",
      "descripcion": "Descripción breve",
      "tags": ["software", "cloud", "datos"],
      "ciclo": "DAW",
      "fuentes": "URLs o referencias usadas"
    }}
  ]
}}
"""

    try:
        resultado = agente.invoke({
            "messages": [
                {
                    "role": "user",
                    "content": mensaje
                }
            ]
        })

        texto = resultado["messages"][-1].content
        texto = limpiar_json_respuesta(texto)

        datos = json.loads(texto)
        empresas = datos.get("empresas", [])

        if isinstance(empresas, list) and empresas:
            return empresas[0]

        return {}

    except Exception as e:
        print(f"❌ Error buscando datos de '{nombre_empresa}': {e}")
        return {}


def agente_buscar_empresas_por_consulta(agente, consulta):
    mensaje = f"""
Busca empresas tecnológicas reales de Zaragoza o Aragón usando esta consulta:

{consulta}

Instrucciones:
- Usa la herramienta buscar_en_internet con la consulta indicada.
- Analiza los resultados obtenidos.
- Extrae solo empresas reales ubicadas o con sede/oficina/actividad clara en Zaragoza o Aragón.
- Prioriza empresas relacionadas con los temas que aparecen en la consulta.
- Devuelve como máximo 5 empresas.
- Para cada empresa intenta devolver:
  - nombre
  - descripcion
  - tags
  - ciclo
  - fuentes
- No incluyas universidades, institutos, administraciones públicas, medios de comunicación ni noticias.
- No inventes empresas.
- Si no hay empresas claras, devuelve una lista vacía.
- Devuelve únicamente JSON válido.

Formato obligatorio:

{{
  "empresas": [
    {{
      "nombre": "Nombre empresa",
      "descripcion": "Descripción breve",
      "tags": ["software", "cloud", "datos"],
      "ciclo": "DAW",
      "fuentes": "URLs o referencias usadas"
    }}
  ]
}}
"""

    try:
        resultado = agente.invoke({
            "messages": [
                {
                    "role": "user",
                    "content": mensaje
                }
            ]
        })

        texto = resultado["messages"][-1].content
        texto = limpiar_json_respuesta(texto)

        datos = json.loads(texto)
        empresas = datos.get("empresas", [])

        if not isinstance(empresas, list):
            return []

        return empresas

    except Exception as e:
        print(f"❌ Error en búsqueda por consulta: {e}")
        return []


# ==================================================
# 10. PREPARAR EMPRESA
# ==================================================

def preparar_empresa_limpia(empresa):
    nombre = str(empresa.get("nombre", "")).strip()
    descripcion = str(empresa.get("descripcion", "")).strip()
    tags = normalizar_tags(empresa.get("tags", []))
    ciclo = normalizar_ciclo(empresa.get("ciclo", "Otro"))
    fuentes = str(empresa.get("fuentes", "")).strip()

    return {
        "nombre": nombre,
        "descripcion": descripcion,
        "tags": tags,
        "ciclo": ciclo,
        "fuentes": fuentes
    }


def empresa_tiene_datos_minimos(empresa):
    if not tiene_valor(empresa.get("nombre", "")):
        return False, "La empresa no tiene nombre"

    if not tiene_valor(empresa.get("descripcion", "")):
        return False, "No se pudo obtener descripción"

    if not tiene_valor(empresa.get("tags", "")):
        return False, "No se pudieron obtener tags"

    return True, ""


# ==================================================
# 11. GUARDAR EMPRESAS
# ==================================================

def preparar_fila_final(empresa, geo):
    return [
        empresa["nombre"],
        geo.get("latitud", ""),
        geo.get("longitud", ""),
        geo.get("direccion", ""),
        empresa["descripcion"],
        empresa["tags"],
        empresa["ciclo"],
        "",
        "ok",
        empresa["fuentes"],
        fecha_hoy()
    ]


def preparar_fila_nodata(empresa, origen, motivo_error):
    direccion_intentada = f'{empresa.get("nombre", "")}, {CIUDAD}, {REGION}, {PAIS}'

    return [
        empresa.get("nombre", ""),
        empresa.get("descripcion", ""),
        empresa.get("tags", ""),
        empresa.get("ciclo", ""),
        direccion_intentada,
        motivo_error,
        "pendiente_revision",
        origen,
        empresa.get("fuentes", ""),
        fecha_actual()
    ]


def añadir_empresa_final(
    hoja_finales,
    empresa,
    geo,
    nombres_finales,
    nombres_globales
):
    fila = preparar_fila_final(empresa, geo)

    hoja_finales.append_row(
        fila,
        value_input_option="USER_ENTERED"
    )

    nombre_normalizado = normalizar_nombre(empresa["nombre"])

    nombres_finales.add(nombre_normalizado)
    nombres_globales.add(nombre_normalizado)

    print(f"✅ Añadida a empresas_finales: {empresa['nombre']}")


def añadir_empresa_nodata(
    hoja_nodata,
    empresa,
    origen,
    motivo_error,
    nombres_globales
):
    if not tiene_valor(empresa.get("nombre", "")):
        print("⚠️ Empresa sin nombre. No se añade a empresas_nodata.")
        return False

    fila = preparar_fila_nodata(
        empresa,
        origen,
        motivo_error
    )

    hoja_nodata.append_row(
        fila,
        value_input_option="USER_ENTERED"
    )

    nombres_globales.add(normalizar_nombre(empresa["nombre"]))

    print(f"⚠️ Añadida a empresas_nodata: {empresa['nombre']}")
    print(f"   Motivo: {motivo_error}")

    return True


# ==================================================
# 12. PROCESO CENTRAL DE UNA EMPRESA
# ==================================================

def procesar_y_guardar_empresa(
    hoja_finales,
    hoja_nodata,
    hoja_tags,
    agente,
    empresa,
    nombres_finales,
    nombres_globales,
    origen
):
    empresa = preparar_empresa_limpia(empresa)

    nombre = empresa.get("nombre", "")

    if not tiene_valor(nombre):
        print("⚠️ Empresa sin nombre. Se omite.")
        return "omitida"

    nombre_normalizado = normalizar_nombre(nombre)

    if nombre_normalizado in nombres_globales:
        print(f"⏩ Ya existe en empresas_finales o empresas_nodata: {nombre}")
        return "duplicada"

    datos_ok, motivo_error = empresa_tiene_datos_minimos(empresa)

    if not datos_ok:
        print(f"⚠️ Datos incompletos de {nombre}. Reintentando búsqueda específica...")

        empresa_reintentada = agente_buscar_datos_empresa(
            agente,
            nombre
        )

        if empresa_reintentada:
            empresa = preparar_empresa_limpia(empresa_reintentada)
            datos_ok, motivo_error = empresa_tiene_datos_minimos(empresa)

    print("\n🧠 Datos obtenidos:")
    print(f"Nombre: {empresa.get('nombre')}")
    print(f"Descripción: {empresa.get('descripcion')}")
    print(f"Tags: {empresa.get('tags')}")
    print(f"Ciclo: {empresa.get('ciclo')}")
    print(f"Fuentes: {empresa.get('fuentes')}")
    print(f"Origen: {origen}")

    if not datos_ok:
        añadir_empresa_nodata(
            hoja_nodata=hoja_nodata,
            empresa=empresa,
            origen=origen,
            motivo_error=motivo_error,
            nombres_globales=nombres_globales
        )

        return "nodata_sin_datos"

    print("\n📍 Geolocalizando con Geoapify...")

    geo = geolocalizar_empresa_geoapify(nombre)

    print(f"Estado Geoapify: {geo.get('estado_geo')}")
    print(f"Consulta: {geo.get('consulta')}")
    print(f"Dirección: {geo.get('direccion')}")
    print(f"Latitud: {geo.get('latitud')}")
    print(f"Longitud: {geo.get('longitud')}")

    # SIN_UBICACION: la empresa se guarda igualmente, sin coordenadas.
    if geo.get("estado_geo") not in ("OK", "SIN_UBICACION"):
        motivo_error = (
            f"Error geolocalización Geoapify: "
            f"{geo.get('estado_geo')} - {geo.get('mensaje')}"
        )

        añadir_empresa_nodata(
            hoja_nodata=hoja_nodata,
            empresa=empresa,
            origen=origen,
            motivo_error=motivo_error,
            nombres_globales=nombres_globales
        )

        actualizar_tags_con_empresa(
            hoja_tags,
            empresa
        )

        return "nodata_con_datos"

    añadir_empresa_final(
        hoja_finales=hoja_finales,
        empresa=empresa,
        geo=geo,
        nombres_finales=nombres_finales,
        nombres_globales=nombres_globales
    )

    actualizar_tags_con_empresa(
        hoja_tags,
        empresa
    )

    return "final"


# ==================================================
# 13. CONSULTAS DINÁMICAS
# ==================================================

def generar_consultas_web_dinamicas(hoja_tags, hoja_finales):
    consultas = []

    tags_disponibles = asegurar_tags_disponibles(
        hoja_tags,
        hoja_finales
    )

    if not tags_disponibles:
        tags_disponibles = TAGS_BUSQUEDA_WEB

    plantillas = PLANTILLAS_CONSULTA_WEB.copy()
    random.shuffle(plantillas)

    for plantilla in plantillas[:NUM_CONSULTAS_WEB_POR_PASADA]:
        max_tags = min(
            NUM_TAGS_POR_CONSULTA_MAX,
            len(tags_disponibles)
        )

        min_tags = min(
            NUM_TAGS_POR_CONSULTA_MIN,
            max_tags
        )

        numero_tags = random.randint(
            min_tags,
            max_tags
        )

        tags_elegidos = random.sample(
            tags_disponibles,
            numero_tags
        )

        texto_tags = " ".join(tags_elegidos)

        consulta = plantilla.format(tags=texto_tags)

        consultas.append({
            "consulta": consulta,
            "tags_usados": tags_elegidos
        })

    return consultas


# ==================================================
# 14. PASO 1 - INTERNET
# ==================================================

def procesar_busquedas_web(
    hoja_finales,
    hoja_nodata,
    hoja_tags,
    agente,
    nombres_finales,
    nombres_globales
):
    print("\n==================================================")
    print("🌐 PASO 1 - BUSCANDO 5 EMPRESAS NUEVAS EN INTERNET")
    print("==================================================")

    consultas_dinamicas = generar_consultas_web_dinamicas(
        hoja_tags,
        hoja_finales
    )

    print("\n🧩 Consultas generadas para esta pasada:")

    for item in consultas_dinamicas:
        print(f"- {item['consulta']}")

    total_procesadas = 0

    for item_consulta in consultas_dinamicas:
        if total_procesadas >= MAX_EMPRESAS_WEB:
            print("🛑 Ya se han procesado 5 empresas desde internet.")
            break

        consulta = item_consulta["consulta"]
        tags_usados = item_consulta["tags_usados"]

        print("\n--------------------------------------------------")
        print(f"🔎 Consulta dinámica: {consulta}")
        print(f"🏷️ Tags usados: {', '.join(tags_usados)}")

        empresas = agente_buscar_empresas_por_consulta(
            agente,
            consulta
        )

        print(f"📌 Candidatas encontradas: {len(empresas)}")

        for empresa in empresas:
            if total_procesadas >= MAX_EMPRESAS_WEB:
                print("🛑 Ya se han procesado 5 empresas desde internet.")
                break

            empresa = preparar_empresa_limpia(empresa)
            nombre = empresa.get("nombre", "")

            if not tiene_valor(nombre):
                continue

            nombre_normalizado = normalizar_nombre(nombre)

            if nombre_normalizado in nombres_finales:
                print(f"⏩ Ya está en empresas_finales: {nombre}")
                continue

            if nombre_normalizado in nombres_globales:
                print(f"⏩ Ya existe en alguna hoja: {nombre}")
                continue

            print("\n--------------------------------------------------")
            print(f"🏢 Empresa web candidata: {nombre}")

            resultado = procesar_y_guardar_empresa(
                hoja_finales=hoja_finales,
                hoja_nodata=hoja_nodata,
                hoja_tags=hoja_tags,
                agente=agente,
                empresa=empresa,
                nombres_finales=nombres_finales,
                nombres_globales=nombres_globales,
                origen="busqueda_web"
            )

            if resultado in ["final", "nodata_con_datos", "nodata_sin_datos"]:
                total_procesadas += 1

            time.sleep(1)

        time.sleep(1)

    print(f"\n✅ Empresas procesadas desde internet: {total_procesadas}")

    return total_procesadas


# ==================================================
# 15. PASO 2 - empresas_base
# ==================================================

def procesar_empresas_base(
    hoja_base,
    hoja_finales,
    hoja_nodata,
    hoja_tags,
    agente,
    nombres_finales,
    nombres_globales
):
    print("\n==================================================")
    print("📄 PASO 2 - PROCESANDO empresas_base NO PROCESADAS")
    print("==================================================")

    datos = hoja_base.get_all_values()

    if not datos:
        print("ℹ️ empresas_base está vacía.")
        return 0

    cabecera = datos[0]
    filas = datos[1:]

    idx_nombre = buscar_indice_columna(
        cabecera,
        ["nombre", "empresa", "nombre_empresa"]
    )

    idx_procesada = buscar_indice_columna(
        cabecera,
        ["procesada"]
    )

    if idx_nombre is None:
        idx_nombre = 0

    if idx_procesada is None:
        idx_procesada = 1

    total_procesadas = 0
    actualizaciones = []

    for numero_fila_google, fila in enumerate(filas, start=2):
        nombre = valor_columna(fila, idx_nombre)
        procesada = valor_columna(fila, idx_procesada)

        if not tiene_valor(nombre):
            continue

        if es_procesada(procesada):
            print(f"⏩ Ya procesada: {nombre}")
            continue

        print("\n--------------------------------------------------")
        print(f"🏢 Empresa base pendiente: {nombre}")

        nombre_normalizado = normalizar_nombre(nombre)

        if nombre_normalizado in nombres_finales:
            print(f"⏩ Ya está en empresas_finales: {nombre}")

            actualizaciones.append({
                "range": celda_a1(numero_fila_google, idx_procesada),
                "values": [["sí"]]
            })

            continue

        empresa_datos = agente_buscar_datos_empresa(
            agente,
            nombre
        )

        if not empresa_datos:
            empresa_datos = {
                "nombre": nombre,
                "descripcion": "",
                "tags": [],
                "ciclo": "Otro",
                "fuentes": ""
            }

        resultado = procesar_y_guardar_empresa(
            hoja_finales=hoja_finales,
            hoja_nodata=hoja_nodata,
            hoja_tags=hoja_tags,
            agente=agente,
            empresa=empresa_datos,
            nombres_finales=nombres_finales,
            nombres_globales=nombres_globales,
            origen="empresas_base"
        )

        if resultado in ["final", "nodata_con_datos", "duplicada"]:
            total_procesadas += 1

            actualizaciones.append({
                "range": celda_a1(numero_fila_google, idx_procesada),
                "values": [["sí"]]
            })

            print(f"✅ Marcada como procesada en empresas_base: {nombre}")

        elif resultado == "nodata_sin_datos":
            print(f"⚠️ No se marca como procesada porque no se obtuvieron datos: {nombre}")

        else:
            print(f"ℹ️ No se marca como procesada. Resultado: {resultado}")

        time.sleep(1)

    if actualizaciones:
        try:
            hoja_base.batch_update(actualizaciones)
            print("✅ empresas_base actualizada.")
        except Exception as e:
            print(f"❌ Error actualizando empresas_base: {e}")

    print(f"\n✅ Empresas base marcadas como procesadas: {total_procesadas}")

    return total_procesadas