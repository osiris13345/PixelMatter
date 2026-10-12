import os

def extraer_audio(input_path, output_path):
    try:
        print(f"[*] Abriendo video: {os.path.basename(input_path)}...")
        from moviepy.video.io.VideoFileClip import VideoFileClip

        clip = VideoFileClip(input_path)
        if clip.audio is None:
            print("[!] El video seleccionado no contiene pistas de audio.")
            clip.close()
            return False

        print("[*] Exportando audio a MP3...")
        clip.audio.write_audiofile(output_path, logger=None)
        clip.close()
        print(f"[✔] Audio extraído con éxito: {output_path}")
        return True
    except Exception as e:
        print(f"[✖] Error al extraer audio: {e}")
        return False


def recortar_video(input_path, output_path, start_time, end_time):
    try:
        print(f"[*] Abriendo video para recorte: {os.path.basename(input_path)}...")
        from moviepy.video.io.VideoFileClip import VideoFileClip

        clip = VideoFileClip(input_path)
        duracion = clip.duration
        if end_time > duracion:
            end_time = duracion
        if start_time < 0:
            start_time = 0
        if start_time >= end_time:
            clip.close()
            return False

        subclip = clip.subclip(start_time, end_time)
        
        # Forzamos fps estable y preset equilibrado para evitar fotogramas congelados
        subclip.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac", 
            fps=clip.fps or 30, 
            preset="medium",
            logger=None
        )
        
        subclip.close()
        clip.close()
        print(f"[✔] Video recortado con éxito: {output_path}")
        return True
    except Exception as e:
        print(f"[✖] Error al recortar video: {e}")
        return False


def cambiar_formato_video(input_path, output_path, formato_destino):
    try:
        print(f"[*] Procesando formato de video para: {os.path.basename(input_path)}...")
        from moviepy.video.io.VideoFileClip import VideoFileClip

        clip = VideoFileClip(input_path)
        w, h = clip.size
        
        if formato_destino == "9:16 (Vertical)":
            nuevo_w = int(h * (9 / 16))
            x_center = w / 2
            subclip = clip.crop(x1=x_center - nuevo_w/2, y1=0, x2=x_center + nuevo_w/2, y2=h)
        elif formato_destino == "1:1 (Cuadrado)":
            lado = min(w, h)
            x_center = w / 2
            y_center = h / 2
            subclip = clip.crop(x1=x_center - lado/2, y1=y_center - lado/2, x2=x_center + lado/2, y2=y_center + lado/2)
        else:
            subclip = clip

        print("[*] Exportando video con nuevo formato a MP4 con sincronización fluida...")
        subclip.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac", 
            fps=clip.fps or 30, 
            preset="medium",
            logger=None
        )
        
        subclip.close()
        clip.close()
        print(f"[✔] Video redimensionado con éxito: {output_path}")
        return True
        
    except Exception as e:
        print(f"[✖] Error al cambiar formato de video: {e}")
        return False