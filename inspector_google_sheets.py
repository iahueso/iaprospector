#!/usr/bin/env python3
"""
INSPECTOR - Ver qué datos hay en la hoja 'empresas_base' de Google Sheets
"""

import gspread
from google.oauth2.service_account import Credentials

GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1xLmiNv39VsXb6przp_9A-pINm7KfbPXCQJ5XjCRzd7Y/edit?gid=2096546069#gid=2096546069"
GOOGLE_CREDENTIALS_JSON = "credenciales_google.json"

print("\n" + "="*100)
print("INSPECTOR - VER CONTENIDO DE GOOGLE SHEETS")
print("="*100)

try:
    # Autenticarse
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
    
    print("\n📋 Hojas disponibles en el Google Sheet:")
    for h in spreadsheet.worksheets():
        print(f"  ✓ {h.title}")
    
    # Inspeccionar cada hoja
    for hoja_nombre in ["empresas_base", "empresas_finales", "test"]:
        print(f"\n{'='*100}")
        print(f"📊 HOJA: '{hoja_nombre}'")
        print(f"{'='*100}")
        
        try:
            hoja = spreadsheet.worksheet(hoja_nombre)
            datos = hoja.get_all_records()
            
            print(f"\n✓ Filas: {len(datos)}")
            
            if datos:
                print(f"\n🔍 Primeras filas:")
                for i, row in enumerate(datos[:3], 1):
                    print(f"\n  Fila {i}:")
                    for col, valor in row.items():
                        print(f"    • {col}: {valor}")
                
                if len(datos) > 3:
                    print(f"\n  ... y {len(datos) - 3} filas más")
            else:
                print("\n  ⚠️  La hoja está vacía")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
