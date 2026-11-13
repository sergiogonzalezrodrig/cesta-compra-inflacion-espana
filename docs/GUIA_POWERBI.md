# Guía del dashboard en Power BI

Objetivo: 3 páginas (Resumen · Matriz precio × consumo · Detalle por producto) a partir de los CSV de `data/processed/`.

---

## Paso 0 · Configuración previa (¡importante!)

Los CSV usan **coma decimal** y **punto y coma** como separador. Para que Power BI lea bien los números:

1. **Archivo → Opciones y configuración → Opciones**
2. *Archivo actual → Configuración regional* → **Español (España)**
3. *Archivo actual → Carga de datos* → desmarca **Fecha y hora automáticas** (no tenemos fechas, solo años)
4. **Diseño → Importar tema** → selecciona `powerbi/tema_cesta.json` (en versiones antiguas de Power BI: *Ver → Temas ▾ → Examinar temas*)

---

## Paso 1 · Cargar los datos

**Inicio → Obtener datos → Texto/CSV** y carga estos 3 ficheros:

| Fichero | Para qué |
|---|---|
| `data/processed/kpis_cuadrantes.csv` | Cuadrantes y variaciones (2020–2025) |
| `data/processed/cesta_final.csv` | Evolución año a año (2019–2025) para las líneas |
| `data/dim_producto.csv` | Familia de cada producto |

En la ventana de vista previa comprueba:
- **Origen del archivo:** `65001: Unicode (UTF-8)` → si no, las tildes salen mal.
- **Delimitador:** `Punto y coma`.

Pulsa **Transformar datos** y revisa en Power Query que las columnas numéricas (`var_precio_pct`, `idx_ipc`…) salen como **número decimal** (icono 1.2) y no como texto (ABC). Si alguna sale como texto: clic derecho → *Cambiar tipo → Usar configuración regional* → Número decimal · Español (España).

Renombra las tablas a `kpis`, `cesta` y `dim_producto`. **Cerrar y aplicar.**

---

## Paso 2 · Modelo de datos

### Tabla de años
**Modelado → Nueva tabla:**
```dax
dim_anio = DISTINCT ( cesta[anio] )
```

### Relaciones (vista Modelo)
| Desde | Hacia | Cardinalidad |
|---|---|---|
| `dim_producto[producto]` | `kpis[producto]` | 1 a varios |
| `dim_producto[producto]` | `cesta[producto]` | 1 a varios |
| `dim_anio[anio]` | `kpis[anio]` | 1 a varios |
| `dim_anio[anio]` | `cesta[anio]` | 1 a varios |

> Usa **siempre** `dim_producto[producto]` y `dim_anio[anio]` en segmentadores y ejes. Así filtran las dos tablas a la vez.

Oculta en las tablas de hechos (clic derecho → *Ocultar en la vista de informes*) las columnas `producto` y `anio` de `kpis` y `cesta`, para no usarlas por error.

### Ordenar familias
Selecciona `dim_producto[familia]` → *Herramientas de columnas → Ordenar por columna* → `orden_familia`.

---

## Paso 3 · Medidas DAX

Crea una tabla vacía para guardarlas: **Inicio → Especificar datos** → llámala `_Medidas` → Cargar. Crea cada medida con **Nueva medida** dentro de esa tabla.

> Las variaciones del CSV vienen en puntos (69 = 69%). Las medidas las dividen entre 100 para poder darles **formato de porcentaje**.

```dax
Var precio % = DIVIDE ( AVERAGE ( kpis[var_precio_pct] ), 100 )

Var consumo % = DIVIDE ( AVERAGE ( kpis[var_consumo_pct] ), 100 )

Var gasto % = DIVIDE ( AVERAGE ( kpis[var_gasto_pct] ), 100 )

Brecha trading down = AVERAGE ( kpis[brecha_trading_down] )

Umbral precio = DIVIDE ( AVERAGE ( kpis[umbral_precio_pct] ), 100 )

Umbral consumo = DIVIDE ( AVERAGE ( kpis[umbral_consumo_pct] ), 100 )
```

**Tarjetas de la página de resumen** (Total alimentación):
```dax
Inflación alimentaria pagada =
VAR _anio = MAX ( dim_anio[anio] )
RETURN
    CALCULATE (
        DIVIDE ( AVERAGE ( cesta[idx_precio_pagado] ), 100 ) - 1,
        dim_producto[producto] = "Total alimentación",
        dim_anio[anio] = _anio
    )

Var consumo total =
VAR _anio = MAX ( dim_anio[anio] )
RETURN
    CALCULATE (
        DIVIDE ( AVERAGE ( cesta[idx_consumo_pc] ), 100 ) - 1,
        dim_producto[producto] = "Total alimentación",
        dim_anio[anio] = _anio
    )

Producto que más sube =
MAXX (
    TOPN ( 1, FILTER ( VALUES ( dim_producto[producto] ), NOT ISBLANK ( [Var precio %] ) ), [Var precio %], DESC ),
    dim_producto[producto]
)

Producto que más cae =
MAXX (
    TOPN ( 1, FILTER ( VALUES ( dim_producto[producto] ), NOT ISBLANK ( [Var consumo %] ) ), [Var consumo %], ASC ),
    dim_producto[producto]
)

Nº imprescindibles = CALCULATE ( COUNTROWS ( kpis ), kpis[cuadrante] = "Imprescindible" )
Nº recortados      = CALCULATE ( COUNTROWS ( kpis ), kpis[cuadrante] = "Recortado" )
```

**Para la página de detalle** (índices 2019 = 100):
```dax
Índice IPC = AVERAGE ( cesta[idx_ipc] )
Índice precio pagado = AVERAGE ( cesta[idx_precio_pagado] )
Índice consumo = AVERAGE ( cesta[idx_consumo_pc] )
Cuadrante = SELECTEDVALUE ( kpis[cuadrante], "—" )
Trading down = SELECTEDVALUE ( kpis[trading_down], "—" )
Año pico precio = SELECTEDVALUE ( kpis[anio_pico_precio] )
Nota ajuste = SELECTEDVALUE ( cesta[nota], "" )
```

**Formato:** selecciona cada medida que acaba en `%` (y los umbrales y las dos tarjetas) → *Herramientas de medición* → **Porcentaje**, 1 decimal.

---

## Paso 4 · Páginas

### Colores de los cuadrantes (úsalos siempre igual)
| Cuadrante | Color |
|---|---|
| 🔵 Imprescindible | `#2563EB` |
| 🔴 Recortado | `#DC2626` |
| 🟢 Resiliente | `#16A34A` |
| 🟡 En declive | `#D97706` |

---

### Página 1 · Resumen

**Título** (cuadro de texto): *¿Qué dejamos de comprar cuando sube el precio?* · subtítulo: *Cesta de la compra en España, 2019 = 100*

| Visual | Configuración |
|---|---|
| **Segmentador** | `dim_anio[anio]` · estilo *Mosaico* · selección única · valor por defecto **2025** · quita 2019 con el filtro del visual (`anio` > 2019) |
| **4 tarjetas** | `Inflación alimentaria pagada` · `Var consumo total` · `Producto que más sube` · `Producto que más cae` |
| **Gráfico de barras horizontales** | Eje Y: `dim_producto[producto]` · Eje X: `Var precio %` · Leyenda: `kpis[cuadrante]` · ordenado de mayor a menor · filtro: quitar *Total alimentación* |
| **Gráfico de anillos** (opcional) | Leyenda: `kpis[cuadrante]` · Valores: recuento de `kpis[producto]` |

Asigna los colores de los cuadrantes en *Formato → Barras / Sectores*.

---

### Página 2 · Matriz precio × consumo ⭐ (la imagen del post)

| Elemento | Configuración |
|---|---|
| **Gráfico de dispersión** | Valores: `dim_producto[producto]` · Eje X: `Var precio %` · Eje Y: `Var consumo %` · Leyenda: `kpis[cuadrante]` · Tamaño (opcional): `Var gasto %` |
| **Etiquetas** | *Formato → Etiquetas de categoría* → **Activado** (para ver el nombre de cada producto) |
| **Línea vertical** | Panel *Análisis* (lupa) → **Línea X constante** → valor `fx` → medida `Umbral precio` · discontinua, gris |
| **Línea horizontal** | **Línea Y constante** → `fx` → `Umbral consumo` · discontinua, gris |
| **Segmentador** | `dim_anio[anio]` (sincronízalo con la página 1: *Ver → Sincronizar segmentaciones*) |
| **Etiquetas de cuadrante** | 4 cuadros de texto en las esquinas: *Imprescindible* (arriba-dcha), *Recortado* (abajo-dcha), *Resiliente* (arriba-izq), *En declive* (abajo-izq) |

**Información sobre herramientas** (tooltip): arrastra `Brecha trading down`, `Trading down` y `kpis[caso_frontera]` al campo *Información sobre herramientas*.

> 💡 Si los nombres se solapan, filtra con un segmentador de `dim_producto[familia]`: con *Proteínas* se ve perfecta la historia de la sustitución de carne.

---

### Página 3 · Detalle por producto

| Visual | Configuración |
|---|---|
| **Segmentador** | `dim_producto[producto]` · lista desplegable · selección única |
| **Gráfico de líneas** | Eje X: `dim_anio[anio]` · Valores: `Índice IPC`, `Índice precio pagado`, `Índice consumo` · panel *Análisis* → línea Y constante en **100** (año base) |
| **Tarjetas** | `Cuadrante` · `Trading down` · `Año pico precio` (filtra estas tarjetas a 2025 con el panel de filtros) |
| **Cuadro de texto** | `Nota ajuste` en una tarjeta pequeña para avisar si el cruce con el IPC es aproximado |
| **Tabla** | `dim_anio[anio]`, `Índice IPC`, `Índice precio pagado`, `Índice consumo`, `Brecha trading down` |

> 💡 Ejemplos para probar: **Pan** (las líneas de IPC y precio pagado se separan → trading down) y **Aceite de oliva** (pico en 2024).

---

## Paso 5 · Guardar y capturas

1. Guarda como `powerbi/cesta_compra_ipc.pbix`.
2. Exporta cada página en imagen (*Archivo → Exportar → PDF* o captura con Win + Shift + S) y guárdalas en `docs/img/`:
   - `01_resumen.png`
   - `02_matriz.png` ← la del post
   - `03_detalle_pan.png`
3. Esas imágenes son las que irán en el README de GitHub y en LinkedIn.
