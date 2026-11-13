# %% [markdown]
# # 02 · Limpieza del IPC (INE) y unión con el MAPA
#
# **Entrada:** `data/raw/ine/ine_ipc_subclases_anual.csv`
#              `data/mapeo_mapa_ipc.csv`
#              `data/processed/mapa_hogares_limpio.csv` (salida del script 01)
# **Salida:**  `data/processed/ipc_subclases_limpio.csv`
#              `data/processed/cesta_final.csv`  ← tabla para Power BI

# %%
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
DATA = RAIZ / "data"
PROCESSED = DATA / "processed"
AÑO_BASE = 2019

# %% [markdown]
# ## 1. Limpieza del IPC
# El CSV del INE viene en latin-1, con coma decimal y en base 2025 = 100.

# %%
ipc = pd.read_csv(DATA / "raw" / "ine" / "ine_ipc_subclases_anual.csv",
                  sep=";", decimal=",", encoding="latin-1")
ipc.columns = ["subclase", "tipo_dato", "anio", "indice_base2025"]
ipc["subclase"] = ipc["subclase"].str.strip()
ipc["codigo"] = ipc["subclase"].str.extract(r"^(\d{2}\.\d\.\d\.\d)")[0].fillna("GENERAL")
ipc["nombre"] = ipc["subclase"].str.replace(r"^\d{2}\.\d\.\d\.\d\s*", "", regex=True)

# Rebase a 2019 = 100
base = ipc[ipc.anio == AÑO_BASE].set_index("codigo")["indice_base2025"]
ipc["indice_base2019"] = (ipc["indice_base2025"] / ipc["codigo"].map(base) * 100).round(2)

ipc = ipc[["codigo", "nombre", "anio", "indice_base2025", "indice_base2019"]].sort_values(["codigo", "anio"])
sin_dato = ipc[ipc.indice_base2019.isna()].codigo.unique()
print(f"Subclases: {ipc.codigo.nunique()} · sin dato en algún año (no se usan): {list(sin_dato)}")
ipc.to_csv(PROCESSED / "ipc_subclases_limpio.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig")

# %% [markdown]
# ## 2. Mapeo producto MAPA → subclase(s) IPC
# Si un producto tiene varias subclases, se usa la media simple de sus índices.

# %%
mapeo = pd.read_csv(DATA / "mapeo_mapa_ipc.csv", sep=";").fillna({"codigos_ipc": "GENERAL", "nota": ""})
mapeo["codigo"] = mapeo["codigos_ipc"].str.split("|")
mapeo_largo = mapeo.explode("codigo")

idx_ipc = (mapeo_largo.merge(ipc[["codigo", "anio", "indice_base2019"]], on="codigo", how="left")
           .groupby(["producto", "anio"], as_index=False)["indice_base2019"].mean()
           .rename(columns={"indice_base2019": "idx_ipc"}))

# %% [markdown]
# ## 3. Unión con el MAPA y métricas
# - `idx_ipc`: precio "puro" (misma calidad y formato), 2019 = 100
# - `idx_precio_pagado`: precio medio que realmente pagan los hogares (MAPA), 2019 = 100
# - `brecha_trading_down` = idx_precio_pagado − idx_ipc → si es negativa, los hogares
#   pagan menos de lo que sube el precio: se pasan a formatos o marcas más baratas.

# %%
mapa = pd.read_csv(PROCESSED / "mapa_hogares_limpio.csv", sep=";", decimal=",")
cesta = (mapa.merge(idx_ipc, on=["producto", "anio"], how="left")
             .merge(mapeo[["producto", "codigos_ipc", "ajuste", "nota"]], on="producto", how="left")
             .rename(columns={"idx_precio_medio_eur_kg_l": "idx_precio_pagado",
                              "idx_consumo_pc_kg_l": "idx_consumo_pc",
                              "idx_gasto_pc_eur": "idx_gasto_pc"}))
cesta["idx_ipc"] = cesta["idx_ipc"].round(2)
cesta["brecha_trading_down"] = (cesta["idx_precio_pagado"] - cesta["idx_ipc"]).round(2)
# Total alimentación se compara con el Índice general (no con alimentos): la brecha no tiene sentido
cesta.loc[cesta.ajuste == "referencia", "brecha_trading_down"] = None

cesta.to_csv(PROCESSED / "cesta_final.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig")
print(f"✅ Guardado: {PROCESSED / 'cesta_final.csv'}  ({len(cesta)} filas)")

# %% [markdown]
# ## 4. Vistazo rápido: 2025 frente a 2019

# %%
resumen = (cesta[cesta.anio == cesta.anio.max()]
           .set_index("producto")[["ajuste", "idx_ipc", "idx_precio_pagado", "idx_consumo_pc", "brecha_trading_down"]]
           .sort_values("idx_ipc", ascending=False))
print(resumen.to_string())
