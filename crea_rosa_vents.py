import numpy as np
import pandas as pd
import plotly.graph_objects as go
import re

# Enllaç a Dades Obertes XEMA
URL_XEMA = "https://analisi.transparenciacatalunya.cat/Medi-Ambient/Dades-meteorol-giques-de-la-XEMA/nzvn-apee/about_data"

DIRECTIONS = [
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
]
N_SECTORS = len(DIRECTIONS)
SECTOR_ANGLE = 360 / N_SECTORS  # 22.5°

PATRO = re.compile(r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})\s+([\d.]+)\s+(\d+)°")


def parse_dia(text, data):
  """Converteix el text enganxat d'un dia en un DataFrame amb direction i speed."""
  files = [(data, ini, float(v), int(d)) for ini, _, v, d in PATRO.findall(text)]
  return pd.DataFrame(files, columns=["data", "hora", "speed", "direction"])


# Intervals de velocitat en km/h (límit superior , color, etiqueta)
SPEED_BINS = [
    (5, "hsl(200, 70%, 60%)", "0–5"),
    (15, "hsl(160, 70%, 50%)", "5–15"),
    (30, "hsl(55, 80%, 50%)", "15–30"),
    (50, "hsl(30, 90%, 55%)", "30–50"),
    (np.inf, "hsl(0, 80%, 55%)", ">50"),
]
BIN_EDGES = [b[0] for b in SPEED_BINS[:-1]]
GRID_COLOR = "hsl(220, 15%, 25%)"  
MODERN_FONT = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial,'
    " sans-serif"
)


def classify(df):
  """Retorna la matriu (sectors x intervals) de comptatges i el nre. de mesures vàlides."""
  df = df[(df["direction"].notna()) & (df["speed"].notna())].copy()

  # Es desplaça mig sector perquè el N quedi centrat a 0°
  adjusted = (df["direction"] + SECTOR_ANGLE / 2) % 360
  df["sector"] = (adjusted // SECTOR_ANGLE).astype(int) % N_SECTORS

  # Interval: primer límit tal que speed <= límit
  df["bin"] = np.searchsorted(BIN_EDGES, df["speed"].to_numpy(), side="left")

  counts = (
      df.groupby(["sector", "bin"])
      .size()
      .unstack(fill_value=0)
      .reindex(
          index=range(N_SECTORS), columns=range(len(SPEED_BINS)), fill_value=0
      )
  )
  return counts.to_numpy(), len(df)


def wind_rose(df, station_name, output="rosa_vents.html"):
  counts, valid = classify(df)

  if valid == 0:
    print("No hi ha dades de vent per a este dia")
    return

  # Radi màxim: màxim % per sector arrodonit a múltiple de 5
  max_percent = counts.sum(axis=1).max() / valid * 100
  ring_max = np.ceil(max_percent / 5) * 5 or 10

  # Valors per als anells radials (25%, 50%, 75%, 100% del màxim)
  tick_fractions = (0.25, 0.5, 0.75, 1.0)
  tick_vals = [ring_max * f for f in tick_fractions]
  tick_texts = [f"{int(ring_max * f)}%" for f in tick_fractions]

  thetas = np.arange(N_SECTORS) * SECTOR_ANGLE
  fig = go.Figure()

  # Barres apilades de cada rang de velocitat
  for b, (_, color, label) in enumerate(SPEED_BINS):
    fig.add_trace(
        go.Barpolar(
            r=counts[:, b] / valid * 100,
            theta=thetas,
            width=SECTOR_ANGLE - 2,
            name=f"{label} km/h",
            marker=dict(color=color, line=dict(color="rgba(0,0,0,0.2)", width=0.5)),
            opacity=0.85,
            customdata=np.column_stack([DIRECTIONS, counts[:, b]]),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                f"{label} km/h: %{{r:.1f}}%"
                " (%{customdata[1]} mesures)<extra></extra>"
            ),
        )
    )

  
  fig.update_layout(
      font=dict(family=MODERN_FONT, color="hsl(210, 15%, 85%)"),
      title=dict(
          text=(
              f'<span style="font-size: 18px; font-weight: 600; color:'
              f' white;">{station_name}</span><br><span style="font-size: 12px;'
              ' font-weight: 400; color: hsl(210, 15%, 65%);">Rosa de vents'
              " horària i distribució de velocitats</span>"
          ),
          x=0.5,
          y=0.95,
          xanchor="center",
          yanchor="top",
      ),
      paper_bgcolor="hsl(220, 25%, 9%)",   # Fons exterior un pèl més fosc
      plot_bgcolor="hsl(220, 25%, 9%)",
      hoverlabel=dict(
          bgcolor="hsl(220, 20%, 18%)",
          bordercolor="hsl(220, 20%, 30%)",
          font=dict(family=MODERN_FONT, color="white", size=12),
      ),
      polar=dict(
          bgcolor="hsl(220, 20%, 16%)",    # Interior de la rosa una mica més clar
          barmode="stack",
          angularaxis=dict(
              direction="clockwise",
              rotation=90,
              tickmode="array",
              tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
              ticktext=[
                  "<b>N</b>",
                  "<b>NE</b>",
                  "<b>E</b>",
                  "<b>SE</b>",
                  "<b>S</b>",
                  "<b>SW</b>",
                  "<b>W</b>",
                  "<b>NW</b>",
              ],
              tickfont=dict(size=12, color="white", family=MODERN_FONT),
              gridcolor=GRID_COLOR,
              linecolor="rgba(0,0,0,0)",
          ),
          radialaxis=dict(
              range=[0, ring_max],
              tickvals=tick_vals,
              ticktext=tick_texts,  # Mostra el % en cada cercle
              angle=180,             # Escriure sobre linia 180º (W)
              tickangle=180,          # Força la lletra completament horitzontal
              gridcolor=GRID_COLOR,
              linecolor="rgba(0,0,0,0)",
              tickfont=dict(color="hsl(210, 15%, 65%)", size=10),
          ),
      ),
      legend=dict(
          orientation="h",
          x=0.5,
          xanchor="center",
          y=-0.04,
          yanchor="top",
          font=dict(size=11, color="hsl(210, 15%, 80%)"),
          bgcolor="rgba(0,0,0,0)",
      ),
      annotations=[
          dict(
              text=(
                  f'<span style="color: hsl(210, 15%, 70%);">{valid} mesures ·'
                  ' intervals de 30 min</span><br><span style="font-size: 10px;'
                  ' color: hsl(210, 15%, 50%);">Font: <a'
                  f' href="{URL_XEMA}" target="_blank" style="color:'
                  ' hsl(200, 70%, 65%); text-decoration: none;">Dades Obertes XEMA'
                  " (SMC)</a> · Autor: Albert Aparicio</span>"
              ),
              x=0.5,
              y=-0.14,
              xref="paper",
              yref="paper",
              xanchor="center",
              yanchor="top",
              showarrow=False,
              align="center",
          )
      ],
      margin=dict(t=100, b=120, l=60, r=60),
      width=600,
      height=740,
  )

  fig.write_html(output, include_plotlyjs="cdn")


if __name__ == "__main__":
# dades dies exemple extretes de Dades Obertes de la XEMA del SMC
  dia_26 = """
    00:00 - 00:30    0.7    168° SSE
    00:30 - 01:00    0.4    190° S
    01:00 - 01:30    0.7    196° SSW
    01:30 - 02:00    1.1    122° ESE
    02:00 - 02:30    1.1    128° SE
    02:30 - 03:00    0.4    102° ESE
    03:00 - 03:30    1.1    101° E
    03:30 - 04:00    0.4    138° SE
    04:00 - 04:30    0.0    146° SE
    04:30 - 05:00    0.7    144° SE
    05:00 - 05:30    0.4    240° WSW
    05:30 - 06:00    3.2    353° N
    06:00 - 06:30    4.0    354° N
    06:30 - 07:00    4.0    357° N
    07:00 - 07:30    4.3    0° N
    07:30 - 08:00    2.2    338° NNW
    08:00 - 08:30    3.2    150° SSE
    08:30 - 09:00    7.2    115° ESE
    09:00 - 09:30    9.0    125° SE
    09:30 - 10:00    10.8    177° S
    10:00 - 10:30    10.4    200° SSW
    10:30 - 11:00    10.4    203° SSW
    11:00 - 11:30    11.5    209° SSW
    11:30 - 12:00    11.2    197° SSW
    12:00 - 12:30    11.5    189° S
    12:30 - 13:00    11.9    188° S
    13:00 - 13:30    10.4    181° S
    13:30 - 14:00    12.6    186° S
    14:00 - 14:30    12.2    185° S
    14:30 - 15:00    11.5    178° S
    15:00 - 15:30    13.0    195° SSW
    15:30 - 16:00    12.2    195° SSW
    16:00 - 16:30    12.2    189° S
    16:30 - 17:00    11.2    192° SSW
    17:00 - 17:30    10.4    203° SSW
    17:30 - 18:00    11.2    212° SSW
    18:00 - 18:30    10.8    203° SSW
    18:30 - 19:00    7.9    194° SSW
    19:00 - 19:30    5.8    178° S
    19:30 - 20:00    2.2    103° ESE
    20:00 - 20:30    3.2    97° E
    20:30 - 21:00    2.2    174° S
    21:00 - 21:30    1.4    156° SSE
    21:30 - 22:00    2.5    163° SSE
    22:00 - 22:30    1.8    128° SE
    22:30 - 23:00    1.4    213° SSW
    23:00 - 23:30    0.7    178° S
    23:30 - 00:00    0.7    165° SSE
    """
  dia_27 = """
    Període km/h    Rumb
    00:00 - 00:30    18.0    339° NNW
    00:30 - 01:00    20.5    339° NNW
    01:00 - 01:30    26.3    355° N
    01:30 - 02:00    26.3    359° N
    02:00 - 02:30    24.8    358° N
    02:30 - 03:00    23.8    357° N
    03:00 - 03:30    25.6    0° N
    03:30 - 04:00    22.3    4° N
    04:00 - 04:30    27.4    3° N
    04:30 - 05:00    25.9    3° N
    05:00 - 05:30    23.0    3° N
    05:30 - 06:00    24.5    3° N
    06:00 - 06:30    25.6    2° N
    06:30 - 07:00    26.3    0° N
    07:00 - 07:30    26.3    0° N
    07:30 - 08:00    26.6    345° NNW
    08:00 - 08:30    26.6    338° NNW
    08:30 - 09:00    25.9    340° NNW
    09:00 - 09:30    27.7    349° N
    09:30 - 10:00    30.2    357° N
    10:00 - 10:30    32.4    0° N
    10:30 - 11:00    35.6    1° N
    11:00 - 11:30    33.8    3° N
    11:30 - 12:00    32.0    10° N
    12:00 - 12:30    32.0    11° N
    12:30 - 13:00    31.7    12° NNE
    13:00 - 13:30    32.4    10° N
    13:30 - 14:00    27.7    12° NNE
    14:00 - 14:30    27.4    7° N
    14:30 - 15:00    25.6    355° N
    15:00 - 15:30    26.3    359° N
    15:30 - 16:00    23.0    4° N
    16:00 - 16:30    26.6    358° N
    16:30 - 17:00    26.3    10° N
    17:00 - 17:30    25.2    9° N
    17:30 - 18:00    22.3    15° NNE
    18:00 - 18:30    22.7    15° NNE
    18:30 - 19:00    17.3    15° NNE
    19:00 - 19:30    17.6    7° N
    19:30 - 20:00    17.6    7° N
    20:00 - 20:30    15.5    2° N
    20:30 - 21:00    14.0    4° N
    21:00 - 21:30    13.7    334° NNW
    21:30 - 22:00    13.0    303° WNW
    22:00 - 22:30    13.0    333° NNW
    22:30 - 23:00    7.6    328° NNW
    23:00 - 23:30    6.1    326° NW
    23:30 - 00:00    6.5    243° WSW
    """
  dia_28 = """
    Període km/h    Rumb
    00:00 - 00:30    0.7    132° SE
    00:30 - 01:00    1.1    191° S
    01:00 - 01:30    0.4    136° SE
    01:30 - 02:00    0.4    169° S
    02:00 - 02:30    0.4    212° SSW
    02:30 - 03:00    2.2    215° SW
    03:00 - 03:30    1.4    302° WNW
    03:30 - 04:00    2.2    335° NNW
    04:00 - 04:30    2.2    240° WSW
    04:30 - 05:00    5.4    358° N
    05:00 - 05:30    6.1    3° N
    05:30 - 06:00    6.8    5° N
    06:00 - 06:30    6.1    6° N
    06:30 - 07:00    4.3    0° N
    07:00 - 07:30    6.1    0° N
    07:30 - 08:00    2.2    30° NNE
    08:00 - 08:30    3.2    99° E
    08:30 - 09:00    8.6    30° NNE
    09:00 - 09:30    8.6    78° ENE
    09:30 - 10:00    10.4    133° SE
    10:00 - 10:30    9.0    157° SSE
    10:30 - 11:00    8.6    153° SSE
    11:00 - 11:30    8.6    138° SE
    11:30 - 12:00    9.0    134° SE
    12:00 - 12:30    6.5    144° SE
    12:30 - 13:00    9.0    162° SSE
    13:00 - 13:30    11.9    202° SSW
    13:30 - 14:00    13.0    211° SSW
    14:00 - 14:30    14.8    210° SSW
    14:30 - 15:00    14.8    209° SSW
    15:00 - 15:30    18.4    206° SSW
    15:30 - 16:00    18.0    203° SSW
    16:00 - 16:30    16.2    203° SSW
    16:30 - 17:00    16.2    205° SSW
    17:00 - 17:30    16.6    202° SSW
    17:30 - 18:00    14.4    203° SSW
    18:00 - 18:30    11.9    209° SSW
    18:30 - 19:00    10.8    202° SSW
    19:00 - 19:30    1.8    186° S
    19:30 - 20:00    2.2    233° SW
    20:00 - 20:30    0.4    238° WSW
    20:30 - 21:00    1.1    189° S
    21:00 - 21:30    1.4    178° S
    21:30 - 22:00    1.1    189° S
    22:00 - 22:30    0.0    245° WSW
    22:30 - 23:00    1.1    185° S
    23:00 - 23:30    1.1    109° ESE
    23:30 - 00:00    1.4    14° NNE
    """

  df = pd.concat(
      [
          parse_dia(dia_26, "2026-03-26"),
          parse_dia(dia_27, "2026-03-27"),
          parse_dia(dia_28, "2026-03-28"),
      ],
      ignore_index=True,
  )

  # Generar la rosa global i per dies

  #wind_rose(
  #    df, "Nom estació (26–28/03/2026)", output="rosa_vents_3dies.html"
  #)

  for data, df_dia in df.groupby("data"):
    wind_rose(
        df_dia, f"Palafrugell (codi estació YP) ({data})", output=f"rosa_vents_{data}.html"
    )
