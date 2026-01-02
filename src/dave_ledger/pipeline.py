import logging

from dave_ledger.analysis import baselines, valuation
from dave_ledger.core import scoring
from dave_ledger.core.config import load_config
from dave_ledger.etl import cleaning, ingest

# Configure simple logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_dave(update: bool = False):
    """
    Main entry point for the DAVE Ledger.
    Runs Ingestion -> Transform -> Scoring -> Baselines -> Valuation.
    """
    # 1. Load Configuration
    try:
        cfg = load_config()
        logger.info("✅ Configuration Loaded.")
    except Exception as e:
        logger.error(f"❌ Failed to load config: {e}")
        raise

    # 2. Ingest Data (Optional)
    if update:
        logger.info("🔄 Update requested. Running ingestion...")
        try:
            ingest.update_data()
        except Exception as e:
            logger.error(f"❌ Ingestion failed: {e}")
            raise

    # 3. Load & Clean Data
    logger.info("1. [TRANSFORM] Loading & Merging History...")
    try:
        df_raw = cleaning.load_and_clean_data()
        logger.info(f"   -> Loaded {len(df_raw)} rows of history.")
    except FileNotFoundError:
        logger.error("❌ Data not found! Hint: Run 'run_dave(update=True)' first.")
        raise

    # 4. Apply Scoring
    logger.info("2. [SCORING] Applying League Rules...")
    df_scored = scoring.apply_fantasy_scoring(df_raw, cfg['scoring'])
    
    # 5. Calculate Baselines (The "Replacement Level")
    logger.info("3. [BASELINES] Calculating League Replacement Levels...")
    pos_baselines = baselines.calculate_replacement_level(df_scored, cfg)
    
    # 6. Run Valuation (The "Draft Board")
    logger.info("4. [VALUATION] Forecasting Asset Prices...")
    # Initialize Valuator with data, full config, and the baselines we just calculated
    valuator = valuation.AssetValuator(df_scored, cfg, baselines=pos_baselines)
    df_final = valuator.run_valuation()
    
    logger.info("✅ Pipeline Complete.")
    return df_final

if __name__ == "__main__":
    # Allows running `python -m dave_ledger.pipeline` from terminal
    df = run_dave(update=False)
    
    # Quick print of the Top 20 most valuable assets
    cols = ['full_name', 'position', 'current_age', 'talent_ppg', 'vorp', 'dcf_value']
    print("\n🏆 TOP 20 ASSETS (PRELIMINARY RANKINGS)")
    print(df[cols].head(20).to_string(index=False))
