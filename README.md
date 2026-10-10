# 🏔️ Presenta — Explorador Gestual de la Cordillera Blanca

> Explora destinos de la Cordillera Blanca usando solo tu mano y una webcam.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8?logo=opencv&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Hand%20Tracking-4285F4?logo=google&logoColor=white)

**Presenta** es una aplicación de escritorio desarrollada en Python que convierte la mano en un puntero para recorrer destinos turísticos de la Cordillera Blanca. El proyecto combina visión por computadora, una interfaz visual y datos de referencia para crear una experiencia de exploración sin mouse.

## ✨ Características

- 🖐️ Detección de mano en tiempo real con MediaPipe.
- ☝️ Puntero controlado por la punta del dedo índice.
- 🗺️ Mapa ilustrado interactivo de la Cordillera Blanca.
- 📍 Puntos turísticos, montañas y rutas con información contextual.
- 🎯 Activación por permanencia (*hover*) para evitar selecciones accidentales.
- 🎞️ Recursos visuales locales; funciona sin conexión después de preparar los recursos.
- 🌦️ Integración opcional con NASA POWER y EONET.

## 🧰 Requisitos

- Python 3.10 o superior
- Webcam
- Windows, macOS o Linux con acceso a cámara

## 🚀 Instalación rápida

```bash
# 1. Clona el repositorio
git clone https://github.com/jesuschhu/ProyectoDeteccion.git
cd ProyectoDeteccion

# 2. Crea y activa un entorno virtual
python -m venv .venv

# Windows (PowerShell)
.venv\\Scripts\\Activate.ps1

# macOS / Linux
source .venv/bin/activate

# 3. Instala las dependencias
pip install -r requirements.txt

# 4. Ejecuta la aplicación
python app.py
```

> La primera ejecución puede descargar el modelo de detección de manos si no está disponible localmente. Después se almacena en `models/`.

## 🎮 Uso

1. Permite el acceso a la webcam si tu sistema lo solicita.
2. Coloca tu mano frente a la cámara y mueve el dedo índice para controlar el puntero.
3. Mantén el puntero sobre un destino para abrir su información.

| Tecla | Acción |
| --- | --- |
| `D` | Muestra u oculta la capa de depuración |
| `Q` o `Esc` | Cierra la aplicación |

## 🌦️ Integración NASA opcional

El proyecto puede consumir datos de NASA POWER y EONET. La clave no se incluye en el repositorio.

```powershell
# Solo para la sesión actual de PowerShell
$env:NASA_API_KEY = "tu_clave_de_nasa"
python app.py
```

Consulta [`.env.example`](.env.example) como referencia. Nunca publiques tu clave API en commits, capturas o documentación.

## 🗂️ Estructura del proyecto

```text
ProyectoDeteccion/
├── app.py                 # Aplicación principal
├── nasa_integration.py    # Cliente de datos NASA
├── data/                  # Puntos turísticos y datos de referencia
├── models/                # Modelo local de detección de manos
├── assets/                # Imágenes, fuentes y videos de destinos
├── requirements.txt       # Dependencias de Python
└── README.md              # Esta guía
```

## 🧪 Verificaciones locales

```bash
python test_local.py
python test_nasa.py
```

## 🧭 Próximas mejoras

- [ ] Añadir más rutas y filtros por dificultad o temporada.
- [ ] Incorporar una ilustración cartográfica propia de mayor detalle.
- [ ] Exportar una versión ejecutable para demostraciones.
- [ ] Mejorar la accesibilidad y los flujos sin webcam.

## 👤 Autoría

Proyecto académico desarrollado por **Jesús Chuquihuanga**. Si lo usas o adaptas, una mención al proyecto será muy apreciada.

---

Hecho con Python, visión por computadora y mucho cariño por la Cordillera Blanca. ⛰️
