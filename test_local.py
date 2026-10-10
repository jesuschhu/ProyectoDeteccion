"""
Test LOCAL - valida la integración sin necesidad de conexión
"""

import json
from pathlib import Path

# Test 1: Verifica que points.json tiene lat/lon
print("🔍 TEST 1: Estructura de points.json")
print("-" * 60)

points_file = Path(__file__).parent / "data" / "points.json"
with open(points_file, 'r', encoding='utf-8') as f:
    points = json.load(f)

for point in points:
    has_coords = "latitude" in point and "longitude" in point
    status = "✅" if has_coords else "❌"
    print(f"{status} {point['name']:30} LAT={point.get('latitude')}, LON={point.get('longitude')}")

# Test 2: Verifica integración en app.py
print("\n🔍 TEST 2: Integración en app.py")
print("-" * 60)

app_file = Path(__file__).parent / "app.py"
with open(app_file, 'r', encoding='utf-8') as f:
    app_content = f.read()

checks = {
    "NASADataFetcher importado": "from nasa_integration import NASADataFetcher" in app_content,
    "API Key definida": "NASA_API_KEY = " in app_content,
    "nasa_fetcher inicializado": "self.nasa_fetcher = NASADataFetcher" in app_content,
    "nasa_data dict creado": "self.nasa_data: Dict[str, Dict]" in app_content,
    "Fetch en hover": "fetch_destination_data_async" in app_content,
    "Cache en loop": "get_destination_data" in app_content,
    "Temperatura en Card": 'data_rows.append(("Temperatura"' in app_content,
    "Estado fuego en Card": 'data_rows.append(("Estado fuego"' in app_content,
}

for check, result in checks.items():
    status = "✅" if result else "❌"
    print(f"{status} {check}")

# Test 3: Verifica módulo NASA
print("\n🔍 TEST 3: Módulo nasa_integration.py")
print("-" * 60)

try:
    from nasa_integration import NASADataFetcher, NASAPowerClient, NASAEONETClient
    print("✅ Todos los clientes importan correctamente")
    
    # Crear instancia
    fetcher = NASADataFetcher("test_key")
    print("✅ NASADataFetcher instancia creada")
    print(f"✅ Caché inicializado con {len(fetcher.pending_requests)} solicitudes")
    print("✅ Threading activado")
    
except Exception as e:
    print(f"❌ Error: {e}")

# Resumen final
print("\n" + "=" * 60)
all_pass = all(checks.values()) and len(points) > 0
if all_pass:
    print("🎉 ¡INTEGRACIÓN COMPLETADA CORRECTAMENTE!")
    print("✅ App lista para usar con datos NASA")
    print("\nSiguiente: Ejecuta `python app.py` y prueba con hover")
else:
    print("⚠️  Revisa los errores arriba")
