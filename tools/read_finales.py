#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para leer empresas_finales"""

import sys
from config import GOOGLE_SHEET_URL, GOOGLE_CREDENTIALS_JSON
import gspread
from google.oauth2.service_account import Credentials

print("🔍 Leyendo empresas_finales...\n")

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
    hoja = spreadsheet.worksheet("empresas_finales")
    
    print("✅ Conexión exitosa\n")
    
    datos = hoja.get_all_values()
    
    if not datos:
        print("❌ La hoja empresas_finales está vacía")
        sys.exit(0)
    
    cabecera = datos[0]
    print(f"📌 Cabecera: {cabecera}\n")
    
    print("="*150)
    print("EMPRESAS FINALES")
    print("="*150 + "\n")
    
    for idx, fila in enumerate(datos[1:], start=1):
        if fila and len(fila) > 0:
            print(f"Empresa #{idx}:")
            for col_idx, (nombre_col, valor) in enumerate(zip(cabecera, fila)):
                print(f"  {nombre_col:<20} : {valor}")
            print()
    
    print(f"✅ Total de empresas: {len(datos) - 1}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
