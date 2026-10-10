# ⚡ QUICK START - 5 MINUTOS

## 📦 Lo que recibiste

```
✅ nasa_integration.py      (312 líneas, listo para usar)
✅ data/points.json         (actualizado con coordenadas)
✅ test_nasa.py             (script para probar)
📖 Documentación completa    (4 archivos .md)
```

---

## 🚀 TL;DR - Integración mínima

### 1️⃣ Copia nasa_integration.py a tu carpeta (ya hecho)

### 2️⃣ Abre app.py y agrega esto en línea 14:

```python
from nasa_integration import NASADataFetcher
NASA_API_KEY = "your_nasa_api_key_here"
```

### 3️⃣ En __init__ (línea ~117), agrega:

```python
self.nasa_fetcher = NASADataFetcher(NASA_API_KEY)
self.nasa_data = {}
```

### 4️⃣ En _update_interaction_logic (línea ~351), reemplaza:

```python
                if self.active_point_id != hovered_id:
                    self.active_point_id = hovered_id
                    self.card_target_visible = True
                    
                    # ⭐ AGREGAR ESTO
                    point_data = next((p for p in self.points if p["id"] == hovered_id), None)
                    if point_data and "latitude" in point_data and "longitude" in point_data:
                        self.nasa_fetcher.fetch_destination_data_async(
                            hovered_id, point_data["latitude"], point_data["longitude"], 50)
                    
                    btn_active_point_id = hovered_id
```

### 5️⃣ En run() (línea ~145), agrega después de _update_interaction_logic:

```python
            if self.active_point_id:
                nasa_data = self.nasa_fetcher.get_destination_data(self.active_point_id)
                if nasa_data:
                    self.nasa_data[self.active_point_id] = nasa_data
```

### 6️⃣ En _render_card (línea ~1130), reemplaza data_rows:

```python
        # ⭐ AGREGAR ANTES
        nasa_temp = None
        fires_count = 0
        if point["id"] in self.nasa_data:
            nasa_info = self.nasa_data[point["id"]]
            nasa_temp = nasa_info.get("temperature")
            fires_count = len(nasa_info.get("fires", []))
        
        # ⭐ ORIGINAL + NUEVAS FILAS
        data_rows = [
            ("Altitud", f"{point['altitude_m']} msnm"),
            ("Duración", str(point.get("duration", ""))),
            ("Mejor época", str(point.get("best_season", ""))),
            ("Dificultad", str(point.get("difficulty", ""))),
        ]
        
        if nasa_temp is not None:
            data_rows.append(("Temperatura", f"{nasa_temp:.1f}°C"))
            fire_status = f"⚠️ {fires_count}" if fires_count > 0 else "✓ Sin fuego"
            data_rows.append(("Estado fuego", fire_status))
```

---

## ✅ Listo para probar

```bash
# Test rápido (opcional)
python test_nasa.py

# Ejecutar app
python app.py
```

**Resultado esperado:**
1. Puntero sobre destino
2. Espera 0.35 segundos
3. Card aparece
4. **¡En 2-5 seg ve temperatura y estado de fuegos!**

---

## 📝 Archivos de referencia

Si necesitas más detalles:

| Archivo | Para qué |
|---------|----------|
| `README_NASA_INTEGRATION.md` | Guía completa + arquitectura |
| `INSTRUCCIONES_NASA_INTEGRATION.md` | Paso a paso detallado |
| `NASA_INTEGRATION_SNIPPETS.md` | Código copy-paste |
| `CHECKLIST_INTEGRACION.md` | Línea exacta de cada cambio |

---

## 🔑 API Key

Tu clave: `your_nasa_api_key_here`

(Límite: ~40 req/día con caché, totalmente suficiente)

---

## 💡 ¿Qué sucede internamente?

```
1. Hover 0.35 seg → Activa destino
2. Dispara thread background (NO bloquea)
3. Thread obtiene: T2M de NASA + Incendios de EONET
4. Datos en caché (10-15 min)
5. Next frame: Card muestra datos
6. Usuario ve todo integrado
```

---

## 🚨 Si algo falla

```python
# Test quick
import nasa_integration
print("✓ Módulo importa correctamente")

# Test API
client = nasa_integration.NASAPowerClient(API_KEY)
temp = client.get_temperature(-9.12, -77.61)
print(f"Temperatura: {temp}")  # ← Debería mostrar un número

# Si ves error, mira:
# 1. API Key correcta
# 2. Internet conectado
# 3. points.json tiene lat/lon
```

---

## 🎯 Próximos pasos (opcionales)

- Agregar colores dinámicos según temperatura
- Mostrar detalles del incendio más cercano
- Guardar histórico climático en CSV
- Generar alertas si hay incendios cerca

---

**¡Eso es todo! Tu app ahora tiene clima en tiempo real. 🌍**
