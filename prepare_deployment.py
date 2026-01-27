import pandas as pd
import os
import glob

# Config
DATA_DIR = r"c:\Users\Kaiyan Zhang\Desktop\ntl_crime\data"
OUTPUT_DIR = r"c:\Users\Kaiyan Zhang\Desktop\ntl_crime\dashboard"
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
ID_COLS = ['state_abb', 'year', 'month', 'agency_name', 'fips_state_code', 'fips_place_code', 'population']

def create_optimized_dataset():
    crime_folder = os.path.join(DATA_DIR, "offenses_known_csv_1960_2024_month")
    all_files = glob.glob(os.path.join(crime_folder, "*.csv"))
    
    dfs = []
    
    # Only load 2012-2024 to save space as per user dashboard scope
    # Filenames are offenses_known_monthly_YYYY.csv
    
    print("Processing CSVs...")
    for f in all_files:
        filename = os.path.basename(f)
        try:
            year = int(filename.split('_')[-1].split('.')[0])
            if year < 2012 or year > 2024:
                continue
        except:
            continue
            
        print(f"Loading {filename}...")
        try:
            # Check cols first
            header = pd.read_csv(f, nrows=0).columns.tolist()
            available_cols = [c for c in ID_COLS + METRIC_COLS if c in header]
            
            # Load subset
            df = pd.read_csv(f, usecols=available_cols)
            
            # Optimize types
            # metrics -> int32 or float32
            # population -> float32
            for c in df.columns:
                if 'actual_' in c or c == 'population':
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
                if 'fips' in c:
                     df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)

            dfs.append(df)
        except Exception as e:
            print(f"Error {filename}: {e}")

    if not dfs:
        print("No data found.")
        return

    print("Concatenating...")
    full_df = pd.concat(dfs, ignore_index=True)
    
    print("Saving to Parquet...")
    # Use compression to minimize size
    output_path = os.path.join(OUTPUT_DIR, "crime_data_optimized.parquet")
    full_df.to_parquet(output_path, index=False, compression='brotli')
    
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Saved optimized parquet to {output_path}")
    print(f"Size: {size_mb:.2f} MB")

if __name__ == "__main__":
    create_optimized_dataset()
