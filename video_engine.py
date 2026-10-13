"""Motor de video para PixelMatte (compatible con MoviePy 1.x y 2.x).

Las funciones de acción devuelven (ok: bool, mensaje: str).
"""
import os

from PIL import Image

_LANCZOS = getattr(Image, "Resampling", Image).LANCZOS

# Relación de aspecto objetivo por formato. Se busca la clave dentro del texto del menú.
FORMATOS = {
    "16:9": 16 / 9,
    "9:16": 9 / 16,
    "1:1": 1.0,
}

# Texto del menú -> CRF de libx264 (menor = mejor calidad y más peso)
CALIDADES_CRF = {
    "Alta (menos compresión)": 20,
    "Media (recomendada)": 26,
    "Baja (mínimo peso)": 32,
}

# Texto del menú -> altura máxima en px (None = sin cambiar)
ALTURAS = {"Original": None, "1080p": 1080, "720p": 720, "480p": 480}

# Un GIF largo consume mucha memoria y pesa demasiado
MAX_GIF_SEG = 30


# ---------- Utilidades internas ----------
def _abrir_clip(path):
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
    except ImportError as e:
        raise RuntimeError("MoviePy no está instalado. Instálalo con: pip install moviepy") from e
    return VideoFileClip(path)


def _subclip(clip, inicio, fin):
    # MoviePy 2.x: subclipped(); MoviePy 1.x: subclip()
    metodo = getattr(clip, "subclipped", None) or clip.subclip
    return metodo(inicio, fin)


def _crop(clip, x1, y1, x2, y2):
    # MoviePy 2.x: cropped(); MoviePy 1.x: crop()
    metodo = getattr(clip, "cropped", None) or clip.crop
    return metodo(x1=x1, y1=y1, x2=x2, y2=y2)


def _resize(clip, ancho, alto):
    # MoviePy 2.x: resized(); MoviePy 1.x: resize(). El tamaño va posicional (el nombre cambia entre versiones).
    metodo = getattr(clip, "resized", None) or clip.resize
    return metodo((ancho, alto))


def _par(n):
    """libx264 con yuv420p exige dimensiones pares."""
    n = int(n)
    return max(2, n - n % 2)


def _forzar_par(clip):
    w, h = clip.size
    if w % 2 or h % 2:
        return _crop(clip, 0, 0, _par(w), _par(h))
    return clip


def _mb(n):
    return f"{n / 1024 ** 2:.1f} MB"


def _guardar_video(clip, output_path, fps, crf=None, audio_bitrate=None):
    params = ["-pix_fmt", "yuv420p", "-movflags", "+faststart"]  # compatible y listo para web
    if crf is not None:
        params += ["-crf", str(crf)]
    extra = {"audio_bitrate": audio_bitrate} if audio_bitrate else {}

    _forzar_par(clip).write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=fps,
        preset="medium",
        ffmpeg_params=params,
        logger=None,
        **extra,
    )


def _cerrar(*clips):
    for c in clips:
        if c is not None:
            try:
                c.close()
            except Exception:
                pass


def _rango(clip, inicio, fin):
    """Normaliza inicio/fin. Devuelve (inicio, fin, error_o_None)."""
    duracion = clip.duration
    inicio = max(0.0, inicio or 0.0)
    fin = duracion if fin is None else min(fin, duracion)
    if inicio >= fin:
        return inicio, fin, f"El inicio debe ser menor que el fin (el video dura {duracion:.2f} s)."
    return inicio, fin, None


# ---------- API pública ----------
def obtener_fotograma(path, t=0):
    """Devuelve el fotograma en el segundo t como arreglo numpy (lanza excepción si falla)."""
    clip = None
    try:
        clip = _abrir_clip(path)
        return clip.get_frame(t)
    finally:
        _cerrar(clip)


def extraer_audio(input_path, output_path):
    clip = None
    try:
        clip = _abrir_clip(input_path)
        if clip.audio is None:
            return False, "El video seleccionado no contiene pistas de audio."
        clip.audio.write_audiofile(output_path, logger=None)
        return True, "Audio extraído correctamente."
    except Exception as e:
        return False, f"No se pudo extraer el audio: {e}"
    finally:
        _cerrar(clip)


def recortar_video(input_path, output_path, inicio=0.0, fin=None):
    """Recorta de inicio a fin (segundos). fin=None significa hasta el final."""
    clip = sub = None
    try:
        clip = _abrir_clip(input_path)
        inicio, fin, error = _rango(clip, inicio, fin)
        if error:
            return False, error

        sub = _subclip(clip, inicio, fin)
        _guardar_video(sub, output_path, clip.fps or 30)
        return True, f"Segmento de {inicio:.2f}s a {fin:.2f}s guardado."
    except Exception as e:
        return False, f"No se pudo recortar el video: {e}"
    finally:
        _cerrar(sub, clip)


def cambiar_formato_video(input_path, output_path, formato_destino):
    """Recorta (centrado) el video a la relación de aspecto elegida y lo exporta a MP4."""
    clip = recorte = None
    try:
        clave = next((k for k in FORMATOS if k in formato_destino), None)
        if clave is None:
            return False, f"Formato no reconocido: {formato_destino}"
        ratio = FORMATOS[clave]

        clip = _abrir_clip(input_path)
        w, h = clip.size

        # Mayor área posible con esa proporción dentro del video original
        if w / h > ratio:
            nuevo_w, nuevo_h = h * ratio, h
        else:
            nuevo_w, nuevo_h = w, w / ratio
        nuevo_w, nuevo_h = _par(min(nuevo_w, w)), _par(min(nuevo_h, h))

        x1 = (w - nuevo_w) // 2
        y1 = (h - nuevo_h) // 2
        recorte = _crop(clip, x1, y1, x1 + nuevo_w, y1 + nuevo_h)

        _guardar_video(recorte, output_path, clip.fps or 30)
        return True, f"Video exportado a {nuevo_w}x{nuevo_h} ({clave})."
    except Exception as e:
        return False, f"No se pudo cambiar el formato: {e}"
    finally:
        _cerrar(recorte, clip)


def comprimir_video(input_path, output_path, crf=26, altura_max=None):
    """Reduce el peso con CRF de libx264 y, opcionalmente, bajando la resolución."""
    clip = None
    try:
        clip = _abrir_clip(input_path)
        w, h = clip.size

        a_guardar = clip
        if altura_max and h > altura_max:
            nuevo_h = _par(altura_max)
            nuevo_w = _par(w * nuevo_h / h)
            a_guardar = _resize(clip, nuevo_w, nuevo_h)

        _guardar_video(a_guardar, output_path, clip.fps or 30, crf=crf, audio_bitrate="128k")

        antes = os.path.getsize(input_path)
        despues = os.path.getsize(output_path)
        cambio = (despues / antes - 1) * 100 if antes else 0
        return True, f"{_mb(antes)} → {_mb(despues)} ({cambio:+.0f}%)"
    except Exception as e:
        return False, f"No se pudo comprimir el video: {e}"
    finally:
        _cerrar(clip)


def video_a_gif(input_path, output_path, inicio=0.0, fin=None, fps=12, ancho=480):
    """Convierte un segmento (máx. MAX_GIF_SEG s) a GIF animado usando Pillow."""
    clip = sub = None
    try:
        clip = _abrir_clip(input_path)
        inicio, fin, error = _rango(clip, inicio, fin)
        if error:
            return False, error
        if fin - inicio > MAX_GIF_SEG:
            return False, (
                f"El segmento dura {fin - inicio:.1f} s y el máximo para GIF es {MAX_GIF_SEG} s.\n"
                "Usa Inicio y Fin (sección Recortar) para elegir un tramo más corto."
            )

        sub = _subclip(clip, inicio, fin)
        fps = max(1, min(int(fps), int(clip.fps or fps)))
        w, h = clip.size
        ancho = max(2, min(int(ancho), w))
        alto = max(2, round(h * ancho / w))

        frames = [
            Image.fromarray(fr).resize((ancho, alto), _LANCZOS).quantize(colors=256)
            for fr in sub.iter_frames(fps=fps, dtype="uint8")
        ]
        if not frames:
            return False, "No se pudieron obtener fotogramas del segmento."

        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=int(1000 / fps),
            loop=0,
            disposal=2,
        )
        peso = _mb(os.path.getsize(output_path))
        return True, f"GIF de {len(frames)} fotogramas a {ancho}x{alto}, {fps} fps, {peso}."
    except Exception as e:
        return False, f"No se pudo crear el GIF: {e}"
    finally:
        _cerrar(sub, clip)
