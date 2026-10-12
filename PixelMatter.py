import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image

# Intento seguro de carga para tkinterdnd2 en Linux
HAS_DND = False
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except Exception:
    HAS_DND = False

# Configuración de apariencia
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# Clase base robusta que evita bloqueos si DnD falla en Linux
if HAS_DND:
    class CTkBase(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            try:
                self.TkdndVersion = TkinterDnD._require(self)
            except Exception:
                global HAS_DND
                HAS_DND = False
else:
    class CTkBase(ctk.CTk):
        pass


class PixelMatteApp(CTkBase):
    def __init__(self):
        super().__init__()

        # Ventana principal
        self.title("PixelMatte - Multimedia Suite")
        self.geometry("750x850")
        self.minsize(650, 750) # Evitamos que se reduzca demasiado y rompa el diseño

        # Variables para archivos e imágenes
        self.img_input_path = ""
        self.video_input_path = ""
        self.img_preview_obj = None
        self.vid_preview_obj = None

        # Título Header
        self.label_header = ctk.CTkLabel(
            self, text="PixelMatte", font=("Arial", 22, "bold")
        )
        self.label_header.pack(pady=(15, 2), anchor="center")

        # Barra de Estado Global
        self.lbl_status = ctk.CTkLabel(
            self, text="Listo para procesar", text_color="#3b82f6", font=("Arial", 11, "bold")
        )
        self.lbl_status.pack(pady=(0, 2), anchor="center")

        # Barra de Progreso Visual
        self.progress_bar = ctk.CTkProgressBar(self, height=12)
        self.progress_bar.pack(pady=(0, 10), padx=25, fill="x")
        self.progress_bar.set(0)

        # Contenedor de Pestañas (Expandible de forma fluida)
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)

        self.tab_image = self.tabview.add("Imágenes")
        self.tab_video = self.tabview.add("Video")

        # Construcción de pestañas
        self._setup_image_tab()
        self._setup_video_tab()

    # ==========================================
    # PESTAÑA 1: IMÁGENES
    # ==========================================
    def _setup_image_tab(self):
        self.frame_model = ctk.CTkFrame(self.tab_image)
        self.frame_model.pack(pady=8, padx=10, fill="x")

        self.lbl_model = ctk.CTkLabel(
            self.frame_model, text="Modelo IA (Rembg):", font=("Arial", 12, "bold")
        )
        self.lbl_model.pack(side="left", padx=15, pady=10)

        self.model_options = [
            "u2netp (Ultra-Ligero)",
            "silueta (Balanceado)",
            "u2net (Pro / HD)",
        ]
        self.model_menu = ctk.CTkOptionMenu(
            self.frame_model, values=self.model_options
        )
        self.model_menu.set("u2netp (Ultra-Ligero)")
        self.model_menu.pack(side="right", padx=15, pady=10)

        self.btn_select_img = ctk.CTkButton(
            self.tab_image, text="Seleccionar Imagen", command=self.seleccionar_imagen
        )
        self.btn_select_img.pack(pady=8, padx=10, fill="x")

        self.lbl_img_file = ctk.CTkLabel(
            self.tab_image, text="Ningún archivo seleccionado", text_color="gray"
        )
        self.lbl_img_file.pack(pady=2)

        self.frame_img_preview = ctk.CTkFrame(self.tab_image, height=140)
        self.frame_img_preview.pack(pady=8, padx=10, fill="x")
        self.frame_img_preview.pack_propagate(False)

        texto_drop_img = "Arrastra y suelta tu imagen aquí\no haz clic en Seleccionar" if HAS_DND else "[ Vista Previa Imagen ]"
        self.lbl_img_preview = ctk.CTkLabel(
            self.frame_img_preview, text=texto_drop_img, text_color="gray"
        )
        self.lbl_img_preview.pack(expand=True, fill="both")

        if HAS_DND:
            try:
                self.frame_img_preview.drop_target_register(DND_FILES)
                self.frame_img_preview.dnd_bind('<<Drop>>', self._on_drop_image)
            except Exception:
                pass

        self.frame_resize = ctk.CTkFrame(self.tab_image)
        self.frame_resize.pack(pady=8, padx=10, fill="x")

        self.lbl_resize_title = ctk.CTkLabel(
            self.frame_resize, text="Redimensionar (Opcional):", font=("Arial", 12, "bold")
        )
        self.lbl_resize_title.pack(anchor="w", padx=15, pady=(8, 0))

        self.frame_entries = ctk.CTkFrame(self.frame_resize, fg_color="transparent")
        self.frame_entries.pack(fill="x", padx=10, pady=8)

        self.entry_width = ctk.CTkEntry(self.frame_entries, placeholder_text="Ancho (px)")
        self.entry_width.pack(side="left", padx=5, expand=True, fill="x")

        self.entry_height = ctk.CTkEntry(self.frame_entries, placeholder_text="Alto (px)")
        self.entry_height.pack(side="right", padx=5, expand=True, fill="x")

        self.btn_remove_bg = ctk.CTkButton(
            self.tab_image,
            text="Remover Fondo con IA",
            fg_color="#2b825c",
            hover_color="#1e5c41",
            command=self.ejecutar_remover_fondo,
        )
        self.btn_remove_bg.pack(pady=6, padx=10, fill="x")

        self.btn_resize = ctk.CTkButton(
            self.tab_image,
            text="Solo Redimensionar",
            fg_color="#3b6998",
            hover_color="#274665",
            command=self.ejecutar_redimensionado,
        )
        self.btn_resize.pack(pady=6, padx=10, fill="x")

    # ==========================================
    # PESTAÑA 2: VIDEO
    # ==========================================
    def _setup_video_tab(self):
        self.btn_select_vid = ctk.CTkButton(
            self.tab_video, text="Seleccionar Video", command=self.seleccionar_video
        )
        self.btn_select_vid.pack(pady=8, padx=10, fill="x")

        self.lbl_vid_file = ctk.CTkLabel(
            self.tab_video, text="Ningún archivo seleccionado", text_color="gray"
        )
        self.lbl_vid_file.pack(pady=2)

        self.frame_vid_preview = ctk.CTkFrame(self.tab_video, height=120)
        self.frame_vid_preview.pack(pady=8, padx=10, fill="x")
        self.frame_vid_preview.pack_propagate(False)

        texto_drop_vid = "Arrastra y suelta tu video aquí\no haz clic en Seleccionar" if HAS_DND else "[ Vista Previa Fotograma ]"
        self.lbl_vid_preview = ctk.CTkLabel(
            self.frame_vid_preview, text=texto_drop_vid, text_color="gray"
        )
        self.lbl_vid_preview.pack(expand=True, fill="both")

        if HAS_DND:
            try:
                self.frame_vid_preview.drop_target_register(DND_FILES)
                self.frame_vid_preview.dnd_bind('<<Drop>>', self._on_drop_video)
            except Exception:
                pass

        # Selector de Formato de Video (Aspect Ratio)
        self.frame_aspect = ctk.CTkFrame(self.tab_video)
        self.frame_aspect.pack(pady=6, padx=10, fill="x")

        self.lbl_aspect = ctk.CTkLabel(
            self.frame_aspect, text="Formato de Destino:", font=("Arial", 12, "bold")
        )
        self.lbl_aspect.pack(side="left", padx=15, pady=8)

        self.aspect_options = [
            "16:9 (Horizontal / Clásico)",
            "9:16 (Vertical / Shorts)",
            "1:1 (Cuadrado)"
        ]
        self.aspect_menu = ctk.CTkOptionMenu(
            self.frame_aspect, values=self.aspect_options
        )
        self.aspect_menu.set("16:9 (Horizontal / Clásico)")
        self.aspect_menu.pack(side="right", padx=15, pady=8)

        # Controles de Recorte por Tiempos
        self.frame_trim = ctk.CTkFrame(self.tab_video)
        self.frame_trim.pack(pady=6, padx=10, fill="x")

        self.lbl_trim_title = ctk.CTkLabel(
            self.frame_trim, text="Recortar Segmento (Segundos):", font=("Arial", 12, "bold")
        )
        self.lbl_trim_title.pack(anchor="w", padx=15, pady=(6, 0))

        self.frame_trim_entries = ctk.CTkFrame(self.frame_trim, fg_color="transparent")
        self.frame_trim_entries.pack(fill="x", padx=10, pady=6)

        self.entry_start = ctk.CTkEntry(self.frame_trim_entries, placeholder_text="Inicio (ej: 0)")
        self.entry_start.pack(side="left", padx=5, expand=True, fill="x")

        self.entry_end = ctk.CTkEntry(self.frame_trim_entries, placeholder_text="Fin (ej: 10)")
        self.entry_end.pack(side="right", padx=5, expand=True, fill="x")

        # Botones de Acción de Video
        self.btn_format_video = ctk.CTkButton(
            self.tab_video,
            text="Cambiar Formato / Escalar (MP4)",
            fg_color="#5a388c",
            hover_color="#422566",
            command=self.ejecutar_cambio_formato,
        )
        self.btn_format_video.pack(pady=5, padx=10, fill="x")

        self.btn_trim_video = ctk.CTkButton(
            self.tab_video,
            text="Recortar Video",
            fg_color="#2b6982",
            hover_color="#1e495c",
            command=self.ejecutar_recorte_video,
        )
        self.btn_trim_video.pack(pady=5, padx=10, fill="x")

        self.btn_extract_audio = ctk.CTkButton(
            self.tab_video,
            text="Extraer Audio (MP3)",
            fg_color="#8c3838",
            hover_color="#632626",
            command=self.ejecutar_extraer_audio,
        )
        self.btn_extract_audio.pack(pady=5, padx=10, fill="x")

    # ==========================================
    # LÓGICA Y EVENTOS DRAG AND DROP
    # ==========================================
    def _limpiar_ruta_drop(self, event_data):
        path = event_data.strip()
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]
        return path

    def _on_drop_image(self, event):
        path = self._limpiar_ruta_drop(event.data)
        if os.path.isfile(path) and path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            self._cargar_imagen_desde_ruta(path)
        else:
            messagebox.showerror("Archivo no válido", "Por favor arrastra un archivo de imagen válido.")

    def _on_drop_video(self, event):
        path = self._limpiar_ruta_drop(event.data)
        if os.path.isfile(path) and path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
            self._cargar_video_desde_ruta(path)
        else:
            messagebox.showerror("Archivo no válido", "Por favor arrastra un archivo de video válido.")

    # ==========================================
    # PROCESAMIENTO Y VISTA PREVIA
    # ==========================================
    def seleccionar_imagen(self):
        path = filedialog.askopenfilename(
            title="Seleccionar Imagen",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp")],
        )
        if path:
            self._cargar_imagen_desde_ruta(path)

    def _cargar_imagen_desde_ruta(self, path):
        self.img_input_path = path
        self.lbl_img_file.configure(text=os.path.basename(path), text_color="white")

        try:
            pil_img = Image.open(path)
            pil_img.thumbnail((220, 120))
            self.img_preview_obj = ctk.CTkImage(
                light_image=pil_img, dark_image=pil_img, size=pil_img.size
            )
            self.lbl_img_preview.configure(image=self.img_preview_obj, text="")
        except Exception as e:
            self.lbl_img_preview.configure(text=f"Error en vista previa: {e}")

    def seleccionar_video(self):
        path = filedialog.askopenfilename(
            title="Seleccionar Video",
            filetypes=[("Archivos de Video", "*.mp4 *.mkv *.avi *.mov")],
        )
        if path:
            self._cargar_video_desde_ruta(path)

    def _cargar_video_desde_ruta(self, path):
        self.video_input_path = path
        self.lbl_vid_file.configure(text=os.path.basename(path), text_color="white")
        self.lbl_vid_preview.configure(text="Cargando fotograma...")

        self.update_idletasks()

        try:
            from moviepy.video.io.VideoFileClip import VideoFileClip

            clip = VideoFileClip(path)
            frame_array = clip.get_frame(0)
            clip.close()

            pil_frame = Image.fromarray(frame_array)
            pil_frame.thumbnail((200, 100))

            self.vid_preview_obj = ctk.CTkImage(
                light_image=pil_frame, dark_image=pil_frame, size=pil_frame.size
            )
            self.lbl_vid_preview.configure(image=self.vid_preview_obj, text="")
        except Exception as e:
            self.lbl_vid_preview.configure(text=f"No se pudo cargar fotograma:\n{e}")

    # ==========================================
    # EJECUCIÓN DE ACCIONES
    # ==========================================
    def ejecutar_remover_fondo(self):
        if not self.img_input_path:
            messagebox.showerror("Error", "Selecciona o arrastra una imagen primero.")
            return

        from image_engine import remover_fondo_imagen

        seleccion = self.model_menu.get()
        modelo_key = seleccion.split(" ")[0]

        base, ext = os.path.splitext(self.img_input_path)
        output_path = f"{base}_sin_fondo.png"

        self.lbl_status.configure(text=f"Procesando imagen con '{modelo_key}'...", text_color="#eab308")
        self.progress_bar.set(0.5)
        self.update_idletasks()

        exito = remover_fondo_imagen(self.img_input_path, output_path, modelo=modelo_key)
        
        if exito:
            self.progress_bar.set(1.0)
            self.lbl_status.configure(text="¡Imagen procesada con éxito!", text_color="#22c55e")
            messagebox.showinfo("Éxito", f"Imagen guardada en:\n{output_path}")
        else:
            self.progress_bar.set(0)
            self.lbl_status.configure(text="Error al procesar la imagen", text_color="#ef4444")
            messagebox.showerror("Error", "No se pudo procesar la imagen.")

    def ejecutar_redimensionado(self):
        if not self.img_input_path:
            messagebox.showerror("Error", "Selecciona o arrastra una imagen primero.")
            return

        try:
            w = int(self.entry_width.get())
            h = int(self.entry_height.get())
        except ValueError:
            messagebox.showerror("Error", "Introduce un ancho y alto numéricos válidos.")
            return

        from image_engine import redimensionar_imagen

        base, ext = os.path.splitext(self.img_input_path)
        output_path = f"{base}_{w}x{h}{ext}"

        self.lbl_status.configure(text="Redimensionando imagen...", text_color="#eab308")
        self.progress_bar.set(0.5)
        self.update_idletasks()

        exito = redimensionar_imagen(self.img_input_path, output_path, w, h)
        if exito:
            self.progress_bar.set(1.0)
            self.lbl_status.configure(text="¡Imagen redimensionada con éxito!", text_color="#22c55e")
            messagebox.showinfo("Éxito", f"Imagen redimensionada en:\n{output_path}")
        else:
            self.progress_bar.set(0)
            self.lbl_status.configure(text="Error al redimensionar", text_color="#ef4444")
            messagebox.showerror("Error", "Error al redimensionar la imagen.")

    def ejecutar_cambio_formato(self):
        if not self.video_input_path:
            messagebox.showerror("Error", "Selecciona o arrastra un video primero.")
            return

        formato_seleccionado = self.aspect_menu.get()
        tag = "vertical" if "9:16" in formato_seleccionado else ("cuadrado" if "1:1" in formato_seleccionado else "horizontal")

        from video_engine import cambiar_formato_video

        base, _ = os.path.splitext(self.video_input_path)
        output_path = f"{base}_{tag}.mp4"

        self.lbl_status.configure(text=f"Cambiando formato a {formato_seleccionado} (MP4)...", text_color="#eab308")
        self.progress_bar.set(0.4)
        self.update_idletasks()

        exito = cambiar_formato_video(self.video_input_path, output_path, formato_seleccionado)

        if exito:
            self.progress_bar.set(1.0)
            self.lbl_status.configure(text="¡Video convertido con éxito!", text_color="#22c55e")
            messagebox.showinfo("Éxito", f"Video convertido guardado en:\n{output_path}")
        else:
            self.progress_bar.set(0)
            self.lbl_status.configure(text="Error al convertir video", text_color="#ef4444")
            messagebox.showerror("Error", "Ocurrió un error al cambiar el formato del video.")

    def ejecutar_recorte_video(self):
        if not self.video_input_path:
            messagebox.showerror("Error", "Selecciona o arrastra un video primero.")
            return

        try:
            start = float(self.entry_start.get())
            end = float(self.entry_end.get())
        except ValueError:
            messagebox.showerror("Error", "Introduce valores numéricos válidos en segundos para el inicio y fin.")
            return

        from video_engine import recortar_video

        base, ext = os.path.splitext(self.video_input_path)
        output_path = f"{base}_recortado{ext}"

        self.lbl_status.configure(text=f"Recortando video de {start}s a {end}s...", text_color="#eab308")
        self.progress_bar.set(0.4)
        self.update_idletasks()

        exito = recortar_video(self.video_input_path, output_path, start, end)

        if exito:
            self.progress_bar.set(1.0)
            self.lbl_status.configure(text="¡Video recortado con éxito!", text_color="#22c55e")
            messagebox.showinfo("Éxito", f"Video recortado guardado en:\n{output_path}")
        else:
            self.progress_bar.set(0)
            self.lbl_status.configure(text="Error al recortar video", text_color="#ef4444")
            messagebox.showerror("Error", "Ocurrió un error al recortar el video.")

    def ejecutar_extraer_audio(self):
        if not self.video_input_path:
            messagebox.showerror("Error", "Selecciona o arrastra un video primero.")
            return

        from video_engine import extraer_audio

        base, _ = os.path.splitext(self.video_input_path)
        output_path = f"{base}_audio.mp3"

        self.lbl_status.configure(text="Extrayendo audio a MP3...", text_color="#eab308")
        self.progress_bar.set(0.5)
        self.update_idletasks()

        exito = extraer_audio(self.video_input_path, output_path)

        if exito:
            self.progress_bar.set(1.0)
            self.lbl_status.configure(text="¡Audio extraído con éxito!", text_color="#22c55e")
            messagebox.showinfo("Éxito", f"Audio guardado en:\n{output_path}")
        else:
            self.progress_bar.set(0)
            self.lbl_status.configure(text="Error al extraer audio", text_color="#ef4444")
            messagebox.showerror("Error", "Ocurrió un error al extraer el audio.")


if __name__ == "__main__":
    app = PixelMatteApp()
    app.mainloop()