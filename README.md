# Presenta: Explorador Gestual de la Cordillera Blanca

Aplicacion de escritorio en Python que permite explorar puntos turisticos de la Cordillera Blanca usando solo la mano y una webcam.

## Funcionalidades del MVP

- Deteccion de mano en tiempo real con MediaPipe.
- Puntero basado en la punta del dedo indice.
- Mapa ilustrado dibujado en la interfaz (sin internet).
- Zonas interactivas para montanas y rutas.
- Hover suave por permanencia para evitar activaciones accidentales.
- Highlight visual del punto activo.
- Card de informacion con transicion.

## Requisitos

- Python 3.10+
- Webcam estándar

## Instalación

1. Crear y activar entorno virtual.
2. Instalar dependencias:

   pip install -r requirements.txt

## Ejecutar

python app.py

Nota: con versiones nuevas de MediaPipe (API Tasks), la primera ejecucion descarga el modelo
`hand_landmarker.task` en la carpeta `models/`. Luego la app funciona offline usando ese archivo local.

## Controles

- Tecla D: mostrar/ocultar capa de debug.
- Tecla Q o ESC: salir.

## Estructura

- app.py: aplicación principal.
- data/points.json: puntos interactivos con datos reales de referencia.

## Roadmap sugerido

1. Reemplazar el mapa dibujado por una ilustracion final propia.
2. Ajustar coordenadas de puntos para la version final del mapa.
3. Anadir mas rutas y filtros por dificultad/temporada.
4. Exportar como ejecutable para demo.
