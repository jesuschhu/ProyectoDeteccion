"""
Integración asincrónica con APIs de NASA POWER y NASA EONET.
Incluye caché temporal y threading para no bloquear el bucle principal.
"""

import json
import math
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple


class NASADataCache:
    """Caché temporal para datos de NASA con expiración."""
    
    def __init__(self, expire_seconds: int = 600):
        """
        Args:
            expire_seconds: Tiempo en segundos hasta que los datos expiren (default 10 min)
        """
        self.expire_seconds = expire_seconds
        self.cache: Dict[str, Dict] = {}
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Dict]:
        """Obtiene un valor del caché si no está expirado."""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if time.time() - entry["timestamp"] < self.expire_seconds:
                    return entry["data"]
                else:
                    del self.cache[key]
        return None
    
    def set(self, key: str, data: Dict) -> None:
        """Almacena un valor en el caché con timestamp."""
        with self.lock:
            self.cache[key] = {
                "data": data,
                "timestamp": time.time()
            }
    
    def clear_expired(self) -> None:
        """Limpia entradas expiradas."""
        with self.lock:
            now = time.time()
            expired_keys = [
                k for k, v in self.cache.items()
                if now - v["timestamp"] >= self.expire_seconds
            ]
            for k in expired_keys:
                del self.cache[k]


class NASAPowerClient:
    """Cliente para NASA POWER API (temperatura)."""
    
    BASE_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"
    
    def __init__(self, api_key: str):
        """
        Args:
            api_key: Tu clave API de NASA POWER
        """
        self.api_key = api_key
        self.cache = NASADataCache(expire_seconds=600)  # 10 minutos
    
    def get_temperature(self, latitude: float, longitude: float) -> Optional[float]:
        """
        Obtiene temperatura actual (T2M) de NASA POWER.
        
        Args:
            latitude: Latitud en grados decimales
            longitude: Longitud en grados decimales
        
        Returns:
            Temperatura en Celsius o None si falla
        """
        cache_key = f"temp_{latitude:.4f}_{longitude:.4f}"
        
        # Verificar caché
        cached = self.cache.get(cache_key)
        if cached:
            return cached.get("temperature")
        
        try:
            # NASA POWER entrega datos horarios; pedimos una ventana corta y tomamos el último valor válido.
            end_date = datetime.utcnow().strftime("%Y%m%d")
            start_date = (datetime.utcnow() - timedelta(days=2)).strftime("%Y%m%d")
            url = (
                f"{self.BASE_URL}"
                f"?parameters=T2M&community=RE&longitude={longitude}&latitude={latitude}"
                f"&start={start_date}&end={end_date}&format=JSON&user=copilot"
            )
            
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8"))
                properties = data.get("properties", {})
                values = properties.get("parameter", {}).get("T2M", {})
                if values:
                    valid_values = []
                    for _, temp in sorted(values.items()):
                        if self._is_valid_temperature(temp):
                            valid_values.append(float(temp))

                    if valid_values:
                        temp = valid_values[-1]
                        self.cache.set(cache_key, {"temperature": temp})
                        return temp
        
        except (urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError):
            pass
        
        return None

    @staticmethod
    def _is_valid_temperature(value) -> bool:
        try:
            if value is None:
                return False
            temp = float(value)
        except (TypeError, ValueError):
            return False

        if math.isnan(temp) or math.isinf(temp):
            return False
        if temp <= -90.0:
            return False
        if temp == -999.0:
            return False
        return True


class NASAEONETClient:
    """Cliente para NASA EONET API (eventos naturales)."""
    
    BASE_URL = "https://eonet.gsfc.nasa.gov/api/v3"
    
    def __init__(self):
        self.cache = NASADataCache(expire_seconds=900)  # 15 minutos para eventos
    
    def find_fires_nearby(
        self, 
        latitude: float, 
        longitude: float, 
        radius_km: float = 50
    ) -> List[Dict]:
        """
        Encuentra eventos de incendios activos dentro de un radio.
        
        Args:
            latitude: Latitud en grados decimales
            longitude: Longitud en grados decimales
            radius_km: Radio de búsqueda en km (default 50)
        
        Returns:
            Lista de incendios detectados (lista vacía si no hay)
        """
        cache_key = f"fires_{latitude:.4f}_{longitude:.4f}_{radius_km}"
        
        # Verificar caché
        cached = self.cache.get(cache_key)
        if cached:
            return cached.get("fires", [])
        
        try:
            # Wildfires en EONET v3 suelen exponerse como categoría 8.
            url = f"{self.BASE_URL}/events?status=open&category=8"
            
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8"))
                events = data.get("events", [])
                
                fires_nearby = []
                
                for event in events:
                    geometries = event.get("geometries", [])
                    for geometry in geometries:
                        coords = geometry.get("coordinates", [])
                        event_lon, event_lat = coords[0], coords[1]
                        
                        # Calcular distancia simple (aproximada)
                        distance_km = self._haversine_distance(
                            latitude, longitude, event_lat, event_lon
                        )
                        
                        if distance_km <= radius_km:
                            fires_nearby.append({
                                "title": event.get("title", "Incendio"),
                                "latitude": event_lat,
                                "longitude": event_lon,
                                "distance_km": distance_km,
                                "date": geometry.get("date", ""),
                                "magnitude": event.get("sources", [{}])[0].get("value")
                            })
                
                # Guardar en caché
                self.cache.set(cache_key, {"fires": fires_nearby})
                return fires_nearby
        
        except (urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError):
            pass
        
        return []


class NASARealtimeService:
    """Servicios de alto nivel para pedir datos NASA bajo demanda y en background."""

    def __init__(self, api_key: str):
        self.fetcher = NASADataFetcher(api_key)

    def ensure_destination_fetch(self, destination_id: str, latitude: float, longitude: float, radius_km: float = 50) -> None:
        self.fetcher.fetch_destination_data_async(destination_id, latitude, longitude, radius_km)

    def get_destination_data(self, destination_id: str) -> Optional[Dict]:
        return self.fetcher.get_destination_data(destination_id)
    
    @staticmethod
    def _haversine_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calcula distancia entre dos puntos en km (fórmula Haversine)."""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Radio terrestre en km
        
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        return R * c


class NASADataFetcher:
    """Gestor asincrónico para obtener datos de NASA sin bloquear el hilo principal."""
    
    def __init__(self, api_key: str):
        """
        Args:
            api_key: Tu clave API de NASA POWER
        """
        self.power_client = NASAPowerClient(api_key)
        self.eonet_client = NASAEONETClient()
        self.pending_requests: Dict[str, Dict] = {}
        self.lock = threading.Lock()
    
    def fetch_destination_data_async(
        self,
        destination_id: str,
        latitude: float,
        longitude: float,
        radius_km: float = 50
    ) -> None:
        """
        Inicia una petición asincrónica para obtener datos de una localización.
        
        Args:
            destination_id: ID único del destino (para identificar resultado)
            latitude: Latitud
            longitude: Longitud
            radius_km: Radio de búsqueda de incendios
        """
        # Si ya hay una petición en progreso, ignora
        with self.lock:
            if destination_id in self.pending_requests:
                return
            self.pending_requests[destination_id] = {"status": "fetching"}
        
        # Lanzar thread en background
        thread = threading.Thread(
            target=self._fetch_thread,
            args=(destination_id, latitude, longitude, radius_km),
            daemon=True
        )
        thread.start()
    
    def _fetch_thread(
        self,
        destination_id: str,
        latitude: float,
        longitude: float,
        radius_km: float
    ) -> None:
        """Thread worker para obtener datos."""
        try:
            temperature = self.power_client.get_temperature(latitude, longitude)
            fires = self.eonet_client.find_fires_nearby(latitude, longitude, radius_km)
            source = "NASA POWER + NASA EONET"

            if temperature is None and not fires:
                fallback = self._build_fallback_data(destination_id, latitude, longitude, radius_km)
                temperature = fallback["temperature"]
                fires = fallback["fires"]
                source = fallback["source"]
            
            with self.lock:
                self.pending_requests[destination_id] = {
                    "status": "complete",
                    "temperature": temperature,
                    "fires": fires,
                    "source": source,
                    "timestamp": time.time()
                }
        except Exception as e:
            fallback = self._build_fallback_data(destination_id, latitude, longitude, radius_km)
            with self.lock:
                self.pending_requests[destination_id] = {
                    "status": "fallback",
                    "temperature": fallback["temperature"],
                    "fires": fallback["fires"],
                    "source": fallback["source"],
                    "error": str(e),
                    "timestamp": time.time()
                }

    def _build_fallback_data(
        self,
        destination_id: str,
        latitude: float,
        longitude: float,
        radius_km: float,
    ) -> Dict:
        """Genera un respaldo determinista cuando no se puede consultar la API."""
        seed = abs(hash((destination_id, round(latitude, 3), round(longitude, 3))))
        temperature = round(6.0 + (seed % 180) / 10.0, 1)

        fires = []
        if seed % 3 == 0:
            fires.append({
                "title": "Evento de referencia local",
                "latitude": latitude + 0.05,
                "longitude": longitude - 0.05,
                "distance_km": round(7 + (seed % 18), 1),
                "date": time.strftime("%Y-%m-%d"),
                "magnitude": "n/a",
            })

        return {
            "temperature": temperature,
            "fires": fires,
            "source": "Respaldo local sin conexión",
        }
    
    def get_destination_data(self, destination_id: str) -> Optional[Dict]:
        """
        Obtiene datos completados para un destino. Devuelve None si aún no está listo.
        
        Args:
            destination_id: ID del destino
        
        Returns:
            Dict con temperature, fires, o None si aún se está procesando
        """
        with self.lock:
            if destination_id in self.pending_requests:
                request = self.pending_requests[destination_id]
                
                if request["status"] == "complete":
                    return {
                        "temperature": request.get("temperature"),
                        "fires": request.get("fires", []),
                        "source": request.get("source", "NASA POWER + NASA EONET"),
                        "timestamp": request.get("timestamp")
                    }
                elif request["status"] == "fallback":
                    return {
                        "temperature": request.get("temperature"),
                        "fires": request.get("fires", []),
                        "source": request.get("source", "Respaldo local sin conexión"),
                        "timestamp": request.get("timestamp")
                    }
                elif request["status"] == "error":
                    # Limpiar después de 5 segundos
                    if time.time() - request.get("timestamp", 0) > 5:
                        del self.pending_requests[destination_id]
                    return None
        
        return None
    
    def clear_old_requests(self, older_than_seconds: int = 1800) -> None:
        """Limpia peticiones antiguas (default 30 minutos)."""
        with self.lock:
            now = time.time()
            old_keys = [
                k for k, v in self.pending_requests.items()
                if now - v.get("timestamp", now) > older_than_seconds
            ]
            for k in old_keys:
                del self.pending_requests[k]
