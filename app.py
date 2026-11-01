import html
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# =====================================================================
#  EV DASHBOARD  -  rebuilt from the Tableau workbook "EV_DASHBOARD.twb"
# =====================================================================
st.set_page_config(page_title="Electric Vehicles Data Analysis", page_icon="⚡",
                   layout="wide", initial_sidebar_state="collapsed")

# ---------- Colours taken from the Tableau file ----------
RED = "#aa0000"        # chart titles + KPI labels
TITLE_BG = "#f5eddc"   # chart title background
BLUE = "#4e79a7"       # "% of Total" text in BEV / PHEV tiles
AREA = "#72b966"       # Model Year area
LINE = "#59a14f"       # Model Year line
BAR = "#8cd17d"        # Top Make bars
HEADER = "#a0d1ff"     # Model table measure headers
PIE_COLORS = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f"]  # Tableau 10

BEV = "Battery Electric Vehicle (BEV)"
PHEV = "Plug-in Hybrid Electric Vehicle (PHEV)"
CAFV_COL = "Clean Alternative Fuel Vehicle (CAFV) Eligibility"

# Aliases (renamed values) from the Tableau file
CAFV_ALIAS = {
    "Clean Alternative Fuel Vehicle Eligible": "CAFV Eligible",
    "Eligibility unknown as battery range has not been researched": "CAFV Unknown",
    "Not eligible due to low battery range": "CAFV Not eligible",
}
TYPE_ALIAS = {BEV: "BEV", PHEV: "PHEV"}

SMALL_FILE = "ev_data_small.csv"
FULL_FILE = "Electric_Vehicle_Population_Data.csv"
LOGO_FILES = ["EV DASHBOARD.png", "logo.png"]

st.markdown(
    f"""
<style>
.block-container {{padding-top: 1rem; padding-bottom: 0.5rem; max-width: 1600px;}}
.dash-title {{font-weight: 700; font-size: 20px; text-align: center; padding: 4px 0 8px 0;}}
.ctitle {{background: {TITLE_BG}; color: {RED}; font-weight: 700; font-size: 12px; padding: 4px 8px;}}
.kpi {{background: #fff; border: 1px solid #eee; padding: 8px 12px; min-height: 100px;}}
.kpi-label {{color: {RED}; font-weight: 700; font-size: 12px;}}
.kpi-value {{font-weight: 700; font-size: 22px;}}
.kpi-pct {{color: {BLUE}; font-weight: 700; font-size: 14px;}}
.mtable-wrap {{max-height: 300px; overflow-y: auto; border: 1px solid #eee;}}
.mtable {{border-collapse: collapse; width: 100%; font-size: 11px;}}
.mtable th {{position: sticky; top: 0; background: #f2f2f2; padding: 3px 6px; text-align: left;}}
.mtable th.m {{background: {HEADER};}}
.mtable td {{padding: 2px 6px; border-bottom: 1px solid #f0f0f0;}}
.mtable td.num {{text-align: right;}}
</style>
""",
    unsafe_allow_html=True,
)

# ---------- Load data ----------
RULES = {
    "DOL Vehicle ID": ("dol vehicle id", "vehicle id"),
    "State": ("state", None),
    "Model Year": ("model year", None),
    "Make": ("make", None),
    "Model": ("model", None),
    "Electric Vehicle Type": ("electric vehicle type", "vehicle type"),
    CAFV_COL: ("clean alternative fuel vehicle (cafv) eligibility", "cafv"),
    "Electric Range": ("electric range", None),
}


def clean(name):
    return " ".join(str(name).replace("\ufeff", "").split()).lower()


@st.cache_data
def load_data() -> pd.DataFrame:
    if os.path.exists(SMALL_FILE):
        d = pd.read_csv(SMALL_FILE)
        d.columns = [c.strip() for c in d.columns]
        return d
    if os.path.exists(FULL_FILE):
        header = pd.read_csv(FULL_FILE, nrows=0).columns.tolist()
        mapping = {}
        for canonical, (exact, keyword) in RULES.items():
            found = next((c for c in header if clean(c) == exact), None)
            if found is None and keyword:
                found = next((c for c in header if keyword in clean(c)), None)
            if found is not None:
                mapping[found] = canonical
        return pd.read_csv(FULL_FILE, usecols=list(mapping.keys())).rename(columns=mapping)
    return pd.DataFrame()


df = load_data()
if df.empty:
    st.error(f"CSV not found. Put '{FULL_FILE}' (or '{SMALL_FILE}') in the same folder as app.py")
    st.stop()

df["CAFV"] = df[CAFV_COL].map(CAFV_ALIAS).fillna(df[CAFV_COL])
df["EV Type"] = df["Electric Vehicle Type"].map(TYPE_ALIAS).fillna(df["Electric Vehicle Type"])

# ---------- Click-to-filter (Tableau dashboard actions) ----------
if "sel_n" not in st.session_state:
    st.session_state["sel_n"] = 0
N = st.session_state["sel_n"]
MAKE_KEY, STATE_KEY = f"make_chart_{N}", f"state_chart_{N}"


def clicked(key, field):
    """Values the user clicked in a chart (read from the previous run)."""
    try:
        pts = st.session_state[key]["selection"]["points"]
        return [p[field] for p in pts if p.get(field) is not None]
    except Exception:
        return []


sel_makes = clicked(MAKE_KEY, "y")
sel_states = clicked(STATE_KEY, "location")


# ---------- Small helpers ----------
def count(d):
    return int(d["DOL Vehicle ID"].nunique())


def kfmt(v):
    return f"{v / 1000:,.1f}K"


def ctitle(text):
    st.markdown(f'<div class="ctitle">{html.escape(text)}</div>', unsafe_allow_html=True)


def empty_msg():
    st.info("No data for the current selection.")


def kpi(label, value, pct=None):
    extra = f'<div class="kpi-pct">% of Total : {pct:.1%}</div>' if pct is not None else ""
    st.markdown(
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>{extra}</div>',
        unsafe_allow_html=True,
    )


CFG = {"displayModeBar": False}

# ---------- Page title ----------
st.markdown('<div class="dash-title">ELECTRIC VEHICLES DATA ANALYSIS</div>', unsafe_allow_html=True)

left, right = st.columns([14, 86])

# ---------- LEFT PANEL: logo + 4 filters ----------
with left:
    logo = next((p for p in LOGO_FILES if os.path.exists(p)), None)
    if logo:
        st.image(logo, use_container_width=True)
    else:
        st.markdown("### ⚡ EV")

    f_cafv = st.multiselect("CAFV Eligibility", sorted(df["CAFV"].dropna().unique()), placeholder="(All)")
    f_type = st.multiselect("EV Type", sorted(df["EV Type"].dropna().unique()), placeholder="(All)")
    f_model = st.multiselect("Model", sorted(df["Model"].dropna().unique()), placeholder="(All)")
    f_state = st.multiselect("State", sorted(df["State"].dropna().unique()), placeholder="(All)")

    if sel_makes or sel_states:
        if st.button("Clear click selection"):
            st.session_state["sel_n"] += 1
            st.rerun()

base = df
if f_cafv:
    base = base[base["CAFV"].isin(f_cafv)]
if f_type:
    base = base[base["EV Type"].isin(f_type)]
if f_model:
    base = base[base["Model"].isin(f_model)]
if f_state:
    base = base[base["State"].isin(f_state)]

# Which sheets react to which click (same as the two Tableau actions)
by_make_filter = base[base["Make"].isin(sel_makes)] if sel_makes else base
by_state_filter = base[base["State"].isin(sel_states)] if sel_states else base
full = by_state_filter[by_state_filter["Make"].isin(sel_makes)] if sel_makes else by_state_filter
map_data = by_make_filter                # map: reacts to Make click only
make_data = by_state_filter              # Top Make: reacts to State click only

with right:
    if base.empty or full.empty:
        st.warning("No data for these filters.")
        st.stop()

    # ---------- ROW 1: KPI tiles ----------
    total = count(full)
    bev = count(full[full["Electric Vehicle Type"] == BEV])
    phev = count(full[full["Electric Vehicle Type"] == PHEV])
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi("Avg Electric Range", f"{full['Electric Range'].mean():,.1f} Miles")
    with k2:
        kpi("Total Vehicles", f"{total:,}")
    with k3:
        kpi("Total BEV Vehicles", f"{bev:,}", bev / total)
    with k4:
        kpi("Total PHEV Vehicles", f"{phev:,}", phev / total)

    # ---------- ROW 2: Model Year  |  State map ----------
    r2a, r2b = st.columns(2)

    with r2a:
        ctitle("Total Vehicles By Model Year")
        by_year = (full.groupby("Model Year")["DOL Vehicle ID"].nunique().reset_index(name="V").sort_values("Model Year"))
        x = by_year["Model Year"].astype(str)
        avg_v = by_year["V"].mean()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=by_year["V"], mode="lines", fill="tozeroy",
                                 line=dict(color=AREA, width=1), fillcolor="rgba(114,185,102,0.5)",
                                 hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=x, y=by_year["V"], mode="lines+text", line=dict(color=LINE, width=1.5),
                                 text=[kfmt(v) for v in by_year["V"]], textposition="top center",
                                 textfont=dict(size=8), cliponaxis=False,
                                 hovertemplate="%{x}: %{y:,}<extra></extra>"))
        fig.add_hline(y=avg_v, line_dash="dash", line_color="rgba(117,161,199,0.6)", line_width=1,
                      annotation_text=f"Avg : {kfmt(avg_v)}", annotation_position="top left",
                      annotation_font_size=9)
        fig.update_layout(height=340, showlegend=False, margin=dict(l=5, r=5, t=25, b=5),
                          xaxis=dict(type="category", tickangle=-90, tickfont=dict(size=8), showgrid=False),
                          yaxis=dict(visible=False, showgrid=False, range=[0, by_year["V"].max() * 1.2]),
                          plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True, config=CFG)

    with r2b:
        ctitle("Total Vehicles By State")
        by_state = (map_data.groupby("State")["DOL Vehicle ID"].nunique().reset_index(name="V"))
        fig = go.Figure()
        fig.add_trace(go.Choropleth(locations=by_state["State"], z=by_state["V"], locationmode="USA-states",
                                    colorscale=[[0, "#e9f5e1"], [1, "#2e7d32"]], showscale=False,
                                    marker_line_color="white",
                                    hovertemplate="%{location}: %{z:,}<extra></extra>"))
        fig.add_trace(go.Scattergeo(locations=by_state["State"], locationmode="USA-states",
                                    text=[f"{v:,}" for v in by_state["V"]], mode="text",
                                    textfont=dict(size=8), hoverinfo="skip"))
        fig.update_layout(height=340, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                          geo=dict(scope="usa", showlakes=False, bgcolor="white"), clickmode="event+select")
        st.plotly_chart(fig, use_container_width=True, config=CFG, key=STATE_KEY,
                        on_select="rerun", selection_mode="points")

    # ---------- ROW 3: Top N Make | CAFV pie | Model table ----------
    r3a, r3b, r3c = st.columns([27, 22, 36])

    with r3a:
        top_n = st.slider("Top N", 1, 15, 10)
        ctitle(f"Top {top_n} Total Vehicles By Make")
        by_make = make_data.groupby("Make")["DOL Vehicle ID"].nunique().nlargest(top_n).reset_index(name="V")
        by_make = by_make.sort_values("Make")  # Tableau shows them alphabetically
        tot = by_make["V"].sum()
        fig = go.Figure(go.Bar(
            x=by_make["V"], y=by_make["Make"], orientation="h", marker_color=BAR,
            text=[f"{v:,} ; {v / tot:.2%}" for v in by_make["V"]], textposition="outside",
            textfont=dict(size=8), cliponaxis=False, hoverinfo="skip"))
        fig.update_layout(height=300, margin=dict(l=5, r=5, t=5, b=5), showlegend=False,
                          xaxis=dict(visible=False, range=[0, by_make["V"].max() * 1.5]),
                          yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
                          plot_bgcolor="white", clickmode="event+select")
        fig.update_traces(selected=dict(marker=dict(color=BAR)), unselected=dict(marker=dict(opacity=0.35)))
        st.plotly_chart(fig, use_container_width=True, config=CFG, key=MAKE_KEY,
                        on_select="rerun", selection_mode="points")

    with r3b:
        ctitle("Total Vehicles By CAFV Eligibility")
        cafv_raw = full.groupby(CAFV_COL)["DOL Vehicle ID"].nunique().reset_index(name="V").sort_values(CAFV_COL)
        tot = cafv_raw["V"].sum()
        labels = [CAFV_ALIAS.get(n, n) for n in cafv_raw[CAFV_COL]]
        text = [f"{l}<br>{v:,} ; {v / tot:.2%}" for l, v in zip(labels, cafv_raw["V"])]
        fig = go.Figure(go.Pie(labels=labels, values=cafv_raw["V"], hole=0.5, sort=False,
                               marker=dict(colors=PIE_COLORS[:len(labels)]),
                               text=text, textinfo="text", textposition="outside",
                               textfont=dict(size=9), hoverinfo="skip"))
        fig.update_layout(height=300, margin=dict(l=30, r=30, t=20, b=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config=CFG)

    with r3c:
        ctitle("Total Vehicles By Model")
        t = (full.groupby(["Model", "Make", "EV Type"])["DOL Vehicle ID"].nunique().reset_index(name="V")
             .sort_values(["Model", "Make", "EV Type"]))
        tot = t["V"].sum()
        lo, hi = t["V"].min(), t["V"].max()
        c0, c1 = (233, 245, 224), (46, 125, 50)
        rows = []
        for _, r in t.iterrows():
            k = 0 if hi == lo else (r["V"] - lo) / (hi - lo)
            rgb = tuple(int(c0[i] + (c1[i] - c0[i]) * k) for i in range(3))
            fg = "#fff" if k > 0.6 else "#000"
            rows.append(
                f"<tr><td>{html.escape(str(r['Model']))}</td><td>{html.escape(str(r['Make']))}</td>"
                f"<td>{html.escape(str(r['EV Type']))}</td>"
                f"<td class='num' style='background:rgb{rgb};color:{fg}'>{r['V']:,}</td>"
                f"<td class='num'>{r['V'] / tot:.2%}</td></tr>")
        st.markdown(
            "<div class='mtable-wrap'><table class='mtable'><thead><tr>"
            "<th>Model</th><th>Make</th><th>EV Type</th>"
            "<th class='m'>Total Vehicles</th><th class='m'>% of Total</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>",
            unsafe_allow_html=True)
