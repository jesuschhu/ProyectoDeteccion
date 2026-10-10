# Integración NASA POWER + EONET en Presenta

## 📋 PASO 1: Agregar import en app.py (línea 14)

```python
from nasa_integration import NASADataFetcher

# Tu API Key (reemplaza con la tuya)
NASA_API_KEY = "your_nasa_api_key_here"
```

---

## 📋 PASO 2: Inicializar en __init__ (alrededor de línea 120)

En el método `__init__` de `GestureMapApp`, después de `self.font_welcome_button`, agrega:

```python
        # Integración NASA
        self.nasa_fetcher = NASADataFetcher(NASA_API_KEY)
        self.nasa_data: Dict[str, Dict] = {}  # Cache local de datos NASA
```

---

## 📋 PASO 3: Disparar petición asincrónica en hover (línea 351-354)

En el método `_update_interaction_logic`, donde se detecta que un punto ha estado en hover durante `HOVER_TIME_SEC`, agrega la llamada:

```python
        if hovered_id and (now - self.hover_start) >= HOVER_TIME_SEC:
            if self.active_point_id != hovered_id:
                self.active_point_id = hovered_id
                self.card_target_visible = True
                
                # ⭐ DISPARAR PETICIÓN ASINCRÓNICA
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

## 📋 PASO 4: Obtener datos en el bucle principal (línea 145)

En el método `run()`, después de `self._update_interaction_logic(now, dt)`, agrega:

```python
            self._update_interaction_logic(now, dt)
            
            # ⭐ ACTUALIZAR CACHE DE DATOS NASA
            if self.active_point_id:
                nasa_data = self.nasa_fetcher.get_destination_data(self.active_point_id)
                if nasa_data:
                    self.nasa_data[self.active_point_id] = nasa_data
```

---

## 📋 PASO 5: Renderizar datos NASA en la Card (línea 1130-1145)

En el método que renderiza la Card (alrededor de `data_rows = [`), **antes de ese código**, agrega:

```python
        # ⭐ Obtener datos NASA si están disponibles
        nasa_temp = None
        fires_count = 0
        if point["id"] in self.nasa_data:
            nasa_info = self.nasa_data[point["id"]]
            nasa_temp = nasa_info.get("temperature")
            fires_count = len(nasa_info.get("fires", []))
        
        # Filas de datos con información NASA integrada
        data_rows = [
            ("Altitud", f"{point['altitude_m']} msnm"),
            ("Duración", str(point.get("duration", ""))),
            ("Mejor época", str(point.get("best_season", ""))),
            ("Dificultad", str(point.get("difficulty", ""))),
        ]
        
        # ⭐ Agregar datos NASA si disponibles
        if nasa_temp is not None:
            temp_display = f"{nasa_temp:.1f}°C"
            data_rows.append(("Temperatura (NASA)", temp_display))
        
        if fires_count > 0:
            fire_status = f"⚠️ {fires_count} evento(s)"
            data_rows.append(("Estado de fuego", fire_status))
        elif nasa_temp is not None:  # Solo mostrar si tenemos datos NASA
            data_rows.append(("Estado de fuego", "✓ Sin incendios"))
```

---

## 📋 PASO 6: Limpieza de caché (linea 160)

En el método `run()`, dentro del bucle principal, puedes agregar (cada 30 segundos aproximadamente):

```python
            # ⭐ Limpieza periódica (cada frame, pero con check de tiempo)
            if self.frame_count % 900 == 0:  # ~30 seg a 30 FPS
                self.nasa_fetcher.clear_old_requests(older_than_seconds=1800)
```

---

## 🎨 Personalización CSS/Colores (Opcional)

Para que los datos NASA se destaquen, puedes modificar los colores en la Card:

```python
# En la sección de colores (línea ~48)
FIRE_WARNING_COLOR = (0, 0, 255)      # Rojo en BGR
FIRE_SAFE_COLOR = (0, 200, 100)       # Verde en BGR
TEMP_COLOR = (100, 150, 255)          # Naranja en BGR
```

Luego usarlos en la sección de renderizado:

```python
        if fires_count > 0:
            fire_status = f"⚠️ {fires_count} evento(s)"
            color = FIRE_WARNING_COLOR  # Rojo
        else:
            fire_status = "✓ Sin incendios"
            color = FIRE_SAFE_COLOR    # Verde
        
        data_rows.append(("Estado de fuego", fire_status))
        # Necesitarías modificar el loop de renderizado para usar estos colores
```

---

## 🔑 Verificación

1. **Comprueba que requirements.txt tenga todo** (no necesita cambios, usa urllib que es built-in)
2. **Prueba el flujo:**
   - Abre la app
   - Pasa sobre un destino (0.35 segundos de hover)
   - Verifica que aparezca temperatura y estado de fuegos en la Card
   - Los datos se actualizan cada 10-15 minutos (caché)

---

## ⚠️ Notas importantes

- **API Key**: Asegúrate de usar la correcta
- **Rate limiting**: NASA POWER permite ~40 requests/día por IP. Con caché de 10 min, es más que suficiente
- **No bloquea**: Todo corre en threads, la cámara sigue fluidez
- **Timeout**: 5 segundos por petición, si falla vuelve a intentar en el siguiente hover

---

## 🐛 Debugging

Si algo no funciona, agrega prints temporales en `nasa_integration.py`:

```python
# En _fetch_thread
print(f"[NASA] Fetching {destination_id}: T={temperature}°C, Fires={len(fires)}")

# En get_destination_data
print(f"[NASA] Status for {destination_id}: {request['status']}")
```
