#!/usr/bin/env python3
"""
LAUNCHER - Ejecuta Presenta en MODO SIMULADO (sin internet)

Uso:
    python app_demo.py
"""

import sys
from pathlib import Path

# Agregar project root al path
sys.path.insert(0, str(Path(__file__).parent))

from app import GestureMapApp
from nasa_mock import enable_mock_mode


def main():
    print("\n" + "=" * 70)
    print("🌍 PRESENTA - CORDILLERA BLANCA")
    print("Modo SIMULADO (datos NASA locales, sin internet requerida)")
    print("=" * 70)
    print("\n📋 INSTRUCCIONES:")
    print("  1. Levanta tu mano frente a la cámara")
    print("  2. Pasa sobre un destino en el mapa (0.35+ segundos)")
    print("  3. La Card aparecerá con TEMPERATURA y ESTADO DE FUEGOS")
    print("\n  Presiona 'd' para toggle debug")
    print("  Presiona 'q' o ESC para salir")
    print("\n" + "=" * 70 + "\n")
    
    # Crear app
    app = GestureMapApp()
    
    # Activar modo simulado (reemplaza NASADataFetcher)
    enable_mock_mode(app)
    
    # Habilitar debug por defecto
    app.debug = True
    
    # Ejecutar
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n✓ Salida graceful")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
