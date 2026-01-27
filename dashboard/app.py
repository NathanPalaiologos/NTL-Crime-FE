import streamlit as st
import pandas as pd
import geopandas as gpd
import os
import glob
import plotly.express as px

# --- Page Config ---

# Set page config
st.set_page_config(page_title="Crime Data Dashboard", layout="wide")

st.title("United States Crime Trends Dashboard")

# Paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

METRIC_COLS = [
    'actual_murder', 
    'actual_rape_total', 
    'actual_robbery_total', 
    'actual_assault_aggravated', 
    'actual_burglary_total', 
    'actual_theft_total', 
    'actual_motor_vehicle_theft_total', 
    'actual_arson',
    # 'actual_index_violent', 
    'actual_index_violent',
    'actual_index_property',
    'actual_index_total'
]

MONTH_MAP = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
}

# --- Data Loading ---

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
    Loads crime data.
    If national=True, aggregates by STATE.
    If state_abbr provided, filters by state and keeps AGENCY level detail.
    """
    crime_folder = os.path.join(DATA_DIR, "offenses_known_csv_1960_2024_month")
    all_files = glob.glob(os.path.join(crime_folder, "*.csv"))
    
    dfs = []
    
    # Columns to load
    # Basic IDs
    id_cols = ['state_abb', 'year', 'month']
    
    if not national:
        # We need detail columns for linking
        id_cols += ['ori', 'agency_name', 'fips_state_code', 'fips_place_code', 'population']
    
    cols_to_seek = set(id_cols + METRIC_COLS)
    
    for f in all_files:
        try:
            # Check headers
            header_row = pd.read_csv(f, nrows=0)
            file_cols = header_row.columns.tolist()
            available_cols = [c for c in file_cols if c in cols_to_seek]
            
            if 'state_abb' not in available_cols:
                 continue

            # Load data
            temp = pd.read_csv(f, usecols=available_cols)
            
            if not national and state_abbr:
                temp = temp[temp['state_abb'] == state_abbr]
            
            if not temp.empty:
                if national:
                    # Aggregate by state/year/month immediately
                     for m in METRIC_COLS:
                         if m in temp.columns:
                             temp[m] = pd.to_numeric(temp[m], errors='coerce').fillna(0)
                             
                     agg_cols = [c for c in METRIC_COLS if c in temp.columns]
                     temp = temp.groupby(['state_abb', 'year', 'month'])[agg_cols].sum().reset_index()
                
                dfs.append(temp)
        except Exception as e:
            continue
            
    if not dfs:
        return pd.DataFrame()
        
    full_df = pd.concat(dfs, ignore_index=True)
    
    # Map months to numbers
    # Ensure month column is string lower first
    full_df['month_lower'] = full_df['month'].astype(str).str.lower()
    full_df['month_num'] = full_df['month_lower'].map(MONTH_MAP)
    
    # Drop rows where month parse failed? Or keep as is?
    # If month_num is NaN, we can't make a date. Filter them out.
    full_df = full_df.dropna(subset=['month_num'])
    full_df['month_num'] = full_df['month_num'].astype(int)
    
    # Create Date Column
    full_df['month_str'] = full_df['month_num'].astype(str).str.zfill(2)
    full_df['date'] = pd.to_datetime(full_df['year'].astype(str) + '-' + full_df['month_str'] + '-01', errors='coerce')
    
    # Creating GEOID for place-level matches
    if not national:
        # FIPS State (2) + FIPS Place (5)
        full_df['fips_state_clean'] = pd.to_numeric(full_df['fips_state_code'], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(2)
        full_df['fips_place_clean'] = pd.to_numeric(full_df['fips_place_code'], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(5)
        full_df['GEOID'] = full_df['fips_state_clean'] + full_df['fips_place_clean']
        
        # Format strings
        full_df['agency_name'] = full_df['agency_name'].str.title()
    
    # Melt
    id_vars = ['year', 'month_num', 'date'] # Use month_num instead of raw string
    if national:
        id_vars += ['state_abb']
    else:
        id_vars += ['agency_name', 'state_abb', 'GEOID', 'population']

    existing_metrics = [c for c in METRIC_COLS if c in full_df.columns]
    
    df_long = full_df.melt(
        id_vars=id_vars,
        value_vars=existing_metrics,
        var_name='Crime Type', 
        value_name='Incidents'
    )
    
    # Clean up crime type names
    df_long['Crime Type'] = df_long['Crime Type'].str.replace('actual_', '').str.replace('_', ' ').str.title()
    
    return df_long

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
        # We need full state names for better visualization
        state_map = get_state_mapping()
        if not state_map.empty:
             df = df.merge(state_map[['STATE_NAME', 'STUSPS']], left_on='state_abb', right_on='STUSPS', how='left')
             # Renaming for clarity in Hover
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
    # Ensure axes capitalized
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

# Explanation of metric
st.caption(f"**Note:** '{map_metric}' represents the {map_metric.lower()} per location over the selected time period ({start_year}-{end_year}).")

if analysis_level == "National Level":
    # National Map
    # Group by State
    agg_dict = {'Incidents': map_agg_func}
    if 'State Name' in filtered_df.columns:
         agg_dict['State Name'] = 'first'
         
    map_df = filtered_df.groupby('state_abb').agg(agg_dict).reset_index()
    
    hover_cols = {'Incidents': True, 'state_abb': True}
    if 'State Name' in map_df.columns:
        hover_name = 'State Name'
    else:
        hover_name = 'state_abb'

    fig_map = px.choropleth(
        map_df,
        locations='state_abb',
        locationmode="USA-states",
        color='Incidents',
        hover_name=hover_name, # Full name in hover
        hover_data=['state_abb'], # Add Code to hover too
        scope="usa",
        color_continuous_scale="Reds",
        title=f"{map_metric} by State ({start_year}-{end_year})"
    )
    fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    st.plotly_chart(fig_map, width="stretch")

else:
    # State Map (Place Level)
    if gdf is not None and not gdf.empty:
        # Aggregation by GEOID
        group_cols = ['GEOID']
        
        map_df = filtered_df.groupby(group_cols).agg(
            Incidents=('Incidents', map_agg_func),
            Population=('population', 'max'), 
            Agency_Name=('agency_name', 'first')
        ).reset_index()
        
        # Merge with Geo
        merged_gdf = gdf.merge(map_df, on='GEOID', how='left')
        merged_gdf['Incidents'] = merged_gdf['Incidents'].fillna(0)
        
        merged_gdf['Population'] = merged_gdf['Population'].fillna(0).astype(int)
        
        # Center map
        centroid = merged_gdf.geometry.centroid
        avg_lat = centroid.y.mean()
        avg_lon = centroid.x.mean()
        
        fig_map = px.choropleth_mapbox(
            merged_gdf,
            geojson=merged_gdf.geometry.__geo_interface__,
            locations=merged_gdf.index,
            color='Incidents',
            hover_name='NAME',
            hover_data={'Agency_Name':True, 'Population': True}, # Population in hover
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
