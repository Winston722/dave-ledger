import pandas as pd
import numpy as np
import logging
from typing import Dict

logger = logging.getLogger(__name__)

def calculate_replacement_level(df: pd.DataFrame, cfg: Dict) -> Dict[str, float]:
    """
    Calculates Baseline PPG using the 'fantasy_group' column.
    """
    league = cfg['league']
    teams = league['num_teams']
    starters = league['starters']
    bench_factors = league.get('bench_factors', {}) 
    
    # 1. Filter to Current Landscape
    current_year = df['season'].max()
    df_curr = df[df['season'] == current_year].copy()
    
    # Safety Check: Ensure fantasy_group exists
    if 'fantasy_group' not in df_curr.columns:
        logger.warning("⚠️ 'fantasy_group' column missing! Falling back to 'position'.")
        df_curr['fantasy_group'] = df_curr['position']
    
    # --- THE FIX IS HERE ---
    # We must use 'fantasy_points' (from transform.py), NOT 'points' (which might be season total)
    target_col = 'fantasy_points'
    
    # Calculate PPG (Average of Weekly Scores)
    ppg_map = df_curr.groupby(['player_id', 'fantasy_group', 'full_name'])[target_col].mean().reset_index()
    
    # Rename for consistency
    ppg_map.rename(columns={target_col: 'ppg', 'fantasy_group': 'position'}, inplace=True)
    baselines = {}
    
    # Flex Definitions
    flex_split = {'RB': 0.5, 'WR': 0.5, 'TE': 0.0} 
    idp_flex_split = {'LB': 0.6, 'DL': 0.4, 'DB': 0.0}
    
    # 2. Iterate through GENERIC slots (The keys in your YAML starters)
    # e.g., QB, RB, LB, DL...
    target_positions = [k for k in starters.keys() if k not in ['FLEX', 'SUPERFLEX', 'IDP_FLEX', 'DEF']]
    
    for pos in target_positions:
        base_starts = starters.get(pos, 0)
        
        # --- A. DISTRIBUTE VIRTUAL STARTERS ---
        effective_starts = base_starts
        
        if pos == 'QB': effective_starts += starters.get('SUPERFLEX', 0)
        if pos in flex_split: effective_starts += starters.get('FLEX', 0) * flex_split[pos]
        if pos in idp_flex_split: effective_starts += starters.get('IDP_FLEX', 0) * idp_flex_split[pos]

        # --- B. APPLY DEPTH ---
        factor = bench_factors.get(pos, 0.0)
        total_slots = int(teams * (effective_starts * (1 + factor)))
        
        # --- C. FIND CUTOFF ---
        # Filter by the Generic Group (LB, DL, etc.)
        pos_df = ppg_map[ppg_map['position'] == pos].sort_values('ppg', ascending=False).reset_index(drop=True)
        
        if len(pos_df) > total_slots and total_slots > 0:
            baseline_row = pos_df.iloc[total_slots-1]
            baseline_score = baseline_row['ppg']
            
            # Floor protection
            if baseline_score < 1.0:
                valid_pool = pos_df[pos_df['ppg'] > 2.0]
                if not valid_pool.empty:
                    baseline_score = valid_pool.iloc[-1]['ppg']
            
            logger.info(f"📉 {pos} Baseline: {effective_starts:.1f} starts -> Rank {total_slots} ({baseline_row['full_name']}) = {baseline_score:.2f} PPG")
        else:
            baseline_score = 0.0
            if total_slots > 0:
                logger.warning(f"⚠️ {pos}: Not enough players to fill {total_slots} spots.")

        baselines[pos] = baseline_score

    return baselines 
