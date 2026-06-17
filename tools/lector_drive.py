import urllib.request

# URL de tu archivo en la carpeta iaprospector
URL_DRIVE_CSV = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRErQ9aPtfcwvsYaTkJ4fupISiUCE1e4y-0yd7nSF-fYSdZRn7eRun_F4_3tVc2VKD56HtT3udNHO5H/pub?output=csv'

def probar_lectura_drive():
    print("\n==================================================")
    print("🔬 SCRIPT DE DIAGNÓSTICO: PROBANDO LECTURA DIRECTA")
    print("==================================================")
    print(f"🔄 Conectando con Google Drive...")
    
    try:
        # Petición simulando navegador
        peticion = urllib.request.Request(
            URL_DRIVE_CSV, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        response = urllib.request.urlopen(peticion)
        
        # Leemos las líneas y las decodificamos
        lineas = [linea.decode('utf-8').strip( ) for linea in response.readlines()]
        
        print(f"✅ ¡Conexión con éxito! El archivo tiene {len(lineas)} líneas.")
        print("\n👇 AQUÍ ABAJO TIENES LAS 4 PRIMERAS LÍNEAS REALES DE TU ARCHIVO:\n")
        
        # Mostramos solo las 4 primeras líneas para inspeccionarlas de forma segura
        for i, linea in enumerate(lineas[:4]):
            print(f"[LÍNEA REAL {i+1}]: {linea}")
            print("-" * 60)
            
    except Exception as e:
        print(f"❌ Error al intentar leer el archivo: {e}")
        print("Revisa si el archivo en tu Drive tiene los permisos correctos.")

if __name__ == "__main__":
    probar_lectura_drive()