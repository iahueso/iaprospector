#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script de prueba para conectar a Google Sheets"""

import os
import sys

print("🔍 Iniciando prueba de conexión a Google Sheets...")

# Importar config
try:
    from config import GOOGLE_SHEET_URL, GOOGLE_CREDENTIALS_JSON
    print(f"✅ Config importada correctamente")
    print(f"   URL: {GOOGLE_SHEET_URL}")
    print(f"   JSON: {GOOGLE_CREDENTIALS_JSON}")
except Exception as e:
    print(f"❌ Error importando config: {e}")
    sys.exit(1)

# Verificar que el archivo JSON existe
if os.path.exists(GOOGLE_CREDENTIALS_JSON):
    print(f"✅ Archivo de credenciales encontrado: {GOOGLE_CREDENTIALS_JSON}")
else:
    print(f"❌ Archivo de credenciales NO encontrado: {GOOGLE_CREDENTIALS_JSON}")
    sys.exit(1)

# Intentar importar gspread
print("\n🔍 Importando gspread...")
try:
    import gspread
    from google.oauth2.service_account import Credentials
    print("✅ Librerías importadas correctamente")
except Exception as e:
    print(f"❌ Error importando librerías: {e}")
    sys.exit(1)

# Intentar conectar con Google Sheets
print("\n🔍 Intentando conectar con Google Sheets...")
try:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    print("   Cargando credenciales...")
    credenciales = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_JSON,
        scopes=scopes
    )
    print("   ✅ Credenciales cargadas")

    print("   Autorizando cliente...")
    cliente = gspread.authorize(credenciales)
    print("   ✅ Cliente autorizado")

    print("   Abriendo spreadsheet...")
    spreadsheet = cliente.open_by_url(GOOGLE_SHEET_URL)
    print("   ✅ Spreadsheet abierto")

    print(f"\n✅ Conexión exitosa")
    print(f"   Hojas disponibles: {[w.title for w in spreadsheet.worksheets()]}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Prueba completada exitosamente")
