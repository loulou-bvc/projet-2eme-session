import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os

# CONFIGURATION PAGE
st.set_page_config(
    page_title="Prix Négatifs Électricité — Europe",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS
st.markdown("""
<style>
    /* Fond principal */
    .stApp { background-color: #0f1117; }

    /* KPI cards */
    .kpi-card {
        background: #1a1d2e;
        border-radius: 10px;
        padding: 18px 22px;
        border-left: 4px solid #444;
        margin-bottom: 8px;
    }
    .kpi-green  { border-left-color: #2ecc71; }
    .kpi-yellow { border-left-color: #f39c12; }
    .kpi-red    { border-left-color: #e74c3c; }

    .kpi-label  { color: #8892a4; font-size: 13px; letter-spacing: 0.05em; text-transform: uppercase; }
    .kpi-value  { color: #ffffff; font-size: 28px; font-weight: 700; margin: 4px 0 0; }
    .kpi-sub    { color: #8892a4; font-size: 12px; margin-top: 2px; }

    /* Section titles */
    .section-title {
        color: #c9d1d9;
        font-size: 18px;
        font-weight: 600;
        border-bottom: 1px solid #30363d;
        padding-bottom: 6px;
        margin: 32px 0 16px;
    }
    .section-sub {
        color: #8892a4;
        font-size: 13px;
        margin-top: -12px;
        margin-bottom: 16px;
    }

    /* Alert banners */
    .alert-red    { background:#2d1117; border:1px solid #e74c3c; border-radius:8px; padding:10px 16px; color:#f97583; }
    .alert-yellow { background:#2d2208; border:1px solid #f39c12; border-radius:8px; padding:10px 16px; color:#f0b429; }
    .alert-green  { background:#0d2a1a; border:1px solid #2ecc71; border-radius:8px; padding:10px 16px; color:#56d364; }
    .alert-text   { font-size: 13px; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #161b22; }
    .sidebar-title { color:#58a6ff; font-weight:700; font-size:15px; margin-bottom:4px; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #161b22;
        border-radius: 8px;
        padding: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #8892a4;
        border-radius: 6px;
        padding: 10px 18px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1a1d2e !important;
        color: #58a6ff !important;
    }

    /* Placeholder pour modèle ML */
    .ml-placeholder {
        background: #1a1d2e;
        border: 1px dashed #58a6ff;
        border-radius: 10px;
        padding: 30px;
        text-align: center;
        color: #8892a4;
        margin: 12px 0;
    }
    .ml-placeholder h4 { color: #58a6ff; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

# CHARGEMENT & CACHE DES DONNÉES
DATA_PATH = os.path.join(
    os.path.dirname(__file__),
    "data", "processed", "opsd_clean_focus_countries.csv"
)

@st.cache_data(show_spinner="Chargement des données OPSD…")
def load_data():
    df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = df["timestamp"].dt.date
    df["hour"] = df["timestamp"].dt.hour
    df["month_name"] = df["timestamp"].dt.strftime("%b")
    df["month_num"] = df["timestamp"].dt.month
    df["year"] = df["timestamp"].dt.year

    # Pénétration renouvelable DE (%)
    df["DE_renewable_gen"] = df["DE_wind_generation_actual"] + df["DE_solar_generation_actual"]
    df["DE_renewable_pct"] = (df["DE_renewable_gen"] / df["DE_load_actual_entsoe_transparency"] * 100).clip(0, 200)

    # Flag prix négatifs
    df["DK1_neg"] = df["DK_1_price_day_ahead"] < 0
    df["DK2_neg"] = df["DK_2_price_day_ahead"] < 0

    return df

df = load_data()

# CONSTANTES VISUELLES
COLORS = {
    "wind":    "#5b9bd5",
    "solar":   "#ffd166",
    "load":    "#a29bfe",
    "price":   "#fd7f6f",
    "neg":     "#e74c3c",
    "pos":     "#2ecc71",
    "neutral": "#636e72",
    "dk1":     "#fd7f6f",
    "dk2":     "#4ecdc4",
    "fr":      "#a29bfe",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#0f1117",
    plot_bgcolor="#161b22",
    font=dict(color="#c9d1d9", size=12),
    xaxis=dict(gridcolor="#21262d", zerolinecolor="#30363d"),
    yaxis=dict(gridcolor="#21262d", zerolinecolor="#30363d"),
    legend=dict(bgcolor="#1a1d2e", bordercolor="#30363d", borderwidth=1),
    margin=dict(l=50, r=30, t=40, b=40),
)

# SIDEBAR — FILTRES GLOBAUX
with st.sidebar:
    st.markdown('<div class="sidebar-title">Filtres du Dashboard</div>', unsafe_allow_html=True)
    st.caption("Prix Négatifs d'Électricité — Europe (2015–2020)")
    st.divider()

    # Plage d'années
    year_min, year_max = int(df["year"].min()), int(df["year"].max())
    year_range = st.slider(
        "Plage d'années",
        min_value=year_min, max_value=year_max,
        value=(year_min, year_max),
        help="Restreindre l'analyse à une période donnée"
    )

    # Saison / mois
    MONTHS = {
        "Tous": list(range(1, 13)),
        "Hiver (Déc–Fév)": [12, 1, 2],
        "Printemps (Mar–Mai)": [3, 4, 5],
        "Été (Juin–Août)": [6, 7, 8],
        "Automne (Sep–Nov)": [9, 10, 11],
    }
    season_sel = st.selectbox("Saison", list(MONTHS.keys()))
    months_sel = MONTHS[season_sel]

    # Weekend/Semaine
    day_type = st.radio(
        "Type de jour",
        ["Tous", "Semaine", "Weekend"],
        horizontal=True
    )

    st.divider()

    # Zone de marché prix
    st.markdown("**Zone de marché (prix)**")
    zone_labels = {
        "DK-1 (Est Danemark)":   "DK_1_price_day_ahead",
        "DK-2 (Ouest Danemark)": "DK_2_price_day_ahead",
        "IT-NORD/France":        "IT_NORD_FR_price_day_ahead",
    }
    zone_sel = st.selectbox("Zone", list(zone_labels.keys()))
    price_col = zone_labels[zone_sel]

    st.divider()

    # Bouton de téléchargement
    st.markdown("**Export des données**")
    st.caption("Téléchargez les observations correspondant aux filtres actifs")

    st.divider()
    st.caption("Source : Open Power System Data (OPSD)\nLicence CC-BY 4.0 — TU Berlin / ETH Zürich")

# APPLICATION DES FILTRES
mask = (
    df["year"].between(year_range[0], year_range[1]) &
    df["month_num"].isin(months_sel)
)
if day_type == "Semaine":
    mask &= df["is_weekend"] == 0
elif day_type == "Weekend":
    mask &= df["is_weekend"] == 1

dff = df[mask].copy()

# Bouton download (dans la sidebar mais après calcul de dff)
with st.sidebar:
    csv_data = dff.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Télécharger CSV filtré",
        data=csv_data,
        file_name=f"opsd_filtered_{year_range[0]}_{year_range[1]}.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ENTÊTE
st.markdown("## Prix Négatifs de l'Électricité Renouvelable en Europe")
st.caption(
    f"Données horaires OPSD · {year_range[0]}–{year_range[1]} · "
    f"{season_sel} · {day_type} · {len(dff):,} observations filtrées"
)

# CALCULS PARTAGÉS (utilisés dans plusieurs onglets)
prices = dff[price_col].dropna()
neg_count  = (prices < 0).sum()
neg_pct    = neg_count / len(prices) * 100 if len(prices) > 0 else 0
avg_price  = prices.mean()
min_price  = prices.min()
max_price  = prices.max()
de_avg_load = dff["DE_load_actual_entsoe_transparency"].mean()

def kpi_card(label, value, sub, level="green"):
    return f"""
    <div class="kpi-card kpi-{level}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>
    """

# CRÉATION DES ONGLETS
tab_overview, tab_causality, tab_temporal, tab_capacity, tab_ml = st.tabs([
    "Vue d'ensemble",
    "Causalité EnR → Prix",
    "Patterns temporels",
    "Charge & Capacités",
    "Modèle prédictif",
])

# ONGLET 1 — VUE D'ENSEMBLE
with tab_overview:

    # KPIs
    st.markdown('<div class="section-title">Chiffres clés</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Lisez la situation en 5 secondes</div>', unsafe_allow_html=True)

    if avg_price < 0:
        price_level = "red"
    elif avg_price < 20:
        price_level = "yellow"
    else:
        price_level = "green"
    neg_level = "red" if neg_pct > 5 else ("yellow" if neg_pct > 1 else "green")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(kpi_card("Prix moyen", f"{avg_price:.1f} €/MWh",
                             f"Zone : {zone_sel}", price_level), unsafe_allow_html=True)
    with col2:
        st.markdown(kpi_card("% Heures négatives", f"{neg_pct:.2f}%",
                             f"{neg_count:,} occurrences", neg_level), unsafe_allow_html=True)
    with col3:
        st.markdown(kpi_card("Prix minimum (pire)", f"{min_price:.1f} €/MWh",
                             "Surproduction extrême",
                             "red" if min_price < 0 else "green"), unsafe_allow_html=True)
    with col4:
        st.markdown(kpi_card("Prix maximum", f"{max_price:.1f} €/MWh",
                             "Pic de tension réseau", "yellow"), unsafe_allow_html=True)
    with col5:
        st.markdown(kpi_card("Charge moy. Allemagne", f"{de_avg_load/1000:.1f} GW",
                             "Demande nationale DE", "green"), unsafe_allow_html=True)

    # Bandeau d'alerte
    st.markdown("<br>", unsafe_allow_html=True)
    if neg_pct > 5:
        st.markdown(
            f'<div class="alert-red alert-text"><strong>ALERTE :</strong> {neg_pct:.1f}% des heures ont un prix négatif sur la période sélectionnée. '
            f'Le réseau est en surproduction structurelle — les flexibilités (stockage, effacement) sont insuffisantes.</div>',
            unsafe_allow_html=True
        )
    elif neg_pct > 1:
        st.markdown(
            f'<div class="alert-yellow alert-text"><strong>VIGILANCE :</strong> {neg_pct:.1f}% des heures à prix négatif. '
            f'Surproduction ponctuelle renouvelable observée — opportunité de stockage ou d\'export.</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="alert-green alert-text"><strong>NORMAL :</strong> {neg_pct:.2f}% des heures à prix négatif. '
            f'Equilibre offre/demande satisfaisant sur la période.</div>',
            unsafe_allow_html=True
        )

    # Prix Day-Ahead
    st.markdown('<div class="section-title">Prix Day-Ahead</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Série temporelle avec seuil 0 €/MWh — les zones rouges signalent un dysfonctionnement de marché</div>', unsafe_allow_html=True)

    col_ts, col_dist = st.columns([3, 1])

    with col_ts:
        # Prix day-ahead journalier moyen (fig_price)
        daily = dff.groupby("date")[price_col].mean().reset_index()
        daily.columns = ["date", "price"]
        daily["date"] = pd.to_datetime(daily["date"])

        fig_price = go.Figure()
        fig_price.add_hrect(
            y0=daily["price"].min() - 5, y1=0,
            fillcolor="rgba(231,76,60,0.12)", line_width=0,
            annotation_text="Zone négative", annotation_position="top left",
            annotation_font_color="#e74c3c", annotation_font_size=11,
        )
        fig_price.add_trace(go.Scatter(
            x=daily["date"], y=daily["price"], mode="lines", name=zone_sel,
            line=dict(color=COLORS["price"], width=1.5),
            fill="tozeroy", fillcolor="rgba(253,127,111,0.10)",
        ))
        fig_price.add_hline(y=0, line=dict(color="#e74c3c", width=1.5, dash="dash"),
                            annotation_text="Seuil 0 €/MWh", annotation_font_color="#e74c3c")
        fig_price.add_hline(y=20, line=dict(color="#f39c12", width=1, dash="dot"),
                            annotation_text="20 €/MWh", annotation_font_color="#f39c12")
        fig_price.update_layout(
            **PLOTLY_LAYOUT,
            title=f"Prix day-ahead journalier moyen — {zone_sel}",
            xaxis_title="Date", yaxis_title="Prix (€/MWh)",
            height=320, showlegend=False,
        )
        st.plotly_chart(fig_price, use_container_width=True)

    with col_dist:
        # Distribution des prix (fig_hist)
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=dff[price_col].dropna(), nbinsx=60,
            name="Distribution", marker_color=COLORS["price"], opacity=0.8,
        ))
        fig_hist.add_vline(x=0, line=dict(color="#e74c3c", width=2, dash="dash"),
                           annotation_text="0 €", annotation_font_color="#e74c3c")
        fig_hist.update_layout(
            **PLOTLY_LAYOUT,
            title="Distribution des prix",
            xaxis_title="€/MWh", yaxis_title="Fréquence",
            height=320, showlegend=False,
        )
        st.plotly_chart(fig_hist, use_container_width=True)

# ONGLET 2 — CAUSALITÉ EnR → PRIX
with tab_causality:

    st.markdown('<div class="section-title">Production Renouvelable & Prix</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">La causalité derrière les prix négatifs : fort vent + fort solaire → prix qui s\'effondre</div>', unsafe_allow_html=True)

    col_scatter, col_stack = st.columns([1, 2])

    with col_scatter:
        # Renouvelable DE vs Prix (fig_sc)
        sample = dff.sample(min(3000, len(dff)), random_state=42)
        price_for_scatter = "DK_1_price_day_ahead" if price_col == "DK_1_price_day_ahead" else price_col

        fig_sc = go.Figure()
        fig_sc.add_trace(go.Scatter(
            x=sample["DE_renewable_gen"], y=sample[price_for_scatter],
            mode="markers",
            marker=dict(
                color=sample[price_for_scatter],
                colorscale=[
                    [0.0, "#e74c3c"], [0.35, "#f39c12"],
                    [0.6, "#2ecc71"], [1.0, "#5b9bd5"],
                ],
                cmin=sample[price_for_scatter].quantile(0.01),
                cmax=sample[price_for_scatter].quantile(0.99),
                size=3, opacity=0.6,
                colorbar=dict(title="€/MWh", len=0.6),
            ),
            hovertemplate="Renouvelable: %{x:,.0f} MW<br>Prix: %{y:.1f} €/MWh<extra></extra>",
        ))
        fig_sc.add_hline(y=0, line=dict(color="#e74c3c", width=1.5, dash="dash"))
        fig_sc.update_layout(
            **PLOTLY_LAYOUT,
            title="Renouvelable DE vs Prix",
            xaxis_title="Vent + Solaire DE (MW)", yaxis_title="Prix (€/MWh)",
            height=370,
        )
        st.plotly_chart(fig_sc, use_container_width=True)

    with col_stack:
        # Mix énergétique DE & Prix DK-1 (fig_stack)
        weekly = dff.copy()
        weekly["week"] = weekly["timestamp"].dt.to_period("W").dt.start_time
        weekly_agg = weekly.groupby("week").agg(
            wind=("DE_wind_generation_actual", "mean"),
            solar=("DE_solar_generation_actual", "mean"),
            load=("DE_load_actual_entsoe_transparency", "mean"),
            price_dk1=("DK_1_price_day_ahead", "mean"),
        ).reset_index()

        fig_stack = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.65, 0.35], vertical_spacing=0.05,
        )
        fig_stack.add_trace(go.Scatter(
            x=weekly_agg["week"], y=weekly_agg["load"],
            mode="lines", name="Charge DE",
            line=dict(color=COLORS["load"], width=1.5, dash="dot"), fill=None,
        ), row=1, col=1)
        fig_stack.add_trace(go.Scatter(
            x=weekly_agg["week"], y=weekly_agg["wind"],
            mode="lines", name="Éolien DE", stackgroup="gen",
            line=dict(color=COLORS["wind"], width=0),
            fillcolor="rgba(91,155,213,0.6)",
        ), row=1, col=1)
        fig_stack.add_trace(go.Scatter(
            x=weekly_agg["week"], y=weekly_agg["solar"],
            mode="lines", name="Solaire DE", stackgroup="gen",
            line=dict(color=COLORS["solar"], width=0),
            fillcolor="rgba(255,209,102,0.7)",
        ), row=1, col=1)
        fig_stack.add_trace(go.Scatter(
            x=weekly_agg["week"], y=weekly_agg["price_dk1"],
            mode="lines", name="Prix DK-1",
            line=dict(color=COLORS["price"], width=1.5),
            fill="tozeroy", fillcolor="rgba(253,127,111,0.10)",
        ), row=2, col=1)
        fig_stack.add_hline(y=0, line=dict(color="#e74c3c", width=1, dash="dash"), row=2, col=1)
        fig_stack.update_layout(
            **PLOTLY_LAYOUT,
            title="Mix énergétique DE (moy. hebdomadaire) & Prix DK-1",
            yaxis_title="MW", yaxis2_title="€/MWh",
            height=370,
        )
        st.plotly_chart(fig_stack, use_container_width=True)

# ONGLET 3 — PATTERNS TEMPORELS
with tab_temporal:

    st.markdown('<div class="section-title">Patterns Temporels des Prix Négatifs</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Quand les prix négatifs apparaissent-ils ? Heure, mois, année — pour anticiper et agir</div>', unsafe_allow_html=True)

    col_hm, col_year = st.columns([2, 1])

    with col_hm:
        # Heatmap heure × mois (fig_hm)
        neg_flag = "DK_1_price_day_ahead" if "DK" in zone_sel else price_col
        hm_data = dff.groupby(["hour", "month_num"]).apply(
            lambda g: (g[neg_flag] < 0).mean() * 100
        ).reset_index(name="neg_pct")

        hm_pivot = hm_data.pivot(index="hour", columns="month_num", values="neg_pct")
        month_labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
                        "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
        cols_present = [c for c in range(1, 13) if c in hm_pivot.columns]
        hm_pivot = hm_pivot[cols_present]
        col_labels = [month_labels[c - 1] for c in cols_present]

        fig_hm = go.Figure(go.Heatmap(
            z=hm_pivot.values, x=col_labels, y=list(hm_pivot.index),
            colorscale=[
                [0.0, "#0d2a1a"], [0.01, "#2ecc71"],
                [0.10, "#f39c12"], [0.30, "#e74c3c"], [1.0, "#7b0000"],
            ],
            colorbar=dict(title="% heures<br>négatives"),
            hovertemplate="Heure %{y}h · %{x}<br>% négatif : %{z:.1f}%<extra></extra>",
        ))
        fig_hm.update_layout(
            **PLOTLY_LAYOUT,
            title="Heatmap : % heures à prix négatif par heure × mois",
            xaxis_title="Mois", yaxis_title="Heure du jour",
            height=380,
        )
        st.plotly_chart(fig_hm, use_container_width=True)

    with col_year:
        # Heures à prix négatif / an (fig_yr)
        yearly_neg = dff[dff[price_col] < 0].groupby("year").size().reset_index(name="neg_count")
        yearly_total = dff.groupby("year").size().reset_index(name="total")
        yearly = yearly_neg.merge(yearly_total, on="year", how="right").fillna(0)
        yearly["neg_pct"] = yearly["neg_count"] / yearly["total"] * 100

        fig_yr = go.Figure()
        fig_yr.add_trace(go.Bar(
            x=yearly["year"].astype(str), y=yearly["neg_count"],
            marker_color=[
                "#e74c3c" if p > 3 else ("#f39c12" if p > 1 else "#2ecc71")
                for p in yearly["neg_pct"]
            ],
            text=yearly["neg_pct"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
            textfont=dict(color="#c9d1d9", size=11),
            hovertemplate="Année %{x}<br>%{y:.0f} heures négatives<extra></extra>",
        ))
        fig_yr.update_layout(
            **PLOTLY_LAYOUT,
            title="Heures à prix négatif / an",
            xaxis_title="Année", yaxis_title="Nombre d'heures",
            height=380, showlegend=False,
        )
        st.plotly_chart(fig_yr, use_container_width=True)

    # Profil horaire moyen (fig_hourly)
    hourly_avg = dff.groupby("hour")[price_col].mean().reset_index()
    hourly_std = dff.groupby("hour")[price_col].std().reset_index(name="std")
    hourly_p = hourly_avg.merge(hourly_std, on="hour")
    hourly_p["upper"] = hourly_p[price_col] + hourly_p["std"]
    hourly_p["lower"] = hourly_p[price_col] - hourly_p["std"]

    fig_hourly = go.Figure()
    fig_hourly.add_trace(go.Scatter(
        x=hourly_p["hour"], y=hourly_p["upper"],
        mode="lines", line=dict(width=0), showlegend=False,
        fillcolor="rgba(253,127,111,0.15)", fill=None,
    ))
    fig_hourly.add_trace(go.Scatter(
        x=hourly_p["hour"], y=hourly_p["lower"],
        mode="lines", line=dict(width=0), showlegend=False,
        fill="tonexty", fillcolor="rgba(253,127,111,0.15)",
    ))
    fig_hourly.add_trace(go.Scatter(
        x=hourly_p["hour"], y=hourly_p[price_col],
        mode="lines+markers", name="Prix moyen",
        line=dict(color=COLORS["price"], width=2),
        marker=dict(size=6),
        hovertemplate="Heure %{x}h<br>Prix moy : %{y:.1f} €/MWh<extra></extra>",
    ))
    fig_hourly.add_hline(y=0, line=dict(color="#e74c3c", width=1.5, dash="dash"))
    fig_hourly.update_layout(
        **{**PLOTLY_LAYOUT, "xaxis": dict(tickmode="linear", dtick=2, **PLOTLY_LAYOUT["xaxis"])},
        title="Profil horaire moyen du prix (± écart-type)",
        xaxis_title="Heure de la journée", yaxis_title="Prix (€/MWh)",
        height=260, showlegend=False,
    )
    st.plotly_chart(fig_hourly, use_container_width=True)

# ONGLET 4 — CHARGE & CAPACITÉS
with tab_capacity:

    st.markdown('<div class="section-title">Charge & Capacités Installées</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Évolution des capacités renouvelables et erreur de prévision de charge</div>', unsafe_allow_html=True)

    # Capacités installées Allemagne (fig_cap)
    cap_data = dff.groupby("year")[
        ["DE_solar_capacity", "DE_wind_onshore_capacity", "DE_wind_offshore_capacity"]
    ].max().reset_index()

    fig_cap = go.Figure()
    fig_cap.add_trace(go.Bar(
        x=cap_data["year"].astype(str),
        y=cap_data["DE_solar_capacity"] / 1000,
        name="Solaire", marker_color=COLORS["solar"],
    ))
    fig_cap.add_trace(go.Bar(
        x=cap_data["year"].astype(str),
        y=cap_data["DE_wind_onshore_capacity"] / 1000,
        name="Éolien onshore", marker_color=COLORS["wind"],
    ))
    fig_cap.add_trace(go.Bar(
        x=cap_data["year"].astype(str),
        y=cap_data["DE_wind_offshore_capacity"] / 1000,
        name="Éolien offshore", marker_color="#2c7eb3",
    ))
    fig_cap.update_layout(
        **PLOTLY_LAYOUT,
        title="Capacités installées Allemagne (GW)",
        barmode="stack",
        xaxis_title="Année", yaxis_title="Capacité (GW)",
        height=380,
    )
    st.plotly_chart(fig_cap, use_container_width=True)

    # Erreur de prévision de charge DE (fig_err)
    st.markdown('<div class="section-title">Erreur de Prévision de Charge</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Écart (MW) entre charge réelle et prévue — un fort écart positif = déséquilibre réseau</div>', unsafe_allow_html=True)

    dff["DE_load_error"] = dff["DE_load_actual_entsoe_transparency"] - dff["DE_load_forecast_entsoe_transparency"]
    error_monthly = dff.groupby(["year", "month_num"])["DE_load_error"].agg(["mean", "std"]).reset_index()
    error_monthly["period"] = error_monthly.apply(
        lambda r: f"{int(r['year'])}-{int(r['month_num']):02d}", axis=1
    )

    fig_err = go.Figure()
    fig_err.add_trace(go.Bar(
        x=error_monthly["period"], y=error_monthly["mean"],
        error_y=dict(type="data", array=error_monthly["std"], visible=True, color="#636e72"),
        marker_color=error_monthly["mean"].apply(
            lambda v: "#e74c3c" if abs(v) > 500 else ("#f39c12" if abs(v) > 200 else "#2ecc71")
        ),
        hovertemplate="%{x}<br>Erreur moy : %{y:.0f} MW<extra></extra>",
    ))
    fig_err.add_hline(y=0, line=dict(color="#636e72", width=1))
    fig_err.add_hline(y=500, line=dict(color="#f39c12", width=1, dash="dot"),
                      annotation_text="Seuil +500 MW", annotation_font_color="#f39c12")
    fig_err.add_hline(y=-500, line=dict(color="#f39c12", width=1, dash="dot"),
                      annotation_text="Seuil -500 MW", annotation_font_color="#f39c12")
    fig_err.update_layout(
        **PLOTLY_LAYOUT,
        title="Erreur de prévision de charge DE (Réel − Prévision)",
        xaxis_title="Mois", yaxis_title="Erreur (MW)",
        height=270, showlegend=False,
    )
    st.plotly_chart(fig_err, use_container_width=True)

# ONGLET 5 — MODÈLE PRÉDICTIF
with tab_ml:

    import json as _json

    ROLE4_PATH = os.path.join(os.path.dirname(__file__), "role4")

    @st.cache_data(show_spinner="Chargement des données ML…")
    def load_ml_data():
        with open(os.path.join(ROLE4_PATH, "reports", "run_summary.json"), encoding="utf-8") as f:
            summary = _json.load(f)
        perf = pd.read_csv(os.path.join(ROLE4_PATH, "reports", "model_performance.csv"))
        feat = pd.read_csv(os.path.join(ROLE4_PATH, "reports", "permutation_importance_best_model.csv"))
        horizon = pd.read_csv(os.path.join(ROLE4_PATH, "reports", "horizon_comparison.csv"))
        return summary, perf, feat, horizon

    run_summary, perf_df, feat_df, horizon_df = load_ml_data()
    bm = run_summary["best_metrics"]

    st.markdown('<div class="section-title">Modèle prédictif des prix négatifs</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-sub">Random Forest — classification binaire (prix négatif oui/non) · '
        'Horizon H+1 · Entraîné sur 2015–2019 · Testé sur 2019–2020</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="alert-green alert-text"><strong>MODÈLE INTÉGRÉ :</strong> '
        'Random Forest (meilleur modèle sélectionné sur F1 pondéré) — '
        f'ROC-AUC = {bm["roc_auc"]:.3f} · F1 = {bm["f1"]:.3f} · Seuil optimal = {bm["threshold"]:.3f}. '
        'Données : Open Power System Data (OPSD) 2015–2020, zone DK-1.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # KPIs
    st.markdown("**Métriques de performance du meilleur modèle (test set)**")
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        st.markdown(kpi_card(
            "Balanced Accuracy",
            f"{bm['balanced_accuracy']:.1%}",
            "Moyenne sensibilité/spécificité", "green"
        ), unsafe_allow_html=True)
    with mc2:
        st.markdown(kpi_card(
            "Precision",
            f"{bm['precision']:.1%}",
            "% vrais positifs parmi détectés", "green"
        ), unsafe_allow_html=True)
    with mc3:
        st.markdown(kpi_card(
            "Recall",
            f"{bm['recall']:.1%}",
            "% prix négatifs capturés", "yellow"
        ), unsafe_allow_html=True)
    with mc4:
        st.markdown(kpi_card(
            "F1-score",
            f"{bm['f1']:.1%}",
            f"ROC-AUC = {bm['roc_auc']:.3f}", "green"
        ), unsafe_allow_html=True)

    st.caption("Modèle : Random Forest · Zone DK-1 · Horizon H+1 · Test set Nov 2019 – Sep 2020")
    st.markdown("<br>", unsafe_allow_html=True)

    # Comparaison des modèles
    st.markdown('<div class="section-title">Comparaison des modèles (H+1)</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Tous les modèles évalués sur le même test set · ★ = modèle retenu</div>', unsafe_allow_html=True)

    perf_plot = perf_df[perf_df["model"] != "dummy_most_frequent"].copy()
    model_labels = {
        "random_forest": "Random Forest ★",
        "logistic_regression": "Logistic Regression",
        "hist_gradient_boosting": "Hist GradientBoosting",
    }
    perf_plot["label"] = perf_plot["model"].map(model_labels).fillna(perf_plot["model"])
    metrics_to_show = ["f1", "precision", "recall", "roc_auc"]
    metric_names    = ["F1-score", "Precision", "Recall", "ROC-AUC"]
    colors_bar = ["#58a6ff", "#ffd166", "#2ecc71"]

    fig_cmp = go.Figure()
    for i, row in perf_plot.iterrows():
        fig_cmp.add_trace(go.Bar(
            name=row["label"],
            x=metric_names,
            y=[row[m] for m in metrics_to_show],
            marker_color=colors_bar[list(perf_plot.index).index(i) % len(colors_bar)],
            text=[f"{row[m]:.3f}" for m in metrics_to_show],
            textposition="outside",
            textfont=dict(size=11),
        ))
    fig_cmp.update_layout(
        **{**PLOTLY_LAYOUT, "yaxis": dict(range=[0, 1.05], gridcolor="#21262d", zerolinecolor="#30363d")},
        barmode="group",
        title="Comparaison des modèles sur le test set",
        height=340,
    )
    st.plotly_chart(fig_cmp, use_container_width=True)
    st.caption("Tous les modèles · même test set · seuil optimisé par Precision-Recall · zone DK-1 · H+1")

    # Feature importance + Confusion matrix
    col_fi, col_cm = st.columns(2)

    with col_fi:
        st.markdown('<div class="section-title" style="font-size:15px;">Feature Importance (permutation)</div>', unsafe_allow_html=True)
        top_feat = feat_df[feat_df["importance_mean"] > 0].nlargest(15, "importance_mean")
        fig_fi = go.Figure()
        fig_fi.add_trace(go.Bar(
            x=top_feat["importance_mean"],
            y=top_feat["feature"],
            orientation="h",
            marker=dict(
                color=top_feat["importance_mean"],
                colorscale=[[0, "#30363d"], [0.3, "#58a6ff"], [1, "#2ecc71"]],
                showscale=False,
            ),
            error_x=dict(type="data", array=top_feat["importance_std"], visible=True, color="#636e72"),
            hovertemplate="%{y}<br>Importance : %{x:.4f}<extra></extra>",
        ))
        fig_fi.update_layout(
            **{**PLOTLY_LAYOUT, "yaxis": dict(autorange="reversed", gridcolor="#21262d", zerolinecolor="#30363d")},
            title="Random Forest — Top 15 features (permutation importance)",
            xaxis_title="Importance moyenne",
            height=430,
        )
        st.plotly_chart(fig_fi, use_container_width=True)
        st.caption("Modèle : Random Forest (meilleur modèle) · H+1 · test set · moyenne sur 5 répétitions de permutation")

    with col_cm:
        st.markdown('<div class="section-title" style="font-size:15px;">Matrice de confusion & Courbes P-R</div>', unsafe_allow_html=True)
        cm_path = os.path.join(ROLE4_PATH, "figures", "confusion_matrix_best_model.png")
        pr_path = os.path.join(ROLE4_PATH, "figures", "precision_recall_curves.png")
        if os.path.exists(cm_path):
            st.image(cm_path, caption="Matrice de confusion — Random Forest (test set)", use_container_width=True)
        if os.path.exists(pr_path):
            st.image(pr_path, caption="Courbes Precision-Recall par modèle", use_container_width=True)

    # Comparaison par horizon
    st.markdown('<div class="section-title">Performance par horizon de prédiction</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">La performance se dégrade naturellement à mesure que l\'horizon augmente (H+1 → H+12)</div>', unsafe_allow_html=True)

    fig_hz = go.Figure()
    fig_hz.add_trace(go.Scatter(
        x=horizon_df["horizon_h"], y=horizon_df["roc_auc"],
        mode="lines+markers+text",
        name="ROC-AUC",
        line=dict(color="#58a6ff", width=2),
        marker=dict(size=9),
        text=[f"{v:.3f}" for v in horizon_df["roc_auc"]],
        textposition="top center",
        hovertemplate="H+%{x}h<br>ROC-AUC : %{y:.3f}<extra></extra>",
    ))
    fig_hz.add_trace(go.Scatter(
        x=horizon_df["horizon_h"], y=horizon_df["f1"],
        mode="lines+markers+text",
        name="F1-score",
        line=dict(color="#2ecc71", width=2),
        marker=dict(size=9),
        text=[f"{v:.3f}" for v in horizon_df["f1"]],
        textposition="bottom center",
        hovertemplate="H+%{x}h<br>F1 : %{y:.3f}<extra></extra>",
    ))
    fig_hz.add_trace(go.Scatter(
        x=horizon_df["horizon_h"], y=horizon_df["average_precision"],
        mode="lines+markers+text",
        name="Average Precision",
        line=dict(color="#ffd166", width=2, dash="dot"),
        marker=dict(size=9),
        text=[f"{v:.3f}" for v in horizon_df["average_precision"]],
        textposition="top center",
        hovertemplate="H+%{x}h<br>Avg Precision : %{y:.3f}<extra></extra>",
    ))
    _hz_model_short = {
        "random_forest": "RF",
        "logistic_regression": "LR",
        "hist_gradient_boosting": "HGB",
    }
    hz_annotations = [
        dict(
            x=row["horizon_h"], y=row["roc_auc"] + 0.07,
            text=f"<b>{_hz_model_short.get(row['best_model'], row['best_model'])}</b>",
            showarrow=False,
            font=dict(size=11, color="#8892a4"),
            bgcolor="#1a1d2e", bordercolor="#30363d", borderwidth=1,
            borderpad=3,
        )
        for _, row in horizon_df.iterrows()
    ]
    fig_hz.update_layout(
        **{
            **PLOTLY_LAYOUT,
            "xaxis": dict(
                tickmode="array", tickvals=horizon_df["horizon_h"].tolist(),
                ticktext=[f"H+{h}h" for h in horizon_df["horizon_h"]],
                gridcolor="#21262d", zerolinecolor="#30363d",
            ),
            "yaxis": dict(range=[0, 1.12], title="Score", gridcolor="#21262d", zerolinecolor="#30363d"),
        },
        title="Dégradation de la performance selon l'horizon — modèle retenu par horizon",
        annotations=hz_annotations,
        height=340,
    )
    st.plotly_chart(fig_hz, use_container_width=True)
    st.caption("RF = Random Forest · HGB = HistGradientBoosting · LR = Logistic Regression · étiquettes = meilleur modèle à chaque horizon · zone DK-1")

    # Périodes d'entraînement
    st.markdown('<div class="section-title">Découpage temporel (train / validation / test)</div>', unsafe_allow_html=True)
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.markdown(kpi_card(
            "Entraînement",
            "2015 → Jan 2019",
            run_summary["train_period"][0][:10] + " – " + run_summary["train_period"][1][:10],
            "green"
        ), unsafe_allow_html=True)
    with col_info2:
        st.markdown(kpi_card(
            "Validation",
            "Jan → Nov 2019",
            run_summary["validation_period"][0][:10] + " – " + run_summary["validation_period"][1][:10],
            "yellow"
        ), unsafe_allow_html=True)
    with col_info3:
        st.markdown(kpi_card(
            "Test",
            "Nov 2019 → Sep 2020",
            run_summary["test_period"][0][:10] + " – " + run_summary["test_period"][1][:10],
            "red"
        ), unsafe_allow_html=True)

# FOOTER
st.divider()
st.caption(
    "**Projet 8 — Prix Négatifs de l'Électricité Renouvelable en Europe**  \n"
    "Source : Open Power System Data (OPSD) · Licence CC-BY 4.0 · TU Berlin / ETH Zürich  \n"
    "Rôle 6 — Visualisation & Interface · Dashboard Streamlit + Plotly"
)