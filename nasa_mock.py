"""
Módulo de SIMULACIÓN para NASA APIs
Usa datos locales en lugar de conectarse a internet
Útil para testing y debugging sin conexión
"""

import random
from typing import Dict, List, Optional


# Datos de prueba por destino
MOCK_DATA = {
    "huascaran": {
        "temperature": 3.2,
        "fires": []
    },
    "alpamayo": {
        "temperature": 5.8,
        "fires": [
            {
                "title": "Fuego en Pampas",
                "latitude": -8.95,
                "longitude": -77.50,
                "distance_km": 12.3,
                "date": "2026-04-28",
                "magnitude": "4.2"
            }
        ]
    },
    "santa_cruz": {
        "temperature": 12.5,
        "fires": []
    },
    "laguna_69": {
        "temperature": 9.1,
        "fires": []
    },
    "chavin": {
        "temperature": 18.3,
        "fires": []
    }
}


class MockNASADataFetcher:
    """Version simulada que devuelve datos locales al instante."""
    
    def __init__(self, api_key: str = None):
        """Inicializa con datos simulados (ignora API key)."""
        self.pending_requests: Dict[str, Dict] = {}
    
    def fetch_destination_data_async(
        self,
        destination_id: str,
        latitude: float = None,
        longitude: float = None,
        radius_km: float = 50
    ) -> None:
        """Simula fetch asincrónico - devuelve datos al instante."""
        print(f"[MOCK] Simulando fetch para {destination_id}")
        
        # Simular "en progreso"
        self.pending_requests[destination_id] = {"status": "fetching"}
        
        # Obtener datos simulados
        if destination_id in MOCK_DATA:
            mock_data = MOCK_DATA[destination_id]
        else:
            # Generar datos aleatorios si no existe
            mock_data = {
                "temperature": random.uniform(0, 25),
                "fires": []
            }
        
        # "Completar" inmediatamente (sin thread, para testing)
        self.pending_requests[destination_id] = {
            "status": "complete",
            "temperature": mock_data["temperature"],
            "fires": mock_data["fires"]
        }
    
    def get_destination_data(self, destination_id: str) -> Optional[Dict]:
        """Obtiene datos completados al instante."""
        if destination_id in self.pending_requests:
            request = self.pending_requests[destination_id]
            
            if request["status"] == "complete":
                return {
                    "temperature": request.get("temperature"),
                    "fires": request.get("fires", [])
                }
        
        return None
    
    def clear_old_requests(self, older_than_seconds: int = 1800) -> None:
        """No-op en modo simulado."""
        pass


def enable_mock_mode(app_instance):
    """
    Activa el modo simulado en una instancia de GestureMapApp.
    
    Uso:
        from nasa_mock import enable_mock_mode
        app = GestureMapApp()
        enable_mock_mode(app)  # Reemplaza con datos simulados
        app.run()
    """
    print("\n" + "=" * 60)
    print("🎭 MODO SIMULADO ACTIVADO")
    print("=" * 60)
    print("⚠️  Usando datos locales (sin conexión a internet)")
    print("✅ Datos completados al instante (sin threading)")
    print("=" * 60 + "\n")
    
    # Reemplazar fetcher con versión simulada
    app_instance.nasa_fetcher = MockNASADataFetcher()


# Datos simulados con variaciones para demostración
def get_random_mock_data(destination_id: str) -> Dict:
    """Devuelve datos aleatorios para variar entre hovers."""
    base_data = MOCK_DATA.get(destination_id, {
        "temperature": random.uniform(0, 25),
        "fires": []
    })
    
    # Agregar pequeña variación
    varied = {
        "temperature": base_data["temperature"] + random.uniform(-2, 2),
        "fires": base_data["fires"]
    }
    
    return varied
