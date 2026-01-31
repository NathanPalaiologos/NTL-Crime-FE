import streamlit as st
import pandas as pd
import geopandas as gpd
import os
import plotly.express as px
import plotly.graph_objects as go
from statsmodels.tsa.stattools import acf, pacf

# Set page config
st.set_page_config(page_title="Crime Data Dashboard", layout="wide")

st.title("United States Crime Trends Dashboard")

# Paths
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

METRIC_COLS = [
    'actual_murder', 
    'actual_rape_total', 
    'actual_robbery_total', 
    'actual_assault_aggravated', 
    'actual_burglary_total', 
    'actual_theft_total', 
    'actual_motor_vehicle_theft_total', 
    'actual_arson', 
    'actual_index_violent',
    'actual_index_property',
    'actual_index_total'
]

MONTH_MAP = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
}

# --- Utils ---
def filter_map_types(selected_types):
    if not selected_types:
        return []
    final_types = set(selected_types)
    if "Index Total" in final_types:
        return ["Index Total"]
    violent_sub = ["Murder", "Rape Total", "Robbery Total", "Assault Aggravated"]
    property_sub = ["Burglary Total", "Theft Total", "Motor Vehicle Theft Total", "Arson"]
    if "Index Violent" in final_types:
        for t in violent_sub:
            if t in final_types: final_types.remove(t)
    if "Index Property" in final_types:
        for t in property_sub:
            if t in final_types: final_types.remove(t)
    return list(final_types)

@st.cache_data
def get_state_mapping():
    geo_path = os.path.join(DATA_DIR, "us_places.geojson")
    if not os.path.exists(geo_path): return pd.DataFrame()
    try:
        gdf = gpd.read_file(geo_path, encoding='latin-1', ignore_geometry=True)
    except:
         gdf = gpd.read_file(geo_path, encoding='latin-1')
    if 'STATEFP' in gdf.columns and 'STATE_NAME' in gdf.columns:
        return gdf[['STATE_NAME', 'STUSPS', 'STATEFP']].drop_duplicates().sort_values('STATE_NAME')
    return pd.DataFrame()

@st.cache_data
def load_geo_data(state_fp):
    geo_path = os.path.join(DATA_DIR, "us_places.geojson")
    if not os.path.exists(geo_path): return None
    gdf = gpd.read_file(geo_path, encoding='latin-1')
    state_gdf = gdf[gdf['STATEFP'] == state_fp].copy()
    state_gdf['NAME'] = state_gdf['NAME'].str.title()
    return state_gdf

@st.cache_data
def load_crime_data_long(state_abbr=None, national=False):
    parquet_path = os.path.join(DATA_DIR, "crime_data_optimized.parquet")
    if not os.path.exists(parquet_path):
        st.error("Data file not found.")
        return pd.DataFrame()

    try:
        if national:
            df = pd.read_parquet(parquet_path)
            cols = [c for c in METRIC_COLS if c in df.columns]
            if 'population' in df.columns: cols.append('population') 
            df = df.groupby(['state_abb', 'year', 'month'])[cols].sum().reset_index()
            
        else:
            filters = [('state_abb', '==', state_abbr)] if state_abbr else None
            df = pd.read_parquet(parquet_path, filters=filters)

        if df.empty: return pd.DataFrame()

        df['month_lower'] = df['month'].astype(str).str.lower()
        df['month_num'] = df['month_lower'].map(MONTH_MAP)
        df = df.dropna(subset=['month_num'])
        df['month_num'] = df['month_num'].astype(int)
        df['month_str'] = df['month_num'].astype(str).str.zfill(2)
        df['date'] = pd.to_datetime(df['year'].astype(str) + '-' + df['month_str'] + '-01', errors='coerce')

        if not national:
            df['fips_state_clean'] = pd.to_numeric(df['fips_state_code'], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(2)
            df['fips_place_clean'] = pd.to_numeric(df['fips_place_code'], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(5)
            df['GEOID'] = df['fips_state_clean'] + df['fips_place_clean']
            df['agency_name'] = df['agency_name'].str.title()

        id_vars = ['year', 'month_num', 'date']
        if 'population' in df.columns: id_vars.append('population')
        if national: id_vars += ['state_abb']
        else: id_vars += ['agency_name', 'state_abb', 'GEOID']

        existing_metrics = [c for c in METRIC_COLS if c in df.columns]
        df_long = df.melt(id_vars=id_vars, value_vars=existing_metrics, var_name='Crime Type', value_name='Incidents')
        df_long['Crime Type'] = df_long['Crime Type'].str.replace('actual_', '').str.replace('_', ' ').str.title()
        return df_long
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# --- Sidebar ---
st.sidebar.header("Data Configuration")
analysis_level = st.sidebar.radio("Analysis Level", ["State Level", "National Level"])

selected_state_name = None
state_abbr = None
state_fp = None

if analysis_level == "State Level":
    with st.spinner("Loading..."):
        state_map = get_state_mapping()
    state_options = state_map['STATE_NAME'].tolist()
    default_ix = state_options.index("Alabama") if "Alabama" in state_options else 0
    selected_state_name = st.sidebar.selectbox("Select State", state_options, index=default_ix)
    state_row = state_map[state_map['STATE_NAME'] == selected_state_name].iloc[0]
    state_abbr = state_row['STUSPS']
    state_fp = state_row['STATEFP']
    with st.spinner("Fetching Data..."):
        df = load_crime_data_long(state_abbr=state_abbr, national=False)
        gdf = load_geo_data(state_fp)
else:
    with st.spinner("Fetching Data..."):
        df = load_crime_data_long(national=True)
        state_map = get_state_mapping()
        if not state_map.empty:
             df = df.merge(state_map[['STATE_NAME', 'STUSPS']], left_on='state_abb', right_on='STUSPS', how='left')
             df.rename(columns={'STATE_NAME': 'State Name'}, inplace=True)
        else: df['State Name'] = df['state_abb']
    gdf = None

if df.empty:
    st.error("No data available.")
    st.stop()

st.sidebar.subheader("Time Filters")
min_year = int(df['year'].min())
max_year = int(df['year'].max())
start_year, end_year = st.sidebar.slider("Year Range", min_year, max_year, (min_year, max_year))

st.sidebar.subheader("Crime Types")
available_types = sorted(df['Crime Type'].unique())
default_types = ["Index Total", "Index Violent"]
defaults = [t for t in default_types if t in available_types]
if not defaults: defaults = [available_types[0]]
selected_types = st.sidebar.multiselect("Select Types", available_types, default=defaults)
if not selected_types: st.stop()

# --- Econometrics Sidebar ---
st.sidebar.markdown("---")
st.sidebar.header("Econometrics Controls")

# 1. Metric: Rate vs Count
metric_choice = st.sidebar.radio("Map Metric Scale", ["Total Incidents", "Crime Rate (per 100k Population)"])

# 2. Fixed Effects Toggle
use_fixed_effects = st.sidebar.checkbox("De-mean Monthly Regional Effects")
st.sidebar.caption("Subtracts the average value for each month (Jan-Dec) specific to each geographic unit to remove seasonality.")

# --- Data Processing (FE) ---

filtered_df = df[
    (df['year'] >= start_year) & 
    (df['year'] <= end_year) & 
    (df['Crime Type'].isin(selected_types))
].copy()

if use_fixed_effects:
    # Calculate Monthly Means per Unit
    # Unit ID depends on level: National=state_abb, State=GEOID
    unit_col = 'state_abb' if analysis_level == "National Level" else 'GEOID'
    
    # We calculate the mean for each (Unit, Month, Crime Type) tuple
    # This represents the "seasonal norm" for that unit and crime
    monthly_means = filtered_df.groupby([unit_col, 'month_num', 'Crime Type'])['Incidents'].transform('mean')
    
    # De-mean
    filtered_df['Incidents_Raw'] = filtered_df['Incidents']
    filtered_df['Incidents'] = filtered_df['Incidents'] - monthly_means
    
    # Note on Population for Rate de-meaning?
    # Usually we de-mean the outcome variable. 
    # If the user selects Rate, we should probably de-mean the Rate, not the Count.
    # Refinement: Calculate Rate first, then De-mean the Rate/Count.
    
    # Let's adjust logic: Calculate Metric First (Count or Rate), then De-mean that metric.

# Recalculate 'Value' for analysis based on Metric Choice
def calculate_metric(row):
    val = row['Incidents']
    pop = row['population'] if 'population' in row else 0
    
    if use_fixed_effects and 'Incidents_Raw' in row:
        # If we already demeaned incidents, we use that for "Total Incidents" mode
        # But for Rate mode, we need to demean the rate.
        pass # handled below block in vectorized way
    return val

# Standardize Metric Calculation
if metric_choice == "Crime Rate (per 100k Population)":
    # Rate = (Count / Pop) * 100k
    # Avoid zero div
    filtered_df['Metric_Value'] = (filtered_df['Incidents'] / filtered_df['population'].replace(0, 1)) * 100000
    filtered_df.loc[filtered_df['population'] == 0, 'Metric_Value'] = 0
else:
    filtered_df['Metric_Value'] = filtered_df['Incidents']

# Apply FE to the Metric_Value directly
if use_fixed_effects:
    unit_col = 'state_abb' if analysis_level == "National Level" else 'GEOID'
    # Re-calculate means on the *Metric_Value*
    monthly_means_metric = filtered_df.groupby(['month_num', 'Crime Type'])['Metric_Value'].transform('mean')
    filtered_df['Metric_Value'] = filtered_df['Metric_Value'] - monthly_means_metric


# --- Visualizations ---

col_trend, col_dist = st.columns([2, 1])

# Trend Chart
with col_trend:
    st.subheader("Time Series Analysis")
    # Aggregation for Plotting
    # Summing Metric Values across all units for the timeline?
    # If FE is on, Sum of (Value - Mean) might be close to zero if frames align, 
    # but informative if looking at deviations.
    trend_df = filtered_df.groupby(['date', 'Crime Type'])['Metric_Value'].sum().reset_index()
    
    y_label = "De-meaned Value" if use_fixed_effects else metric_choice
    
    fig_trend = px.line(
        trend_df, x='date', y='Metric_Value', color='Crime Type',
        title=f"Trends ({y_label})",
        labels={'date': 'Date', 'Metric_Value': y_label}
    )
    # Add horizontal zero line for FE
    if use_fixed_effects:
        fig_trend.add_hline(y=0, line_dash="dash", line_color="gray")
    
    st.plotly_chart(fig_trend, width="stretch")

# Distribution Chart
with col_dist:
    st.subheader("Distribution")
    # Note: If FE is on, this shows net deviation from seasonal norm
    dist_df = filtered_df.groupby(['Crime Type'])['Metric_Value'].sum().reset_index()
    fig_dist = px.bar(
        dist_df, x='Crime Type', y='Metric_Value', color='Crime Type',
        title=f"Total {y_label}",
        text_auto=True
    )
    fig_dist.update_layout(showlegend=False, xaxis_title="Crime Type", yaxis_title=y_label)
    st.plotly_chart(fig_dist, width="stretch")


# --- Map ---
st.subheader("Geospatial Distribution")

map_types = filter_map_types(selected_types)
map_filtered_df = filtered_df[filtered_df['Crime Type'].isin(map_types)].copy()

if len(map_types) < len(selected_types):
    removed = set(selected_types) - set(map_types)
    st.info(f"**Map Note:** Sub-types merged into parents: {', '.join(removed)}")


# Map Aggregation
# If FE is on, we are mapping the "Average Deviation from Meaning" over the period
# If period is long, it should average to 0. If period is a specific bad month, we see hotspots.
aggs = {'Metric_Value': 'sum', 'population': 'mean'}
if analysis_level == "National Level":
    group_col = 'state_abb'
else:
    group_col = 'GEOID' # Agency

# Add extraCols
extras = {}
if analysis_level == "National Level":
    if 'State Name' in map_filtered_df.columns: extras['State Name'] = 'first'
else:
    extras['agency_name'] = 'first'

aggs.update(extras)

map_df = map_filtered_df.groupby(group_col).agg(aggs).reset_index()

# Color Scale logic: If FE, use diverging. Else sequential.
color_scale = "RdBu_r" if use_fixed_effects else "Reds"
# For RdBu_r, 0 should be middle.
cmid = 0 if use_fixed_effects else None

hover_name = 'State Name' if analysis_level == "National Level" and 'State Name' in map_df.columns else ('agency_name' if 'agency_name' in map_df.columns else group_col)
hover_cols = {'Metric_Value': True, 'population': True}

if analysis_level == "National Level":
    fig_map = px.choropleth(
        map_df,
        locations='state_abb',
        locationmode="USA-states",
        color='Metric_Value',
        hover_name=hover_name,
        hover_data=hover_cols,
        scope="usa",
        color_continuous_scale=color_scale,
        color_continuous_midpoint=cmid,
        title=f"{y_label} by State"
    )
else:
    if gdf is not None and not gdf.empty:
        merged_gdf = gdf.merge(map_df, on='GEOID', how='left')
        merged_gdf['Metric_Value'] = merged_gdf['Metric_Value'].fillna(0)
        
        centroid = merged_gdf.geometry.centroid
        fig_map = px.choropleth_mapbox(
            merged_gdf,
            geojson=merged_gdf.geometry.__geo_interface__,
            locations=merged_gdf.index,
            color='Metric_Value',
            hover_name='NAME',
            hover_data=extras,
            color_continuous_scale=color_scale,
            color_continuous_midpoint=cmid,
            mapbox_style="carto-positron",
            center={"lat": centroid.y.mean(), "lon": centroid.x.mean()},
            zoom=6,
            opacity=0.6,
            title=f"{y_label} by Place"
        )
    else:
        fig_map = None

if fig_map:
    fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    st.plotly_chart(fig_map, width="stretch")


# --- Advanced Econometrics: ACF/PACF ---
st.markdown("---")
st.header("Advanced Time Series Analysis")
st.markdown("Autocorrelation and Partial Autocorrelation plots for the aggregated time series.")

with st.expander("Show Autocorrelation Plots", expanded=True):
    # Controls
    acf_col1, acf_col2 = st.columns(2)
    with acf_col1:
        target_series_type = st.selectbox("Select Crime Type for ACF", selected_types)
    with acf_col2:
        apply_diff = st.checkbox("Apply First Differencing (d=1)")
    
    # Prepare Data
    # Filter for single series (Aggregate over all units for the selected analysis level)
    ts_data = filtered_df[filtered_df['Crime Type'] == target_series_type].groupby('date')['Metric_Value'].sum().sort_index()
    
    if apply_diff:
        ts_data = ts_data.diff().dropna()
        st.caption("First differencing applied: $y_t' = y_t - y_{t-1}$")
    
    if len(ts_data) > 2:
        lags = min(40, len(ts_data)//2 - 1)
        
        # ACF
        acf_vals = acf(ts_data, nlags=lags)
        fig_acf = px.bar(x=list(range(len(acf_vals))), y=acf_vals, labels={'x':'Lag', 'y':'Autocorrelation'}, title=f"ACF: {target_series_type}")
        fig_acf.update_yaxes(range=[-1.1, 1.1])
        
        # PACF
        try:
            pacf_vals = pacf(ts_data, nlags=lags)
            fig_pacf = px.bar(x=list(range(len(pacf_vals))), y=pacf_vals, labels={'x':'Lag', 'y':'Partial Autocorrelation'}, title=f"PACF: {target_series_type}")
            fig_pacf.update_yaxes(range=[-1.1, 1.1])
        except:
             fig_pacf = None
             st.warning("Not enough data points for PACF.")

        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(fig_acf, key="acf_plot")
        with c2: 
            if fig_pacf: st.plotly_chart(fig_pacf, key="pacf_plot")
    else:
        st.warning("Not enough data for time series analysis.")

