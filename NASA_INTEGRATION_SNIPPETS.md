# SNIPPETS DE INTEGRACIÓN - Copia/pega exacto

## SNIPPET 1: Imports (agregar después de línea 14)
```python
import json
import math
import time
import threading  # ← Agregar esto
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np
import qrcode
from PIL import Image, ImageDraw, ImageFont

# ⭐ AGREGAR ESTOS IMPORTS
from nasa_integration import NASADataFetcher

# ⭐ TU API KEY
NASA_API_KEY = "your_nasa_api_key_here"
```

---

## SNIPPET 2: Inicialización en __init__ (después de línea 114)
```python
        self.destination_image_cache: Dict[str, np.ndarray] = {}
        self.detail_qr_cache: Dict[str, np.ndarray] = {}
        self.detail_fallback_cache: Dict[str, np.ndarray] = {}
        
        # ⭐ INTEGRACIÓN NASA
        self.nasa_fetcher = NASADataFetcher(NASA_API_KEY)
        self.nasa_data: Dict[str, Dict] = {}  # {destination_id: {temperature, fires, timestamp}}
```

---

## SNIPPET 3: Disparar fetch en hover (reemplazar línea 351-354)
```python
        # Detectar fin de hover y activar destino
        if hovered_id and (now - self.hover_start) >= HOVER_TIME_SEC:
            if self.active_point_id != hovered_id:
                self.active_point_id = hovered_id
                self.card_target_visible = True
                
                # ⭐ DISPARAR PETICIÓN ASINCRÓNICA A NASA
                point_data = next((p for p in self.points if p["id"] == hovered_id), None)
                if point_data and "latitude" in point_data and "longitude" in point_data:
                    self.nasa_fetcher.fetch_destination_data_async(
                        destination_id=hovered_id,
                        latitude=point_data["latitude"],
                        longitude=point_data["longitude"],
                        radius_km=50
                    )
                
                btn_active_point_id = hovered_id
```

---

## SNIPPET 4: Actualizar cache en bucle principal (después de línea 144)
```python
            frame = cv2.flip(frame, 1)
            self.frame_count += 1
            now = time.time()
            dt = max(1e-3, now - self.last_frame_time)
            self.last_frame_time = now

            self._update_pointer_from_frame(frame)
            self._update_interaction_logic(now, dt)
            
            # ⭐ ACTUALIZAR CACHE LOCAL DE DATOS NASA
            if self.active_point_id:
                nasa_data = self.nasa_fetcher.get_destination_data(self.active_point_id)
                if nasa_data:
                    self.nasa_data[self.active_point_id] = nasa_data

            canvas = self._draw_scene(frame, dt)
```

---

## SNIPPET 5: Renderizar datos en Card (BUSCA línea ~1130 "data_rows = [")

**ANTES de:**
```python
        data_rows = [
            ("Altitud", f"{point['altitude_m']} msnm"),
            ("Duración", str(point.get("duration", ""))),
            ("Mejor época", str(point.get("best_season", ""))),
            ("Dificultad", str(point.get("difficulty", ""))),
        ]
```

**REEMPLAZA CON:**
```python
        # ⭐ OBTENER DATOS NASA SI ESTÁN DISPONIBLES
        nasa_temp = None
        fires_count = 0
        if point["id"] in self.nasa_data:
            nasa_info = self.nasa_data[point["id"]]
            nasa_temp = nasa_info.get("temperature")
            fires_count = len(nasa_info.get("fires", []))
        
        # Filas de datos
        data_rows = [
            ("Altitud", f"{point['altitude_m']} msnm"),
            ("Duración", str(point.get("duration", ""))),
            ("Mejor época", str(point.get("best_season", ""))),
            ("Dificultad", str(point.get("difficulty", ""))),
        ]
        
        # ⭐ AGREGAR DATOS NASA SI DISPONIBLES
        if nasa_temp is not None:
            temp_display = f"{nasa_temp:.1f}°C"
            data_rows.append(("Temperatura", temp_display))
        
        if fires_count > 0:
            fire_display = f"⚠️ {fires_count} evento(s)"
        else:
            fire_display = "✓ Sin fuego" if nasa_temp is not None else "Cargando..."
        
        if nasa_temp is not None:  # Solo mostrar si tenemos datos
            data_rows.append(("Estado fuego", fire_display))
```

---

## SNIPPET 6: Limpieza periódica (opcional, en run() después de línea 158)
```python
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
            if key in (ord("d"),):
                self.debug = not self.debug
            
            # ⭐ LIMPIEZA PERIÓDICA DE CACHÉ (cada ~30 segundos)
            if self.frame_count % 900 == 0:  # 30 FPS * 30 sec
                self.nasa_fetcher.clear_old_requests(older_than_seconds=1800)
```

---

## ✅ CHECKLIST DE INTEGRACIÓN

- [ ] Crear archivo `nasa_integration.py` (ya creado)
- [ ] Agregar import `from nasa_integration import NASADataFetcher` en app.py
- [ ] Agregar `NASA_API_KEY = "..."` en app.py
- [ ] Inicializar `self.nasa_fetcher` en `__init__`
- [ ] Inicializar `self.nasa_data = {}` en `__init__`
- [ ] Disparar fetch en línea ~351 de `_update_interaction_logic`
- [ ] Actualizar caché en línea ~145 del bucle `run()`
- [ ] Agregar datos en renderizado de Card (~línea 1130)
- [ ] (Opcional) Agregar limpieza en línea ~160

---

## 🧪 TEST RÁPIDO

Para verificar que todo funciona:

```python
# En una terminal Python
from nasa_integration import NASAPowerClient, NASAEONETClient

api_key = "your_nasa_api_key_here"
power = NASAPowerClient(api_key)
eonet = NASAEONETClient()

# Test 1: Temperatura Huascarán
temp = power.get_temperature(-9.1201, -77.6107)
print(f"Temp Huascarán: {temp}°C")

# Test 2: Incendios cerca de Huascarán
fires = eonet.find_fires_nearby(-9.1201, -77.6107, radius_km=50)
print(f"Incendios: {len(fires)}")
for fire in fires:
    print(f"  - {fire['title']}: {fire['distance_km']:.1f}km")
```

---

## 💡 OPTIMIZACIONES OPCIONALES

### 1. Mostrar indicador de "cargando"
Antes de que los datos llegen, mostrar un spinner:

```python
if point["id"] == self.active_point_id and point["id"] not in self.nasa_data:
    data_rows.append(("Estado", "⏳ Obteniendo datos NASA..."))
```

### 2. Colores dinámicos según temperatura
```python
def get_temp_color(temp):
    if temp < 0:
        return (255, 100, 0)  # Azul
    elif temp < 10:
        return (200, 150, 0)  # Verde
    else:
        return (100, 100, 255)  # Naranja
```

### 3. Alertas de incendios activadas
```python
if fires_count > 0:
    # Mostrar más detalles del incendio más cercano
    closest_fire = min(fires, key=lambda f: f['distance_km'])
    data_rows.append(("Incendio más cercano", f"{closest_fire['distance_km']:.1f}km"))
```
