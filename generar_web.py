import csv
import urllib.request
import json

# URL de tu Google Sheet publicado como CSV (dentro de iaprospector)
URL_DRIVE_CSV = 'https://docs.google.com/spreadsheets/d/1xLmiNv39VsXb6przp_9A-pINm7KfbPXCQJ5XjCRzd7Y/edit?usp=drive_link'

def descargar_datos():
    print("\n--- 1. INICIANDO CONEXIÓN CON DRIVE ---")
    try:
        peticion = urllib.request.Request(
            URL_DRIVE_CSV, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        response = urllib.request.urlopen(peticion)
        lineas = [linea.decode('utf-8') for linea in response.readlines()]
        print(f"✅ Descarga completada. Archivo de Drive recibido correctamente.")
        return lineas
    except Exception as e:
        print(f"❌ Error al descargar de Drive: {e}")
        return None

def generar_html(datos_csv):
    print("\n--- 2. PROCESANDO DATOS POR POSICIÓN DE COLUMNA ---")
    
    # Forzamos la detección de filas limpiando los saltos de línea
    lineas_limpias = [linea.strip() for linea in datos_csv if linea.strip()]
    
    empresas_para_mapa = []
    tarjetas_html = ""
    contador_tarjetas = 0

    print("🔎 Leyendo registros reales:")
    
    # Empezamos en la línea 1 para saltarnos la cabecera pegada
    for num_fila, linea in enumerate(lineas_limpias[1:], start=1):
        
        # Rompemos la línea detectando si usa punto y coma o coma de forma interna
        separador = ';' if ';' in linea else ','
        columnas = next(csv.reader([linea], delimiter=separador))
        
        # Si la fila está prácticamente vacía, la saltamos
        if len(columnas) < 3:
            continue
            
        # Asignamos las variables de forma segura basándonos en el orden de tus cabeceras:
        # 0: ID | 1: Nombre | 2: Latitud | 3: Longitud | 4: Descripción | 5: Tags | 6: Ciclo Asignado | 7: NAlumnos
        try:
            nombre = columnas[1].strip() if len(columnas) > 1 else "Sin nombre"
            lat_str = columnas[2].strip() if len(columnas) > 2 else "0"
            lng_str = columnas[3].strip() if len(columnas) > 3 else "0"
            descripcion = columnas[4].strip() if len(columnas) > 4 else "Sin descripción"
            tags_raw = columnas[5].strip() if len(columnas) > 5 else ""
            ciclo = columnas[6].strip() if len(columnas) > 6 else "No asignado"
            alumnos = columnas[7].strip() if len(columnas) > 7 else "0"
        except IndexError:
            # Por si alguna fila viene más corta de lo normal
            continue

        # Limpieza de comillas dobles residuales
        nombre = nombre.replace('"', '')
        descripcion = descripcion.replace('"', '')

        print(f"   [Fila {num_fila}] Empresa: '{nombre}' | Ciclo: {ciclo} | Coordenadas: ({lat_str}, {lng_str})")

        # Intentar transformar las coordenadas para el mapa interactivo
        try:
            lat = float(lat_str.replace(',', '.')) if lat_str else 0.0
            lng = float(lng_str.replace(',', '.')) if lng_str else 0.0
            if lat != 0 and lng != 0:
                empresas_para_mapa.append({
                    "nombre": nombre,
                    "lat": lat,
                    "lng": lng,
                    "ciclo": ciclo
                })
        except ValueError:
            pass

        # Procesar los tags
        tags_lista = tags_raw.split(',')
        tags_html = "".join([f'<span class="tag">#{t.strip().replace("""\"""", "")}</span>' for t in tags_lista if t.strip()])

        # Construimos la tarjeta HTML para esta empresa
        tarjetas_html += f"""
            <div class="card">
                <div>
                    <h2>{nombre}</h2>
                    <span class="badge-ciclo">{ciclo}</span>
                    <p class="descripcion">{descripcion}</p>
                </div>
                <div>
                    <div class="tags">{tags_html}</div>
                    <div class="info-footer">
                        <span>📍 Lat: {lat_str}, Lng: {lng_str}</span>
                        <span>👥 Alumnos: <strong>{alumnos}</strong></span>
                    </div>
                </div>
            </div>
"""
        contador_tarjetas += 1

    # Estructura de la plantilla HTML final
    html_final = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IAProspector - Mapa y Empresas V2</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f7f6; margin: 0; padding: 0; color: #333; }}
        header {{ background-color: #1e293b; color: white; text-align: center; padding: 1.5rem 1rem; }}
        #mapa-contenedor {{ max-width: 1200px; margin: 1.5rem auto; padding: 0 1rem; }}
        #map {{ height: 400px; width: 100%; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        main {{ max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }}
        .grid-empresas {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem; }}
        .card {{ background: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #3b82f6; display: flex; flex-direction: column; justify-content: space-between; }}
        .card h2 {{ margin-top: 0; color: #1e293b; font-size: 1.3rem; }}
        .badge-ciclo {{ background-color: #e0f2fe; color: #0369a1; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.85rem; font-weight: bold; display: inline-block; margin-bottom: 1rem; align-self: flex-start; }}
        .descripcion {{ font-size: 0.95rem; color: #4b5563; line-height: 1.4; margin-bottom: 1rem; }}
        .tags {{ margin: 1rem 0; }}
        .tag {{ background: #f1f5f9; color: #475569; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem; margin-right: 0.5rem; display: inline-block; margin-bottom: 0.25rem; }}
        .info-footer {{ display: flex; justify-content: space-between; font-size: 0.85rem; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 0.75rem; margin-top: auto; }}
    </style>
</head>
<body>
    <header>
        <h1>IAProspector: Geolocalización de Empresas</h1>
        <p>Versión 2 - Datos dinámicos mapeados desde Google Drive</p>
    </header>
    <section id="mapa-contenedor"><div id="map"></div></section>
    <main>
        <div class="grid-empresas">
            {tarjetas_html}
        </div>
    </main>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const map = L.map('map').setView([41.65606, -0.87734], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {{
            attribution: '&copy; OpenStreetMap contributors'
        }}).addTo(map);

        const datosMarcadores = {json.dumps(empresas_para_mapa, ensure_ascii=False)};

        datosMarcadores.forEach(empresa => {{
            L.marker([empresa.lat, empresa.lng])
                .addTo(map)
                .bindPopup(`<b>${empresa.nombre}</b><br>Ciclo: ${empresa.ciclo}`);
        }});

        if (datosMarcadores.length > 0) {{
            const group = new L.featureGroup(datosMarcadores.map(e => L.marker([e.lat, e.lng])));
            map.fitBounds(group.getBounds().pad(0.1));
        }}
    </script>
</body>
</html>
"""

    print("\n--- 3. ESCRIBIENDO ARCHIVO FINAL ---")
    with open("index.html", "w", encoding="utf-8") as archivo:
        archivo.write(html_final)
        
    print(f"✅ ¡Archivo 'index.html' generado correctamente con su mapa e información!")
    print(f"📊 Resumen: {contador_tarjetas} empresas procesadas | {len(empresas_para_mapa)} puntos añadidos al mapa.")

if __name__ == "__main__":
    datos = descargar_datos()
    if datos:
        generar_html(datos)