# 🎨 PixelMatte - Multimedia Suite

**PixelMatte** es una suite multimedia de escritorio, ligera y moderna, diseñada para el procesamiento rápido de imágenes y videos mediante integración con modelos de inteligencia artificial y herramientas optimizadas.

Construida con un diseño limpio y minimalista que soporta modos claro y oscuro, ofrece una experiencia fluida tanto para creadores de contenido como para desarrolladores y editores.

---

### ✨ Características Principales

#### 🖼️ Módulo de Imágenes
* **Eliminación de fondo con IA:** Integración con modelos avanzados (`u2netp`, `u2net`, `isnet-general-use`) para recortes precisos con un solo clic.
* **Creación de Stickers:** Generación automática de stickers con bordes personalizados.
* **Redimensionamiento y Formato:** Conversión de formatos y ajuste de dimensiones conservando la calidad visual.
* **Filtro Pixel Art:** Transformación de imágenes en arte pixelado personalizable.
* **Vista previa y comparación:** Herramientas para comparar el estado original y el resultado antes de exportar.

#### 🎥 Módulo de Video
* **Conversión de Formato:** Exportación rápida entre los contenedores de video más comunes.
* **Recorte de Segmentos:** Edición precisa de fragmentos de video.
* **Compresión:** Reducción eficiente del tamaño de archivo ajustando parámetros de calidad.
* **Video a GIF:** Conversión de clips de video a animaciones GIF optimizadas.
* **Extracción de Audio:** Herramientas dedicadas para procesamiento y separación de audio.

---

### 🛠️ Tecnologías Utilizadas

* **Lenguaje:** Python 3.10+
* **Interfaz Gráfica:** `CustomTkinter`
* **Iconografía:** `Remix Icon` (Font & CSS)
* **Motor de IA:** `Rembg` & `ONNX Runtime`
* **Procesamiento de Video:** `FFmpeg` / `OpenCV`
* **Compilación:** GitHub Actions + `PyInstaller` (Distribución en `.exe` para Windows)

---

### 🚀 Instalación y Uso

#### Descargar Ejecutable (Windows)
Puedes descargar la versión compilada en `.exe` directamente desde la pestaña de **Releases** o desde los **Artifacts** de GitHub Actions sin necesidad de instalar Python ni dependencias.

#### Ejecutar desde el código fuente
1. Clona este repositorio:
   ```bash
   git clone [https://github.com/osiris13345/PixelMatter.git](https://github.com/osiris13345/PixelMatter.git)
   cd PixelMatter
