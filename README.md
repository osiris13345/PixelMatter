🎨 PixelMatte

Aplicación de escritorio moderna y de alto rendimiento para el procesamiento multimedia y la eliminación automatizada de fondos impulsada por Inteligencia Artificial.

✨ Características Principales

Eliminación de Fondos con IA: Procesamiento preciso y rápido tanto en imágenes como en secuencias de video gracias a la integración con rembg y onnxruntime.

Interfaz Moderna y Fluida: Construida con CustomTkinter, ofreciendo una experiencia visual limpia, elegante y con soporte para arrastrar y soltar archivos (tkinterdnd2).

Arquitectura Modular: Código limpio y escalable separado en motores independientes para mantener un rendimiento óptimo.

Empaquetado Portátil: Compilado automáticamente para Windows como un ejecutable independiente de archivo único (.exe).

🛠️ Estructura del Proyecto

El repositorio está organizado de forma modular para facilitar su mantenimiento y escalabilidad:

PixelMatter/
├── .github/
│   └── workflows/
│       └── build.yml       # Pipeline de CI/CD para la compilación automática con PyInstaller
├── PixelMatte.py           # Punto de entrada principal y controlador de la interfaz gráfica
├── image_engine.py         # Módulo especializado en el procesamiento de imágenes
├── video_engine.py         # Módulo encargado del manejo de fotogramas y videos con MoviePy
└── requirements.txt        # Lista de dependencias del proyecto


⚙️ Dependencias Principales

El proyecto se sustenta sobre las siguientes librerías de Python:

customtkinter — Interfaz gráfica avanzada.

rembg — Segmentación de objetos y remoción de fondos por IA.

MoviePy — Edición y procesamiento de video.

tkinterdnd2 — Soporte de funciones Drag and Drop.

Pillow — Manipulación avanzada de imágenes.

💻 Instrucciones de Instalación y Ejecución Local

🪟 Windows

Opción 1: Ejecutable listo para usar (Recomendado)

Ve a la pestaña Actions (o sección de Releases) en este repositorio.

Descarga el artefacto comprimido PixelMatte-Windows-EXE.

Extrae el archivo .zip y ejecuta directamente PixelMatte.exe. No requiere instalación previa de Python.

Opción 2: Desde el código fuente

Asegúrate de tener Python 3.10 o superior instalado y añadido al PATH.

Clona el repositorio o descarga el código fuente:

git clone https://github.com/osiris13345/PixelMatter.git
cd PixelMatter


Crea y activa un entorno virtual:

python -m venv venv
venv\Scripts\activate


Instala las dependencias:

pip install --upgrade pip
pip install -r requirements.txt


Ejecuta la aplicación:

python PixelMatte.py


🐧 Linux (Linux Mint / Ubuntu / Debian)

Desde el código fuente

Abre una terminal e instala Python, pip y los paquetes del sistema necesarios para soporte de interfaz gráfica y multimedia:

sudo apt update
sudo apt install python3 python3-pip python3-venv python3-tk ffmpeg -y


Clona el repositorio:

git clone https://github.com/osiris13345/PixelMatter.git
cd PixelMatter


Crea y activa un entorno virtual:

python3 -m venv venv
source venv/bin/activate


Actualiza pip e instala las dependencias de Python:

pip install --upgrade pip
pip install -r requirements.txt


Ejecuta la aplicación:

python3 PixelMatte.py


Nota para Linux: Se incluye ffmpeg en la instalación del sistema para garantizar que moviepy y el motor de video procesen las pistas de audio y formatos multimedia sin inconvenientes.

🚀 Compilación y Automatización (CI/CD)

El proyecto cuenta con un flujo de trabajo automatizado en GitHub Actions (build.yml) que empaqueta todo el código fuente y sus dependencias complejas mediante PyInstaller, generando el archivo ejecutable (.exe) listo para su distribución en la sección de artefactos y liberaciones.
