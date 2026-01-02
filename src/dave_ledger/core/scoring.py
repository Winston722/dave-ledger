import pandas as pd
from typing import Dict

def apply_fantasy_scoring(df: pd.DataFrame, rules: Dict[str, float]) -> pd.DataFrame:
    """
    Applies fantasy scoring rules defined in the config.
    """
    # 1. Initialize Points Vector
    total_points = pd.Series(0.0, index=df.index)

    # 2. Iterate through every rule in the config
    for col_name, multiplier in rules.items():
        if multiplier == 0:
            continue
            
        # Check if the column exists in the dataset
        if col_name in df.columns:
            # Add points: Value * Multiplier
            total_points += df[col_name].fillna(0) * multiplier
        else:
            # Optional: Verbose logging
            pass

    # 3. Assign to DataFrame
    df = df.copy()
    df['points'] = total_points
    return df