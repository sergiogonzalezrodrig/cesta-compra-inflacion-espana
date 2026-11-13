# %% [markdown]
# # 01 · Limpieza del Panel de Consumo Alimentario en Hogares (MAPA)
#
# Lee los Excel anuales del MAPA (2019–2025), extrae **Total España** para la
# cesta de productos seleccionada y genera una tabla limpia para cruzar con el IPC.
#
# **Entrada:** `data/raw/mapa/mapa_hogares_<año>_c<censo>.xlsx`
# **Salida:**  `data/processed/mapa_hogares_limpio.csv`
#              `data/processed/mapa_control_cambio_base.csv`

# %%
from pathlib import Path
import re
import unicodedata
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd().parent
RAW = RAIZ / "data" / "raw" / "mapa"
PROCESSED = RAIZ / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

AÑO_SOLAPE = 2022      # año publicado en las dos bases censales
UMBRAL_ENLACE = 2.0    # % de diferencia a partir del cual se enlaza la serie

# %% [markdown]
# ## Cesta de productos
# Clave = nombre limpio que usaremos en el proyecto.
# Valor = lista de nombres posibles en el Excel (el MAPA cambia alguno entre versiones).

# %%
CESTA = {
    "Total alimentación": [".TOTAL ALIMENTACION"],
    "Huevos":             ["T.HUEVOS KGS"],
    "Leche líquida":      ["TOTAL LECHE LIQUIDA"],
    "Yogur":              ["YOGURT", "YOGUR"],  # en 2025 pasa a llamarse YOGUR
    "Queso":              ["QUESO"],
    "Aceite de oliva":    ["TOTAL ACEITES OLIVA", "TOTAL ACEITES DE OLIVA"],
    "Aceite de girasol":  ["ACEITE DE GIRASOL"],
    "Azúcar":             ["AZUCAR"],
    "Pan":                ["PAN"],
    "Arroz":              ["ARROZ"],
    "Pasta":              ["TOTAL PASTAS"],
    "Legumbres":          ["LEGUMBRES"],
    "Pollo":              ["CARNE POLLO"],
    "Cerdo":              ["CARNE CERDO"],
    "Vacuno":             ["CARNE VACUNO"],
    "Pescado":            ["TOTAL PESCA"],
    "Patatas frescas":    ["PATATAS FRESCAS"],
    "Frutas frescas":     ["T.FRUTAS FRESCAS"],
    "Plátanos":           ["PLATANOS"],
    "Hortalizas frescas": ["T.HORTALIZAS FRESCAS"],
    "Tomates":            ["TOMATES"],   # 1ª aparición = tomate fresco (la 2ª es conserva)
    "Café e infusiones":  ["CAFES E INFUSIONES"],
    "Cerveza":            ["CERVEZAS"],
    "Agua envasada":      ["AGUA DE BEBIDA ENVAS."],
}

HOJAS = {
    "VOLUMEN":        "volumen_miles_kg_l",
    "VALOR":          "valor_miles_eur",
    "PRECIO":         "precio_medio_eur_kg_l",
    "CONSUMOXCÁPITA": "consumo_pc_kg_l",
    "GASTOXCÁPITA":   "gasto_pc_eur",
    "PENETRACIÓN":    "penetracion_pct",
}
# Variables que dependen de la población estimada (las que se enlazan)
VARS_POBLACION = ["volumen_miles_kg_l", "valor_miles_eur", "consumo_pc_kg_l", "gasto_pc_eur"]

# %% [markdown]
# ## Funciones de lectura

# %%
def normalizar(texto: str) -> str:
    """'CONSUMO X CÁPITA' -> 'CONSUMOXCAPITA' (los nombres de hoja cambian entre años)."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z]", "", sin_tildes.upper())


def buscar_hoja(ruta: Path, hoja: str) -> str:
    """Encuentra el nombre real de la hoja en ese Excel."""
    for nombre in pd.ExcelFile(ruta).sheet_names:
        if normalizar(nombre) == normalizar(hoja):
            return nombre
    raise ValueError(f"{ruta.name}: no encuentro la hoja {hoja}")


def leer_hoja(ruta: Path, hoja: str) -> pd.Series:
    """Devuelve la columna T.ESPAÑA de una hoja, indexada por producto (1ª aparición)."""
    hoja = buscar_hoja(ruta, hoja)
    cabecera = pd.read_excel(ruta, sheet_name=hoja, header=None, nrows=3)
    assert str(cabecera.iloc[2, 1]).strip() == "T.ESPAÑA", f"{ruta.name}/{hoja}: la columna B no es T.ESPAÑA"
    df = pd.read_excel(ruta, sheet_name=hoja, header=None, skiprows=3, usecols=[0, 1])
    df.columns = ["producto_mapa", "valor"]
    df["producto_mapa"] = df["producto_mapa"].astype(str).str.strip()
    df = df.dropna(subset=["valor"]).drop_duplicates("producto_mapa", keep="first")
    return df.set_index("producto_mapa")["valor"]


def leer_fichero(ruta: Path) -> pd.DataFrame:
    """Extrae la cesta de un Excel del MAPA → una fila por producto y una columna por variable."""
    año, censo = map(int, re.search(r"_(\d{4})_c(\d{4})", ruta.name).groups())
    series = {var: leer_hoja(ruta, hoja) for hoja, var in HOJAS.items()}
    filas = []
    for producto, alias in CESTA.items():
        nombre = next((a for a in alias if a in series["volumen_miles_kg_l"].index), None)
        if nombre is None:
            print(f"  ⚠️ {ruta.name}: no encuentro '{producto}' ({alias})")
            continue
        fila = {"anio": año, "censo": censo, "producto": producto, "producto_mapa": nombre}
        fila.update({var: s.get(nombre) for var, s in series.items()})
        filas.append(fila)
    return pd.DataFrame(filas)

# %% [markdown]
# ## Lectura de todos los ficheros

# %%
ficheros = sorted(RAW.glob("mapa_hogares_*_c*.xlsx"))
print(f"Ficheros encontrados: {len(ficheros)}")
todo = pd.concat([leer_fichero(f) for f in ficheros], ignore_index=True)
print(todo.groupby(["anio", "censo"]).size())

# %% [markdown]
# ## Control del cambio de base censal (año solapado)
# Ratio = valor en censo 2021 / valor en censo 2011 para el año 2022.

# %%
c11 = todo.query("anio == @AÑO_SOLAPE and censo == 2011").set_index("producto")
c21 = todo.query("anio == @AÑO_SOLAPE and censo == 2021").set_index("producto")
variables = list(HOJAS.values())

ratios = (c21[variables] / c11[variables])
control = ((ratios - 1) * 100).round(2).add_prefix("dif_pct_")
control.to_csv(PROCESSED / "mapa_control_cambio_base.csv", encoding="utf-8-sig")
print(control[["dif_pct_precio_medio_eur_kg_l", "dif_pct_consumo_pc_kg_l"]])

# Productos a enlazar: diferencia en consumo per cápita por encima del umbral
a_enlazar = control.index[control["dif_pct_consumo_pc_kg_l"].abs() > UMBRAL_ENLACE].tolist()
print(f"\nSe enlazan (>|{UMBRAL_ENLACE}%| en consumo per cápita): {a_enlazar}")

# %% [markdown]
# ## Construcción de la serie final
# - ≤ 2021: censo 2011 · ≥ 2022: censo 2021
# - En los productos a enlazar, los años del censo 2011 se multiplican por el ratio de 2022
#   en las variables que dependen de la población (el precio medio no se toca).

# %%
serie = todo[((todo.anio < AÑO_SOLAPE) & (todo.censo == 2011)) |
             ((todo.anio >= AÑO_SOLAPE) & (todo.censo == 2021))].copy()
serie["enlazado"] = False

if not c11.empty and not c21.empty:
    mask = (serie.censo == 2011) & serie.producto.isin(a_enlazar)
    for var in VARS_POBLACION:
        serie.loc[mask, var] = serie.loc[mask, var] * serie.loc[mask, "producto"].map(ratios[var])
    serie.loc[mask, "enlazado"] = True
else:
    print("⚠️ Falta alguna versión de 2022: no se aplica el enlace.")

serie = serie.sort_values(["producto", "anio"]).reset_index(drop=True)

# Base 2019 = 100 (para comparar con el IPC)
for var in ["precio_medio_eur_kg_l", "consumo_pc_kg_l", "gasto_pc_eur"]:
    base = serie[serie.anio == 2019].set_index("producto")[var]
    serie[f"idx_{var}"] = (serie[var] / serie.producto.map(base) * 100).round(2)

serie.to_csv(PROCESSED / "mapa_hogares_limpio.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig")
print(f"\n✅ Guardado: {PROCESSED / 'mapa_hogares_limpio.csv'}  ({len(serie)} filas)")
serie.head(10)
