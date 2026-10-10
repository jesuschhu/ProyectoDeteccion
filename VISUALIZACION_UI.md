# 🎨 VISUALIZACIÓN - Cómo se vería la Card con datos NASA

## Before (Original)

```
┌────────────────────────────────────────┐
│                                        │
│      [Foto del destino]                │
│                                        │
├────────────────────────────────────────┤
│ HUASCARÁN                        GOLD  │
│ Montaña                          GRAY  │
├────────────────────────────────────────┤
│                                        │
│ Altitud                    6768 msnm  │
│ Duración                    3-5 días  │
│ Mejor época            Mayo - sept    │
│ Dificultad                    Alta    │
│                                        │
├────────────────────────────────────────┤
│ La cumbre mas alta del Peru...         │
│                                        │
└────────────────────────────────────────┘
```

---

## After (Con datos NASA) ⭐

```
┌────────────────────────────────────────┐
│                                        │
│      [Foto del destino]                │
│                                        │
├────────────────────────────────────────┤
│ HUASCARÁN                        GOLD  │
│ Montaña                          GRAY  │
├────────────────────────────────────────┤
│                                        │
│ Altitud                    6768 msnm  │
│ Duración                    3-5 días  │
│ Mejor época            Mayo - sept    │
│ Dificultad                    Alta    │
│ Temperatura             5.3°C    ⭐ NEW
│ Estado fuego    ✓ Sin fuego      ⭐ NEW
│                                        │
├────────────────────────────────────────┤
│ La cumbre mas alta del Peru...         │
│                                        │
└────────────────────────────────────────┘
```

---

## Escenarios adicionales

### Escenario 1: Datos cargando

```
│ Temperatura             Cargando...    │ ⏳ (gris)
│ Estado fuego            ⏳ En progreso  │
```

### Escenario 2: Con incendios activos

```
│ Temperatura             12.4°C         │ 🔥 (Naranja)
│ Estado fuego      ⚠️ 2 evento(s)      │ 🔴 (Rojo)
│ Incendio cercano      21.3 km         │ (Detail adicional)
```

### Escenario 3: Zona segura, sin incendios

```
│ Temperatura              0.1°C         │ ❄️ (Azul)
│ Estado fuego      ✓ Sin incendios      │ 🟢 (Verde)
```

### Escenario 4: Error temporal (timeout)

```
│ Temperatura             N/A            │ (Gris, no se muestra)
│ Estado fuego            N/A            │ (Oculto hasta siguiente hover)
```

---

## 🎨 Variantes de color (opcionales)

Puedes modificar los colores según temperatura:

| Rango Temp | Color | Ícono | RGB |
|-----------|-------|-------|-----|
| < -5°C | Azul oscuro | ❄️ | (200, 150, 255) |
| -5 a 0°C | Azul | 🥶 | (150, 180, 255) |
| 0 a 10°C | Verde agua | 🌿 | (150, 220, 180) |
| 10 a 20°C | Verde | 🌲 | (100, 200, 100) |
| 20 a 30°C | Naranja | 🔥 | (100, 150, 255) |
| > 30°C | Rojo | 🔴 | (0, 100, 255) |

---

## 📱 Representación ASCII completa

```
╔════════════════════════════════════════╗
║         EXPLORADOR GESTUAL             ║
║        CORDILLERA BLANCA               ║
╠════════════════════════════════════════╣
║                                        ║
║  [MAPA CON PUNTOS]                     ║  
║  🗻 ← Huascarán (hover aquí)           ║
║                                        ║
╠════════════════════════════════════════╣
║                                        ║
║       CARD INFORMACIÓN DEL LUGAR       ║
║                                        ║
║  ┌──────────────────────────────────┐  ║
║  │  [Foto de la montaña]            │  ║
║  └──────────────────────────────────┘  ║
║                                        ║
║  🏔️  HUASCARÁN        ★ Montaña      ║
║  ─────────────────────────────────────  ║
║  │ Altitud      │ 6768 msnm           ║
║  │ Duración     │ 3-5 días            ║
║  │ Mejor época  │ Mayo - Septiembre   ║
║  │ Dificultad   │ Alta ⚠️             ║
║  │ Temperatura  │ 5.3°C 🌡️  ⭐ NEW   ║
║  │ Estado fuego │ ✓ Sin fuego 🟢 NEW  ║
║  ─────────────────────────────────────  ║
║  La cumbre mas alta del Peru...        ║
║                                        ║
╚════════════════════════════════════════╝
```

---

## 🔄 Diagrama de estados de la Card

```
┌─────────────────────────────┐
│  NO HOVER                   │
│  - NASA data: vacío         │
│  - Card oculta              │
│  - Filas: ninguna           │
└──────────────┬──────────────┘
               │ (Hover 0.35 seg)
               ▼
┌─────────────────────────────┐
│  HOVER ACTIVO               │
│  - nasa_fetcher.fetch()     │
│  - Status: "fetching"       │
│  - Card animando            │
│  - Filas: sin NASA datos    │
└──────────────┬──────────────┘
               │ (2-5 segundos)
               ▼
┌─────────────────────────────┐
│  DATOS LISTOS ✅            │
│  - nasa_data[id] completo  │
│  - Status: "complete"       │
│  - Card con animación       │
│  - Filas: + Temp + Fuego    │ ⭐
└─────────────────────────────┘
       │ (desplaza a otro)
       ▼
┌─────────────────────────────┐
│  NUEVO DESTINO              │
│  - NASA data: vacío         │
│  - Repite ciclo             │
└─────────────────────────────┘
```

---

## 📊 Comparación: antes vs después

### Información mostrada

| Campo | Original | Con NASA |
|-------|----------|----------|
| Foto | ✅ | ✅ |
| Nombre | ✅ | ✅ |
| Tipo | ✅ | ✅ |
| Altitud | ✅ | ✅ |
| Duración | ✅ | ✅ |
| Mejor época | ✅ | ✅ |
| Dificultad | ✅ | ✅ |
| **Temperatura** | ❌ | ✅ NEW |
| **Estado de fuegos** | ❌ | ✅ NEW |
| **Distancia a incendios** | ❌ | ✅ NEW (opcional) |
| Descripción | ✅ | ✅ |

### Campos de datos (data_rows)

**Antes:**
```python
[
    ("Altitud", "6768 msnm"),
    ("Duración", "3-5 días"),
    ("Mejor época", "Mayo a septiembre"),
    ("Dificultad", "Alta"),
]
# Total: 4 filas
```

**Después:**
```python
[
    ("Altitud", "6768 msnm"),
    ("Duración", "3-5 días"),
    ("Mejor época", "Mayo a septiembre"),
    ("Dificultad", "Alta"),
    ("Temperatura", "5.3°C"),           # ⭐ NEW
    ("Estado fuego", "✓ Sin fuego"),    # ⭐ NEW
]
# Total: 6 filas (+2)
```

---

## 🎬 Animación de Card

```
Frame 1 (t=0):
  ┌─────┐
  │ •   │  (pequeño, 94% scale)
  └─────┘

Frame 2 (t=0.5):
  ┌──────────┐
  │   •      │  (mediano, 97% scale)
  └──────────┘

Frame 3 (t=1.0):
  ┌────────────────────┐
  │      COMPLETO      │  (100% scale)
  │  CON DATOS NASA    │
  └────────────────────┘
```

---

## 🔍 Zoom: Área de datos NASA

```
Área completa del Card:
┌────────────────────────────────────────┐
│                                        │
│         [Foto]                         │
│                                        │
├────────────────────────────────────────┤
│ Título + Tipo                          │
├────────────────────────────────────────┤
│ Altitud | msnm                         │  ┐
│ Duración | Días                        │  │
│ Mejor época | Mes                      │  ├─ Datos básicos
│ Dificultad | Nivel                     │  │
│ Temperatura | °C              ⭐ NEW   │  │ ← Zona NASA
│ Estado fuego | Estado         ⭐ NEW   │  ┘
├────────────────────────────────────────┤
│ Descripción...                         │
│                                        │
└────────────────────────────────────────┘
```

---

## 💻 Ejemplo real de salida

```
=== HUASCARÁN ===
Altitud:           6768 msnm
Duración:          3-5 días
Mejor época:       Mayo a septiembre
Dificultad:        Alta
Temperatura:       5.3°C           ⭐ (obtenido de NASA POWER)
Estado fuego:      ✓ Sin fuego     ⭐ (de NASA EONET, radio 50km)
Descripción:       La cumbre mas alta del Peru...

=== ALPAMAYO ===
Altitud:           5947 msnm
Duración:          4-6 días
Mejor época:       Junio a agosto
Dificultad:        Alta
Temperatura:       8.1°C           ⭐
Estado fuego:      ⚠️ 1 evento     ⭐ (¡Alerta!)
Descripción:       Pico piramidal de fama mundial...

=== LAGUNA 69 ===
Altitud:           4604 msnm
Duración:          1 dia
Mejor época:       Mayo a septiembre
Dificultad:        Media
Temperatura:       12.4°C          ⭐
Estado fuego:      ✓ Sin fuego     ⭐
Descripción:       Caminata iconica hacia laguna turquesa...
```

---

## 📐 Layout exacto en píxeles

```
Card Width:  CARD_W = 1280 - 860 = 420 px
Card Height: ~435 px
Photo Height: 200 px

Data section:
├─ Title (x=20, y=200+20)
├─ Type (x=20, y=225)
├─ Separator line
├─ Data rows (x=20, gap=16px each)
│  └─ Label (left) | Value (right)
├─ Separator line
└─ Description

Con NASA:
  Last row adicional: (+16px height)
```

---

## ✨ Experiencia de usuario

**Timeline del usuario:**

```
t=0: Usuario mueve mano sobre Huascarán
     "Veo el destino resaltado"

t=0.35: Llega a HOVER_TIME_SEC
        "La card empieza a aparecer"

t=1.0: Card completamente visible
       "Veo: Altitud, Duración, Dificultad..."

t=2.5: ⭐ Datos NASA llegan
       "¡Ah! Ahora veo la temperatura: 5.3°C"
       "Y no hay incendios cerca, excelente"

t=5.0: Usuario ve toda la información contextual
       "Perfecta para planificar mi expedición"
```

---

**¡La integración es invisible pero muy útil! 🌍**
