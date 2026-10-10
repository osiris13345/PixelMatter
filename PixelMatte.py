#!/usr/bin/env python3
import os
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from rembg import remove, new_session

class VideoEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PixelMatte - Editor Inteligente Pro")
        self.root.geometry("480x850")

        self.input_path = ""
        
        # Detección automática de la carpeta Escritorio/Desktop según el sistema operativo
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(desktop_path):
            desktop_path = os.path.join(os.path.expanduser("~"), "Escritorio")
        if not os.path.exists(desktop_path):
            desktop_path = os.getcwd()
            
        self.output_dir = desktop_path
        self.cancel_requested = False

        try:
            self.session = new_session("u2netp")
        except Exception as e:
            print("Aviso al cargar modelo rembg:", e)
            self.session = None

        # --- INTERFAZ ---
        self.label = tk.Label(root, text="Arrastra un video o imagen aquí\no usa el botón de selección", font=("Arial", 10), wraplength=440)
        self.label.pack(pady=8)

        btn_file_frame = tk.Frame(root)
        btn_file_frame.pack(pady=2)

        self.select_btn = tk.Button(btn_file_frame, text="Seleccionar Archivo", command=self.select_file, width=20, height=2)
        self.select_btn.pack(side="left", padx=5)

        self.select_out_btn = tk.Button(btn_file_frame, text="Carpeta de Salida", command=self.select_output_dir, width=20, height=2)
        self.select_out_btn.pack(side="left", padx=5)

        self.out_label = tk.Label(root, text=f"Salida: {self.output_dir}", font=("Arial", 8), fg="darkgray", wraplength=440)
        self.out_label.pack(pady=2)

        # Opciones Avanzadas
        options_frame = tk.LabelFrame(root, text=" Opciones de Edición e Inteligencia Artificial ", font=("Arial", 9, "bold"))
        options_frame.pack(fill="x", padx=20, pady=8)

        tk.Label(options_frame, text="Formato de Red Social:", font=("Arial", 9)).pack(anchor="w", padx=10, pady=2)
        self.format_var = tk.StringVar(value="9:16 (Vertical / Reels)")
        format_cb = ttk.Combobox(options_frame, textvariable=self.format_var, values=["9:16 (Vertical / Reels)", "1:1 (Cuadrado)"], state="readonly", width=35)
        format_cb.pack(padx=10, pady=5)

        tk.Label(options_frame, text="Fondo para espacios vacíos:", font=("Arial", 9)).pack(anchor="w", padx=10, pady=2)
        self.bg_var = tk.StringVar(value="Difuminado (Blur)")
        bg_cb = ttk.Combobox(options_frame, textvariable=self.bg_var, values=["Difuminado (Blur)", "Sólido Negro", "Transparente"], state="readonly", width=35)
        bg_cb.pack(padx=10, pady=5)

        self.ai_var = tk.BooleanVar(value=False)
        ai_chk = tk.Checkbutton(options_frame, text="Activar recorte inteligente con IA (rembg)", variable=self.ai_var, font=("Arial", 9))
        ai_chk.pack(anchor="w", padx=10, pady=5)

        self.enhance_var = tk.BooleanVar(value=True)
        enhance_chk = tk.Checkbutton(options_frame, text="Mejorar nitidez y calidad de imagen", variable=self.enhance_var, font=("Arial", 9))
        enhance_chk.pack(anchor="w", padx=10, pady=5)

        # Botones de Acción
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=8)

        self.process_btn = tk.Button(btn_frame, text="Procesar y Exportar", command=self.start_processing_thread, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=18, height=2)
        self.process_btn.pack(side="left", padx=5)

        self.cancel_btn = tk.Button(btn_frame, text="Cancelar", command=self.request_cancel, bg="#f44336", fg="white", font=("Arial", 10, "bold"), width=12, height=2, state="disabled")
        self.cancel_btn.pack(side="left", padx=5)

        self.progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=5)

        self.status_label = tk.Label(root, text="Estado: Esperando archivo...", font=("Arial", 9), fg="gray")
        self.status_label.pack(pady=2)

        self.eta_label = tk.Label(root, text="ETA: --:--", font=("Arial", 9, "italic"), fg="blue")
        self.eta_label.pack(pady=2)

        try:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self.handle_drop)
        except Exception as e:
            print("Aviso de Drag & Drop:", e)

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar video o imagen",
            filetypes=[("Archivos Multimedia", "*.mp4 *.avi *.mov *.mkv *.webm *.jpg *.jpeg *.png *.webp *.bmp"), ("Todos los archivos", "*.*")]
        )
        if file_path:
            self.input_path = file_path
            filename = os.path.basename(file_path)
            self.label.config(text=f"Archivo cargado:\n{filename}")
            self.status_label.config(text="Estado: Archivo listo para procesar.")

    def select_output_dir(self):
        dir_path = filedialog.askdirectory(title="Seleccionar carpeta de salida", initialdir=self.output_dir)
        if dir_path:
            self.output_dir = dir_path
            self.out_label.config(text=f"Salida: {self.output_dir}")

    def handle_drop(self, event):
        # Manejo seguro y multiplataforma de archivos arrastrados (compatible con espacios en Windows)
        files = self.root.tk.splitlist(event.data)
        if files:
            file_path = files[0]
            if os.path.exists(file_path):
                self.input_path = file_path
                filename = os.path.basename(file_path)
                self.label.config(text=f"Archivo cargado:\n{filename}")
                self.status_label.config(text="Estado: Archivo listo para procesar.")

    def request_cancel(self):
        self.cancel_requested = True
        self.status_label.config(text="Estado: Cancelando proceso...")

    def start_processing_thread(self):
        if not self.input_path:
            messagebox.showerror("Error", "Por favor selecciona o arrastra un archivo primero.")
            return
        
        self.cancel_requested = False
        self.process_btn.config(state="disabled")
        self.select_btn.config(state="disabled")
        self.select_out_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        
        threading.Thread(target=self.process_media, daemon=True).start()

    def process_media(self):
        ext = os.path.splitext(self.input_path)[1].lower()
        is_image = ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']

        if is_image:
            self.process_image()
        else:
            self.process_video()

    def process_image(self):
        try:
            self.status_label.config(text="Estado: Procesando imagen...")
            self.progress["value"] = 30

            pil_img = Image.open(self.input_path).convert("RGBA")

            if self.ai_var.get() and self.session is not None:
                self.status_label.config(text="Estado: Removiendo fondo con IA...")
                pil_img = remove(pil_img, session=self.session)

            if self.enhance_var.get():
                self.status_label.config(text="Estado: Mejorando nitidez y calidad...")
                enhancer_sharp = ImageEnhance.Sharpness(pil_img)
                pil_img = enhancer_sharp.enhance(1.3)
                
                enhancer_contrast = ImageEnhance.Contrast(pil_img)
                pil_img = enhancer_contrast.enhance(1.1)

            selected_format = self.format_var.get()
            target_w, target_h = (1080, 1920) if "9:16" in selected_format else (1080, 1080)

            orig_w, orig_h = pil_img.size
            scale = min(target_w / orig_w, target_h / orig_h)
            new_w = max(1, int(orig_w * scale))
            new_h = max(1, int(orig_h * scale))

            resized_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            bg_style = self.bg_var.get()
            if "Transparente" in bg_style:
                canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            elif "Difuminado" in bg_style:
                bg_canvas = pil_img.convert("RGB").resize((target_w, target_h), Image.Resampling.LANCZOS)
                bg_canvas = bg_canvas.filter(ImageFilter.GaussianBlur(30))
                canvas = bg_canvas.convert("RGBA")
            else:
                canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 255))

            x_offset = (target_w - new_w) // 2
            y_offset = (target_h - new_h) // 2

            canvas.paste(resized_img, (x_offset, y_offset), resized_img)

            os.makedirs(self.output_dir, exist_ok=True)
            base_name = os.path.splitext(os.path.basename(self.input_path))[0]
            output_path = os.path.join(self.output_dir, f"{base_name}_editado.png")

            canvas.save(output_path, "PNG")

            self.progress["value"] = 100
            self.status_label.config(text=f"¡Imagen lista! Guardada en: {output_path}")
            messagebox.showinfo("Completado", f"Imagen procesada y exportada en:\n{output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error procesando la imagen:\n{str(e)}")
            self.status_label.config(text="Estado: Error en la exportación.")
        finally:
            self.reset_ui()

    def process_video(self):
        cap = None
        out = None
        output_path = ""
        try:
            self.status_label.config(text="Estado: Analizando video...")
            
            cap = cv2.VideoCapture(self.input_path)
            if not cap.isOpened():
                messagebox.showerror("Error", "No se pudo abrir el archivo de video.")
                return

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0: fps = 30.0

            selected_format = self.format_var.get()
            target_w, target_h = (1080, 1920) if "9:16" in selected_format else (1080, 1080)

            os.makedirs(self.output_dir, exist_ok=True)
            base_name = os.path.splitext(os.path.basename(self.input_path))[0]
            output_path = os.path.join(self.output_dir, f"{base_name}_editado.mp4")

            fourcc_list = [cv2.VideoWriter_fourcc(*'mp4v'), cv2.VideoWriter_fourcc(*'XVID'), cv2.VideoWriter_fourcc(*'MJPG')]
            for fcc in fourcc_list:
                out = cv2.VideoWriter(output_path, fcc, fps, (target_w, target_h))
                if out.isOpened():
                    break

            if not out or not out.isOpened():
                messagebox.showerror("Error", "No se pudo inicializar el codificador de video de OpenCV.")
                return

            self.progress["maximum"] = total_frames if total_frames > 0 else 100
            current_frame_idx = 0
            start_time = time.time()
            use_ai = self.ai_var.get()

            while cap.isOpened():
                if self.cancel_requested:
                    self.status_label.config(text="Estado: Proceso cancelado por el usuario.")
                    break

                ret, frame = cap.read()
                if not ret:
                    break

                if use_ai and self.session is not None:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(rgb_frame)
                    processed_pil = remove(pil_img, session=self.session)
                    frame = cv2.cvtColor(np.array(processed_pil), cv2.COLOR_RGBA2BGRA if processed_pil.mode == 'RGBA' else cv2.COLOR_RGB2BGR)

                orig_h, orig_w = frame.shape[:2]
                scale = min(target_w / orig_w, target_h / orig_h)
                new_w = int(orig_w * scale)
                new_h = int(orig_h * scale)

                if frame.shape[2] == 4:
                    resized_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                else:
                    resized_frame = cv2.resize(frame, (new_w, new_h))

                bg_style = self.bg_var.get()
                if "Difuminado" in bg_style:
                    bg_canvas = cv2.resize(frame[:, :, :3] if frame.shape[2] == 4 else frame, (target_w, target_h))
                    bg_canvas = cv2.GaussianBlur(bg_canvas, (55, 55), 30)
                elif "Transparente" in bg_style and frame.shape[2] == 4:
                    bg_canvas = np.zeros((target_h, target_w, 4), dtype=np.uint8)
                else:
                    bg_canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)

                x_offset = (target_w - new_w) // 2
                y_offset = (target_h - new_h) // 2

                if frame.shape[2] == 4 and bg_canvas.shape[2] == 4:
                    alpha_s = resized_frame[:, :, 3] / 255.0
                    alpha_l = 1.0 - alpha_s
                    for c in range(0, 3):
                        bg_canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w, c] = (
                            alpha_s * resized_frame[:, :, c] +
                            alpha_l * bg_canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w, c]
                        )
                    bg_canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w, 3] = 255
                else:
                    if bg_canvas.shape[2] == 4:
                        bg_canvas = cv2.cvtColor(bg_canvas, cv2.COLOR_BGRA2BGR)
                    if resized_frame.shape[2] == 4:
                        resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGRA2BGR)
                    bg_canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized_frame

                out.write(bg_canvas)

                current_frame_idx += 1
                if total_frames > 0:
                    self.progress["value"] = current_frame_idx
                    
                    elapsed = time.time() - start_time
                    if current_frame_idx > 5 and elapsed > 0:
                        fps_proc = current_frame_idx / elapsed
                        remaining_frames = total_frames - current_frame_idx
                        eta_sec = remaining_frames / fps_proc if fps_proc > 0 else 0
                        mins, secs = divmod(int(eta_sec), 60)
                        self.eta_label.config(text=f"ETA: {mins:02d}:{secs:02d}")

            cap.release()
            if out:
                out.release()

            if self.cancel_requested:
                if os.path.exists(output_path):
                    os.remove(output_path)
                messagebox.showinfo("Cancelado", "El procesamiento fue cancelado.")
            else:
                self.status_label.config(text=f"¡Proceso exitoso! Guardado en: {output_path}")
                messagebox.showinfo("Completado", f"Video exportado correctamente en:\n{output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error durante el procesamiento:\n{str(e)}")
            self.status_label.config(text="Estado: Error en la exportación.")
        
        finally:
            if cap: cap.release()
            if out: out.release()
            self.reset_ui()

    def reset_ui(self):
        self.process_btn.config(state="normal")
        self.select_btn.config(state="normal")
        self.select_out_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.progress["value"] = 0
        self.eta_label.config(text="ETA: --:--")
        self.cancel_requested = False

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = VideoEditorApp(root)
    root.mainloop()