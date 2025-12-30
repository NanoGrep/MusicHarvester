import sys
import os
import shutil
import requests
import yt_dlp
import io
import base64
from PIL import Image
from mutagen.oggopus import OggOpus
from mutagen.flac import Picture
import time
import random

"""
Script de Descarga y Organización de Música (Youtube Music -> Opus)

Este script permite descargar canciones o playlists desde YouTube/Youtube Music,
convertirlas a formato Opus, aplicar etiquetas de metadatos avanzadas (título,
artista, álbum, carátula, letras, etc.) y organizar los archivos en una estructura
de carpetas limpia: Musica/Artista/Album/.

Requisitos:
    - yt-dlp (actualizado)
    - ffmpeg (instalado en el sistema)
    - Librerías python: mutagen, Pillow, requests, yt-dlp

Uso:
    python3 musica.py [URL] [Ruta Cookies]
"""

def limpiar_nombre_archivo(nombre):
    """
    Limpia una cadena de texto para que sea segura de usar como nombre de archivo o carpeta.
    
    Args:
        nombre (str): El nombre sucio (puede contener caracteres ilegales).
        
    Returns:
        str: El nombre limpio, sin caracteres especiales no permitidos en sistemas de archivos.
             Si el input es None, retorna "Unknown".
    """
    # Permite letras, números y algunos caracteres seguros
    if not nombre: return "Unknown"
    nombre = str(nombre)
    return "".join([c for c in nombre if c.isalpha() or c.isdigit() or c in ' .-_()']).strip()

def obtener_info_caratula(thumbnails):
    """
    Selecciona la mejor carátula disponible de la lista de thumbnails proporcionada por yt-dlp.
    Prioriza imágenes cuadradas (1:1) de alta resolución, ideales para portadas de álbumes.
    
    Args:
        thumbnails (list): Lista de diccionarios con info de imágenes (url, width, height).
        
    Returns:
        tuple: (url_mejor_imagen (str), es_cuadrada (bool))
    """
    best_thumb = None
    max_res = 0
    found_square = False
    for thumb in thumbnails:
        width = thumb.get('width', 0)
        height = thumb.get('height', 0)
        url = thumb.get('url', '')
        if width > 0 and abs(width - height) <= 2:
            if (width * height) > max_res:
                max_res = width * height
                best_thumb = url
                found_square = True
    if found_square:
        return best_thumb, True
    
    # Fallback si no hay thumbnails o lista vacía
    if not thumbnails:
        return None, False
        
    best_thumb = thumbnails[-1]['url']
    for thumb in thumbnails:
        if (thumb.get('width', 0) * thumb.get('height', 0)) > max_res:
            max_res = thumb.get('width', 0) * thumb.get('height', 0)
            best_thumb = thumb['url']
    return best_thumb, False

def procesar_imagen(url):
    """
    Descarga y procesa la imagen desde la URL. Recorta la imagen al centro para hacerla cuadrada
    si no lo es, y la redimensiona a 800x800px para estandarizar el peso y tamaño.
    
    Args:
        url (str): URL de la imagen a procesar.
        
    Returns:
        tuple: (bytes_imagen_jpeg, ancho, alto)
               Retorna (None, 0, 0) si falla.
    """
    if not url: return None, 0, 0
    try:
        response = requests.get(url, timeout=10)
        img = Image.open(io.BytesIO(response.content))
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        width, height = img.size
        if width != height:
            new_size = min(width, height)
            left = int((width - new_size) / 2)
            top = int((height - new_size) / 2)
            right = int((width + new_size) / 2)
            bottom = int((height + new_size) / 2)
            img = img.crop((left, top, right, bottom))
        img.thumbnail((800, 800), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        return buffer.getvalue(), img.width, img.height
    except Exception as e:
        print(f"⚠️ Error procesando imagen: {e}")
        return None, 0, 0

def etiquetar_y_mover(ruta_archivo, info_dict):
    """
    Aplica metadatos al archivo de audio (Opus) usando Mutagen y lo mueve a su carpeta final.
    
    Etapas:
    1. Lee metadatos proporcionados por yt-dlp (info_dict).
    2. Inserta tags: Título, Artista, Álbum, Fecha, ISRC, Descripción, Tracknumber, etc.
    3. Descarga e incrusta la carátula procesada.
    4. Mueve el archivo a: Musica/{Artista}/{Album}/{Cancion}.opus
    
    Args:
        ruta_archivo (str): Ruta temporal del archivo descargado.
        info_dict (dict): Diccionario con toda la metadata del video extraída por yt-dlp.
    """
    # Variables para organizar carpetas
    artista_final = "Unknown Artist"
    album_final = "Singles"
    
    # --- ETAPA 1: ETIQUETADO ---
    try:
        audio = OggOpus(ruta_archivo)
        
        # 1. Datos Principales
        titulo = info_dict.get('title', 'Unknown')
        raw_artist = info_dict.get('artist')
        
        if raw_artist:
            if isinstance(raw_artist, list):
                artista = str(raw_artist[0])
            else:
                artista = str(raw_artist).split(',')[0].strip()
        else:
            artista = info_dict.get('uploader', 'Unknown')
            
        album = info_dict.get('album')
        
        # Guardamos estos datos limpios para usar en la Etapa 2 (Carpetas)
        artista_final = artista
        # Lógica: Si hay album y no es igual al título (single), es un album.
        if album and album.lower() != titulo.lower():
            album_final = album

        # Fecha
        fecha_raw = info_dict.get('release_date') or info_dict.get('upload_date')
        fecha_fmt = f"{fecha_raw[:4]}-{fecha_raw[4:6]}-{fecha_raw[6:]}" if fecha_raw and len(fecha_raw) == 8 else None

        # Asignación de Tags
        audio['title'] = titulo
        audio['artist'] = artista
        audio['album_artist'] = info_dict.get('album_artist') or artista
        audio['album'] = album if album else titulo # En metadata, si es single, el album suele ser el titulo
        audio['encodedby'] = "yt-dlp script"
        
        if fecha_fmt:
            audio['date'] = fecha_fmt
            audio['originaldate'] = fecha_fmt

        # 2. Créditos
        compositor = info_dict.get('composer') or info_dict.get('creator')
        if compositor: audio['composer'] = compositor
        
        publisher = info_dict.get('record_label')
        copyright_str = info_dict.get('copyright')
        
        if publisher:
            audio['organization'] = publisher
            audio['publisher'] = publisher
        elif copyright_str:
            parts = copyright_str.split(' ', 2)
            if len(parts) > 2:
                audio['organization'] = parts[-1]

        audio['copyright'] = copyright_str if copyright_str else f"(C) {fecha_fmt[:4] if fecha_fmt else '2024'} {artista}"

        # 3. Otros metadatos
        if info_dict.get('isrc'): audio['isrc'] = info_dict.get('isrc')
        desc = info_dict.get('description')
        if desc: audio['description'] = desc[:500] # Limite opcional
        if info_dict.get('language'): audio['language'] = info_dict.get('language')
        
        # URLs
        audio['woas'] = info_dict.get('webpage_url')
        
        # 4. Numeración
        track_num = info_dict.get('track_number') or info_dict.get('playlist_index')
        total_tracks = info_dict.get('n_entries')
        
        if track_num: audio['tracknumber'] = str(track_num)
        if total_tracks and total_tracks > 1: audio['tracktotal'] = str(total_tracks)

        # 5. Carátula
        thumbnails = info_dict.get('thumbnails', [])
        if thumbnails:
            url_caratula, _ = obtener_info_caratula(thumbnails)
            img_data, w, h = procesar_imagen(url_caratula)
            if img_data:
                p = Picture()
                p.data = img_data
                p.type = 3
                p.mime = "image/jpeg"
                p.width = w
                p.height = h
                p.depth = 24
                picture_data = p.write()
                encoded_data = base64.b64encode(picture_data).decode("ascii")
                audio["metadata_block_picture"] = [encoded_data]

        audio.save()
        print(f"Etiquetas aplicadas a: {os.path.basename(ruta_archivo)}")

    except Exception as e:
        print(f"Error al etiquetar (continuando movimiento): {e}")

    # --- ETAPA 2: MOVER ARCHIVO ---
    # Esta parte ahora está FUERA del try/except del etiquetado
    try:
        # 1. Limpiar nombres para carpetas
        clean_artist = limpiar_nombre_archivo(artista_final)
        if not clean_artist: clean_artist = "Unknown_Artist"
        
        clean_album = limpiar_nombre_archivo(album_final)
        if not clean_album: clean_album = "Singles"
            
        # 2. Estructura: Musica / Artista / Album
        cwd = os.getcwd()
        base_dir = os.path.join(cwd, "Musica")
        final_dir = os.path.join(base_dir, clean_artist, clean_album)
        
        if not os.path.exists(final_dir):
            os.makedirs(final_dir, exist_ok=True)
            
        # 3. Mover
        nombre_archivo = os.path.basename(ruta_archivo)
        ruta_destino = os.path.join(final_dir, nombre_archivo)
        
        # Si ya existe en destino, borrar para sobrescribir
        if os.path.exists(ruta_destino):
            os.remove(ruta_destino)
            
        shutil.move(ruta_archivo, ruta_destino)
        print(f"Movido a: Musica/{clean_artist}/{clean_album}/{nombre_archivo}")
        
    except Exception as e:
        print(f"Error al mover el archivo: {e}")

def ya_descargado(video_id):
    """
    Verifica si una canción ya ha sido descargada previamente buscando su ID de video
    en todos los archivos .opus dentro de la carpeta 'Musica/'.
    
    Esto evita duplicados incluso si la canción se movió de carpeta, siempre que conserve
    el [ID] en el nombre del archivo.
    
    Args:
        video_id (str): El ID único del video de YouTube.
        
    Returns:
        bool: True si ya existe, False si no.
    """
    cwd = os.getcwd()
    base_dir = os.path.join(cwd, "Musica")
    
    if not os.path.exists(base_dir):
        return False
        
    target = f"[{video_id}]"
    
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".opus") and target in file:
                return True
    return False

def procesar_url(url, ruta_cookies=None):
    """
    Función principal que orquesta la descarga de una URL (Video o Playlist).
    
    Flujo:
    1. Obtiene información de la URL (sin descargar) para listar canciones.
    2. Itera sobre cada canción (entry).
    3. Verifica si ya existe (ya_descargado).
    4. Si no existe, descarga el audio en formato Opus.
    5. Llama a 'etiquetar_y_mover' para finalizar el proceso.
    
    Args:
        url (str): Enlace de YouTube o Youtube Music.
        ruta_cookies (str, optional): Ruta al archivo de cookies (Netscape format) para contenido premium/age-gated.
    """
    # Lógica de cookies
    cookies_opt = None
    if ruta_cookies and os.path.exists(ruta_cookies):
        print(f"Descargando CON cookies ({ruta_cookies})")
        cookies_opt = ruta_cookies
    else:
        print("Descargando SIN cookies")

    ydl_opts_info = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'cookiefile': cookies_opt, # Añadido
    }
    
    try:
        print(f"Obteniendo lista de canciones de: {url}")
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl_info:
            info = ydl_info.extract_info(url, download=False)
            
        if 'entries' in info:
            entries = info['entries']
            n_entries = info.get('playlist_count', len(entries))
        else:
            entries = [info]
            n_entries = 1
        
        for entry in entries:
            if not entry: continue
            
            url_cancion = entry.get('url') or entry.get('webpage_url')
            video_id = entry.get('id')
            
            if not url_cancion or not video_id: continue

            if ya_descargado(video_id):
                print(f"Saltando (Ya existe): {entry.get('title', 'Unknown')}")
                continue

            titulo_temp = limpiar_nombre_archivo(entry.get('title', 'track'))
            temp_filename = f"{titulo_temp} [{video_id}]" 
            
            print(f"\n🎵 Descargando: {entry.get('title')}")
            
            ydl_opts_download = {
                'format': 'bestaudio/best',
                'outtmpl': f"{temp_filename}.%(ext)s",
                'quiet': True,
                'no_warnings': True,
                'cookiefile': cookies_opt, # Añadido
                'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'opus'}],
            }
            
            ruta_opus_local = f"{temp_filename}.opus"

            with yt_dlp.YoutubeDL(ydl_opts_download) as ydl_download:
                info_full = ydl_download.extract_info(url_cancion, download=True)
                info_full['n_entries'] = n_entries
                
                if os.path.exists(ruta_opus_local):
                    etiquetar_y_mover(ruta_opus_local, info_full)
                    
            wait_time = random.uniform(5, 15)
            print(f"Esperando {wait_time:.1f} segundos...")
            time.sleep(wait_time)
                    
    except Exception as e:
        print(f"Error general en proceso: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 musica.py [URL] [Ruta Cookies]")
    else:
        url_input = sys.argv[1]
        # Si hay un tercer argumento, lo toma como ruta de cookies, si no, es None
        cookies_input = sys.argv[2] if len(sys.argv) > 2 else None
        procesar_url(url_input, cookies_input)
