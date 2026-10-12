import os

def extraer_audio(input_path, output_path):
    """
    Extrae el audio de un archivo de video y lo guarda como MP3.
    Compatible con MoviePy v2.x para evitar errores de importación.
    """
    try:
        print(f"[*] Abriendo video: {os.path.basename(input_path)}...")
        
        # Importación compatible con MoviePy 2.x
        from moviepy import VideoFileClip

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
        print(f"[✖] Error al extraer el audio del video: {e}")
        return False