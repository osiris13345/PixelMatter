import io
import math
import os
import platform
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
import tkinter as tk
import webbrowser
from urllib.parse import quote, unquote, urlparse

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageTk

import image_engine
import video_engine

# Intento seguro de carga para tkinterdnd2 en Linux
HAS_DND = False
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except Exception:
    HAS_DND = False

# Configuración de apariencia
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

EXT_IMAGEN = (".png", ".jpg", ".jpeg", ".webp")
EXT_VIDEO = (".mp4", ".mkv", ".avi", ".mov")

# Paleta estilo "UI Kit": tuplas = (modo claro, modo oscuro)
ACCENT = "#3b9ef0"
ACCENT_HOVER = "#2a86d6"
BG = ("#eef1f6", "#1c1f26")
CARD = ("#ffffff", "#262a33")
SOFT = ("#e3e8f0", "#323744")
BORDER = ("#c9d3e0", "#3a4150")
TEXT = ("#333333", "#e6e9ef")
MUTED = ("#4A5568", "#b4bcc9")  # gris oscuro (claro) / gris claro neutro (oscuro)
TEXT_ACC = ("#333333", "#e6e9ef")  # gris oscuro neutro en claro; gris casi blanco en oscuro
DISABLED = ("#6b7280", "#5b6475")
WARN = ("#92400e", "#eab308")
OK = ("#166534", "#22c55e")
ERR = ("#b91c1c", "#ef4444")

# Vista previa: lado máximo de la copia reducida y caja de visualización
PREV_MAX = 640
PREV_BOX = (290, 165)  # se recalcula según el tamaño de la ventana
SIDEBAR_W = 360  # ancho del menú lateral

# Stickers
STICKER_TAMANOS = {
    "512 px (WhatsApp / Telegram)": 512,
    "256 px (pequeño)": 256,
    "1024 px (alta calidad)": 1024,
}
STICKER_FORMATOS = {"PNG": ".png", "WebP (WhatsApp, máx. 100 KB)": ".webp"}

# Feedback / reportes
VERSION_APP = "1.0"
REPORTE_EMAIL = ""  # opcional: si pones un correo, «Enviar Reporte» también abre tu cliente de correo
CARPETA_REPORTES = os.path.join(os.path.expanduser("~"), ".pixelmatte")

# Remix Icon (https://remixicon.com): coloca remixicon.css y remixicon.ttf en assets/remixicon/
ICONOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "remixicon")
ICONO_CLARO = "#333333"   # icono monocromático en modo claro
ICONO_OSCURO = "#e6e9ef"  # icono monocromático en modo oscuro
_RI = {"codigos": None, "fuente": None}


def _cargar_remixicon():
    """Lee del CSS de Remix Icon el código de cada icono (ri-xxx-line -> carácter)."""
    if _RI["codigos"] is None:
        codigos, fuente = {}, None
        try:
            with open(os.path.join(ICONOS_DIR, "remixicon.css"), encoding="utf-8") as f:
                css = f.read()
            patron = r'\.(ri-[a-z0-9-]+):before\s*\{\s*content:\s*"\\([0-9a-fA-F]+)"'
            for nombre, cod in re.findall(patron, css):
                codigos[nombre] = chr(int(cod, 16))
            ttf = os.path.join(ICONOS_DIR, "remixicon.ttf")
            fuente = ttf if os.path.isfile(ttf) else None
        except Exception:
            codigos, fuente = {}, None
        _RI["codigos"], _RI["fuente"] = codigos, fuente
    return _RI["codigos"], _RI["fuente"]


def _pil_ri(nombre, tam, color):
    """Dibuja un icono de Remix Icon en un solo color. None si no está disponible."""
    codigos, ttf = _cargar_remixicon()
    glifo = codigos.get(nombre)
    if not glifo or not ttf:
        return None
    try:
        n = tam * 4  # sobremuestreo para bordes suaves
        fuente = ImageFont.truetype(ttf, n)
        img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((n / 2, n / 2), glifo, font=fuente, fill=color, anchor="mm")
        return img.resize((tam * 2, tam * 2), Image.LANCZOS)
    except Exception:
        return None


def icono_ri(nombre, tam=18):
    """CTkImage monocromático: #333333 en modo claro, gris claro en modo oscuro."""
    claro = _pil_ri(nombre, tam, ICONO_CLARO)
    oscuro = _pil_ri(nombre, tam, ICONO_OSCURO)
    if claro is None or oscuro is None:
        return None
    return ctk.CTkImage(light_image=claro, dark_image=oscuro, size=(tam, tam))


def guardar_reporte(texto):
    """Guarda el reporte en ~/.pixelmatte/reportes.txt. Devuelve (ok, mensaje)."""
    try:
        os.makedirs(CARPETA_REPORTES, exist_ok=True)
        ruta = os.path.join(CARPETA_REPORTES, "reportes.txt")
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] PixelMatte {VERSION_APP} - "
                f"{platform.platform()}\n{texto}\n{'-' * 60}\n"
            )
        if REPORTE_EMAIL:
            asunto = quote(f"Reporte PixelMatte {VERSION_APP}")
            webbrowser.open(f"mailto:{REPORTE_EMAIL}?subject={asunto}&body={quote(texto)}")
        return True, ruta
    except Exception as e:
        return False, str(e)


def _icono_sol(color, n=128):
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c, r = n / 2, n * 0.2
    d.ellipse([c - r, c - r, c + r, c + r], fill=color)
    for k in range(8):
        a = math.pi / 4 * k
        d.line(
            [c + math.cos(a) * n * 0.31, c + math.sin(a) * n * 0.31,
             c + math.cos(a) * n * 0.45, c + math.sin(a) * n * 0.45],
            fill=color, width=int(n * 0.075),
        )
    return img.resize((40, 40), Image.LANCZOS)


def _icono_luna(color, n=128):
    mascara = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(mascara)
    d.ellipse([n * 0.16, n * 0.16, n * 0.84, n * 0.84], fill=255)
    d.ellipse([n * 0.38, n * 0.04, n * 1.04, n * 0.70], fill=0)
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    img.paste(Image.new("RGBA", (n, n), color), mask=mascara)
    return img.resize((40, 40), Image.LANCZOS)


def crear_icono_tema():
    """Luna en modo claro (pulsar = pasar a oscuro); sol en modo oscuro (Remix Icon si existe)."""
    luna = _pil_ri("ri-moon-line", 22, ICONO_CLARO)
    sol = _pil_ri("ri-sun-line", 22, ICONO_OSCURO)
    if luna is not None and sol is not None:
        return ctk.CTkImage(light_image=luna, dark_image=sol, size=(22, 22))
    return ctk.CTkImage(
        light_image=_icono_luna("#333333"),
        dark_image=_icono_sol("#e6e9ef"),
        size=(22, 22),
    )


def _patrones(extensiones):
    # En Linux los filtros del diálogo distinguen mayúsculas: incluimos ambas
    return " ".join(f"*{e} *{e.upper()}" for e in extensiones)


# Clase base robusta que evita bloqueos si DnD falla en Linux
if HAS_DND:
    class CTkBase(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            global HAS_DND
            super().__init__(*args, **kwargs)
            try:
                self.TkdndVersion = TkinterDnD._require(self)
            except Exception:
                HAS_DND = False
else:
    class CTkBase(ctk.CTk):
        pass


class VentanaComparar(ctk.CTkToplevel):
    """Comparador antes/después: arrastra la barra para revelar uno u otro."""

    def __init__(self, master, antes, despues, titulo):
        super().__init__(master)
        self.title(f"Comparar antes / después - {titulo}")
        self.geometry("900x680")
        self.minsize(480, 360)
        self.configure(fg_color=BG)

        self._antes = antes.convert("RGBA")
        self._despues = despues.convert("RGBA")
        self._pos = 0.5  # posición de la barra (0 a 1)
        self._tam = (0, 0)
        self._izq = None
        self._der = None
        self._foto = None
        self._job = None

        self.canvas = tk.Canvas(
            self, highlightthickness=0, bd=0, bg="#1c1f26", cursor="sb_h_double_arrow"
        )
        self.canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self.canvas.bind("<Configure>", self._al_cambiar_tamano)
        self.canvas.bind("<Button-1>", self._mover)
        self.canvas.bind("<B1-Motion>", self._mover)
        self.bind("<Escape>", lambda _e: self.destroy())

    @staticmethod
    def _tablero(w, h, celda=12):
        """Fondo de cuadros para que se note la transparencia."""
        img = Image.new("RGB", (w, h), (214, 218, 226))
        d = ImageDraw.Draw(img)
        for y in range(0, h, celda):
            for x in range(0, w, celda):
                if ((x // celda) + (y // celda)) % 2:
                    d.rectangle([x, y, x + celda - 1, y + celda - 1], fill=(188, 194, 206))
        return img

    @staticmethod
    def _componer(fondo, img, w, h):
        lienzo = fondo.convert("RGBA")
        esc = min(w / img.width, h / img.height)
        nw, nh = max(1, int(img.width * esc)), max(1, int(img.height * esc))
        lienzo.alpha_composite(img.resize((nw, nh), Image.LANCZOS), ((w - nw) // 2, (h - nh) // 2))
        return lienzo.convert("RGB")

    def _al_cambiar_tamano(self, _evento):
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
        self._job = self.after(80, self._rehacer)

    def _rehacer(self):
        self._job = None
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 50 or h < 50:
            return
        self._tam = (w, h)
        fondo = self._tablero(w, h)
        self._izq = self._componer(fondo, self._antes, w, h)
        self._der = self._componer(fondo, self._despues, w, h)
        self._dibujar()

    def _mover(self, evento):
        w = self._tam[0]
        if w <= 0 or self._izq is None:
            return
        self._pos = min(1.0, max(0.0, evento.x / w))
        self._dibujar()

    def _dibujar(self):
        w, h = self._tam
        x = int(self._pos * w)
        comp = self._der.copy()
        if x > 0:
            comp.paste(self._izq.crop((0, 0, x, h)), (0, 0))
        self._foto = ImageTk.PhotoImage(comp)

        c = self.canvas
        c.delete("all")
        c.create_image(0, 0, image=self._foto, anchor="nw")
        c.create_line(x, 0, x, h, fill="#ffffff", width=2)
        r = 17
        c.create_oval(x - r, h // 2 - r, x + r, h // 2 + r, fill=ACCENT, outline="#ffffff", width=2)
        c.create_text(x, h // 2, text="◀▶", fill="#ffffff", font=("Arial", 9, "bold"))
        c.create_rectangle(8, 8, 78, 32, fill="#1c1f26", outline="")
        c.create_text(43, 20, text="ANTES", fill="#ffffff", font=("Arial", 10, "bold"))
        c.create_rectangle(w - 88, 8, w - 8, 32, fill="#1c1f26", outline="")
        c.create_text(w - 48, 20, text="DESPUÉS", fill="#ffffff", font=("Arial", 10, "bold"))


class SelectorModelos(ctk.CTkFrame):
    """Selector de modelo con una pequeña descripción debajo de cada opción."""

    def __init__(self, master, opciones, inicial):
        super().__init__(master, fg_color="transparent")
        self._valor = inicial
        self._tarjetas = {}
        for clave, descripcion in opciones:
            tarjeta = ctk.CTkFrame(
                self, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER
            )
            tarjeta.pack(fill="x", padx=5, pady=3)
            titulo = ctk.CTkLabel(
                tarjeta, text=clave, anchor="w", font=("Arial", 12, "bold"), text_color=TEXT
            )
            titulo.pack(fill="x", padx=12, pady=(8, 0))
            detalle = ctk.CTkLabel(
                tarjeta, text=descripcion, anchor="w", justify="left",
                font=("Arial", 11), text_color=MUTED, wraplength=240,
            )
            detalle.pack(fill="x", padx=12, pady=(0, 8))
            for w in (tarjeta, titulo, detalle):
                w.bind("<Button-1>", lambda _e, c=clave: self.set(c))
            self._tarjetas[clave] = (tarjeta, titulo)
        self.set(inicial)

    def get(self):
        return self._valor

    def set(self, clave):
        if clave not in self._tarjetas:
            return
        self._valor = clave
        for k, (tarjeta, titulo) in self._tarjetas.items():
            activo = k == clave
            tarjeta.configure(
                border_color=ACCENT if activo else BORDER,
                border_width=2 if activo else 1,
                fg_color=SOFT if activo else CARD,
            )
            titulo.configure(text=("●  " if activo else "○  ") + k)


class VentanaReporte(ctk.CTkToplevel):
    """Ventana sencilla para enviar feedback o reportar un problema."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Feedback y reportes")
        self.geometry("460x360")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.transient(master)

        ctk.CTkLabel(
            self, text="Enviar feedback o reportar un problema",
            font=("Arial", 15, "bold"), text_color=TEXT,
        ).pack(anchor="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(
            self, text="Cuéntanos qué pasó, qué esperabas o qué mejorarías.",
            font=("Arial", 11), text_color=MUTED, wraplength=410, justify="left",
        ).pack(anchor="w", padx=20)

        self.caja = ctk.CTkTextbox(
            self, height=170, corner_radius=12, fg_color=CARD, border_width=1,
            border_color=BORDER, text_color=TEXT, wrap="word",
        )
        self.caja.pack(fill="both", expand=True, padx=20, pady=12)

        self.lbl_msg = ctk.CTkLabel(self, text="", font=("Arial", 11), text_color=ERR)
        self.lbl_msg.pack(anchor="w", padx=20)

        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x", padx=20, pady=(6, 18))
        ctk.CTkButton(
            fila, text="Cancelar", width=110, height=38, corner_radius=19,
            fg_color="transparent", border_width=2, border_color=ACCENT,
            text_color=TEXT_ACC, hover_color=SOFT, font=("Arial", 13, "bold"),
            command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            fila, text="Enviar Reporte", height=38, corner_radius=19,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=("#ffffff", "#ffffff"),
            font=("Arial", 13, "bold"), command=self._enviar,
        ).pack(side="right", expand=True, fill="x", padx=(10, 0))

        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(150, self._preparar)

    def _preparar(self):
        try:
            self.lift()
            self.grab_set()  # modal
            self.caja.focus_set()
        except Exception:
            pass

    def _enviar(self):
        texto = self.caja.get("1.0", "end").strip()
        if not texto:
            self.lbl_msg.configure(text="Escribe un mensaje antes de enviar.")
            return
        ok, dato = guardar_reporte(texto)
        if not ok:
            self.lbl_msg.configure(text=f"No se pudo guardar el reporte: {dato}")
            return
        try:
            self.master._aviso_temporal("Reporte guardado. ¡Gracias por tu feedback!", OK)
        except Exception:
            pass
        self.destroy()


class PixelMatteApp(CTkBase):
    TXT_RESULTADO = "Pulsa «Vista previa» en una\nsección para ver cómo quedará"

    def __init__(self):
        super().__init__()

        # Ventana principal
        self.title("PixelMatte - Multimedia Suite")
        self.geometry("1150x760")
        self.minsize(820, 600)
        self.configure(fg_color=BG)

        # Estado
        self.img_input_path = ""
        self.video_input_path = ""
        self.img_preview_obj = None
        self.vid_preview_obj = None
        self._ocupado = False
        self._cola = queue.Queue()  # resultados de los hilos de trabajo
        self._cola_prev = queue.Queue()  # resultados de las vistas previas
        self._prev_token = 0  # invalida vistas previas viejas
        self._prev_ocupado = False
        self.img_result_obj = None
        self._botones_prev = []
        self._fullscreen = False
        self._menu_visible = True
        self._ajuste_job = None
        self._vid_frame_full = None  # fotograma completo para reescalar la vista previa
        self._box_vid = (300, 170)
        self._res_pil_full = None  # vista previa del resultado (para comparar)
        self._res_caption = ""
        self._ultimo_resultado = ""  # último archivo de imagen guardado
        self._ventana_comparar = None
        self._ventana_reporte = None

        # Cabecera
        encabezado = ctk.CTkFrame(self, fg_color=BG)
        encabezado.pack(fill="x", padx=25, pady=(15, 2))
        self.btn_menu = ctk.CTkButton(
            encabezado, text="☰  Menú", width=90, height=30, corner_radius=15,
            fg_color="transparent", border_width=2, border_color=ACCENT,
            text_color=TEXT_ACC, hover_color=SOFT, font=("Arial", 12, "bold"),
            command=self._alternar_menu,
        )
        self.btn_menu.pack(side="left", padx=(0, 28))
        self.label_header = ctk.CTkLabel(
            encabezado, text="PixelMatte", font=("Arial", 22, "bold"), text_color=TEXT_ACC
        )
        self.label_header.pack(side="left")
        self.btn_tema = ctk.CTkButton(
            encabezado, text="", image=crear_icono_tema(), width=38, height=38,
            corner_radius=12, fg_color=SOFT, hover_color=BORDER,
            border_width=1, border_color=BORDER, command=self._cambiar_tema,
        )
        self.btn_tema.pack(side="right")

        icono_rep = icono_ri("ri-feedback-line", 22) or icono_ri("ri-bug-line", 22)
        self.btn_reporte = ctk.CTkButton(
            encabezado, text="" if icono_rep else "✉", image=icono_rep, width=38, height=38,
            corner_radius=12, fg_color="transparent", hover_color=SOFT, text_color=TEXT,
            border_width=0, command=self._abrir_reporte,
        )
        self.btn_reporte.pack(side="right", padx=(0, 6))

        # Barra de Estado Global
        self.lbl_status = ctk.CTkLabel(
            self, text="Listo para procesar", text_color=TEXT_ACC, font=("Arial", 11, "bold")
        )
        self.lbl_status.pack(pady=(0, 2), anchor="center")

        # Barra de Progreso (indeterminada mientras se procesa)
        self.progress_bar = ctk.CTkProgressBar(
            self, height=10, corner_radius=5, progress_color=ACCENT, fg_color=SOFT
        )
        self.progress_bar.pack(pady=(0, 10), padx=25, fill="x")
        self.progress_bar.set(0)

        # Cuerpo: menú lateral (izquierda) + zona de trabajo (derecha, se expande)
        self.body = ctk.CTkFrame(self, fg_color=BG)
        self.body.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        self.body.grid_columnconfigure(1, weight=1)
        self.body.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            self.body, width=SIDEBAR_W, fg_color=BG, corner_radius=18,
            border_width=1, border_color=BORDER,
        )
        self.sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        self.sidebar.pack_propagate(False)

        self.selector_modo = ctk.CTkSegmentedButton(
            self.sidebar, values=["Imágenes", "Video"], command=self._cambiar_modo,
            fg_color=SOFT, selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
            unselected_color=SOFT, unselected_hover_color=BORDER,
            text_color=TEXT, font=("Arial", 12, "bold"), height=34,
        )
        self.selector_modo.pack(fill="x", padx=12, pady=12)
        self.selector_modo.set("Imágenes")

        self.side_img = ctk.CTkScrollableFrame(self.sidebar, fg_color=BG)
        self.side_vid = ctk.CTkScrollableFrame(self.sidebar, fg_color=BG)

        self.main = ctk.CTkFrame(self.body, fg_color=BG)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main_img = ctk.CTkFrame(self.main, fg_color=BG)
        self.main_vid = ctk.CTkFrame(self.main, fg_color=BG)

        self._setup_image_tab()
        self._setup_video_tab()

        # Botones que se bloquean mientras corre una tarea
        self._botones_accion = [
            self.btn_remove_bg,
            self.btn_resize,
            self.btn_convert_img,
            self.btn_pixel,
            self.btn_sticker,
            self.btn_format_video,
            self.btn_trim_video,
            self.btn_extract_audio,
            self.btn_gif,
            self.btn_compress,
        ]

        self._cambiar_modo("Imágenes")
        self.bind("<F11>", self._alternar_pantalla_completa)
        self.bind("<Control-v>", self.pegar_imagen)
        self.bind("<Control-V>", self.pegar_imagen)
        self.bind("<Escape>", self._salir_pantalla_completa)
        self.bind("<Configure>", self._on_configure, add="+")
        self.after(400, self._ajustar_previews)

        self.after(100, self._revisar_cola)

    # ==========================================
    # WIDGETS REUTILIZABLES
    # ==========================================
    def _cambiar_tema(self):
        ctk.set_appearance_mode("Dark" if ctk.get_appearance_mode() == "Light" else "Light")

    def _abrir_reporte(self):
        v = self._ventana_reporte
        if v is not None:
            try:
                if v.winfo_exists():
                    v.lift()
                    v.focus_force()
                    return
            except Exception:
                pass
        self._ventana_reporte = VentanaReporte(self)

    # ==========================================
    # MENÚ LATERAL, PANTALLA COMPLETA Y AJUSTE
    # ==========================================
    def _alternar_menu(self):
        if self._menu_visible:
            self.sidebar.grid_remove()
        else:
            self.sidebar.grid()
        self._menu_visible = not self._menu_visible
        self._programar_ajuste()

    def _alternar_pantalla_completa(self, _evento=None):
        self._fullscreen = not self._fullscreen
        self.attributes("-fullscreen", self._fullscreen)
        self._programar_ajuste()

    def _salir_pantalla_completa(self, _evento=None):
        if self._fullscreen:
            self._alternar_pantalla_completa()

    def _cambiar_modo(self, modo):
        for w in (self.side_img, self.side_vid, self.main_img, self.main_vid):
            w.pack_forget()
        if modo == "Video":
            self.side_vid.pack(fill="both", expand=True, padx=8, pady=(0, 8))
            self.main_vid.pack(fill="both", expand=True)
        else:
            self.side_img.pack(fill="both", expand=True, padx=8, pady=(0, 8))
            self.main_img.pack(fill="both", expand=True)
        self._programar_ajuste()

    def _on_configure(self, evento):
        if evento.widget is self:
            self._programar_ajuste()

    def _programar_ajuste(self):
        if self._ajuste_job is not None:
            try:
                self.after_cancel(self._ajuste_job)
            except Exception:
                pass
        self._ajuste_job = self.after(250, self._ajustar_previews)

    def _calcular_box(self, frame, columnas):
        """Tamaño máximo de miniatura que cabe en el marco de vista previa."""
        if not frame.winfo_ismapped():
            return None
        try:
            esc = self._get_window_scaling()
        except Exception:
            esc = 1.0
        w = frame.winfo_width() / esc
        h = frame.winfo_height() / esc
        if w < 100 or h < 80:
            return None
        ancho = (w - 40) / columnas - 10
        alto = h - (75 if columnas == 2 else 30)
        return (int(min(max(ancho, 120), PREV_MAX)), int(min(max(alto, 80), PREV_MAX)))

    def _ajustar_previews(self):
        """Reescala las vistas previas al nuevo tamaño de la ventana."""
        global PREV_BOX
        self._ajuste_job = None

        box = self._calcular_box(self.frame_img_preview, 2)
        if box and box != PREV_BOX:
            PREV_BOX = box
            if self.img_input_path:
                try:
                    pil = image_engine.cargar_miniatura(self.img_input_path, PREV_BOX)
                    self.img_preview_obj = ctk.CTkImage(
                        light_image=pil, dark_image=pil, size=pil.size
                    )
                    self.lbl_img_preview.configure(image=self.img_preview_obj, text="")
                except Exception:
                    pass

        box_v = self._calcular_box(self.frame_vid_preview, 1)
        if box_v and box_v != self._box_vid:
            self._box_vid = box_v
            if self._vid_frame_full is not None:
                pil = self._vid_frame_full.copy()
                pil.thumbnail(box_v)
                self.vid_preview_obj = ctk.CTkImage(
                    light_image=pil, dark_image=pil, size=pil.size
                )
                self.lbl_vid_preview.configure(image=self.vid_preview_obj, text="")

    # ==========================================
    # WIDGETS REUTILIZABLES (menú lateral)
    # ==========================================
    def _seccion(self, parent, titulo, ayuda=None, abierta=False, icono=None):
        """Sección desplegable. Devuelve el cuerpo donde se añaden los controles."""
        marco = ctk.CTkFrame(
            parent, fg_color=CARD, corner_radius=16, border_width=1, border_color=BORDER
        )
        marco.pack(pady=6, padx=6, fill="x")
        cuerpo = ctk.CTkFrame(marco, fg_color=CARD, corner_radius=0)
        estado = {"abierta": abierta}

        def refrescar():
            cab.configure(text=titulo + ("   ▾" if estado["abierta"] else "   ▸"))
            if estado["abierta"]:
                cuerpo.pack(fill="x", padx=2, pady=(0, 6))
            else:
                cuerpo.pack_forget()

        def alternar():
            estado["abierta"] = not estado["abierta"]
            refrescar()

        cab = ctk.CTkButton(
            marco, text="", anchor="w", height=36, corner_radius=14,
            fg_color="transparent", hover_color=SOFT, text_color=TEXT,
            font=("Arial", 12, "bold"), command=alternar,
            image=icono_ri(icono, 18) if icono else None, compound="left",
        )
        cab.pack(fill="x", padx=4, pady=4)

        if ayuda:
            ctk.CTkLabel(
                cuerpo, text=ayuda, font=("Arial", 11), text_color=MUTED,
                wraplength=250, justify="left", anchor="w",
            ).pack(anchor="w", padx=15, pady=(0, 4))
        refrescar()
        return cuerpo

    def _entry(self, parent, placeholder):
        return ctk.CTkEntry(
            parent, placeholder_text=placeholder, height=34, corner_radius=17,
            fg_color=CARD, border_color=BORDER, text_color=TEXT,
        )

    def _crear_slider(self, parent, titulo, desde, hasta, inicial):
        fila = ctk.CTkFrame(parent, fg_color="transparent")
        fila.pack(fill="x", padx=10, pady=2)

        lbl = ctk.CTkLabel(fila, text=f"{titulo}: {inicial}", anchor="w", text_color=TEXT)
        lbl.pack(fill="x", padx=5)

        def actualizar(valor):
            lbl.configure(text=f"{titulo}: {int(round(valor))}")

        slider = ctk.CTkSlider(
            fila, from_=desde, to=hasta, number_of_steps=hasta - desde, command=actualizar,
            fg_color=SOFT, progress_color=ACCENT,
            button_color=ACCENT, button_hover_color=ACCENT_HOVER,
        )
        slider.set(inicial)
        slider.pack(fill="x", padx=5, pady=(0, 2))
        return slider

    def _crear_menu(self, parent, titulo, valores, inicial):
        fila = ctk.CTkFrame(parent, fg_color="transparent")
        fila.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(fila, text=titulo, anchor="w", text_color=TEXT).pack(fill="x", padx=5)
        # ComboBox de solo lectura: lista desplegable con borde, como en el kit
        menu = ctk.CTkComboBox(
            fila, values=valores, state="readonly", height=34, corner_radius=17,
            fg_color=CARD, border_color=BORDER, text_color=TEXT,
            button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            dropdown_fg_color=CARD, dropdown_text_color=TEXT, dropdown_hover_color=SOFT,
        )
        menu.set(inicial)
        menu.pack(fill="x", padx=5, pady=(0, 2))
        return menu

    def _crear_boton(self, parent, texto, comando, preview=None):
        """Botón de acción (relleno). Con `preview`, añade encima 'Vista previa'."""
        estilo = dict(
            height=38, corner_radius=19, fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color=("#ffffff", "#ffffff"), text_color_disabled=("#333333", "#8a94a6"),
            font=("Arial", 13, "bold"),
        )
        if preview is not None:
            bp = self._boton_borde(parent, "Vista previa", lambda: self.ejecutar_vista_previa(preview))
            bp.pack(pady=(8, 0), padx=15, fill="x")
            self._botones_prev.append(bp)
        boton = ctk.CTkButton(parent, text=texto, command=comando, **estilo)
        boton.pack(pady=(6, 10), padx=15, fill="x")
        return boton

    def _boton_borde(self, parent, texto, comando, icono=None):
        """Botón con borde (estado 'Normal' del kit) para seleccionar archivos."""
        return ctk.CTkButton(
            parent, text=texto, command=comando, height=38, corner_radius=19,
            fg_color="transparent", border_width=2, border_color=ACCENT,
            text_color=TEXT_ACC, hover_color=SOFT, text_color_disabled=DISABLED,
            font=("Arial", 13, "bold"),
            image=icono_ri(icono, 18) if icono else None, compound="left",
        )

    # ==========================================
    # PESTAÑA 1: IMÁGENES
    # ==========================================
    def _setup_image_tab(self):
        main = self.main_img
        side = self.side_img

        # --- Selección y vista previa ---
        fila_sel = ctk.CTkFrame(main, fg_color=BG)
        fila_sel.pack(fill="x", padx=10, pady=8)
        self.btn_select_img = self._boton_borde(fila_sel, "Seleccionar Imagen", self.seleccionar_imagen)
        self.btn_select_img.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self.btn_pegar = self._boton_borde(
            fila_sel, "Pegar", self.pegar_imagen, icono="ri-clipboard-line"
        )
        self.btn_pegar.configure(width=110)
        self.btn_pegar.pack(side="right")

        self.lbl_img_file = ctk.CTkLabel(
            main, text="Ningún archivo seleccionado", text_color=MUTED
        )
        self.lbl_img_file.pack(pady=2)

        self.frame_img_preview = ctk.CTkFrame(
            main, height=215, fg_color=CARD, corner_radius=16, border_width=2, border_color=BORDER
        )
        self.frame_img_preview.pack(pady=8, padx=10, fill="both", expand=True)
        self.frame_img_preview.pack_propagate(False)

        fila_acc = ctk.CTkFrame(main, fg_color=BG)
        fila_acc.pack(fill="x", padx=10, pady=(0, 6))
        self.btn_comparar = self._boton_borde(
            fila_acc, "Comparar antes / después", self.abrir_comparador
        )
        self.btn_comparar.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self.btn_comparar.configure(state="disabled")
        self.btn_copiar = self._boton_borde(fila_acc, "Copiar resultado", self.copiar_resultado)
        self.btn_copiar.pack(side="right", expand=True, fill="x", padx=(6, 0))

        texto_drop_img = (
            "Arrastra y suelta tu imagen aquí\no haz clic en Seleccionar"
            if HAS_DND else "[ Imagen original ]"
        )
        col_o = ctk.CTkFrame(self.frame_img_preview, fg_color="transparent")
        col_o.pack(side="left", expand=True, fill="both", padx=(8, 4), pady=6)
        lbl_o_titulo = ctk.CTkLabel(
            col_o, text="Original", font=("Arial", 11, "bold"), text_color=MUTED
        )
        lbl_o_titulo.pack(pady=(2, 0))
        self.lbl_img_preview = ctk.CTkLabel(col_o, text=texto_drop_img, text_color=MUTED)
        self.lbl_img_preview.pack(expand=True, fill="both")

        col_r = ctk.CTkFrame(self.frame_img_preview, fg_color="transparent")
        col_r.pack(side="left", expand=True, fill="both", padx=(4, 8), pady=6)
        self.lbl_res_titulo = ctk.CTkLabel(
            col_r, text="Vista previa del resultado", font=("Arial", 11, "bold"), text_color=TEXT_ACC
        )
        self.lbl_res_titulo.pack(pady=(2, 0))
        self.lbl_img_result = ctk.CTkLabel(
            col_r, text=self.TXT_RESULTADO, text_color=MUTED
        )
        self.lbl_img_result.pack(expand=True, fill="both")

        if HAS_DND:
            try:
                for w in (self.frame_img_preview, col_o, col_r, lbl_o_titulo,
                          self.lbl_img_preview, self.lbl_res_titulo, self.lbl_img_result):
                    w.drop_target_register(DND_FILES)
                    w.dnd_bind('<<Drop>>', self._on_drop_image)
            except Exception:
                pass

        # --- Quitar fondo ---
        sec = self._seccion(side, "Quitar fondo (IA)", abierta=True, icono="ri-scissors-line")
        self.model_options = list(image_engine.MODELOS_REMBG.items())
        ctk.CTkLabel(sec, text="Modelo (Rembg):", anchor="w", text_color=TEXT).pack(
            fill="x", padx=15, pady=(2, 0)
        )
        self.model_menu = SelectorModelos(sec, self.model_options, image_engine.MODELO_DEFECTO)
        self.model_menu.pack(fill="x", padx=10, pady=(0, 2))
        self.btn_remove_bg = self._crear_boton(
            sec, "Remover Fondo con IA", self.ejecutar_remover_fondo, preview="fondo"
        )

        # --- Sticker ---
        sec = self._seccion(
            side, "Crear sticker",
            "Quita el fondo, añade un borde blanco y lo deja listo para WhatsApp / Telegram. "
            "Usa el modelo de «Quitar fondo».",
            abierta=True,
        )
        self.slider_borde = self._crear_slider(sec, "Grosor del borde (px)", 0, 24, 10)
        self.sticker_tam_menu = self._crear_menu(
            sec, "Tamaño:", list(STICKER_TAMANOS), "512 px (WhatsApp / Telegram)"
        )
        self.sticker_fmt_menu = self._crear_menu(
            sec, "Formato:", list(STICKER_FORMATOS), "PNG"
        )
        self.btn_sticker = self._crear_boton(
            sec, "Crear Sticker", self.ejecutar_sticker, preview="sticker"
        )

        # --- Redimensionar ---
        sec = self._seccion(
            side, "Redimensionar", "Un campo vacío = mantiene la proporción",
            icono="ri-aspect-ratio-line",
        )
        fila = ctk.CTkFrame(sec, fg_color="transparent")
        fila.pack(fill="x", padx=10, pady=4)

        self.entry_width = self._entry(fila, "Ancho (px)")
        self.entry_width.pack(side="left", padx=5, expand=True, fill="x")

        self.entry_height = self._entry(fila, "Alto (px)")
        self.entry_height.pack(side="right", padx=5, expand=True, fill="x")

        self.btn_resize = self._crear_boton(
            sec, "Solo Redimensionar", self.ejecutar_redimensionado, preview="resize"
        )

        # --- Convertir formato ---
        sec = self._seccion(side, "Convertir formato", icono="ri-loop-left-line")
        self.formato_menu = self._crear_menu(
            sec, "Formato de salida:", list(image_engine.FORMATOS_SALIDA), "PNG"
        )
        self.slider_calidad = self._crear_slider(sec, "Calidad (JPG/WEBP)", 10, 100, 90)
        self.btn_convert_img = self._crear_boton(
            sec, "Convertir Formato", self.ejecutar_convertir_formato, preview="convertir"
        )

        # --- Pixel art ---
        sec = self._seccion(side, "Pixel art", icono="ri-grid-line")
        self.slider_pixel = self._crear_slider(sec, "Tamaño de píxel", 2, 32, 8)
        self.slider_colores = self._crear_slider(sec, "Colores máximos", 2, 64, 16)
        self.btn_pixel = self._crear_boton(
            sec, "Convertir a Pixel Art", self.ejecutar_pixel_art, preview="pixel"
        )

    # ==========================================
    # PESTAÑA 2: VIDEO
    # ==========================================
    def _setup_video_tab(self):
        main = self.main_vid
        side = self.side_vid

        # --- Selección y vista previa ---
        self.btn_select_vid = self._boton_borde(main, "Seleccionar Video", self.seleccionar_video)
        self.btn_select_vid.pack(pady=8, padx=10, fill="x")

        self.lbl_vid_file = ctk.CTkLabel(
            main, text="Ningún archivo seleccionado", text_color=MUTED
        )
        self.lbl_vid_file.pack(pady=2)

        self.frame_vid_preview = ctk.CTkFrame(
            main, height=160, fg_color=CARD, corner_radius=16, border_width=2, border_color=BORDER
        )
        self.frame_vid_preview.pack(pady=8, padx=10, fill="both", expand=True)
        self.frame_vid_preview.pack_propagate(False)

        texto_drop_vid = (
            "Arrastra y suelta tu video aquí\no haz clic en Seleccionar"
            if HAS_DND else "[ Vista Previa Fotograma ]"
        )
        self.lbl_vid_preview = ctk.CTkLabel(
            self.frame_vid_preview, text=texto_drop_vid, text_color=MUTED
        )
        self.lbl_vid_preview.pack(expand=True, fill="both")

        if HAS_DND:
            try:
                self.frame_vid_preview.drop_target_register(DND_FILES)
                self.frame_vid_preview.dnd_bind('<<Drop>>', self._on_drop_video)
            except Exception:
                pass

        # --- Formato de destino (relación de aspecto) ---
        sec = self._seccion(
            side, "Cambiar formato", "Recorte centrado a la relación elegida",
            abierta=True, icono="ri-loop-left-line",
        )
        self.aspect_options = [
            "16:9 (Horizontal / Clásico)",
            "9:16 (Vertical / Shorts)",
            "1:1 (Cuadrado)",
        ]
        self.aspect_menu = self._crear_menu(
            sec, "Formato de destino:", self.aspect_options, "16:9 (Horizontal / Clásico)"
        )
        self.btn_format_video = self._crear_boton(
            sec, "Cambiar Formato / Escalar (MP4)", self.ejecutar_cambio_formato
        )

        # --- Recorte por tiempos (también lo usa el GIF) ---
        sec = self._seccion(
            side, "Recortar segmento", "En segundos. Fin vacío = hasta el final",
            icono="ri-video-line",
        )
        fila = ctk.CTkFrame(sec, fg_color="transparent")
        fila.pack(fill="x", padx=10, pady=4)

        self.entry_start = self._entry(fila, "Inicio (ej: 0)")
        self.entry_start.pack(side="left", padx=5, expand=True, fill="x")

        self.entry_end = self._entry(fila, "Fin (ej: 10)")
        self.entry_end.pack(side="right", padx=5, expand=True, fill="x")

        self.btn_trim_video = self._crear_boton(
            sec, "Recortar Video", self.ejecutar_recorte_video
        )

        # --- Comprimir video ---
        sec = self._seccion(side, "Comprimir video", icono="ri-file-reduce-line")
        self.calidad_menu = self._crear_menu(
            sec, "Calidad:", list(video_engine.CALIDADES_CRF), "Media (recomendada)"
        )
        self.altura_menu = self._crear_menu(
            sec, "Resolución máxima:", list(video_engine.ALTURAS), "Original"
        )
        self.btn_compress = self._crear_boton(
            sec, "Comprimir Video (MP4)", self.ejecutar_comprimir_video
        )

        # --- Video a GIF ---
        sec = self._seccion(
            side, "Video a GIF",
            f"Usa Inicio/Fin del recorte si los llenas; máx. {video_engine.MAX_GIF_SEG} s",
            icono="ri-file-gif-line",
        )
        self.slider_gif_fps = self._crear_slider(sec, "Fotogramas por segundo", 5, 30, 12)
        self.slider_gif_ancho = self._crear_slider(sec, "Ancho (px)", 120, 800, 480)
        self.btn_gif = self._crear_boton(
            sec, "Convertir a GIF", self.ejecutar_video_a_gif
        )

        # --- Audio ---
        sec = self._seccion(side, "Audio", icono="ri-volume-up-line")
        self.btn_extract_audio = self._crear_boton(
            sec, "Extraer Audio (MP3)", self.ejecutar_extraer_audio
        )

    # ==========================================
    # UTILIDADES
    # ==========================================
    @staticmethod
    def _ruta_unica(ruta):
        """Evita sobrescribir archivos existentes agregando _1, _2, ..."""
        base, ext = os.path.splitext(ruta)
        n = 1
        while os.path.exists(ruta):
            ruta = f"{base}_{n}{ext}"
            n += 1
        return ruta

    @staticmethod
    def _leer_numero(entry, tipo=float):
        """Devuelve None si el campo está vacío; lanza ValueError si no es válido."""
        texto = entry.get().strip().replace(",", ".")
        if not texto:
            return None
        return tipo(texto)

    def _leer_tiempos(self):
        """Lee Inicio/Fin. Devuelve (inicio, fin) o None si hay error (ya avisó al usuario)."""
        try:
            inicio = self._leer_numero(self.entry_start) or 0.0
            fin = self._leer_numero(self.entry_end)  # None = hasta el final
        except ValueError:
            messagebox.showerror("Error", "Introduce valores numéricos válidos en segundos.")
            return None
        if inicio < 0 or (fin is not None and fin <= inicio):
            messagebox.showerror("Error", "El fin debe ser mayor que el inicio, y ninguno puede ser negativo.")
            return None
        return inicio, fin

    # ==========================================
    # TAREAS EN SEGUNDO PLANO
    # ==========================================
    def _iniciar_tarea(self, estado, funcion, ruta_salida, texto_ok):
        """Ejecuta `funcion` (devuelve (ok, msg)) en un hilo para no congelar la ventana."""
        if self._ocupado:
            return
        self._ocupado = True
        for b in self._botones_accion + self._botones_prev:
            b.configure(state="disabled")

        self.lbl_status.configure(text=estado, text_color=WARN)
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()

        def trabajo():
            try:
                ok, msg = funcion()
            except Exception as e:
                ok, msg = False, str(e)
            self._cola.put((ok, msg, ruta_salida, texto_ok))

        threading.Thread(target=trabajo, daemon=True).start()

    def _revisar_cola(self):
        self.after(100, self._revisar_cola)
        try:
            self._mostrar_preview(*self._cola_prev.get_nowait())
        except queue.Empty:
            pass
        try:
            ok, msg, ruta, texto_ok = self._cola.get_nowait()
        except queue.Empty:
            return
        self._terminar_tarea(ok, msg, ruta, texto_ok)

    def _terminar_tarea(self, ok, msg, ruta, texto_ok):
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self._ocupado = False
        for b in self._botones_accion + self._botones_prev:
            b.configure(state="normal")

        if ok:
            if ruta and str(ruta).lower().endswith(EXT_IMAGEN):
                self._ultimo_resultado = ruta
            self.progress_bar.set(1.0)
            self.lbl_status.configure(text="¡Proceso completado!", text_color=OK)
            messagebox.showinfo("Éxito", f"{texto_ok}\n{ruta}\n\n{msg}")
        else:
            self.progress_bar.set(0)
            self.lbl_status.configure(text="Ocurrió un error", text_color=ERR)
            messagebox.showerror("Error", msg)

    # ==========================================
    # LÓGICA Y EVENTOS DRAG AND DROP
    # ==========================================
    def _limpiar_ruta_drop(self, event_data):
        # splitlist entiende rutas con espacios entre llaves y varios archivos soltados
        partes = self.tk.splitlist(event_data)
        return partes[0] if partes else ""

    def _on_drop_image(self, event):
        path = self._limpiar_ruta_drop(event.data)
        if os.path.isfile(path) and path.lower().endswith(EXT_IMAGEN):
            self._cargar_imagen_desde_ruta(path)
        else:
            messagebox.showerror("Archivo no válido", "Por favor arrastra un archivo de imagen válido.")

    def _on_drop_video(self, event):
        path = self._limpiar_ruta_drop(event.data)
        if os.path.isfile(path) and path.lower().endswith(EXT_VIDEO):
            self._cargar_video_desde_ruta(path)
        else:
            messagebox.showerror("Archivo no válido", "Por favor arrastra un archivo de video válido.")

    # ==========================================
    # SELECCIÓN Y VISTA PREVIA
    # ==========================================
    def seleccionar_imagen(self):
        path = filedialog.askopenfilename(
            title="Seleccionar Imagen",
            filetypes=[("Imágenes", _patrones(EXT_IMAGEN))],
        )
        if path:
            self._cargar_imagen_desde_ruta(path)

    def _cargar_imagen_desde_ruta(self, path):
        self.img_input_path = path
        self._reiniciar_preview()
        self.lbl_img_file.configure(text=os.path.basename(path), text_color=TEXT)

        try:
            pil_img = image_engine.cargar_miniatura(path, PREV_BOX)
            self.img_preview_obj = ctk.CTkImage(
                light_image=pil_img, dark_image=pil_img, size=pil_img.size
            )
            self.lbl_img_preview.configure(image=self.img_preview_obj, text="")
        except Exception as e:
            self.lbl_img_preview.configure(image=None, text=f"Error en vista previa:\n{e}")

    def seleccionar_video(self):
        path = filedialog.askopenfilename(
            title="Seleccionar Video",
            filetypes=[("Archivos de Video", _patrones(EXT_VIDEO))],
        )
        if path:
            self._cargar_video_desde_ruta(path)

    def _cargar_video_desde_ruta(self, path):
        self.video_input_path = path
        self.lbl_vid_file.configure(text=os.path.basename(path), text_color=TEXT)
        self.lbl_vid_preview.configure(image=None, text="Cargando fotograma...")
        self.update_idletasks()

        try:
            frame_array = video_engine.obtener_fotograma(path)
            pil_frame = Image.fromarray(frame_array)
            self._vid_frame_full = pil_frame.copy()
            pil_frame.thumbnail(self._box_vid)

            self.vid_preview_obj = ctk.CTkImage(
                light_image=pil_frame, dark_image=pil_frame, size=pil_frame.size
            )
            self.lbl_vid_preview.configure(image=self.vid_preview_obj, text="")
        except Exception as e:
            self.lbl_vid_preview.configure(image=None, text=f"No se pudo cargar fotograma:\n{e}")

    # ==========================================
    # ACCIONES: IMÁGENES
    # ==========================================
    def _requiere_imagen(self):
        if not self.img_input_path:
            messagebox.showerror("Error", "Selecciona o arrastra una imagen primero.")
            return False
        return True

    def _requiere_video(self):
        if not self.video_input_path:
            messagebox.showerror("Error", "Selecciona o arrastra un video primero.")
            return False
        return True

    def ejecutar_remover_fondo(self):
        if not self._requiere_imagen():
            return

        entrada = self.img_input_path
        modelo = self.model_menu.get().split(" ")[0]
        base, _ = os.path.splitext(entrada)
        salida = self._ruta_unica(f"{base}_sin_fondo.png")

        self._iniciar_tarea(
            f"Procesando con '{modelo}' (la primera vez descarga el modelo)...",
            lambda: image_engine.remover_fondo_imagen(entrada, salida, modelo),
            salida,
            "Imagen guardada en:",
        )

    def ejecutar_redimensionado(self):
        if not self._requiere_imagen():
            return

        try:
            w = self._leer_numero(self.entry_width, int)
            h = self._leer_numero(self.entry_height, int)
        except ValueError:
            messagebox.showerror("Error", "El ancho y el alto deben ser números enteros.")
            return
        if w is None and h is None:
            messagebox.showerror("Error", "Escribe al menos el ancho o el alto.")
            return
        if (w is not None and w <= 0) or (h is not None and h <= 0):
            messagebox.showerror("Error", "El ancho y el alto deben ser mayores que 0.")
            return

        entrada = self.img_input_path
        base, ext = os.path.splitext(entrada)
        salida = self._ruta_unica(f"{base}_{w or 'auto'}x{h or 'auto'}{ext}")

        self._iniciar_tarea(
            "Redimensionando imagen...",
            lambda: image_engine.redimensionar_imagen(entrada, salida, w, h),
            salida,
            "Imagen guardada en:",
        )

    def ejecutar_convertir_formato(self):
        if not self._requiere_imagen():
            return

        entrada = self.img_input_path
        formato = self.formato_menu.get()
        ext = image_engine.FORMATOS_SALIDA[formato]
        calidad = int(round(self.slider_calidad.get()))
        base, _ = os.path.splitext(entrada)
        salida = self._ruta_unica(f"{base}_convertido{ext}")

        self._iniciar_tarea(
            f"Convirtiendo a {formato}...",
            lambda: image_engine.convertir_formato_imagen(entrada, salida, calidad),
            salida,
            "Imagen guardada en:",
        )

    def ejecutar_pixel_art(self):
        if not self._requiere_imagen():
            return

        entrada = self.img_input_path
        tam = int(round(self.slider_pixel.get()))
        colores = int(round(self.slider_colores.get()))
        base, _ = os.path.splitext(entrada)
        salida = self._ruta_unica(f"{base}_pixelart.png")

        self._iniciar_tarea(
            f"Creando pixel art (bloques de {tam}px, {colores} colores)...",
            lambda: image_engine.pixelar_imagen(entrada, salida, tam, colores),
            salida,
            "Imagen guardada en:",
        )

    # ==========================================
    # VISTA PREVIA DEL RESULTADO (imágenes)
    # ==========================================
    def _reiniciar_preview(self):
        """Descarta cualquier vista previa en curso o mostrada (cambió la imagen)."""
        self._prev_token += 1
        self._prev_ocupado = False
        self.img_result_obj = None
        self._res_pil_full = None
        self._ultimo_resultado = ""
        self.btn_comparar.configure(state="disabled")
        self.lbl_img_result.configure(image=None, text=self.TXT_RESULTADO)
        self.lbl_res_titulo.configure(text="Vista previa del resultado")
        if not self._ocupado:
            for b in self._botones_prev:
                b.configure(state="normal")

    def ejecutar_vista_previa(self, tipo):
        if self._ocupado or self._prev_ocupado or not self._requiere_imagen():
            return

        entrada = self.img_input_path
        min_esc = 0.0
        estado = "Generando vista previa..."

        if tipo == "fondo":
            modelo = self.model_menu.get().split(" ")[0]
            ext = ".png"
            caption = f"sin fondo ({modelo})"
            estado = f"Vista previa con '{modelo}' (la primera vez descarga el modelo)..."

            def proceso(i, o, e):
                return image_engine.remover_fondo_imagen(i, o, modelo)

        elif tipo == "resize":
            try:
                w = self._leer_numero(self.entry_width, int)
                h = self._leer_numero(self.entry_height, int)
            except ValueError:
                messagebox.showerror("Error", "El ancho y el alto deben ser números enteros.")
                return
            if w is None and h is None:
                messagebox.showerror("Error", "Escribe al menos el ancho o el alto.")
                return
            if (w is not None and w <= 0) or (h is not None and h <= 0):
                messagebox.showerror("Error", "El ancho y el alto deben ser mayores que 0.")
                return
            try:
                with Image.open(entrada) as im:
                    ow, oh = im.size
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo leer la imagen: {e}")
                return
            if w and h:
                fw, fh = w, h
            elif w:
                fw, fh = w, max(1, round(oh * w / ow))
            else:
                fw, fh = max(1, round(ow * h / oh)), h
            ext = ".png"
            caption = f"{fw} × {fh} px"

            def proceso(i, o, e):
                pw = max(1, round(w * e)) if w else None
                ph = max(1, round(h * e)) if h else None
                return image_engine.redimensionar_imagen(i, o, pw, ph)

        elif tipo == "convertir":
            formato = self.formato_menu.get()
            ext = image_engine.FORMATOS_SALIDA[formato]
            calidad = int(round(self.slider_calidad.get()))
            caption = f"{formato}, calidad {calidad}"

            def proceso(i, o, e):
                return image_engine.convertir_formato_imagen(i, o, calidad)

        elif tipo == "pixel":
            tam = int(round(self.slider_pixel.get()))
            colores = int(round(self.slider_colores.get()))
            ext = ".png"
            caption = f"bloques de {tam}px, {colores} colores"
            min_esc = min(1.0, 4 / tam)  # que el bloque reducido no se redondee a 1 px

            def proceso(i, o, e):
                return image_engine.pixelar_imagen(i, o, max(1, round(tam * e)), colores)

        elif tipo == "sticker":
            modelo = self.model_menu.get().split(" ")[0]
            grosor = int(round(self.slider_borde.get()))
            tam = STICKER_TAMANOS[self.sticker_tam_menu.get()]
            ext = ".png"
            caption = f"sticker {tam} px"
            estado = f"Vista previa del sticker con '{modelo}' (la primera vez descarga el modelo)..."

            def proceso(i, o, e):
                return self._hacer_sticker(i, o, modelo, grosor, tam)

        else:
            return

        self._prev_ocupado = True
        self._prev_token += 1
        token = self._prev_token
        for b in self._botones_prev:
            b.configure(state="disabled")
        self.lbl_status.configure(text=estado, text_color=WARN)

        threading.Thread(
            target=self._hilo_vista_previa,
            args=(token, entrada, proceso, ext, min_esc, caption),
            daemon=True,
        ).start()

    def _hilo_vista_previa(self, token, entrada, proceso, ext, min_esc, caption):
        """Aplica el proceso a una copia reducida (rápido) y devuelve la miniatura."""
        tmp = tempfile.mkdtemp(prefix="pixelmatte_")
        try:
            with Image.open(entrada) as im:
                im.load()
                base = im.convert("RGBA")
            esc = min(1.0, max(PREV_MAX / max(base.size), min_esc))
            if esc < 1.0:
                base = base.resize(
                    (max(1, round(base.width * esc)), max(1, round(base.height * esc))),
                    Image.LANCZOS,
                )
            ent = os.path.join(tmp, "entrada.png")
            sal = os.path.join(tmp, "salida" + ext)
            base.save(ent)

            ok, msg = proceso(ent, sal, esc)
            pil = None
            grande = None
            if ok:
                with Image.open(sal) as r:
                    r.load()
                    pil = r.convert("RGBA")
                grande = pil.copy()
                grande.thumbnail((PREV_MAX, PREV_MAX))
                pil.thumbnail(PREV_BOX)
            self._cola_prev.put((token, ok, msg, pil, caption, grande))
        except Exception as e:
            self._cola_prev.put((token, False, str(e), None, caption))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _mostrar_preview(self, token, ok, msg, pil, caption, grande=None):
        if token != self._prev_token:
            return  # vista previa obsoleta (cambió la imagen u otra solicitud)
        self._prev_ocupado = False
        if not self._ocupado:
            for b in self._botones_prev:
                b.configure(state="normal")
            self.lbl_status.configure(text="Listo para procesar", text_color=TEXT_ACC)

        if ok and pil is not None:
            self.img_result_obj = ctk.CTkImage(light_image=pil, dark_image=pil, size=pil.size)
            self.lbl_img_result.configure(image=self.img_result_obj, text="")
            self.lbl_res_titulo.configure(text=f"Resultado: {caption}")
            self._res_pil_full = grande if grande is not None else pil
            self._res_caption = caption
            self.btn_comparar.configure(state="normal")
        else:
            self.lbl_img_result.configure(image=None, text=f"No se pudo generar la vista previa:\n{msg}")

    # ==========================================
    # STICKERS
    # ==========================================
    def ejecutar_sticker(self):
        if not self._requiere_imagen():
            return
        entrada = self.img_input_path
        modelo = self.model_menu.get().split(" ")[0]
        grosor = int(round(self.slider_borde.get()))
        tam = STICKER_TAMANOS[self.sticker_tam_menu.get()]
        ext = STICKER_FORMATOS[self.sticker_fmt_menu.get()]
        base, _ = os.path.splitext(entrada)
        salida = self._ruta_unica(f"{base}_sticker{ext}")

        self._iniciar_tarea(
            f"Creando sticker con '{modelo}' (la primera vez descarga el modelo)...",
            lambda: self._hacer_sticker(entrada, salida, modelo, grosor, tam),
            salida,
            "Sticker guardado en:",
        )

    def _hacer_sticker(self, entrada, salida, modelo, grosor, tam):
        """Quita el fondo y compone el sticker. Se ejecuta en un hilo (sin tocar widgets)."""
        tmp = tempfile.mkdtemp(prefix="pixelmatte_stk_")
        try:
            sin_fondo = os.path.join(tmp, "sin_fondo.png")
            ok, msg = image_engine.remover_fondo_imagen(entrada, sin_fondo, modelo)
            if not ok:
                return False, msg
            with Image.open(sin_fondo) as im:
                im.load()
                rgba = im.convert("RGBA")
            return self._componer_sticker(rgba, salida, grosor, tam)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @staticmethod
    def _componer_sticker(rgba, salida, grosor, tam):
        """Recorta al objeto, lo centra en un lienzo cuadrado y le dibuja el borde blanco."""
        alfa = rgba.split()[3]
        caja = alfa.point(lambda v: 255 if v > 8 else 0).getbbox()
        if caja is None:
            return False, "No se detectó ningún objeto: al quitar el fondo la imagen quedó vacía."
        rgba = rgba.crop(caja)

        margen = grosor + 6
        interior = max(16, tam - 2 * margen)
        esc = min(interior / rgba.width, interior / rgba.height)
        nw, nh = max(1, round(rgba.width * esc)), max(1, round(rgba.height * esc))
        rgba = rgba.resize((nw, nh), Image.LANCZOS)

        lienzo = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
        lienzo.alpha_composite(rgba, ((tam - nw) // 2, (tam - nh) // 2))

        if grosor > 0:
            mascara = lienzo.split()[3].point(lambda v: 255 if v > 8 else 0)
            # Desenfocar y umbralizar expande la silueta ~1.86*sigma con esquinas redondeadas
            sigma = max(0.6, grosor / 1.86)
            ancha = mascara.filter(ImageFilter.GaussianBlur(sigma)).point(
                lambda v: 255 if v > 8 else 0
            )
            ancha = ancha.filter(ImageFilter.GaussianBlur(0.8))
            borde = Image.new("RGBA", (tam, tam), (255, 255, 255, 0))
            borde.paste((255, 255, 255, 255), mask=ancha)
            borde.alpha_composite(lienzo)
            lienzo = borde

        if os.path.splitext(salida)[1].lower() == ".webp":
            tamano = 0
            for calidad in (92, 85, 75, 65, 50, 35):
                lienzo.save(salida, "WEBP", quality=calidad, method=6)
                tamano = os.path.getsize(salida)
                if tamano <= 100 * 1024:
                    break
            aviso = ""
            if tamano > 100 * 1024:
                aviso = "\nSupera 100 KB: WhatsApp podría rechazarlo; prueba con un tamaño menor."
            return True, f"Sticker {tam}×{tam} px, WebP, {tamano / 1024:.0f} KB.{aviso}"

        lienzo.save(salida, "PNG", optimize=True)
        return True, f"Sticker {tam}×{tam} px, PNG, {os.path.getsize(salida) / 1024:.0f} KB."

    # ==========================================
    # COMPARADOR ANTES / DESPUÉS
    # ==========================================
    def abrir_comparador(self):
        if self._res_pil_full is None or not self.img_input_path:
            messagebox.showinfo(
                "Comparar",
                "Primero genera una vista previa con el botón «Vista previa» de alguna herramienta.",
            )
            return
        try:
            with Image.open(self.img_input_path) as im:
                im.load()
                antes = im.convert("RGBA")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer la imagen original: {e}")
            return
        antes.thumbnail((PREV_MAX, PREV_MAX))

        v = self._ventana_comparar
        if v is not None:
            try:
                if v.winfo_exists():
                    v.destroy()
            except Exception:
                pass
        self._ventana_comparar = VentanaComparar(self, antes, self._res_pil_full, self._res_caption)
        self._ventana_comparar.after(150, self._ventana_comparar.lift)

    # ==========================================
    # PORTAPAPELES (pegar y copiar imágenes)
    # ==========================================
    def _aviso_temporal(self, texto, color):
        self.lbl_status.configure(text=texto, text_color=color)

        def restaurar():
            if not self._ocupado and not self._prev_ocupado:
                self.lbl_status.configure(text="Listo para procesar", text_color=TEXT_ACC)

        self.after(3500, restaurar)

    @staticmethod
    def _carpeta_pegadas():
        base = ""
        try:
            r = subprocess.run(
                ["xdg-user-dir", "PICTURES"], capture_output=True, text=True, timeout=3
            )
            base = r.stdout.strip()
        except Exception:
            pass
        if not base or not os.path.isdir(base):
            base = os.path.join(os.path.expanduser("~"), "Pictures")
        carpeta = os.path.join(base, "PixelMatte")
        os.makedirs(carpeta, exist_ok=True)
        return carpeta

    def _leer_portapapeles(self):
        """Devuelve una imagen PIL, una ruta de archivo de imagen o None."""
        try:
            from PIL import ImageGrab
            datos = ImageGrab.grabclipboard()
        except Exception:
            datos = None  # sin xclip / wl-paste o portapapeles vacío
        if isinstance(datos, Image.Image):
            return datos
        if isinstance(datos, (list, tuple)):
            for d in datos:
                if os.path.isfile(d) and str(d).lower().endswith(EXT_IMAGEN):
                    return d

        try:
            txt = self.clipboard_get().strip()
        except Exception:
            txt = ""
        if txt.startswith("file://"):
            txt = unquote(urlparse(txt).path)
        txt = txt.strip("\"'")
        if txt and os.path.isfile(txt) and txt.lower().endswith(EXT_IMAGEN):
            return txt
        return None

    def pegar_imagen(self, evento=None):
        if evento is not None:
            # Ctrl+V dentro de un campo de texto debe pegar texto, no imagen
            try:
                w = self.focus_get()
                if w is not None and w.winfo_class() in ("Entry", "Text", "TEntry", "TCombobox"):
                    return
            except Exception:
                pass
            if self.selector_modo.get() != "Imágenes":
                return
        if self._ocupado:
            return

        dato = self._leer_portapapeles()
        if dato is None:
            if evento is None:
                messagebox.showinfo(
                    "Pegar imagen",
                    "No hay ninguna imagen en el portapapeles.\n"
                    "Copia una imagen o una captura y vuelve a intentarlo.\n\n"
                    "En Linux hace falta xclip (o wl-clipboard en Wayland):\n"
                    "sudo apt install xclip",
                )
            else:
                self._aviso_temporal("No hay imagen en el portapapeles", WARN)
            return

        if isinstance(dato, Image.Image):
            try:
                img = dato if dato.mode in ("RGB", "RGBA", "L", "LA") else dato.convert("RGBA")
                ruta = os.path.join(
                    self._carpeta_pegadas(), time.strftime("pegada_%Y%m%d_%H%M%S.png")
                )
                img.save(ruta)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar la imagen pegada: {e}")
                return
            self._cargar_imagen_desde_ruta(ruta)
            self._aviso_temporal("Imagen pegada (los resultados se guardan junto a ella)", OK)
        else:
            self._cargar_imagen_desde_ruta(dato)
            self._aviso_temporal("Imagen cargada desde el portapapeles", OK)

    @staticmethod
    def _copiar_imagen_portapapeles(pil):
        buf = io.BytesIO()
        pil.save(buf, "PNG")
        datos = buf.getvalue()
        try:
            if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wl-copy"):
                subprocess.run(["wl-copy", "--type", "image/png"], input=datos, check=True, timeout=15)
                return True, ""
            if shutil.which("xclip"):
                subprocess.run(
                    ["xclip", "-selection", "clipboard", "-t", "image/png", "-i"],
                    input=datos, check=True, timeout=15,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                return True, ""
        except Exception as e:
            return False, str(e)
        return False, "Falta xclip para copiar imágenes.\nInstálalo con: sudo apt install xclip"

    def copiar_resultado(self):
        img = None
        origen = ""
        if self._ultimo_resultado and os.path.isfile(self._ultimo_resultado):
            try:
                with Image.open(self._ultimo_resultado) as im:
                    im.load()
                    img = im.convert("RGBA")
                origen = "resultado guardado"
            except Exception:
                img = None
        if img is None and self._res_pil_full is not None:
            img = self._res_pil_full
            origen = "vista previa"
        if img is None:
            messagebox.showinfo(
                "Copiar resultado",
                "Todavía no hay resultado. Genera una vista previa o procesa la imagen primero.",
            )
            return

        ok, msg = self._copiar_imagen_portapapeles(img)
        if ok:
            self._aviso_temporal(f"Copiado al portapapeles ({origen})", OK)
        else:
            messagebox.showerror("No se pudo copiar", msg)

    # ==========================================
    # ACCIONES: VIDEO
    # ==========================================
    def ejecutar_cambio_formato(self):
        if not self._requiere_video():
            return

        entrada = self.video_input_path
        formato = self.aspect_menu.get()
        if "9:16" in formato:
            tag = "vertical"
        elif "1:1" in formato:
            tag = "cuadrado"
        else:
            tag = "horizontal"

        base, _ = os.path.splitext(entrada)
        salida = self._ruta_unica(f"{base}_{tag}.mp4")

        self._iniciar_tarea(
            f"Cambiando formato a {formato} (MP4)...",
            lambda: video_engine.cambiar_formato_video(entrada, salida, formato),
            salida,
            "Video guardado en:",
        )

    def ejecutar_recorte_video(self):
        if not self._requiere_video():
            return
        tiempos = self._leer_tiempos()
        if tiempos is None:
            return
        inicio, fin = tiempos

        entrada = self.video_input_path
        base, _ = os.path.splitext(entrada)
        salida = self._ruta_unica(f"{base}_recortado.mp4")

        self._iniciar_tarea(
            f"Recortando video de {inicio}s a {fin if fin is not None else 'el final'}...",
            lambda: video_engine.recortar_video(entrada, salida, inicio, fin),
            salida,
            "Video guardado en:",
        )

    def ejecutar_comprimir_video(self):
        if not self._requiere_video():
            return

        entrada = self.video_input_path
        crf = video_engine.CALIDADES_CRF[self.calidad_menu.get()]
        altura = video_engine.ALTURAS[self.altura_menu.get()]
        base, _ = os.path.splitext(entrada)
        salida = self._ruta_unica(f"{base}_comprimido.mp4")

        self._iniciar_tarea(
            "Comprimiendo video (puede tardar)...",
            lambda: video_engine.comprimir_video(entrada, salida, crf, altura),
            salida,
            "Video guardado en:",
        )

    def ejecutar_video_a_gif(self):
        if not self._requiere_video():
            return
        tiempos = self._leer_tiempos()
        if tiempos is None:
            return
        inicio, fin = tiempos

        entrada = self.video_input_path
        fps = int(round(self.slider_gif_fps.get()))
        ancho = int(round(self.slider_gif_ancho.get()))
        base, _ = os.path.splitext(entrada)
        salida = self._ruta_unica(f"{base}.gif")

        self._iniciar_tarea(
            f"Creando GIF ({fps} fps, {ancho}px de ancho)...",
            lambda: video_engine.video_a_gif(entrada, salida, inicio, fin, fps, ancho),
            salida,
            "GIF guardado en:",
        )

    def ejecutar_extraer_audio(self):
        if not self._requiere_video():
            return

        entrada = self.video_input_path
        base, _ = os.path.splitext(entrada)
        salida = self._ruta_unica(f"{base}_audio.mp3")

        self._iniciar_tarea(
            "Extrayendo audio a MP3...",
            lambda: video_engine.extraer_audio(entrada, salida),
            salida,
            "Audio guardado en:",
        )


if __name__ == "__main__":
    app = PixelMatteApp()
    app.mainloop()
