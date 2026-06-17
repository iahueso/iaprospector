import os
import sys
import json
import time
import requests

import gspread
from google.oauth2.service_account import Credentials

from ddgs import DDGS

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_groq import ChatGroq


# ==================================================
# 0. IMPORTAR CONFIG DESDE DIRECTORIO SUPERIOR
# ==================================================

DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
DIRECTORIO_SUPERIOR = os.path.dirname(DIRECTORIO_ACTUAL)

if DIRECTORIO_SUPERIOR not in sys.path:
    sys.path.append(DIRECTORIO_SUPERIOR)


try:
    from config import (
        GROQ_API_KEY,
        GOOGLE_SHEET_URL,
        GOOGLE_CREDENTIALS_JSON,
        GEOAPIFY_API_KEY
    )

    os.environ["GROQ_API_KEY"] = GROQ_API_KEY

except ImportError as e:
    print("❌ Error importando config.py")
    print(e)
    exit(1)


# ==================================================
# 1. CONFIGURACIÓN GENERAL
# ==================================================

HOJA_BASE = "empresas_base"
HOJA_FINALES = "empresas_finales"

CIUDAD = "Zaragoza"
PAIS = "España"

MAX_EMPRESAS_POR_PASADA = 5

CABECERA_BASE = [
    "nombre",
    "procesada"
]

CABECERA_FINALES = [
    "nombre",
    "latitud",
    "longitud",
    "dirección",
    "descripción",
    "tags",
    "ciclo",
    "origen"
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


EMPRESAS_PRECONFIGURADAS = [
    "Hiberus",
    "Integra Tecnología",
    "Endalia",
    "Netex",
    "Imascono",
    "Inycom",
    "DXC Technology Zaragoza",
    "NTT DATA Zaragoza",
    "Deloitte Zaragoza",
    "Inetum Zaragoza"
]


CONSULTAS_WEB = [
    "empresas tecnológicas Zaragoza software desarrollo web",
    "startups Zaragoza inteligencia artificial datos",
    "consultoras tecnológicas Zaragoza transformación digital",
    "empresas TIC Zaragoza desarrollo aplicaciones",
    "empresas software Zaragoza industria logística",
    "empresas ciberseguridad Zaragoza tecnología",
    "empresas inteligencia artificial Zaragoza",
    "empresas desarrollo aplicaciones Zaragoza"
]


# ==================================================
# 2. GOOGLE SHEETS
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
# 3. TEXTO Y DUPLICADOS
# ==================================================

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
        "sin tags"
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


def empresa_ya_existe(nombre, nombres_existentes):
    return normalizar_nombre(nombre) in nombres_existentes


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


def limpiar_json_respuesta(texto):
    texto = str(texto).strip()

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


# ==================================================
# 4. EMPRESAS EXISTENTES
# ==================================================

def obtener_nombres_empresas_finales(hoja_finales):
    datos = hoja_finales.get_all_values()

    if not datos:
        return set()

    cabecera = datos[0]
    filas = datos[1:]

    idx_nombre = buscar_indice_columna(
        cabecera,
        ["nombre", "empresa", "nombre_empresa", "title", "name"]
    )

    if idx_nombre is None:
        idx_nombre = 0

    nombres = set()

    for fila in filas:
        nombre = valor_columna(fila, idx_nombre)

        if tiene_valor(nombre):
            nombres.add(normalizar_nombre(nombre))

    return nombres


# ==================================================
# 5. TOOL DE BÚSQUEDA WEB
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
# 6. GEOAPIFY
# ==================================================

def geolocalizar_empresa_geoapify(nombre_empresa):
    consulta = f"{nombre_empresa}, {CIUDAD}, {PAIS}"

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

        datos = respuesta.json()

        if respuesta.status_code != 200:
            return {
                "estado_geo": "ERROR",
                "latitud": "",
                "longitud": "",
                "direccion": "",
                "mensaje": str(datos)
            }

        resultados = datos.get("results", [])

        if not resultados:
            return {
                "estado_geo": "NO_ENCONTRADO",
                "latitud": "",
                "longitud": "",
                "direccion": "",
                "mensaje": "Sin resultados"
            }

        resultado = resultados[0]

        return {
            "estado_geo": "OK",
            "latitud": str(resultado.get("lat", "")),
            "longitud": str(resultado.get("lon", "")),
            "direccion": resultado.get("formatted", ""),
            "mensaje": ""
        }

    except Exception as e:
        return {
            "estado_geo": "ERROR",
            "latitud": "",
            "longitud": "",
            "direccion": "",
            "mensaje": str(e)
        }


# ==================================================
# 7. CREAR AGENTE
# ==================================================

def crear_agente_buscador():
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0
    )

    system_prompt = """
Eres un agente buscador de empresas tecnológicas de Zaragoza.

Tienes una herramienta llamada buscar_en_internet.

Tu trabajo:
1. Buscar empresas tecnológicas reales.
2. Obtener información pública de una empresa concreta.
3. Generar una descripción breve y objetiva.
4. Generar tags.
5. Proponer un ciclo formativo relacionado.

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

Formato obligatorio:

{
  "empresas": [
    {
      "nombre": "Nombre empresa",
      "descripcion": "Descripción breve",
      "tags": ["tag1", "tag2", "tag3"],
      "ciclo": "DAW"
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


# ==================================================
# 8. USAR EL AGENTE
# ==================================================

def agente_buscar_datos_empresa(agente, nombre_empresa):
    mensaje = f"""
Busca información pública sobre esta empresa de Zaragoza:

{nombre_empresa}

Instrucciones:
- Usa buscar_en_internet con esta consulta:
  "{nombre_empresa} Zaragoza empresa tecnología actividad dirección web"
- Analiza los 5 primeros resultados.
- Genera descripción, tags y ciclo.
- Devuelve una sola empresa dentro de la lista empresas.
- Devuelve únicamente JSON válido.
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
Busca empresas tecnológicas reales de Zaragoza usando esta consulta:

{consulta}

Instrucciones:
- Usa la herramienta buscar_en_internet.
- Analiza los 5 primeros resultados.
- Extrae solo empresas reales.
- Devuelve como máximo 5 empresas.
- Devuelve únicamente JSON válido.
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
# 9. GUARDAR EMPRESA FINAL
# ==================================================

def preparar_fila_final(empresa, origen):
    nombre = str(empresa.get("nombre", "")).strip()
    descripcion = str(empresa.get("descripcion", "")).strip()
    tags = lista_a_texto(empresa.get("tags", []))
    ciclo = str(empresa.get("ciclo", "Otro")).strip()

    if ciclo not in CICLOS_VALIDOS:
        ciclo = "Otro"

    print("\n🧠 Datos generados por el agente:")
    print(f"Nombre: {nombre}")
    print(f"Descripción: {descripcion}")
    print(f"Tags: {tags}")
    print(f"Ciclo: {ciclo}")
    print(f"Origen: {origen}")

    print("\n📍 Geolocalizando con Geoapify...")
    geo = geolocalizar_empresa_geoapify(nombre)

    print(f"Estado Geoapify: {geo.get('estado_geo')}")
    print(f"Dirección: {geo.get('direccion')}")
    print(f"Latitud: {geo.get('latitud')}")
    print(f"Longitud: {geo.get('longitud')}")

    return [
        nombre,
        geo.get("latitud", ""),
        geo.get("longitud", ""),
        geo.get("direccion", ""),
        descripcion,
        tags,
        ciclo,
        origen
    ]


def añadir_empresa_final(hoja_finales, empresa, nombres_existentes, origen):
    nombre = str(empresa.get("nombre", "")).strip()

    if not tiene_valor(nombre):
        print("⚠️ Empresa sin nombre. No se añade.")
        return False

    if empresa_ya_existe(nombre, nombres_existentes):
        print(f"⏩ Ya existe en empresas_finales: {nombre}")
        return False

    fila = preparar_fila_final(empresa, origen)

    try:
        hoja_finales.append_row(
            fila,
            value_input_option="USER_ENTERED"
        )

        nombres_existentes.add(normalizar_nombre(nombre))

        print(f"✅ Añadida a empresas_finales: {nombre}")

        return True

    except Exception as e:
        print(f"❌ Error añadiendo '{nombre}': {e}")
        return False


# ==================================================
# 10. PROCESAR EMPRESAS_BASE
# ==================================================

def procesar_empresas_base(
    hoja_base,
    hoja_finales,
    agente,
    nombres_existentes,
    contador
):
    print("\n==================================================")
    print("📄 PROCESANDO empresas_base")
    print("==================================================")

    datos = hoja_base.get_all_values()

    if not datos:
        print("ℹ️ empresas_base está vacía.")
        return contador, 0

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

    total_añadidas = 0
    actualizaciones = []

    for numero_fila_google, fila in enumerate(filas, start=2):
        if contador >= MAX_EMPRESAS_POR_PASADA:
            print("🛑 Límite global alcanzado.")
            break

        nombre = valor_columna(fila, idx_nombre)
        procesada = valor_columna(fila, idx_procesada)

        if not tiene_valor(nombre):
            continue

        if es_procesada(procesada):
            print(f"⏩ Ya procesada: {nombre}")
            continue

        print("\n--------------------------------------------------")
        print(f"🏢 Empresa base: {nombre}")

        if empresa_ya_existe(nombre, nombres_existentes):
            print("⏩ Ya existe en empresas_finales. Se marca como procesada.")

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
            print("⚠️ No se pudieron obtener datos.")
            continue

        añadida = añadir_empresa_final(
            hoja_finales,
            empresa_datos,
            nombres_existentes,
            origen="empresas_base"
        )

        if añadida:
            total_añadidas += 1
            contador += 1

            actualizaciones.append({
                "range": celda_a1(numero_fila_google, idx_procesada),
                "values": [["sí"]]
            })

        time.sleep(1)

    if actualizaciones:
        try:
            hoja_base.batch_update(actualizaciones)
            print("✅ empresas_base actualizada.")
        except Exception as e:
            print(f"❌ Error actualizando empresas_base: {e}")

    return contador, total_añadidas


# ==================================================
# 11. PROCESAR EMPRESAS PRECONFIGURADAS
# ==================================================

def procesar_empresas_preconfiguradas(
    hoja_finales,
    agente,
    nombres_existentes,
    contador
):
    print("\n==================================================")
    print("📦 PROCESANDO EMPRESAS PRECONFIGURADAS")
    print("==================================================")

    total_añadidas = 0

    for nombre in EMPRESAS_PRECONFIGURADAS:
        if contador >= MAX_EMPRESAS_POR_PASADA:
            print("🛑 Límite global alcanzado.")
            break

        if empresa_ya_existe(nombre, nombres_existentes):
            print(f"⏩ Ya existe: {nombre}")
            continue

        print("\n--------------------------------------------------")
        print(f"🏢 Empresa preconfigurada: {nombre}")

        empresa_datos = agente_buscar_datos_empresa(
            agente,
            nombre
        )

        if not empresa_datos:
            print("⚠️ No se pudieron obtener datos.")
            continue

        añadida = añadir_empresa_final(
            hoja_finales,
            empresa_datos,
            nombres_existentes,
            origen="preconfigurada"
        )

        if añadida:
            total_añadidas += 1
            contador += 1

        time.sleep(1)

    return contador, total_añadidas


# ==================================================
# 12. PROCESAR BÚSQUEDAS WEB GENERALES
# ==================================================

def procesar_busquedas_web(
    hoja_finales,
    agente,
    nombres_existentes,
    contador
):
    print("\n==================================================")
    print("🌐 BÚSQUEDAS WEB GENERALES")
    print("==================================================")

    total_añadidas = 0

    for consulta in CONSULTAS_WEB:
        if contador >= MAX_EMPRESAS_POR_PASADA:
            print("🛑 Límite global alcanzado.")
            break

        print("\n--------------------------------------------------")
        print(f"🔎 Consulta: {consulta}")

        empresas = agente_buscar_empresas_por_consulta(
            agente,
            consulta
        )

        print(f"📌 Candidatas encontradas: {len(empresas)}")

        for empresa in empresas:
            if contador >= MAX_EMPRESAS_POR_PASADA:
                print("🛑 Límite global alcanzado.")
                break

            nombre = str(empresa.get("nombre", "")).strip()

            if not tiene_valor(nombre):
                continue

            if empresa_ya_existe(nombre, nombres_existentes):
                print(f"⏩ Ya existe: {nombre}")
                continue

            añadida = añadir_empresa_final(
                hoja_finales,
                empresa,
                nombres_existentes,
                origen="busqueda_web"
            )

            if añadida:
                total_añadidas += 1
                contador += 1

            time.sleep(1)

        time.sleep(1)

    return contador, total_añadidas


# ==================================================
# 13. PROCESO PRINCIPAL
# ==================================================

def ejecutar_agente_buscador():
    print("\n==================================================")
    print("🤖 AGENTE 1 - BUSCADOR Y GEOLOCALIZADOR")
    print("==================================================")
    print(f"Máximo de empresas nuevas por pasada: {MAX_EMPRESAS_POR_PASADA}")

    try:
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

    except Exception as e:
        print(f"❌ Error conectando con Google Sheets: {e}")
        return

    print("✅ Conexión con Google Sheets correcta.")

    nombres_existentes = obtener_nombres_empresas_finales(
        hoja_finales
    )

    print(f"📌 Empresas ya existentes: {len(nombres_existentes)}")

    agente = crear_agente_buscador()

    contador_global = 0

    contador_global, añadidas_base = procesar_empresas_base(
        hoja_base,
        hoja_finales,
        agente,
        nombres_existentes,
        contador_global
    )

    contador_global, añadidas_preconfiguradas = procesar_empresas_preconfiguradas(
        hoja_finales,
        agente,
        nombres_existentes,
        contador_global
    )

    contador_global, añadidas_web = procesar_busquedas_web(
        hoja_finales,
        agente,
        nombres_existentes,
        contador_global
    )

    print("\n==================================================")
    print("📊 RESUMEN FINAL")
    print("==================================================")
    print(f"Empresas añadidas desde empresas_base: {añadidas_base}")
    print(f"Empresas añadidas preconfiguradas: {añadidas_preconfiguradas}")
    print(f"Empresas añadidas desde búsqueda web: {añadidas_web}")
    print(f"Total nuevas añadidas: {contador_global}")
    print("==================================================")


if __name__ == "__main__":
    ejecutar_agente_buscador()