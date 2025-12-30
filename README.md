# MusicHarvester

**MusicHarvester** es una utilidad en **Python 3** para obtener audio desde **YouTube** / **YouTube Music**, convertirlo a Opus, aplicar etiquetado avanzado de metadatos, incrustar carátulas y organizar automáticamente una biblioteca musical limpia por artista y álbum.

El script está pensado para uso en GNU/Linux, con soporte opcional de cookies para evitar bloqueos por rate-limit, contenido con restricción de edad o cuentas autenticadas.

## Características

- Descarga de audio desde YouTube y YouTube Music
- Conversión automática a Opus
- Etiquetado completo de metadatos (título, artista, álbum, fecha, ISRC, etc.)
- Incrustación de carátulas en el archivo de audio
- Organización automática: Musica/Artista/Álbum/
- Detección de duplicados por ID de YouTube
- Soporte con y sin cookies

## Requisitos

- Python 3.8+
- **ffmpeg** instalado y accesible desde el PATH

```
python3 -m venv venv
source venv/bin/activate
```

```
pip install yt-dlp mutagen pillow requests
```

## Uso

#### Uso básico (sin cookies)

```
python3 musica.py <URL>
```

```
python3 musica.py https://music.youtube.com/playlist?list=XXXXXXXX
```

#### Uso con cookies 

```
python3 musica.py <URL> <ruta_cookies.txt>
```

```
python3 musica.py https://music.youtube.com/playlist?list=XXXXXXXX cookies.txt

```
