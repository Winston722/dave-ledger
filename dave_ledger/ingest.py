import nflreadpy as nfl
import pandas as pd
from dave_ledger import paths, config

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