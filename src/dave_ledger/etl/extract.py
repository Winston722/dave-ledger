import nflreadpy as nfl
import pandas as pd

from dave_ledger.core import config, paths

def extract_xfp_data():
    """
    Downloads Expected Fantasy Points (xFP) from nflverse.
    Iterates through each year to build the full history.
    """
    cfg = config.load_config()
    current_year = cfg['context']['current_year']
    history_years = cfg['context']['history_years']
    
    # Calculate years window
    years = [current_year - i for i in range(history_years)]
    # The URL pattern for year-specific files
    base_url = "https://github.com/ffverse/ffopportunity/releases/download/latest-data/ep_weekly_{}.parquet"
    
    raw_dir = paths.find_repo_root() / "data" / "raw"
    # Ensure directory exists
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = raw_dir / f"xfp_{min(years)}_{max(years)}.parquet"
    
    all_years_data = []
    
    for year in years:
        url = base_url.format(year)
        print(f"   -> Downloading xFP for {year}...")
        
        try:
            df_year = pd.read_parquet(url)
            
            # Safety Check: Ensure 'season' column exists for the merge later
            if 'season' not in df_year.columns:
                df_year['season'] = year
                
            all_years_data.append(df_year)
            
        except Exception as e:
            # We log as a warning so the whole pipeline doesn't crash if one year is missing
            print(f"   ⚠️ Failed to download {year}: {e}")

    if all_years_data:
        # Stack all years together
        df_final = pd.concat(all_years_data, ignore_index=True)
        
        # Save to disk
        df_final.to_parquet(output_path)
        print(f"   -> ✅ Saved {len(df_final):,} rows of xFP data to {output_path.name}")
    else:
        print("❌ No xFP data could be extracted.")


def update_data():
    """
    Downloads the latest 5 years of data from nflverse 
    and saves it to data/raw.
    """
    cfg = config.load_config()
    current_year = cfg['context']['current_year']
    history_years = cfg['context']['history_years']
    
    # Calculate years window
    years = [current_year - i for i in range(history_years)]
    print(f"⬇️  Starting Ingest for window: {years}")

    # Setup Paths
    raw_dir = paths.find_repo_root() / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    suffix = f"{years[-1]}_{years[0]}.parquet"
    files = {
        "weekly": raw_dir / f"weekly_{suffix}",
        "snaps": raw_dir / f"snaps_{suffix}",
        "rosters": raw_dir / f"rosters_{suffix}"
    }

    # 1. Weekly Stats
    print("   -> Downloading Weekly Stats...")
    df_weekly = nfl.load_player_stats(seasons=years).to_pandas()
    df_weekly = df_weekly[df_weekly['season_type'] == 'REG']
    df_weekly.to_parquet(files["weekly"], index=False)

    # 2. Snap Counts
    print("   -> Downloading Snap Counts...")
    df_snaps = nfl.load_snap_counts(seasons=years).to_pandas()
    df_snaps.to_parquet(files["snaps"], index=False)

    # 3. Rosters
    print("   -> Downloading Rosters...")
    df_rosters = nfl.load_rosters(seasons=years).to_pandas()
    df_rosters.to_parquet(files["rosters"], index=False)

    print(f"✅ Ingest Complete. Data saved to {raw_dir}")

if __name__ == "__main__":
    update_data()
    extract_xfp_data()