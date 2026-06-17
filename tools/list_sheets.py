#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para listar todas las hojas disponibles"""

import sys
from config import GOOGLE_SHEET_URL, GOOGLE_CREDENTIALS_JSON
import gspread
from google.oauth2.service_account import Credentials

print("🔍 Listando hojas disponibles en Google Sheets...\n")

try:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    credenciales = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_JSON,
        scopes=scopes
    )
    
    cliente = gspread.authorize(credenciales)
    spreadsheet = cliente.open_by_url(GOOGLE_SHEET_URL)
    
    print("✅ Conexión exitosa\n")
    print("📋 Hojas disponibles:")
    print("="*50)
    
    for idx, hoja in enumerate(spreadsheet.worksheets(), 1):
        print(f"{idx}. '{hoja.title}' (ID: {hoja.id})")
    
    print("\n✅ Listado completado")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
