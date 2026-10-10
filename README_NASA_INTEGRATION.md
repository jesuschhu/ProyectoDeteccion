# 🌍 Integración NASA POWER + EONET en Presenta

## 📦 ¿Qué se entregó?

### 1. **`nasa_integration.py`** (312 líneas)
Módulo completo con:
- ✅ **NASADataCache**: Caché temporal con expiración automática (10-15 min)
- ✅ **NASAPowerClient**: Cliente para obtener T2M (temperatura a 2m) de NASA POWER
- ✅ **NASAEONETClient**: Cliente para detectar incendios activos en radio de 50km
- ✅ **NASADataFetcher**: Gestor asincrónico con threading (NO bloquea el loop principal)

**Características clave:**
- ⚡ Threading: Las peticiones corren en background threads
- 🔄 Caché inteligente: Evita saturar API, 10 min para temperatura, 15 min para fuegos
- 🛡️ Manejo de errores: Timeouts (5 seg), excepciones controladas
- 📊 Distancia Haversine: Cálculo preciso de distancia entre coordenadas

### 2. **`data/points.json` actualizado**
Cada destino ahora tiene:
```json
{
  "id": "huascaran",
  "name": "Huascarán",
  "latitude": -9.1201,
  "longitude": -77.6107,
  ...
}
```

**Coordenadas precisas de Cordillera Blanca:**
- Huascarán: -9.1201, -77.6107 (pico más alto)
- Alpamayo: -8.9906, -77.4761 (pirámide perfecta)
- Santa Cruz: -8.8750, -77.7250 (ruta clásica)
- Laguna 69: -9.0892, -77.7028 (laguna turquesa)
- Chavín: -9.5903, -77.5881 (arqueología)

### 3. **Documentación completa**
- `INSTRUCCIONES_NASA_INTEGRATION.md`: Guía paso a paso (6 pasos)
- `NASA_INTEGRATION_SNIPPETS.md`: Código copy-paste para cada integración
- Este README: Visión general

---

## 🚀 Integración rápida (6 pasos)

### Paso 1: Agregar imports en app.py
```python
from nasa_integration import NASADataFetcher
NASA_API_KEY = "your_nasa_api_key_here"
```

### Paso 2: Inicializar en __init__
```python
self.nasa_fetcher = NASADataFetcher(NASA_API_KEY)
self.nasa_data: Dict[str, Dict] = {}
```

### Paso 3: Disparar fetch en hover (línea ~351)
```python
if self.active_point_id != hovered_id:
    self.active_point_id = hovered_id
    self.card_target_visible = True
    
    # Disparar petición asincrónica
    point_data = next((p for p in self.points if p["id"] == hovered_id), None)
    if point_data and "latitude" in point_data and "longitude" in point_data:
        self.nasa_fetcher.fetch_destination_data_async(
            destination_id=hovered_id,
            latitude=point_data["latitude"],
            longitude=point_data["longitude"],
            radius_km=50
        )
```

### Paso 4: Actualizar cache en bucle (línea ~145)
```python
if self.active_point_id:
    nasa_data = self.nasa_fetcher.get_destination_data(self.active_point_id)
    if nasa_data:
        self.nasa_data[self.active_point_id] = nasa_data
```

### Paso 5: Renderizar en Card (línea ~1130)
```python
# Obtener datos NASA
nasa_temp = None
fires_count = 0
if point["id"] in self.nasa_data:
    nasa_info = self.nasa_data[point["id"]]
    nasa_temp = nasa_info.get("temperature")
    fires_count = len(nasa_info.get("fires", []))

# Agregue a data_rows
if nasa_temp is not None:
    data_rows.append(("Temperatura", f"{nasa_temp:.1f}°C"))

if nasa_temp is not None:
    fire_display = f"⚠️ {fires_count} evento(s)" if fires_count > 0 else "✓ Sin fuego"
    data_rows.append(("Estado fuego", fire_display))
```

### Paso 6: (Opcional) Limpieza periódica
```python
if self.frame_count % 900 == 0:  # Cada 30 seg
    self.nasa_fetcher.clear_old_requests(older_than_seconds=1800)
```

---

## 🏗️ Arquitectura de integración

```
Presente (app.py)
├── Loop OpenCV (30+ FPS)
│   ├── Detecta mano
│   ├── Calcula puntero
│   └── Actualiza interacción
│
└── En hover (0.35 seg):
    ├── Activa destino (active_point_id)
    └── nasa_fetcher.fetch_destination_data_async()
        │
        └── Thread background (NO bloquea):
            ├── NASAPowerClient.get_temperature()
            │   └── NASA POWER API → T2M (°C)
            │
            ├── NASAEONETClient.find_fires_nearby()
            │   └── NASA EONET API → Incendios en 50km
            │
            └── Caché (10-15 min):
                ├── self.nasa_data[id]
                │
                └── Renderiza en Card:
                    ├── Temperatura: X.X°C
                    └── Estado: ✓ Sin fuego / ⚠️ N eventos
```

---

## 🔌 APIs utilizadas

### NASA POWER
- **Endpoint**: `https://power.larc.nasa.gov/api/v1/aggregated`
- **Parámetro**: `T2M` (temperatura a 2 metros)
- **Respuesta**: JSON con temperatura actual
- **Rate limit**: ~40 req/día por IP (suficiente con caché)

### NASA EONET
- **Endpoint**: `https://eonet.gsfc.nasa.gov/api/v3/events`
- **Categoría**: 7 (fuegos/quemas)
- **Estatus**: open (eventos activos)
- **Respuesta**: JSON con coordenadas de incendios

---

## ⚙️ Configuración

### Caché
```python
NASAPowerClient(api_key)      # Cache = 600 seg (10 min)
NASAEONETClient()             # Cache = 900 seg (15 min)
```

### Parámetros de búsqueda
```python
fetch_destination_data_async(
    destination_id,
    latitude,
    longitude,
    radius_km=50  # ← Modificable aquí
)
```

### Timeouts
```python
urllib.request.urlopen(url, timeout=5)  # 5 segundos
```

---

## 📊 Estructura de datos

### NASA Data Cache (self.nasa_data)
```python
{
    "huascaran": {
        "temperature": 5.3,           # Celsius
        "fires": [                    # Array de incendios cercanos
            {
                "title": "Fire Near Huaraz",
                "latitude": -9.12,
                "longitude": -77.61,
                "distance_km": 15.4,
                "date": "2024-04-28",
                "magnitude": "5.2"
            }
        ],
        "timestamp": 1714354800.123
    }
}
```

### Request Status (interno)
```python
{
    "status": "fetching" | "complete" | "error",
    "temperature": float,
    "fires": [list],
    "timestamp": float,
    "error": "str (si status=='error')"
}
```

---

## ✅ Ventajas de esta implementación

| Ventaja | Razón |
|---------|-------|
| **No bloquea FPS** | Threads separados + asyncrónico |
| **Optimizado** | Caché de 10-15 min + deduplicación |
| **Resiliente** | Timeouts, manejo de errores, fallbacks |
| **Escalable** | Limpieza automática de caché antigua |
| **Integración limpia** | Separación de concerns, módulo independiente |
| **Bajo consumo API** | ~2-3 req/destino/sesión (con caché) |

---

## 🐛 Troubleshooting

### "No aparecen datos NASA"
1. Verifica API Key en `NASA_API_KEY`
2. Comprueba que el destino tiene `latitude` y `longitude` en JSON
3. Asegúrate de que el hover dura >0.35 seg
4. Los datos toman 2-5 segundos, aguarda antes de cerrar la Card

### "La app se torna lenta"
1. Revisa que los threads se crean correctamente
2. Limpia caché antiguos cada 30 min (Paso 6 opcional)
3. Reduce `radius_km` si hay muchos incendios

### "API Key inválida"
- Abre `https://api.nasa.gov/`
- Genera una nueva API Key
- Reemplaza en `NASA_API_KEY`

### "Errores de conexión"
- Verifica internet
- Los timeouts de 5 seg son normales en conexiones lentas
- Los datos se mostrarán cuando la conexión mejore

---

## 📝 Notas técnicas

- **GIL (Global Interpreter Lock)**: Python threads son seguros aquí porque las peticiones HTTP liberan el GIL
- **Distancia Haversine**: Exactitud ~1% para distancias <100km
- **UTC vs Local**: Todos los datos de NASA están en UTC, la Card muestra hora local
- **Precision float**: Coordenadas con 4 decimales = ~10 metros de precisión

---

## 🎯 Próximos pasos opcionales

1. **Guardar histórico**: Almacenar temperaturas diarias en CSV/SQLite
2. **Predicción**: Integrar forecast de NASA MERRA2
3. **Alertas**: Push notification si hay incendios cerca
4. **Exportar**: Generar reportes PDF con datos climáticos por destino
5. **WebSocket**: Actualizar datos en tiempo real con conexión persistente

---

## 📄 Licencia y créditos

- **NASA POWER**: https://power.larc.nasa.gov/
- **NASA EONET**: https://eonet.gsfc.nasa.gov/
- **Coordenadas**: OpenStreetMap / Google Maps

---

**¡Listo! Tu explorador gestual ahora tiene datos climáticos en tiempo real. 🚀**
