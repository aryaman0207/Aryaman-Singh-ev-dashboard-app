import os

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------- Page setup ----------
st.set_page_config(page_title="EV Population Dashboard", page_icon="⚡", layout="wide")
st.title("⚡ Electric Vehicle Population Dashboard")
st.caption("Data Visualization project | Built with Python, Streamlit and Plotly")

BEV = "Battery Electric Vehicle (BEV)"
PHEV = "Plug-in Hybrid Electric Vehicle (PHEV)"
CAFV_COL = "Clean Alternative Fuel Vehicle (CAFV) Eligibility"

SMALL_FILE = "ev_data_small.csv"
FULL_FILE = "Electric_Vehicle_Population_Data.csv"


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
    # Prefer the small file (fast). Fall back to the full original CSV.
    if os.path.exists(SMALL_FILE):
        df = pd.read_csv(SMALL_FILE)
        df.columns = [c.strip() for c in df.columns]
        return df
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
    st.error(
        f"CSV not found. Put '{FULL_FILE}' (or '{SMALL_FILE}') in the same folder as app.py"
    )
    st.stop()

# ---------- Sidebar filters ----------
st.sidebar.header("Filters")

yr_min, yr_max = int(df["Model Year"].min()), int(df["Model Year"].max())
years = st.sidebar.slider("Model Year", yr_min, yr_max, (yr_min, yr_max))

types = sorted(df["Electric Vehicle Type"].dropna().unique())
sel_types = st.sidebar.multiselect("Electric Vehicle Type", types, default=types)

makes = sorted(df["Make"].dropna().unique())
sel_makes = st.sidebar.multiselect("Make (empty = all)", makes)

top_n = st.sidebar.slider("Top N (Make / Model charts)", 1, 15, 10)

f = df[df["Model Year"].between(*years) & df["Electric Vehicle Type"].isin(sel_types)]
if sel_makes:
    f = f[f["Make"].isin(sel_makes)]

if f.empty:
    st.warning("No data for these filters.")
    st.stop()

# ---------- KPI cards ----------
total = f["DOL Vehicle ID"].nunique()
bev = f.loc[f["Electric Vehicle Type"] == BEV, "DOL Vehicle ID"].nunique()
phev = f.loc[f["Electric Vehicle Type"] == PHEV, "DOL Vehicle ID"].nunique()
avg_range = f["Electric Range"].mean()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Vehicles", f"{total:,}")
k2.metric("Avg Electric Range (mi)", f"{avg_range:,.1f}")
k3.metric("Total BEV", f"{bev:,}", f"{bev / total:.1%} of total", delta_color="off")
k4.metric("Total PHEV", f"{phev:,}", f"{phev / total:.1%} of total", delta_color="off")

st.divider()

# ---------- Row 1: Model Year trend + CAFV donut ----------
c1, c2 = st.columns([3, 2])

by_year = f.groupby("Model Year")["DOL Vehicle ID"].nunique().reset_index(name="Vehicles")
fig = px.area(by_year, x="Model Year", y="Vehicles", title="Total Vehicles by Model Year", markers=True)
c1.plotly_chart(fig, use_container_width=True)

cafv = f.groupby(CAFV_COL)["DOL Vehicle ID"].nunique().reset_index(name="Vehicles")
fig = px.pie(
    cafv,
    names=CAFV_COL,
    values="Vehicles",
    hole=0.45,
    title="Vehicles by CAFV Eligibility",
)
fig.update_layout(legend=dict(orientation="h", y=-0.2))
c2.plotly_chart(fig, use_container_width=True)

# ---------- Row 2: Top N Make + Top N Model ----------
c3, c4 = st.columns(2)

by_make = f.groupby("Make")["DOL Vehicle ID"].nunique().nlargest(top_n).reset_index(name="Vehicles")
fig = px.bar(
    by_make.sort_values("Vehicles"),
    x="Vehicles",
    y="Make",
    orientation="h",
    text="Vehicles",
    title=f"Top {top_n} Makes by Total Vehicles",
)
c3.plotly_chart(fig, use_container_width=True)

by_model = (
    f.groupby(["Make", "Model"])["DOL Vehicle ID"].nunique().nlargest(top_n).reset_index(name="Vehicles")
)
by_model["Make - Model"] = by_model["Make"] + " " + by_model["Model"]
fig = px.bar(
    by_model.sort_values("Vehicles"),
    x="Vehicles",
    y="Make - Model",
    orientation="h",
    text="Vehicles",
    title=f"Top {top_n} Models by Total Vehicles",
)
c4.plotly_chart(fig, use_container_width=True)

# ---------- Row 3: Map by state + BEV vs PHEV pie ----------
c5, c6 = st.columns([3, 2])

by_state = f.groupby("State")["DOL Vehicle ID"].nunique().reset_index(name="Vehicles")
fig = px.choropleth(
    by_state,
    locations="State",
    locationmode="USA-states",
    color="Vehicles",
    scope="usa",
    color_continuous_scale="Blues",
    title="Total Vehicles by State",
)
c5.plotly_chart(fig, use_container_width=True)

type_split = f.groupby("Electric Vehicle Type")["DOL Vehicle ID"].nunique().reset_index(name="Vehicles")
fig = px.pie(type_split, names="Electric Vehicle Type", values="Vehicles", title="BEV vs PHEV")
fig.update_layout(legend=dict(orientation="h", y=-0.2))
c6.plotly_chart(fig, use_container_width=True)

# ---------- Data table ----------
with st.expander("View filtered data"):
    st.dataframe(f.head(1000), use_container_width=True)
    st.download_button("Download filtered CSV", f.to_csv(index=False), "filtered_ev_data.csv", "text/csv")
