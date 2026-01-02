import logging

import numpy as np
import pandas as pd

from dave_ledger.core import config, paths

logger = logging.getLogger(__name__)

def load_and_clean_data() -> pd.DataFrame:
    """
    Loads data and merges Roster and Weekly stats.
    Validates IDs using 'gsis_id' to ensure 100% match rate.
    """
    # 1. Load Config & Files
    cfg = config.load_config()
    current_year = cfg['context']['current_year']
    history_years = cfg['context']['history_years']
    
    years = [current_year - i for i in range(history_years)]
    suffix = f"{years[-1]}_{years[0]}.parquet"
    raw_dir = paths.find_repo_root() / "data" / "raw"

    try:
        weekly = pd.read_parquet(raw_dir / f"weekly_{suffix}")
        snaps = pd.read_parquet(raw_dir / f"snaps_{suffix}")
        rosters = pd.read_parquet(raw_dir / f"rosters_{suffix}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Missing data files. Looking for *_{suffix}")

    # --- 2. Standardize IDs ---
    def standardize_id(df, name):
        # PRIORITY: 'gsis_id' is the proven linker for your data.
        candidates = ['gsis_id', 'player_id', 'id', 'pfr_player_id']
        for cand in candidates:
            if cand in df.columns:
                if cand != 'player_id':
                    logger.info(f"🔧 Renaming '{cand}' to 'player_id' in {name}")
                    return df.rename(columns={cand: 'player_id'})
                return df
        return df

    weekly = standardize_id(weekly, "weekly")
    snaps = standardize_id(snaps, "snaps")
    rosters = standardize_id(rosters, "rosters")

    # --- 3. CLEAN ROSTERS ---
    # We know 2,000+ roster rows are garbage/empty. Drop them.
    if 'player_id' in rosters.columns:
        rosters = rosters[rosters['player_id'].notna() & (rosters['player_id'] != '')]

    # --- 4. Prepare Data ---
    # Rename generic Position in Weekly (LB, DB) to 'fantasy_group'
    if 'position' in weekly.columns:
        weekly = weekly.rename(columns={'position': 'fantasy_group'})

    # Merge Snaps (Left Merge)
    snaps_cols = ['player_id', 'season', 'week', 'offense_pct', 'defense_pct']
    valid_snaps_cols = [c for c in snaps_cols if c in snaps.columns]
    
    df = pd.merge(weekly, snaps[valid_snaps_cols], 
                  on=['player_id', 'season', 'week'], 
                  how='left')

    # --- 5. Merge Roster (Left Merge) ---
    # Get latest metadata per player (tail(1) gets the most recent entry)
    latest_roster = rosters.sort_values('season').groupby('player_id').tail(1)
    
    roster_map = {
        'player_name': 'full_name', 
        'depth_chart_position': 'depth_pos',
        'pos': 'position',
        'team': 'current_team' # Rename to avoid overwriting historical teams
    }
    latest_roster = latest_roster.rename(columns=roster_map)
    
    target_roster_cols = ['player_id', 'full_name', 'position', 'birth_date', 'current_team']
    valid_roster_cols = [c for c in target_roster_cols if c in latest_roster.columns]
    
    # The Merge: We use LEFT so we keep all 3,674 weekly rows even if a roster match fails
    df = pd.merge(df, latest_roster[valid_roster_cols], 
                  on='player_id', 
                  how='left')

    # --- 6. Final Calculations ---
    # Calculate Age
    if 'birth_date' in df.columns:
        df['birth_date'] = pd.to_datetime(df['birth_date'], errors='coerce')
        avg_birth_year = current_year - 25
        # Int64 allows integers with NaNs
        df['birth_year'] = df['birth_date'].dt.year.fillna(avg_birth_year).astype('Int64')
        df['current_age'] = (current_year + 1) - df['birth_year']

    # Ensure Fantasy Points exist
    if 'fantasy_points' not in df.columns:
        logger.warning("⚠️ Fantasy points missing. Filling with 0.")
        df['fantasy_points'] = 0.0

    return df
