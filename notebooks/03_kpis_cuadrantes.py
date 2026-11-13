# %% [markdown]
# # 03 · KPIs y clasificación de productos en cuadrantes
#
# **Entrada:** `data/processed/cesta_final.csv` (salida del script 02)
# **Salida:**  `data/processed/kpis_cuadrantes.csv` ← una fila por producto y año (vs 2019)
#
# Cada producto se sitúa en una matriz 2×2:
# - **Eje X – subida de precio:** ¿ha subido más o menos que la mediana de la cesta?
# - **Eje Y – evolución del consumo:** ¿ha aguantado mejor o peor que el total de la alimentación?
#
# |                         | Precio sube menos | Precio sube más |
# |-------------------------|-------------------|-----------------|
# | **Consumo aguanta**     | Resiliente        | Imprescindible  |
# | **Consumo cae más**     | En declive        | Recortado       |

# %%
from pathlib import Path
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
PROCESSED = RAIZ / "data" / "processed"
REFERENCIA = "Total alimentación"

cesta = pd.read_csv(PROCESSED / "cesta_final.csv", sep=";", decimal=",")
cesta = cesta[cesta.anio > 2019].copy()

# %% [markdown]
# ## 1. Variaciones respecto a 2019 (en %)
# **Precio de referencia:** IPC si el cruce es exacto o aproximado; precio pagado (MAPA)
# si es agregado, porque ahí el IPC mide una categoría más amplia que el producto.

# %%
usa_ipc = cesta.ajuste.isin(["exacto", "aproximado"])
cesta["fuente_precio"] = np.where(usa_ipc, "IPC", "Precio pagado MAPA")
cesta["var_precio_pct"] = np.where(usa_ipc, cesta.idx_ipc, cesta.idx_precio_pagado) - 100
es_ref = cesta.producto == REFERENCIA   # su IPC es el Índice general, no el de alimentos
cesta.loc[es_ref, "var_precio_pct"] = cesta.loc[es_ref, "idx_precio_pagado"] - 100
cesta.loc[es_ref, "fuente_precio"] = "Precio pagado MAPA"

cesta["var_consumo_pct"] = cesta.idx_consumo_pc - 100
cesta["var_gasto_pct"] = cesta.idx_gasto_pc - 100
cesta["var_ipc_pct"] = cesta.idx_ipc - 100
cesta["var_precio_pagado_pct"] = cesta.idx_precio_pagado - 100

# Sensibilidad aproximada: cuántos puntos cae el consumo por cada punto que sube el precio
# (descriptiva, no es una elasticidad causal)
cesta["sensibilidad"] = (cesta.var_consumo_pct / cesta.var_precio_pct).where(cesta.var_precio_pct > 1)

# %% [markdown]
# ## 2. Umbrales de los cuadrantes (se calculan para cada año)
# - Precio: mediana de la subida de precio de la cesta.
# - Consumo: evolución del consumo de **Total alimentación**. Así se descuenta el efecto
#   general (p. ej. que tras el COVID se come menos en casa) y se mide el comportamiento
#   *relativo* de cada producto.

# %%
productos = cesta[cesta.producto != REFERENCIA]
umbral_precio = productos.groupby("anio").var_precio_pct.median().rename("umbral_precio_pct")
umbral_consumo = (cesta[cesta.producto == REFERENCIA].set_index("anio").var_consumo_pct
                  .rename("umbral_consumo_pct"))

kpis = (productos.merge(umbral_precio, on="anio").merge(umbral_consumo, on="anio"))
kpis["consumo_relativo_pct"] = (kpis.var_consumo_pct - kpis.umbral_consumo_pct).round(2)

precio_alto = kpis.var_precio_pct > kpis.umbral_precio_pct
consumo_aguanta = kpis.var_consumo_pct >= kpis.umbral_consumo_pct
kpis["cuadrante"] = np.select(
    [precio_alto & consumo_aguanta, precio_alto & ~consumo_aguanta,
     ~precio_alto & consumo_aguanta, ~precio_alto & ~consumo_aguanta],
    ["Imprescindible", "Recortado", "Resiliente", "En declive"], default="Sin clasificar")

# Casos frontera: a menos de 2 puntos de algún umbral (su cuadrante es poco robusto)
MARGEN_FRONTERA = 2.0
kpis["caso_frontera"] = ((kpis.var_precio_pct - kpis.umbral_precio_pct).abs() < MARGEN_FRONTERA) | \
                        ((kpis.var_consumo_pct - kpis.umbral_consumo_pct).abs() < MARGEN_FRONTERA)

# ¿Los hogares buscan alternativas más baratas? (solo fiable en cruces exactos/aproximados)
kpis["trading_down"] = np.select(
    [~kpis.ajuste.isin(["exacto", "aproximado"]), kpis.brecha_trading_down <= -10,
     kpis.brecha_trading_down <= -5],
    ["No evaluable", "Fuerte", "Moderado"], default="Bajo")

# %% [markdown]
# ## 3. Pico de precio (año en que el producto fue más caro)

# %%
pico = (kpis.loc[kpis.groupby("producto").var_precio_pct.idxmax(), ["producto", "anio", "var_precio_pct"]]
        .rename(columns={"anio": "anio_pico_precio", "var_precio_pct": "var_precio_pico_pct"}))
kpis = kpis.merge(pico, on="producto")

# %%
columnas = ["producto", "anio", "ajuste", "fuente_precio", "var_precio_pct", "var_ipc_pct",
            "var_precio_pagado_pct", "var_consumo_pct", "consumo_relativo_pct", "var_gasto_pct",
            "brecha_trading_down", "sensibilidad", "umbral_precio_pct", "umbral_consumo_pct",
            "cuadrante", "caso_frontera", "trading_down", "anio_pico_precio", "var_precio_pico_pct"]
kpis = kpis[columnas].round(2).sort_values(["anio", "cuadrante", "var_precio_pct"], ascending=[True, True, False])
kpis.to_csv(PROCESSED / "kpis_cuadrantes.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig")
print(f"✅ Guardado: {PROCESSED / 'kpis_cuadrantes.csv'}  ({len(kpis)} filas)")

# %% [markdown]
# ## 4. Resultado 2025 vs 2019

# %%
ultimo = kpis[kpis.anio == kpis.anio.max()]
print(f"\nUmbrales {ultimo.anio.iloc[0]}: precio > {ultimo.umbral_precio_pct.iloc[0]:.1f}% · "
      f"consumo ≥ {ultimo.umbral_consumo_pct.iloc[0]:.1f}% (Total alimentación)\n")
for cuadrante, grupo in ultimo.groupby("cuadrante"):
    print(f"── {cuadrante.upper()} ──")
    print(grupo[["producto", "var_precio_pct", "var_consumo_pct", "brecha_trading_down", "trading_down", "caso_frontera"]]
          .to_string(index=False), "\n")
