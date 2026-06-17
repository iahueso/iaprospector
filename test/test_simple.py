#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script simple para probar lectura de empresas_base"""

import os
import sys
import time

print("⏱️ Script iniciado a las:", time.strftime("%H:%M:%S"))
print("="*50)

# Paso 1: Importar config
print("\n[1/4] Importando configuración...")
try:
    from config import GOOGLE_SHEET_URL, GOOGLE_CREDENTIALS_JSON
    print("✅ Config importada")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Paso 2: Importar librerías
print("\n[2/4] Importando librerías...")
try:
    import gspread
    from google.oauth2.service_account import Credentials
    print("✅ Librerías importadas")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Paso 3: Conectar a Google Sheets
print("\n[3/4] Conectando a Google Sheets...")
try:
    print("   [3a] Cargando credenciales...")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    credenciales = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_JSON,
        scopes=scopes
    )
    print("   ✅ Credenciales cargadas")
    
    print("   [3b] Autorizando cliente...")
    cliente = gspread.authorize(credenciales)
    print("   ✅ Cliente autorizado")
    
    print("   [3c] Abriendo spreadsheet...")
    spreadsheet = cliente.open_by_url(GOOGLE_SHEET_URL)
    print("   ✅ Spreadsheet abierto")
    
    print("   [3d] Abriendo hoja 'empresas_base'...")
    hoja = spreadsheet.worksheet("empresas_base")
    print("   ✅ Hoja abierta")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Paso 4: Leer datos
print("\n[4/4] Leyendo datos...")
try:
    print("   [4a] Obteniendo valores...")
    datos = hoja.get_all_values()
    print(f"   ✅ Datos obtenidos ({len(datos)} filas)")
    
    if datos:
        cabecera = datos[0]
        print(f"   📌 Cabecera: {cabecera}")
        print(f"\n   {'#':<5} {'Empresa':<50} {'Estado':<15}")
        print("   " + "-" * 70)
        
        count = 0
        for numero, fila in enumerate(datos[1:], start=1):
            if fila and len(fila) > 0:
                empresa = fila[0].strip() if len(fila) > 0 else ""
                estado = fila[1].strip() if len(fila) > 1 else ""
                
                if empresa:
                    count += 1
                    print(f"   {numero:<5} {empresa:<50} {estado:<15}")
        
        print(f"\n   ✅ Total de empresas: {count}")
    else:
        print("   ❌ La hoja está vacía")
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*50)
print("⏱️ Script finalizado a las:", time.strftime("%H:%M:%S"))
print("✅ Proceso completado exitosamente")
