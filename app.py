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
GREEN_PIE = ["#2a6b3c", "#6bb26b", "#a5d89a", "#cfe9c6"]  # dark -> light green like your donut
 
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
div[data-testid="stVerticalBlock"] {{gap: 0.5rem;}}
.dash-title {{background: #ccffe8; font-weight: 700; font-size: 27px; padding: 6px 10px; color: #333;}}
.st-key-leftpanel {{background: #ccffe8; padding: 10px;}}
.ctitle {{background: {TITLE_BG}; color: {RED}; font-weight: 700; font-size: 16px; padding: 6px 8px;}}
.kpi {{background: #fff; border: 1px solid #eee; padding: 8px 12px; min-height: 120px; text-align: center;}}
.kpi-label {{color: {RED}; font-weight: 700; font-size: 16px;}}
.kpi-value {{font-weight: 700; font-size: 30px;}}
.kpi-pct {{color: {BLUE}; font-weight: 700; font-size: 19px;}}
.mtable-wrap {{max-height: 300px; overflow-y: auto; border: 1px solid #eee;}}
.mtable {{border-collapse: collapse; width: 100%; font-size: 12px;}}
.mtable th {{position: sticky; top: 0; background: {HEADER}; padding: 3px 6px; text-align: left;}}
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
 
def classify_type(v):
    u = str(v).upper()
    if "PHEV" in u or "PLUG" in u or "HYBRID" in u:
        return "PHEV"
    if "BEV" in u or "BATTERY" in u:
        return "BEV"
    return str(v).strip()
 
 
def classify_cafv(v):
    u = str(v).upper()
    if "UNKNOWN" in u:
        return "CAFV Unknown"
    if "NOT ELIGIBLE" in u:
        return "CAFV Not eligible"
    if "ELIGIBLE" in u:
        return "CAFV Eligible"
    return str(v).strip()
 
 
CAFV_ORDER = ["CAFV Eligible", "CAFV Unknown", "CAFV Not eligible"]
df["CAFV"] = df[CAFV_COL].map(classify_cafv)
df["EV Type"] = df["Electric Vehicle Type"].map(classify_type)
 
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
 
 
def inr(n):
    """Indian digit grouping like Tableau (en_IN): 150413 -> 1,50,413"""
    s_ = str(int(n))
    if len(s_) <= 3:
        return s_
    head, tail, groups = s_[:-3], s_[-3:], []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups + [tail])
 
 
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
    with st.container(key="leftpanel"):
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
    bev = count(full[full["EV Type"] == "BEV"])
    phev = count(full[full["EV Type"] == "PHEV"])
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi("Avg Electric Range", f"{full['Electric Range'].mean():,.2f} Miles")
    with k2:
        kpi("Total Vehicles", inr(total))
    with k3:
        kpi("Total BEV Vehicles", inr(bev), bev / total)
    with k4:
        kpi("Total PHEV Vehicles", inr(phev), phev / total)
 
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
        fig.update_layout(height=340, showlegend=False, margin=dict(l=5, r=5, t=10, b=5),
                          xaxis=dict(type="category", tickangle=-90, tickfont=dict(size=8), showgrid=False),
                          yaxis=dict(visible=False, showgrid=False, range=[0, by_year["V"].max() * 1.12]),
                          plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True, config=CFG)
 
    with r2b:
        ctitle("Total Vehicles By State")
        by_state = (map_data.groupby("State")["DOL Vehicle ID"].nunique().reset_index(name="V"))
        fig = go.Figure()
        fig.add_trace(go.Choropleth(locations=by_state["State"], z=by_state["V"], locationmode="USA-states",
                                    colorscale=[[0, "#c9e8bd"], [1, "#2a6b3c"]], showscale=False,
                                    marker_line_color="white",
                                    hovertemplate="%{location}: %{z:,}<extra></extra>"))
        fig.add_trace(go.Scattergeo(locations=by_state["State"], locationmode="USA-states",
                                    text=[inr(v) for v in by_state["V"]], mode="text",
                                    textfont=dict(size=8), hoverinfo="skip"))
        fig.update_layout(height=340, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                          geo=dict(scope="usa", showlakes=False, bgcolor="white", showland=True, landcolor="#ececec", showsubunits=True, subunitcolor="#ffffff", showframe=False), clickmode="event+select")
        st.plotly_chart(fig, use_container_width=True, config=CFG, key=STATE_KEY,
                        on_select="rerun", selection_mode="points")
 
    # ---------- ROW 3: Top N Make | CAFV pie | Model table ----------
    r3a, r3b, r3c = st.columns([27, 22, 36])
 
    with r3a:
        tt1, tt2 = st.columns([3, 1])
        with tt2:
            top_n = int(st.number_input("Top N", min_value=1, max_value=15, value=10, step=1,
                                        label_visibility="collapsed"))
        with tt1:
            ctitle(f"Top {top_n} Total Vehicles By Make")
        by_make = make_data.groupby("Make")["DOL Vehicle ID"].nunique().nlargest(top_n).reset_index(name="V")
        by_make = by_make.sort_values(["V", "Make"], ascending=[False, True])  # highest first, like Tableau
        tot = by_make["V"].sum()
        fig = go.Figure(go.Bar(
            x=by_make["V"], y=by_make["Make"], orientation="h", marker_color=BAR,
            text=[f"{inr(v)} ; {v / tot:.2%}" for v in by_make["V"]], textposition="outside",
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
        cafv_raw = full.groupby("CAFV")["DOL Vehicle ID"].nunique().reset_index(name="V")
        cafv_raw["o"] = cafv_raw["CAFV"].map(lambda n: CAFV_ORDER.index(n) if n in CAFV_ORDER else 99)
        cafv_raw = cafv_raw.sort_values(["o", "CAFV"])
        tot = cafv_raw["V"].sum()
        labels = cafv_raw["CAFV"].tolist()
        text = [f"{l}<br>{inr(v)} ; {v / tot:.2%}" for l, v in zip(labels, cafv_raw["V"])]
        fig = go.Figure(go.Pie(labels=labels, values=cafv_raw["V"], hole=0.72, sort=False,
                               marker=dict(colors=GREEN_PIE[:len(labels)]),
                               text=text, textinfo="text", textposition="outside",
                               textfont=dict(size=9), hoverinfo="skip"))
        fig.update_layout(height=300, margin=dict(l=30, r=30, t=20, b=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config=CFG)
 
    with r3c:
        ctitle("Total Vehicles By Model")
        t = (full.groupby(["Model", "Make", "EV Type"])["DOL Vehicle ID"].nunique().reset_index(name="V")
             .sort_values(["V", "Model"], ascending=[False, True]))
        tot = t["V"].sum()
        lo, hi = t["V"].min(), t["V"].max()
        c0, c1 = (214, 238, 203), (30, 100, 55)
        rows = []
        for _, r in t.iterrows():
            k = 0 if hi == lo else (r["V"] - lo) / (hi - lo)
            rgb = tuple(int(c0[i] + (c1[i] - c0[i]) * k) for i in range(3))
            fg = "#fff" if k > 0.6 else "#000"
            rows.append(
                f"<tr><td>{html.escape(str(r['Model']))}</td><td>{html.escape(str(r['Make']))}</td>"
                f"<td>{html.escape(str(r['EV Type']))}</td>"
                f"<td class='num' style='background:rgb{rgb};color:{fg}'>{inr(r['V'])}</td>"
                f"<td class='num' style='background:rgb{rgb};color:{fg}'>{r['V'] / tot:.2%}</td></tr>")
        st.markdown(
            "<div class='mtable-wrap'><table class='mtable'><thead><tr>"
            "<th>Model</th><th>Make</th><th>EV Type</th>"
            "<th class='m'>Total Vehicles</th><th class='m'>% of Total</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>",
            unsafe_allow_html=True)