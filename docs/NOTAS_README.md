# Notas para el README · Proyecto inflación y cesta de la compra

> Cuaderno de decisiones. Se va completando durante el proyecto y al final se convierte en el README.

## Pregunta de negocio
¿Qué productos de la cesta son **imprescindibles** (se siguen comprando aunque suban) y cuáles se **sustituyen o recortan** cuando sube el precio? Periodo 2019–2025 (2019 = año base previo a la inflación).

## Fuentes de datos

### 1. IPC por subclases — INE
- Tabla: *Índices nacionales de subclases. Anual* (ID 76147), clasificación **ECOICOP ver. 2**.
- Selección: subclases del grupo 01 (alimentos y bebidas no alcohólicas) + Índice general · Tipo de dato: **Media anual** · Periodo 2019–2025.
- Descarga: CSV separado por `;` → `data/raw/ine/ine_ipc_subclases_anual.csv`.
- Lectura: `sep=';'`, `decimal=','` y **`encoding='latin-1'`** (el INE no lo guarda en UTF-8: sin esto salen mal las tildes).
- Los índices vienen en **base 2025 = 100** → se rebasan a 2019 = 100.
- ⚠️ **Cambio de base del IPC:** dic-2025 fue el último dato en base 2021; desde ene-2026 rige la **base 2025** (de 12 a 13 grupos, 196 subclases). El INE publica índices retrospectivos para las subclases que existen en ambas bases → serie continua desde 2019.

### 2. Panel de Consumo Alimentario en Hogares — MAPA
- Web MAPA → Alimentación → Consumo y tendencias → Panel de consumo alimentario → Series anuales.
- Ficheros anuales en Excel; se usa la columna **T.ESPAÑA** de las hojas VOLUMEN, VALOR, PRECIO, CONSUMOXCÁPITA, GASTOXCÁPITA y PENETRACIÓN.
- Unidades: volumen en miles de kg/l · valor en miles de € · precio medio en €/kg o l · per cápita en kg/l y €.
- ⚠️ Desde jun-2024 el MAPA recalculó datos por cambios en el etiquetado (código de barras, QR) → usar siempre la versión más reciente de cada fichero.

## Decisiones metodológicas

### Cambio de base censal del MAPA (censo 2011 → censo 2021)
- 2019–2021 solo existen en censo 2011; 2024–2025 solo en censo 2021; **2022 y 2023 en ambas**.
- Se ha evaluado el salto con el año solapado **2022** (Total España):
  - Precio medio: diferencia mediana **+0,1%** (Total alimentación +0,9%).
  - Consumo per cápita: diferencia mediana **+0,4%** (Total alimentación +0,1%).
  - Volumen: diferencia mediana **−0,2%**.
- **Decisión:** serie encadenada → censo 2011 hasta 2021 y censo 2021 desde 2022.
- **Enlace** (coeficiente = valor c2021 / valor c2011 de 2022) para los productos con diferencia > 2% en consumo per cápita: **aceite de girasol (−3,4%), pollo (+4,0%), cerdo (+2,4%)**. Se aplica a volumen, valor y variables per cápita de 2019–2021; el precio medio no se ajusta. Detalle en `data/processed/mapa_control_cambio_base.csv`.
- Se trabaja solo con **categorías agregadas**: los subproductos muy desagregados cambian de definición entre versiones (diferencias del 10–95%; 32 productos solo en c2011 y 54 solo en c2021).
- El MAPA cambia algún nombre entre versiones (p. ej. `TOTAL ACEITES DE OLIVA` → `TOTAL ACEITES OLIVA`); el script admite alias.
- En **2025 el MAPA renombra `YOGURT` → `YOGUR`** y reorganiza sus subcategorías (varias salen a 0): se usa solo el total.
- Las hojas cambian de nombre entre años (`CONSUMO X CÁPITA`, `CONSUMOXCAPITA`, `CONSUMOXCÁPITA`…); el script las normaliza.
- Algunos nombres se repiten en el Excel (p. ej. `TOMATES` = fresco y conserva); se toma la **primera aparición** (fresco).

### Cesta seleccionada (24 productos)
Total alimentación, huevos, leche líquida, yogur, queso, aceite de oliva, aceite de girasol, azúcar, pan, arroz, pasta, legumbres, pollo, cerdo, vacuno, pescado, patatas frescas, frutas frescas, plátanos, hortalizas frescas, tomates, café e infusiones, cerveza, agua envasada.

### Cruce MAPA ↔ IPC (`data/mapeo_mapa_ipc.csv`)
- La ECOICOP ver. 2 es **menos detallada** que el MAPA: no separa pollo/cerdo/vacuno (todo "Carne fresca"), aceite de oliva/girasol ("Aceites vegetales"), arroz ("Cereales"), plátanos ("Frutas tropicales") ni tomates ("Hortalizas cultivadas por su fruto").
- Cada cruce se etiqueta: **exacto** (10), **aproximado** (6, media simple de varias subclases o cobertura distinta), **agregado** (8, el IPC es una categoría más amplia) y **referencia** (Total alimentación vs Índice general).
- Subclases del IPC sin dato en algún año, no usadas: 01.1.4.3, 01.1.4.4, 01.2.9.0, 02.1.9.0.

### Dos medidas de precio (ángulo original del proyecto)
- **IPC** = variación del precio "puro" (mismo producto, misma calidad).
- **Precio medio pagado (MAPA)** = lo que realmente pagan los hogares; incluye el cambio de formato, marca o establecimiento.
- **Brecha trading down** = idx_precio_pagado − idx_ipc. Negativa → los hogares se pasan a opciones más baratas (marca blanca, formatos grandes, súper de descuento). Sustituye al análisis de marca blanca que no se podía hacer con datos abiertos.
- La brecha solo es fiable en cruces **exactos/aproximados**; en los agregados (p. ej. vacuno vs carne fresca) refleja sobre todo diferencias entre productos.

### Primeros hallazgos (2025 vs 2019, cruces exactos)
- Pan: IPC +32%, precio pagado +11% → brecha −21 (fuerte trading down).
- Agua envasada: IPC +33%, pagado +13% → brecha −20.
- Huevos: IPC +69%, consumo +11% → imprescindible.
- Azúcar: IPC +42%, consumo −25% → recorte claro.

### Cuadrantes (`notebooks/03_kpis_cuadrantes.py`)
- Umbral de precio = **mediana** de la subida de la cesta en cada año (2025: +39,7%).
- Umbral de consumo = evolución de **Total alimentación** en cada año (2025: −7,1%) → mide el comportamiento *relativo* y descuenta el efecto post-COVID de comer menos en casa.
- Precio de referencia: IPC en cruces exactos/aproximados; precio pagado MAPA en agregados.
- **Casos frontera** (< 2 puntos de un umbral) marcados en `caso_frontera`: tomates, queso y yogur en 2025.
- Los umbrales son relativos: "Resiliente" o "En declive" no significa que el precio no haya subido (todos suben entre un 17% y un 69%).
- Los cuadrantes cambian año a año (p. ej. el aceite de oliva pasa de Imprescindible en 2022 a Recortado en 2023–2025): conviene enseñarlo con un segmentador de año en Power BI.

## Limitaciones (para mencionar en el README)
- La "sensibilidad" (Δ% volumen / Δ% precio) es una **aproximación descriptiva, no una elasticidad causal**: también influyen renta, hábitos post-COVID, consumo fuera del hogar, etc.
- El panel MAPA mide **consumo en el hogar**; no incluye hostelería.
- Marca blanca: sin datos abiertos detallados → se cita como contexto (informes públicos), no como análisis propio.

- **Efecto COVID:** en 2020 el consumo en el hogar se dispara (+11% total alimentación) por el confinamiento. Comparar siempre contra 2019 y tenerlo en cuenta al interpretar 2020–2021.

## Primeros datos (consumo per cápita y precio medio MAPA, 2019 = 100, año 2025)
- Total alimentación: precio 134 · consumo 93
- Aceite de oliva: precio pico 248 en 2024 → 149 en 2025; consumo mínimo 73 en 2024
- Huevos: precio 165 · consumo 111 (sube precio y sube consumo)
- Vacuno: precio 148 · consumo 78 · Pescado: precio 134 · consumo 79

## Pendiente
- [x] Descargar los Excel del MAPA 2019–2025 y el CSV del IPC
- [x] Script de limpieza del MAPA (`notebooks/01_limpieza_mapa.py`)
- [x] Script de limpieza del IPC y unión (`notebooks/02_ipc_y_union.py`)
- [x] Tabla de mapeo producto MAPA ↔ subclase IPC
- [x] Cálculo de KPIs y cuadrantes (`notebooks/03_kpis_cuadrantes.py`)
- [ ] Dashboard Power BI (3 páginas)
- [ ] Conclusiones + propuesta de valor
- [ ] README final, GitHub y post de LinkedIn
