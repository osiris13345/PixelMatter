"""Motor de imágenes para PixelMatte.

Todas las funciones de acción devuelven (ok: bool, mensaje: str) para que la
interfaz pueda mostrar el motivo real del error.
"""
import os
import sys
import threading

# Con PyInstaller --noconsole, stdout/stderr valen None y las librerías que
# imprimen progreso (descarga del modelo de rembg) fallan. Se redirigen.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from PIL import Image, ImageOps

_Resampling = getattr(Image, "Resampling", Image)
_LANCZOS = _Resampling.LANCZOS
_BOX = _Resampling.BOX
_NEAREST = _Resampling.NEAREST
_MEDIANCUT = getattr(Image, "Quantize", Image).MEDIANCUT
_SIN_DITHER = getattr(Image, "Dither", Image).NONE

# Formato de salida -> extensión
FORMATOS_SALIDA = {"PNG": ".png", "JPG": ".jpg", "WEBP": ".webp"}

# Modelos de rembg disponibles: nombre -> descripción (la interfaz los muestra tal cual).
MODELOS_REMBG = {
    "u2netp": "Ultra-ligero: Más rápido, menos preciso (ideal para pruebas).",
    "u2net": "Estándar: Buen balance entre velocidad y precisión.",
    "isnet-general-use": "Alta precisión: Más lento, mayor calidad en los bordes.",
}
MODELO_DEFECTO = "u2netp"

# Cachea las sesiones de rembg: cargar el modelo es lo más lento del proceso.
_sesiones = {}
_candado = threading.Lock()  # vista previa y tareas corren en hilos distintos


# ---------- Utilidades internas ----------
def _tiene_alpha(img):
    return img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)


def _a_rgb(img):
    """Convierte a RGB aplanando la transparencia sobre blanco (en vez de negro)."""
    if _tiene_alpha(img):
        rgba = img.convert("RGBA")
        fondo = Image.new("RGB", rgba.size, (255, 255, 255))
        fondo.paste(rgba, mask=rgba.getchannel("A"))
        return fondo
    return img.convert("RGB")


def _fmt_tam(n):
    return f"{n / 1024:.0f} KB" if n < 1024 ** 2 else f"{n / 1024 ** 2:.2f} MB"


# ---------- API pública ----------
def cargar_miniatura(path, tam=(220, 120)):
    """Devuelve una miniatura PIL (respeta la orientación EXIF)."""
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        img.thumbnail(tam)
        return img.copy()


def _normalizar_modelo(modelo):
    """Acepta 'u2net' o etiquetas antiguas como 'u2net (Pro / HD)'. Desconocido -> por defecto."""
    nombre = (modelo or "").strip().split(" ")[0]
    return nombre if nombre in MODELOS_REMBG else MODELO_DEFECTO


def remover_fondo_imagen(input_path, output_path, modelo=MODELO_DEFECTO):
    try:
        try:
            from rembg import remove, new_session
        except (ImportError, SystemExit) as e:
            # Se muestra el error real: casi nunca es que falte rembg, sino una
            # dependencia suya (onnxruntime, pymatting, numba...) sin empaquetar.
            return False, f"No se pudo cargar rembg: {type(e).__name__}: {e}"

        modelo = _normalizar_modelo(modelo)
        with _candado:
            if modelo not in _sesiones:
                _sesiones[modelo] = new_session(modelo)  # la primera vez descarga el modelo
            sesion = _sesiones[modelo]

        with Image.open(input_path) as img:
            img = ImageOps.exif_transpose(img).convert("RGBA")
            resultado = remove(img, session=sesion)

        resultado.save(output_path, "PNG")
        return True, "Fondo removido correctamente."
    except Exception as e:
        return False, f"No se pudo quitar el fondo: {e}"


def redimensionar_imagen(input_path, output_path, ancho=None, alto=None):
    """Redimensiona. Si solo se da ancho o alto, calcula el otro conservando la proporción."""
    try:
        if ancho is None and alto is None:
            return False, "Indica al menos el ancho o el alto."
        if (ancho is not None and ancho <= 0) or (alto is not None and alto <= 0):
            return False, "El ancho y el alto deben ser mayores que 0."

        with Image.open(input_path) as img:
            img = ImageOps.exif_transpose(img)
            w, h = img.size
            if ancho is None:
                ancho = max(1, round(w * alto / h))
            elif alto is None:
                alto = max(1, round(h * ancho / w))
            resultado = img.resize((ancho, alto), _LANCZOS)

        salida_lower = output_path.lower()
        if salida_lower.endswith((".jpg", ".jpeg")):
            resultado = _a_rgb(resultado)  # JPEG no soporta transparencia

        opciones = {"quality": 95} if salida_lower.endswith((".jpg", ".jpeg", ".webp")) else {}
        resultado.save(output_path, **opciones)
        return True, f"Nuevo tamaño: {ancho}x{alto} px."
    except Exception as e:
        return False, f"No se pudo redimensionar: {e}"


def convertir_formato_imagen(input_path, output_path, calidad=90):
    """Convierte entre PNG, JPG y WEBP (el formato se toma de la extensión de salida)."""
    try:
        ext = os.path.splitext(output_path)[1].lower()
        calidad = max(1, min(100, int(calidad)))

        with Image.open(input_path) as img:
            img = ImageOps.exif_transpose(img)

            if ext in (".jpg", ".jpeg"):
                img = _a_rgb(img)
                img.save(output_path, "JPEG", quality=calidad, optimize=True)
            elif ext == ".webp":
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA" if _tiene_alpha(img) else "RGB")
                img.save(output_path, "WEBP", quality=calidad)
            elif ext == ".png":
                if img.mode not in ("L", "LA", "P", "RGB", "RGBA"):
                    img = img.convert("RGBA" if _tiene_alpha(img) else "RGB")
                img.save(output_path, "PNG", optimize=True)
            else:
                return False, f"Formato de salida no soportado: {ext}"

        antes = os.path.getsize(input_path)
        despues = os.path.getsize(output_path)
        cambio = (despues / antes - 1) * 100 if antes else 0
        return True, f"{_fmt_tam(antes)} → {_fmt_tam(despues)} ({cambio:+.0f}%)"
    except Exception as e:
        return False, f"No se pudo convertir la imagen: {e}"


def pixelar_imagen(input_path, output_path, tam_pixel=8, colores=16):
    """Efecto pixel art: promedia bloques de tam_pixel y limita la paleta a `colores`."""
    try:
        tam_pixel = max(1, int(tam_pixel))
        colores = max(2, min(256, int(colores)))

        with Image.open(input_path) as img:
            img = ImageOps.exif_transpose(img).convert("RGBA")

        w, h = img.size
        sw, sh = max(1, w // tam_pixel), max(1, h // tam_pixel)

        pequena = img.resize((sw, sh), _BOX)
        alpha = pequena.getchannel("A").point(lambda a: 255 if a >= 128 else 0)  # bordes duros
        rgb = pequena.convert("RGB").quantize(
            colors=colores, method=_MEDIANCUT, dither=_SIN_DITHER
        ).convert("RGB")
        rgb.putalpha(alpha)

        resultado = rgb.resize((sw * tam_pixel, sh * tam_pixel), _NEAREST)
        resultado.save(output_path, "PNG")
        return True, (
            f"Cuadrícula de {sw}x{sh} bloques, {colores} colores máx. "
            f"(salida {resultado.size[0]}x{resultado.size[1]} px)."
        )
    except Exception as e:
        return False, f"No se pudo crear el pixel art: {e}"
