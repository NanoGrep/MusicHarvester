import os
import re
from collections import defaultdict

def buscar_canciones_duplicadas(directorio_base):
    canciones = defaultdict(list)
    
    patron = re.compile(r"^(.*)\s\[.*\]")

    for raiz, dirs, archivos in os.walk(directorio_base):
        for archivo in archivos:
            if archivo.endswith(".opus"):
                nombre_sin_ext = os.path.splitext(archivo)[0]
                
                coincidencia = patron.match(nombre_sin_ext)
                
                if coincidencia:
                    nombre_limpio = coincidencia.group(1).strip()
                    ruta_completa = os.path.join(raiz, archivo)
                    canciones[nombre_limpio].append(ruta_completa)

    encontrados = False

    for nombre, rutas in canciones.items():
        if len(rutas) > 1:
            encontrados = True
            print(f"\nCanción: {nombre}")
            for r in rutas:
                print(f"   - {r}")
    
    if not encontrados:
        print("No se encontraron canciones duplicadas.")

if __name__ == "__main__":
    ruta_musica = "Musica"
    
    if os.path.exists(ruta_musica):
        buscar_canciones_duplicadas(ruta_musica)
    else:
        print(f"Error: La carpeta '{ruta_musica}' no existe.")
