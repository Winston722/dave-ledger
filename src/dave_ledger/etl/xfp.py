import pandas as pd
import logging

logger = logging.getLogger(__name__)

def load_and_clean_xfp(file_path) -> pd.DataFrame:
    """
    Loads raw xFP data, applies custom 6pt Passing TD adjustment, 
    and returns a clean [player_id, season, week, expected_fantasy_points] dataframe.
    """
    if not file_path.exists():
        logger.warning(f"⚠️ xFP file not found at {file_path}. Skipping.")
        return pd.DataFrame()

    try:
        df = pd.read_parquet(file_path)
    except Exception as e:
        logger.error(f"❌ Failed to read xFP file: {e}")
        return pd.DataFrame()
    
    # 1. Standardize IDs
    # nflverse data uses 'player_id' as the gsis_id. 
    # We ensure it's a string to match your other files.
    if 'player_id' in df.columns:
        df['player_id'] = df['player_id'].astype(str)

    # 2. Identify Columns
    # We need the Total (Base) AND the Passing TD component (Adjustment)
    base_col = 'total_fantasy_points_exp'
    td_col = 'pass_touchdown_exp'
    
    # Validation: Ensure we have what we need
    missing_cols = [c for c in [base_col, td_col] if c not in df.columns]
    
    if missing_cols:
        # Fallback: If we can't find specific columns, try to just return total or fail
        logger.warning(f"⚠️ Missing xFP ingredients: {missing_cols}. Looking for generic total...")
        
        # Fuzzy search for at least the total
        candidates = [c for c in df.columns if 'fantasy_points_exp' in c and 'total' in c]
        if candidates:
            base_col = candidates[0]
            # If we miss the TD column, we just can't do the adjustment. Warn and proceed.
            logger.warning(f"   -> Found base '{base_col}', but cannot apply 6pt adjustment.")
            td_col = None 
        else:
            logger.error("❌ Could not find any xFP columns. Returning empty.")
            return pd.DataFrame()

    # 3. Create Working Copy
    # Select only what we need to save memory
    cols_to_select = ['player_id', 'season', 'week', base_col]
    if td_col:
        cols_to_select.append(td_col)
        
    clean_df = df[cols_to_select].copy()
    
    # 4. Fill NaNs
    # Must fill before math, otherwise 5.0 + NaN = NaN
    clean_df = clean_df.fillna(0.0)

    # 5. Apply The 6pt Passing TD Patch
    # Formula: Base (4pt) + (Exp Pass TDs * 2 Extra Points)
    if td_col:
        clean_df['expected_fantasy_points'] = clean_df[base_col] + (clean_df[td_col] * 2.0)
    else:
        clean_df['expected_fantasy_points'] = clean_df[base_col]

    # 6. Final Polish
    final_df = clean_df[['player_id', 'season', 'week', 'expected_fantasy_points']].copy()
    
    logger.info(f"   -> Loaded and adjusted {len(final_df)} rows of xFP data.")
    return final_df