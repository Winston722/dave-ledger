from dave_ledger.config import load_config

if __name__ == "__main__":
    cfg = load_config()
    print(f"DAVE Ledger OK. Config keys: {sorted(cfg.keys())}")
