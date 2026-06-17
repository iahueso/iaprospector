#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para resetear estado de hiberus"""

import sys
from config import GOOGLE_SHEET_URL, GOOGLE_CREDENTIALS_JSON
import gspread
from google.oauth2.service_account import Credentials

print("🔄 Reseteando estado de hiberus...\n")

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
    hoja = spreadsheet.worksheet("empresas_base")
    
    print("✅ Conexión exitosa\n")
    
    # Cambiar estado de fila 2 (la primera empresa) a vacío
    hoja.update_cell(2, 2, "")
    
    print("✅ Estado de hiberus reseteado a vacío")
    print("   Ahora puedes ejecutar agente_grok.py para procesarla de nuevo")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
