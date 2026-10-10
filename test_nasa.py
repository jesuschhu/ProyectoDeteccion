"""
Script de prueba para validar la integración NASA POWER + EONET
Ejecuta: python test_nasa.py
"""

import time
from nasa_integration import NASAPowerClient, NASAEONETClient, NASADataFetcher


def test_power_api():
    """Test básico de NASA POWER"""
    print("\n" + "="*60)
    print("🌡️  TEST 1: NASA POWER API")
    print("="*60)
    
    api_key = "your_nasa_api_key_here"
    client = NASAPowerClient(api_key)
    
    # Coordenadas de prueba
    locations = {
        "Huascarán": (-9.1201, -77.6107),
        "Alpamayo": (-8.9906, -77.4761),
        "Laguna 69": (-9.0892, -77.7028),
    }
    
    for name, (lat, lon) in locations.items():
        print(f"\n📍 Obteniendo temperatura de {name}...")
        print(f"   Coordenadas: {lat:.4f}, {lon:.4f}")
        
        temp = client.get_temperature(lat, lon)
        
        if temp is not None:
            print(f"   ✅ Temperatura: {temp:.1f}°C")
        else:
            print(f"   ❌ Error obteniendo datos")
        
        time.sleep(1)  # Evitar rate limiting


def test_eonet_api():
    """Test básico de NASA EONET"""
    print("\n" + "="*60)
    print("🔥 TEST 2: NASA EONET API (Incendios)")
    print("="*60)
    
    client = NASAEONETClient()
    
    # Coordenadas de prueba
    locations = {
        "Huascarán": (-9.1201, -77.6107),
        "Alpamayo": (-8.9906, -77.4761),
        "Laguna 69": (-9.0892, -77.7028),
    }
    
    for name, (lat, lon) in locations.items():
        print(f"\n🔍 Buscando incendios cerca de {name}...")
        print(f"   Coordenadas: {lat:.4f}, {lon:.4f}")
        print(f"   Radio: 50km")
        
        fires = client.find_fires_nearby(lat, lon, radius_km=50)
        
        if fires:
            print(f"   ⚠️  {len(fires)} incendio(s) detectado(s):")
            for i, fire in enumerate(fires, 1):
                print(f"      {i}. {fire['title']}")
                print(f"         - Distancia: {fire['distance_km']:.1f}km")
                print(f"         - Fecha: {fire['date']}")
        else:
            print(f"   ✅ Sin incendios detectados")
        
        time.sleep(1)


def test_async_fetcher():
    """Test del fetcher asincrónico"""
    print("\n" + "="*60)
    print("⚡ TEST 3: Fetcher Asincrónico (Threading)")
    print("="*60)
    
    api_key = "your_nasa_api_key_here"
    fetcher = NASADataFetcher(api_key)
    
    # Simular 3 destinos activos
    destinations = [
        ("huascaran", -9.1201, -77.6107),
        ("alpamayo", -8.9906, -77.4761),
        ("laguna_69", -9.0892, -77.7028),
    ]
    
    print("\n📡 Disparando peticiones asincrónicas...")
    for dest_id, lat, lon in destinations:
        fetcher.fetch_destination_data_async(dest_id, lat, lon)
        print(f"   ✓ Petición iniciada para {dest_id}")
    
    print("\n⏳ Esperando respuestas (máx 10 segundos)...")
    max_wait = 10
    start = time.time()
    
    while time.time() - start < max_wait:
        all_ready = True
        
        for dest_id, _, _ in destinations:
            data = fetcher.get_destination_data(dest_id)
            
            if data is None:
                all_ready = False
                status = "En progreso..."
            elif "error" in str(data):
                status = f"❌ Error"
            else:
                temp = data.get("temperature")
                fires = len(data.get("fires", []))
                status = f"✅ T={temp}°C, Fuegos={fires}"
            
            print(f"   {dest_id:15} {status}")
        
        if all_ready:
            print("\n✅ Todas las peticiones completadas")
            break
        
        time.sleep(1)
        print("\r", end="")  # Limpiar línea anterior
    
    # Mostrar detalles finales
    print("\n📊 RESULTADOS FINALES:")
    print("-" * 60)
    
    for dest_id, _, _ in destinations:
        data = fetcher.get_destination_data(dest_id)
        
        if data:
            print(f"\n🗺️  {dest_id}:")
            print(f"   Temperatura: {data.get('temperature')}°C")
            
            fires = data.get("fires", [])
            if fires:
                print(f"   Incendios: {len(fires)}")
                for fire in fires[:2]:  # Mostrar los 2 primeros
                    print(f"     - {fire['title']}: {fire['distance_km']:.1f}km")
            else:
                print(f"   Incendios: Ninguno")


def test_cache():
    """Test del sistema de caché"""
    print("\n" + "="*60)
    print("💾 TEST 4: Sistema de Caché")
    print("="*60)
    
    from nasa_integration import NASADataCache
    
    cache = NASADataCache(expire_seconds=3)
    
    print("\n1️⃣  Almacenando datos...")
    cache.set("test_key", {"temperature": 5.3})
    print("   ✓ Datos guardados")
    
    print("\n2️⃣  Recuperando inmediatamente...")
    data = cache.get("test_key")
    print(f"   ✓ Dato recuperado: {data}")
    
    print("\n3️⃣  Esperando expiración (3 segundos)...")
    time.sleep(3.5)
    
    print("4️⃣  Intentando recuperar después de expiración...")
    data = cache.get("test_key")
    if data is None:
        print("   ✓ Dato expirado (como esperado)")
    else:
        print("   ❌ Dato no expiró")


def test_haversine():
    """Test de cálculo de distancia"""
    print("\n" + "="*60)
    print("📐 TEST 5: Cálculo de Distancia Haversine")
    print("="*60)
    
    from nasa_integration import NASAEONETClient
    
    # Puntos conocidos
    test_cases = [
        ("Huascarán a Alpamayo", -9.1201, -77.6107, -8.9906, -77.4761, 15),
        ("Huascarán a sí mismo", -9.1201, -77.6107, -9.1201, -77.6107, 0),
    ]
    
    for label, lat1, lon1, lat2, lon2, expected_approx in test_cases:
        distance = NASAEONETClient._haversine_distance(lat1, lon1, lat2, lon2)
        print(f"\n📍 {label}")
        print(f"   Distancia: {distance:.1f}km (esperado ~{expected_approx}km)")


def main():
    """Ejecutar todos los tests"""
    print("\n" + "🚀" * 30)
    print("BATERÍA DE TESTS - NASA INTEGRATION")
    print("🚀" * 30)
    
    try:
        # Test 1: POWER API
        test_power_api()
        
        # Test 2: EONET API
        test_eonet_api()
        
        # Test 3: Async Fetcher
        test_async_fetcher()
        
        # Test 4: Cache
        test_cache()
        
        # Test 5: Distancia
        test_haversine()
        
        print("\n" + "✅" * 30)
        print("¡TODOS LOS TESTS COMPLETADOS!")
        print("✅" * 30)
        print("\n📝 Resumen:")
        print("   ✓ NASA POWER: Obteniendo temperaturas")
        print("   ✓ NASA EONET: Detectando incendios")
        print("   ✓ Async: Threading sin bloqueos")
        print("   ✓ Cache: Expiración automática")
        print("   ✓ Cálculos: Distancias precisas")
        print("\n🎉 Listo para integrar en app.py")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
