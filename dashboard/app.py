import streamlit as st
import pandas as pd
import geopandas as gpd
import os
import plotly.express as px

# Set page config
st.set_page_config(page_title="Crime Data Dashboard", layout="wide")

st.title("United States Crime Trends Dashboard")

# Paths - Relative to this file for deployment
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

@st.cache_data
def get_state_mapping():
    """Returns a dataframe of State Name, Abbreviation, and FP code."""
    geo_path = os.path.join(DATA_DIR, "us_places.geojson")
    if not os.path.exists(geo_path):
        return pd.DataFrame()
    try:
        gdf = gpd.read_file(geo_path, encoding='latin-1', ignore_geometry=True)
    except:
         gdf = gpd.read_file(geo_path, encoding='latin-1')

    if 'STATEFP' in gdf.columns and 'STATE_NAME' in gdf.columns:
        return gdf[['STATE_NAME', 'STUSPS', 'STATEFP']].drop_duplicates().sort_values('STATE_NAME')
    return pd.DataFrame()

@st.cache_data
def load_geo_data(state_fp):
    """Loads geo data for a specific state."""
    geo_path = os.path.join(DATA_DIR, "us_places.geojson")
    if not os.path.exists(geo_path):
        return None
    
    gdf = gpd.read_file(geo_path, encoding='latin-1')
    
    # Filter for the specific state
    state_gdf = gdf[gdf['STATEFP'] == state_fp].copy()
    
    # Format Names
    state_gdf['NAME'] = state_gdf['NAME'].str.title()
    return state_gdf

@st.cache_data
def load_crime_data_long(state_abbr=None, national=False):
    """
    Loads compressed Parquet data.
    """
    parquet_path = os.path.join(DATA_DIR, "crime_data_optimized.parquet")
    if not os.path.exists(parquet_path):
        st.error("Data file not found.")
        return pd.DataFrame()

    try:
        if national:
            # Load full dataset for selected cols
            # If parquet is partitioned, we can pushdown. Here we just read and group.
            df = pd.read_parquet(parquet_path)
            
            # Helper to convert cols to numeric if needed (parquet preserves types usually)
            cols = [c for c in METRIC_COLS if c in df.columns]
            
            # Aggregation
            df = df.groupby(['state_abb', 'year', 'month'])[cols].sum().reset_index()
            
        else:
            # Filter by state immediately
            # pyarrow allows filtering on read which is memory efficient
            filters = [('state_abb', '==', state_abbr)] if state_abbr else None
            df = pd.read_parquet(parquet_path, filters=filters)

        if df.empty:
            return pd.DataFrame()

        # Pre-processing dates
        df['month_lower'] = df['month'].astype(str).str.lower()
        df['month_num'] = df['month_lower'].map(MONTH_MAP)
        df = df.dropna(subset=['month_num'])
        df['month_num'] = df['month_num'].astype(int)
        
        df['month_str'] = df['month_num'].astype(str).str.zfill(2)
        df['date'] = pd.to_datetime(df['year'].astype(str) + '-' + df['month_str'] + '-01', errors='coerce')

        if not national:
            # GEOID Logic
            df['fips_state_clean'] = pd.to_numeric(df['fips_state_code'], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(2)
            df['fips_place_clean'] = pd.to_numeric(df['fips_place_code'], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(5)
            df['GEOID'] = df['fips_state_clean'] + df['fips_place_clean']
            df['agency_name'] = df['agency_name'].str.title()

        # Melt
        id_vars = ['year', 'month_num', 'date']
        if national:
            id_vars += ['state_abb']
        else:
            id_vars += ['agency_name', 'state_abb', 'GEOID', 'population']

        existing_metrics = [c for c in METRIC_COLS if c in df.columns]
        
        df_long = df.melt(
            id_vars=id_vars,
            value_vars=existing_metrics,
            var_name='Crime Type', 
            value_name='Incidents'
        )
        
        df_long['Crime Type'] = df_long['Crime Type'].str.replace('actual_', '').str.replace('_', ' ').str.title()
        
        return df_long
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# --- Main Logic ---

# Sidebar
st.sidebar.header("Configuration")

analysis_level = st.sidebar.radio("Analysis Level", ["State Level", "National Level"])

# Filters Placeholder
selected_state_name = None
state_abbr = None
state_fp = None

if analysis_level == "State Level":
    # Load State List
    with st.spinner("Loading State List..."):
        state_map = get_state_mapping()
    
    if state_map.empty:
        st.error("Could not load state mapping.")
        st.stop()
    
    state_options = state_map['STATE_NAME'].tolist()
    default_ix = state_options.index("Alabama") if "Alabama" in state_options else 0
    selected_state_name = st.sidebar.selectbox("Select State", state_options, index=default_ix)
    
    state_row = state_map[state_map['STATE_NAME'] == selected_state_name].iloc[0]
    state_abbr = state_row['STUSPS']
    state_fp = state_row['STATEFP']
    
    with st.spinner(f"Loading Crime Data for {selected_state_name}..."):
        df = load_crime_data_long(state_abbr=state_abbr, national=False)
        
    with st.spinner("Loading Geography..."):
        gdf = load_geo_data(state_fp)

else:
    # National
    with st.spinner("Loading National Crime Data..."):
        df = load_crime_data_long(national=True)
        # We need full state names for visualization
        state_map = get_state_mapping()
        if not state_map.empty:
             df = df.merge(state_map[['STATE_NAME', 'STUSPS']], left_on='state_abb', right_on='STUSPS', how='left')
             df.rename(columns={'STATE_NAME': 'State Name'}, inplace=True)
        else:
             df['State Name'] = df['state_abb']

    gdf = None 


if df.empty:
    st.error("No data available.")
    st.stop()

# Common Filters
st.sidebar.subheader("Filters")
min_year = int(df['year'].min())
max_year = int(df['year'].max())
start_year, end_year = st.sidebar.slider("Select Year Range", min_year, max_year, (min_year, max_year))

available_types = sorted(df['Crime Type'].unique())
default_types = ["Index Total", "Index Violent"]
defaults = [t for t in default_types if t in available_types]
if not defaults: defaults = [available_types[0]]

selected_types = st.sidebar.multiselect("Select Crime Types", available_types, default=defaults)
if not selected_types: st.stop()

# Filter Data
filtered_df = df[
    (df['year'] >= start_year) & 
    (df['year'] <= end_year) & 
    (df['Crime Type'].isin(selected_types))
]

# --- Visualizations ---

col_trend, col_dist = st.columns([2, 1])

# Trend Chart
with col_trend:
    st.subheader("Crime Trends Over Time")
    trend_df = filtered_df.groupby(['date', 'Crime Type'])['Incidents'].sum().reset_index()
    fig_trend = px.line(
        trend_df, x='date', y='Incidents', color='Crime Type',
        title=f"Monthly Trends ({start_year}-{end_year})",
        labels={'date': 'Date', 'Incidents': 'Total Incidents'}
    )
    fig_trend.update_layout(xaxis_title="Date", yaxis_title="Total Incidents")
    st.plotly_chart(fig_trend, width="stretch")

# Distribution Chart
with col_dist:
    st.subheader("Distribution by Type")
    dist_df = filtered_df.groupby(['Crime Type'])['Incidents'].sum().reset_index()
    fig_dist = px.bar(
        dist_df, x='Crime Type', y='Incidents', color='Crime Type',
        title=f"Total Incidents ({start_year}-{end_year})",
        text_auto=True
    )
    fig_dist.update_layout(showlegend=False, xaxis_title="Crime Type", yaxis_title="Total Incidents")
    st.plotly_chart(fig_dist, width="stretch")

# --- Map ---
st.subheader("Geospatial Distribution")

map_metric = st.selectbox("Select Statistic for Map", ["Total Incidents", "Average Monthly Incidents"])
map_agg_func = 'sum' if map_metric == "Total Incidents" else 'mean'
st.caption(f"**Note:** '{map_metric}' represents the {map_metric.lower()} per location over the selected time period ({start_year}-{end_year}).")

if analysis_level == "National Level":
    # National Map
    agg_dict = {'Incidents': map_agg_func}
    if 'State Name' in filtered_df.columns:
         agg_dict['State Name'] = 'first'
         
    map_df = filtered_df.groupby('state_abb').agg(agg_dict).reset_index()
    
    hover_name = 'State Name' if 'State Name' in map_df.columns else 'state_abb'

    fig_map = px.choropleth(
        map_df,
        locations='state_abb',
        locationmode="USA-states",
        color='Incidents',
        hover_name=hover_name, 
        hover_data=['state_abb'],
        scope="usa",
        color_continuous_scale="Reds",
        title=f"{map_metric} by State ({start_year}-{end_year})"
    )
    fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    st.plotly_chart(fig_map, width="stretch")

else:
    # State Map (Place Level)
    if gdf is not None and not gdf.empty:
        group_cols = ['GEOID']
        
        map_df = filtered_df.groupby(group_cols).agg(
            Incidents=('Incidents', map_agg_func),
            Population=('population', 'max'), 
            Agency_Name=('agency_name', 'first')
        ).reset_index()
        
        merged_gdf = gdf.merge(map_df, on='GEOID', how='left')
        merged_gdf['Incidents'] = merged_gdf['Incidents'].fillna(0)
        merged_gdf['Population'] = merged_gdf['Population'].fillna(0).astype(int)
        
        centroid = merged_gdf.geometry.centroid
        avg_lat = centroid.y.mean()
        avg_lon = centroid.x.mean()
        
        fig_map = px.choropleth_mapbox(
            merged_gdf,
            geojson=merged_gdf.geometry.__geo_interface__,
            locations=merged_gdf.index,
            color='Incidents',
            hover_name='NAME',
            hover_data={'Agency_Name':True, 'Population': True},
            color_continuous_scale="Reds",
            mapbox_style="carto-positron",
            center={"lat": avg_lat, "lon": avg_lon},
            zoom=6,
            opacity=0.6,
            title=f"{map_metric} by Place ({start_year}-{end_year})"
        )
        fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
        st.plotly_chart(fig_map, width="stretch")
        
        with st.expander("Data Table"):
            st.dataframe(map_df.sort_values('Incidents', ascending=False).head(50))
    else:
        st.warning("Geography not available.")
