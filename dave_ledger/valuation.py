import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class AssetValuator:
    def __init__(self, df: pd.DataFrame, config: Dict[str, Any], baselines: Optional[Dict[str, float]] = None):
        self.df = df
        self.cfg = config
        self.baselines = baselines or {}
        
        # 1. Load Config
        val_cfg = self.cfg.get('valuation', {})
        self.discount_rate = val_cfg.get('discount_rate', 0.15) 
        self.epsilon_val = val_cfg.get('epsilon_val', 0.5)
        self.availability_weight = val_cfg.get('availability_weight', 20)
        
        # 2. Recency Weights
        raw_weights = val_cfg.get('year_weights', {})
        self.year_weights = {int(k): float(v) for k, v in raw_weights.items()}
        if not self.year_weights:
            self.year_weights = {0: 1.0, 1: 0.85, 2: 0.70, 3: 0.55, 4: 0.40}
        
        # 3. Priors
        self.pos_priors = val_cfg.get('availability_priors', {})

        # 4. FORCE 1: Decay (The Washed Factor)
        self.decay_params = val_cfg.get('performance_decay', {})
        self.default_decay = {'start_age': 30, 'decay_rate': 0.10}

        # 5. FORCE 2: Retirement (The Exit Factor)
        self.retire_params = val_cfg.get('retirement_risk', {})
        self.default_retire = {'cliff_age': 34.0, 'k': 0.6}
        
        # 6. FORCE 3: Growth (The Breakout Factor)
        self.growth_params = val_cfg.get('performance_growth', {})
        self.default_growth = {'end_age': 25, 'growth_rate': 0.05}

    def run_valuation(self) -> pd.DataFrame:
        df = self.df.copy()
        if 'fantasy_group' not in df.columns:
            df['fantasy_group'] = df['position']

        logger.info("   -> Running Bayesian Availability Engine...")
        df = self._calculate_availability(df)

        logger.info("   -> Calculating Weighted Talent Baseline...")
        df = self._calculate_talent(df)

        logger.info("   -> Calculating Risk Metrics...")
        df = self._calculate_risk(df)
        
        logger.info("   -> Running Infinite Horizon Projection...")
        df = self._project_infinite_horizon(df)
        
        return df.sort_values('vorp', ascending=False)

    def _calculate_availability(self, df: pd.DataFrame) -> pd.DataFrame:
        def get_bayes_score(sub_df):
            if sub_df.empty: return 0.0
            pos_key = sub_df.iloc[-1].get('fantasy_group', sub_df.iloc[-1]['position'])
            
            played = len(sub_df[ (sub_df['offense_pct'] > 0) | (sub_df['defense_pct'] > 0) ])
            seasons = sub_df['season'].nunique()
            total_possible = seasons * 17
            
            prior_rate = self.pos_priors.get(pos_key, 0.90) 
            weight = self.availability_weight
            score = (played + (prior_rate * weight)) / (total_possible + weight)
            return min(score, 1.0)
        scores = df.groupby('player_id').apply(get_bayes_score)
        latest = df.sort_values('season').groupby('player_id').tail(1).copy()
        latest['availability_score'] = latest['player_id'].map(scores)
        return latest

    def _calculate_talent(self, df: pd.DataFrame) -> pd.DataFrame:
        full_history = self.df
        current_year = self.cfg['context']['current_year']
        def get_weighted_ppg(pid):
            games = full_history[full_history['player_id'] == pid]
            active = games[(games['offense_pct'] > 0) | (games['defense_pct'] > 0)]
            if len(active) == 0: return 0.0
            weighted_sum = 0
            total_weight = 0
            for _, row in active.iterrows():
                offset = current_year - row['season']
                w = self.year_weights.get(offset, 0.1) 
                weighted_sum += (row['points'] * w)
                total_weight += w
            if total_weight == 0: return 0.0
            return weighted_sum / total_weight
        df['talent_ppg'] = df['player_id'].apply(get_weighted_ppg)
        return df

    def _calculate_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        full_history = self.df
        stats = full_history.groupby('player_id')['points'].agg(['std', 'mean'])
        stats['risk_cv'] = stats['std'] / stats['mean']
        stats = stats.fillna(0)
        df['risk_cv'] = df['player_id'].map(stats['risk_cv'])
        return df

    def _project_infinite_horizon(self, df: pd.DataFrame) -> pd.DataFrame:
        
        def get_active_prob(group, age):
            params = self.retire_params.get(group, self.default_retire)
            cliff = params.get('cliff_age', 34.0)
            k = params.get('k', 0.6)
            exponent = k * (age - cliff)
            exponent = max(min(exponent, 100), -100)
            prob_retire = 1.0 / (1.0 + np.exp(exponent)) 
            return 1.0 - prob_retire

        def get_performance_multiplier(group, age):
            # 1. Growth
            g_params = self.growth_params.get(group, self.default_growth)
            if age <= g_params.get('end_age', 25):
                return 1.0 + g_params.get('growth_rate', 0.05)
            
            # 2. Decay
            d_params = self.decay_params.get(group, self.default_decay)
            if age >= d_params.get('start_age', 30):
                return 1.0 - d_params.get('decay_rate', 0.10)
                
            return 1.0

        def get_dcf(row):
            current_ppg = row['talent_ppg']
            availability = row['availability_score']
            age = row['current_age']
            start_exp = row.get('years_exp', 5) # Default to veteran if missing
            group = row['fantasy_group'] 
            floor = self.baselines.get(group, 0.0)
            
            total_dcf = 0
            year = 1
            cumulative_survival = 1.0 
            
            while True:
                future_age = age + year
                future_exp = start_exp + year # FIX: Increment Experience
                
                # A. Retirement (Exit)
                prob_return = get_active_prob(group, future_age)
                cumulative_survival *= prob_return
                
                if cumulative_survival < 0.05: break
                if year > 15: break

                # B. Performance (Growth/Decay)
                perf_mult = get_performance_multiplier(group, future_age)
                current_ppg *= perf_mult
                
                # C. Logic Gates (Shields & Handcuffs)
                is_young = future_age <= 23 or future_exp < 3 # FIX: Use future_exp
                is_handcuff = (group == 'RB') and (current_ppg < floor) and (current_ppg > 2.0)
                
                scoring_ppg = current_ppg
                if scoring_ppg < floor and not is_young:
                    if is_handcuff:
                        scoring_ppg = floor * 0.10 
                    else:
                        break # Cut
                
                # D. Value Calculation
                annual_ev = (scoring_ppg * availability * 17) * cumulative_survival
                pv = annual_ev / ((1 + self.discount_rate) ** year)
                
                if pv < self.epsilon_val: break
                total_dcf += pv
                year += 1
                
            return total_dcf

        df['dcf_value'] = df.apply(get_dcf, axis=1)
        
        def get_replacement_value(row):
            floor = self.baselines.get(row['fantasy_group'], 0.0)
            val = 0
            for i in range(1, 4):
                 val += (floor * 17) / ((1 + self.discount_rate) ** i)
            return val

        df['replacement_value'] = df.apply(get_replacement_value, axis=1)
        df['vorp'] = df['dcf_value'] - df['replacement_value']
        
        return df