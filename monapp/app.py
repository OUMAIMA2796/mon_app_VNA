"""Application financière : Comparaison de la VAN de 2 projets.
Lancement : streamlit run app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="Comparateur VAN - 2 Projets",
    page_icon="📊",
    layout="wide",
)

# ---------- Fonctions financières ----------

def calcul_van(investissement: float, cashflows: list[float], taux: float) -> float:
    """VAN = -I0 + somme(CF_t / (1+r)^t). taux en décimal (ex: 0.10 pour 10%)."""
    van = -investissement
    for t, cf in enumerate(cashflows, start=1):
        van += cf / ((1 + taux) ** t)
    return van


def flux_actualises(cashflows: list[float], taux: float) -> list[float]:
    return [cf / ((1 + taux) ** t) for t, cf in enumerate(cashflows, start=1)]


def van_cumulee(investissement: float, cashflows: list[float], taux: float) -> list[float]:
    """Retourne la VAN cumulée année par année (année 0 = -I0)."""
    fa = flux_actualises(cashflows, taux)
    cumul = [-investissement]
    for f in fa:
        cumul.append(cumul[-1] + f)
    return cumul


def calcul_tri(investissement: float, cashflows: list[float], tol=1e-6, max_iter=200) -> float | None:
    """TRI par dichotomie sur [-99%, +1000%]. Retourne taux décimal ou None si non trouvé."""
    def van_test(r):
        return calcul_van(investissement, cashflows, r)

    bas, haut = -0.999, 10.0
    van_bas, van_haut = van_test(bas), van_test(haut)
    if van_bas * van_haut > 0:
        return None  # pas de changement de signe -> pas de TRI unique
    for _ in range(max_iter):
        mid = (bas + haut) / 2
        van_mid = van_test(mid)
        if abs(van_mid) < tol:
            return mid
        if van_bas * van_mid < 0:
            haut, van_haut = mid, van_mid
        else:
            bas, van_bas = mid, van_mid
    return (bas + haut) / 2


def calcul_ip(investissement: float, cashflows: list[float], taux: float) -> float:
    """Indice de Profitabilité = PV flux futurs / I0."""
    if investissement == 0:
        return float("nan")
    pv = sum(flux_actualises(cashflows, taux))
    return pv / investissement


def calcul_drci(investissement: float, cashflows: list[float], taux: float) -> float | None:
    """Délai de Récupération du Capital Investi (actualisé), en années. None si jamais récupéré."""
    cumul = van_cumulee(investissement, cashflows, taux)
    for t in range(1, len(cumul)):
        if cumul[t] >= 0:
            # interpolation linéaire dans l'année
            prev = cumul[t - 1]
            curr = cumul[t]
            fraction = (0 - prev) / (curr - prev) if curr != prev else 1
            return (t - 1) + fraction
    return None


# ---------- Interface ----------

st.title("📊 Comparateur de VAN — 2 Projets")
st.markdown(
    "Comparez la **Valeur Actuelle Nette (VAN)** de deux projets d'investissement "
    "avec flux actualisés, indicateurs de rentabilité et graphiques interactifs."
)

with st.expander("ℹ️ Rappel : qu'est-ce que la VAN ?", expanded=False):
    st.markdown(
        """
        **VAN = - Investissement initial + Σ [ CF_t / (1 + r)^t ]**

        - **VAN > 0** : projet rentable (crée de la valeur).
        - **VAN < 0** : projet non rentable.
        - Entre 2 projets : on retient en général celui avec la **VAN la plus élevée**.
        - Le **TRI** est le taux qui annule la VAN. On investit si TRI > taux d'actualisation.
        """
    )

# --- Sidebar : paramètres généraux ---
st.sidebar.header("⚙️ Paramètres généraux")
taux_pct = st.sidebar.slider("Taux d'actualisation (%)", 0.0, 30.0, 10.0, 0.5)
taux = taux_pct / 100.0
duree = st.sidebar.slider("Durée des projets (années)", 1, 15, 5, 1)

st.sidebar.divider()
st.sidebar.header("💰 Investissements initiaux")
inv_a = st.sidebar.number_input("Investissement Projet A (€)", min_value=0.0, value=100000.0, step=5000.0, format="%.2f")
inv_b = st.sidebar.number_input("Investissement Projet B (€)", min_value=0.0, value=120000.0, step=5000.0, format="%.2f")

st.sidebar.divider()
mode_saisie = st.sidebar.radio(
    "Mode de saisie des cash-flows",
    ["Saisie annuelle détaillée", "Flux constant + croissance"],
    index=0,
)

# --- Saisie des cash-flows ---
def saisie_cashflows(projet: str, defaut: list[float]) -> list[float]:
    if mode_saisie == "Saisie annuelle détaillée":
        st.subheader(f"Projet {projet}")
        df_defaut = pd.DataFrame(
            {"Année": list(range(1, duree + 1)),
             "Cash-flow (€)": (defaut[:duree] + [0.0] * duree)[:duree]}
        )
        df_edit = st.data_editor(
            df_defaut,
            num_rows="fixed",
            hide_index=True,
            column_config={
                "Année": st.column_config.NumberColumn(disabled=True),
                "Cash-flow (€)": st.column_config.NumberColumn(min_value=-1e12, step=1000.0, format="%.2f"),
            },
            key=f"editor_{projet}",
            width="stretch",
        )
        return df_edit["Cash-flow (€)"].tolist()
    else:
        st.subheader(f"Projet {projet}")
        base = st.number_input(
            f"Cash-flow annuel de base {projet} (€)",
            value=float(defaut[0]),
            step=1000.0,
            key=f"base_{projet}",
        )
        croissance = st.number_input(
            f"Croissance annuelle {projet} (%)",
            value=5.0 if projet == "A" else 3.0,
            step=0.5,
            key=f"croiss_{projet}",
        )
        cfs = [base * ((1 + croissance / 100.0) ** (t - 1)) for t in range(1, duree + 1)]
        st.dataframe(
            pd.DataFrame({"Année": range(1, duree + 1), "Cash-flow (€)": cfs}).style.format({"Cash-flow (€)": "{:,.2f}"}),
            hide_index=True,
            width="stretch",
        )
        return cfs


col_a, col_b = st.columns(2)
with col_a:
    cf_a = saisie_cashflows("A", [30000, 35000, 40000, 45000, 50000, 50000, 50000, 50000, 50000, 50000, 50000, 50000, 50000, 50000, 50000])
with col_b:
    cf_b = saisie_cashflows("B", [20000, 30000, 45000, 55000, 65000, 65000, 65000, 65000, 65000, 65000, 65000, 65000, 65000, 65000, 65000])

# --- Calculs ---
van_a = calcul_van(inv_a, cf_a, taux)
van_b = calcul_van(inv_b, cf_b, taux)
tri_a = calcul_tri(inv_a, cf_a)
tri_b = calcul_tri(inv_b, cf_b)
ip_a = calcul_ip(inv_a, cf_a, taux)
ip_b = calcul_ip(inv_b, cf_b, taux)
drci_a = calcul_drci(inv_a, cf_a, taux)
drci_b = calcul_drci(inv_b, cf_b, taux)

annees = list(range(duree + 1))
cumul_a = van_cumulee(inv_a, cf_a, taux)
cumul_b = van_cumulee(inv_b, cf_b, taux)
fa_a = flux_actualises(cf_a, taux)
fa_b = flux_actualises(cf_b, taux)

# --- Résultats ---
st.divider()
st.header("🏆 Résultats")

m1, m2, m3 = st.columns(3)
m1.metric("VAN Projet A", f"{van_a:,.2f} €", delta=f"TRI {tri_a*100:.2f} %" if tri_a is not None else "TRI non défini")
m2.metric("VAN Projet B", f"{van_b:,.2f} €", delta=f"TRI {tri_b*100:.2f} %" if tri_b is not None else "TRI non défini")
m3.metric("Écart de VAN (A − B)", f"{van_a - van_b:,.2f} €")

if van_a > 0 and van_b > 0:
    gagnant = "A" if van_a > van_b else ("B" if van_b > van_a else "ex æquo")
    if gagnant == "ex æquo":
        st.success("✅ Les deux projets sont rentables et à égalité (même VAN).")
    else:
        st.success(f"✅ Les deux projets sont rentables. **Le Projet {gagnant} crée le plus de valeur** (VAN la plus élevée).")
elif van_a > 0 or van_b > 0:
    gagnant = "A" if van_a > 0 else "B"
    st.warning(f"⚠️ Seul le **Projet {gagnant} est rentable** (VAN > 0). L'autre doit être rejeté.")
else:
    st.error("❌ Aucun projet n'est rentable à ce taux d'actualisation (VAN < 0 pour les deux).")

# Tableau comparatif
df_result = pd.DataFrame({
    "Indicateur": ["Investissement initial (€)", "Somme cash-flows non actualisés (€)",
                   f"VAN @ {taux_pct:.1f}% (€)", "TRI (%)", "Indice de Profitabilité",
                   "DRCI actualisé (années)"],
    "Projet A": [f"{inv_a:,.2f}", f"{sum(cf_a):,.2f}", f"{van_a:,.2f}",
                 f"{tri_a*100:.2f}" if tri_a is not None else "—",
                 f"{ip_a:.3f}", f"{drci_a:.2f}" if drci_a is not None else "Jamais"],
    "Projet B": [f"{inv_b:,.2f}", f"{sum(cf_b):,.2f}", f"{van_b:,.2f}",
                 f"{tri_b*100:.2f}" if tri_b is not None else "—",
                 f"{ip_b:.3f}", f"{drci_b:.2f}" if drci_b is not None else "Jamais"],
})
st.table(df_result)

# Détail annuel
with st.expander("📋 Détail annuel des flux actualisés"):
    df_detail = pd.DataFrame({
        "Année": list(range(1, duree + 1)),
        "CF A (€)": cf_a,
        "CF A actualisé (€)": fa_a,
        "VAN cumulée A (€)": cumul_a[1:],
        "CF B (€)": cf_b,
        "CF B actualisé (€)": fa_b,
        "VAN cumulée B (€)": cumul_b[1:],
    })
    st.dataframe(df_detail.style.format("{:,.2f}", subset=pd.IndexSlice[:, df_detail.columns != "Année"]), hide_index=True, width="stretch")

# --- Graphiques ---
st.divider()
st.header("📈 Illustrations graphiques")

# 1. Barres VAN
fig_van = go.Figure()
fig_van.add_bar(x=["Projet A", "Projet B"], y=[van_a, van_b],
                marker_color=["#2ecc71" if van_a >= 0 else "#e74c3c",
                              "#3498db" if van_b >= 0 else "#e74c3c"],
                text=[f"{van_a:,.0f} €", f"{van_b:,.0f} €"], textposition="outside")
fig_van.add_hline(y=0, line_color="black", line_width=1)
fig_van.update_layout(title=f"Comparaison des VAN (taux = {taux_pct:.1f} %)",
                      yaxis_title="VAN (€)", showlegend=False, height=400)
st.plotly_chart(fig_van, width="stretch")

# 2. VAN cumulée actualisée
fig_cumul = go.Figure()
fig_cumul.add_trace(go.Scatter(x=annees, y=cumul_a, mode="lines+markers", name="Projet A", line=dict(color="#2ecc71", width=3)))
fig_cumul.add_trace(go.Scatter(x=annees, y=cumul_b, mode="lines+markers", name="Projet B", line=dict(color="#3498db", width=3)))
fig_cumul.add_hline(y=0, line_color="black", line_dash="dash")
fig_cumul.update_layout(title="VAN cumulée actualisée (payback actualisé)",
                        xaxis_title="Année", yaxis_title="VAN cumulée (€)", height=450)
st.plotly_chart(fig_cumul, width="stretch")

# 3. Sensibilité VAN au taux
taux_range = np.linspace(0, 0.30, 61)
vans_a = [calcul_van(inv_a, cf_a, r) for r in taux_range]
vans_b = [calcul_van(inv_b, cf_b, r) for r in taux_range]
fig_sensi = go.Figure()
fig_sensi.add_trace(go.Scatter(x=taux_range * 100, y=vans_a, mode="lines", name="Projet A", line=dict(color="#2ecc71", width=3)))
fig_sensi.add_trace(go.Scatter(x=taux_range * 100, y=vans_b, mode="lines", name="Projet B", line=dict(color="#3498db", width=3)))
fig_sensi.add_hline(y=0, line_color="black", line_width=1)
fig_sensi.add_vline(x=taux_pct, line_color="red", line_dash="dot",
                    annotation_text=f"Taux actuel {taux_pct:.1f}%")
fig_sensi.update_layout(title="Sensibilité de la VAN au taux d'actualisation (TRI = intersection avec 0)",
                        xaxis_title="Taux d'actualisation (%)", yaxis_title="VAN (€)", height=450)
st.plotly_chart(fig_sensi, width="stretch")

# 4. Cash-flows bruts vs actualisés
fig_cf = go.Figure()
x_labels = [f"Année {t}" for t in range(1, duree + 1)]
fig_cf.add_bar(x=x_labels, y=cf_a, name="CF A brut", marker_color="rgba(46,204,113,0.5)")
fig_cf.add_bar(x=x_labels, y=fa_a, name="CF A actualisé", marker_color="#2ecc71")
fig_cf.add_bar(x=x_labels, y=cf_b, name="CF B brut", marker_color="rgba(52,152,219,0.4)")
fig_cf.add_bar(x=x_labels, y=fa_b, name="CF B actualisé", marker_color="#3498db")
fig_cf.update_layout(title="Cash-flows bruts vs actualisés par année",
                     yaxis_title="Montant (€)", barmode="group", height=450)
st.plotly_chart(fig_cf, width="stretch")

st.caption("VAN = -I₀ + Σ CF_t/(1+r)^t • TRI = taux annulant la VAN • IP = PV/I₀ • DRCI = délai de récupération actualisé.")
