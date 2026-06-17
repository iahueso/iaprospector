import os
import sys

from web_utils import (
    leer_empresas_desde_sheets,
    generar_json,
    generar_html_completo,
    guardar_html
)


# ==================================================
# 0. DIRECTORIOS
# ==================================================

DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
DIRECTORIO_SUPERIOR = os.path.dirname(DIRECTORIO_ACTUAL)

if DIRECTORIO_SUPERIOR not in sys.path:
    sys.path.append(DIRECTORIO_SUPERIOR)


# ==================================================
# 1. IMPORTAR CONFIG
# ==================================================

from config import GOOGLE_SHEET_URL, GOOGLE_CREDENTIALS_JSON


# ==================================================
# 2. CONFIGURACIÓN
# ==================================================

HOJA_FINALES = "empresas_finales"

CARPETA_WEB = os.path.join(DIRECTORIO_SUPERIOR, "web")
CARPETA_DATA = os.path.join(CARPETA_WEB, "data")

RUTA_JSON = os.path.join(CARPETA_DATA, "empresas_finales.json")

# HTML en la raíz del proyecto
RUTA_HTML = os.path.join(DIRECTORIO_SUPERIOR, "index.html")


# ==================================================
# 3. PROCESO PRINCIPAL
# ==================================================

def main():
    print("\n==================================================")
    print("🌐 GENERADOR WEB IAProspector")
    print("==================================================")

    empresas = leer_empresas_desde_sheets(
        directorio_superior=DIRECTORIO_SUPERIOR,
        google_credentials_json=GOOGLE_CREDENTIALS_JSON,
        google_sheet_url=GOOGLE_SHEET_URL,
        nombre_hoja=HOJA_FINALES
    )

    if not empresas:
        print("⚠️ No hay empresas válidas para publicar.")
        return

    generar_json(
        empresas=empresas,
        ruta_json=RUTA_JSON
    )

    html_completo = generar_html_completo(empresas)

    guardar_html(
        html_completo=html_completo,
        ruta_html=RUTA_HTML
    )

    print("\n==================================================")
    print("✅ WEB GENERADA CORRECTAMENTE")
    print("==================================================")
    print(f"Empresas publicadas: {len(empresas)}")
    print(f"JSON: {RUTA_JSON}")
    print(f"HTML: {RUTA_HTML}")
    print("==================================================")


if __name__ == "__main__":
    main()