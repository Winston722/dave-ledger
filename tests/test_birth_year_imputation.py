import pandas as pd

from dave_ledger.etl.transform import _impute_birth_years


def test_position_median_and_global_fallback():
    current_year = 2025
    df = pd.DataFrame(
        {
            "player_id": [1, 2, 3, 4, 5],
            "position": ["QB", "QB", "RB", "LS", "WR"],
            "birth_date": [
                "1990-01-01",  # QB known
                pd.NaT,        # QB missing -> use QB median (1990)
                "1994-05-01",  # RB known
                pd.NaT,        # LS missing -> no pos median, should use global
                "1992-03-04",  # WR known
            ],
        }
    )

    result = _impute_birth_years(df, current_year)

    # QB missing uses QB median (1990)
    assert result.loc[1, "birth_year"] == 1990
    assert result.loc[1, "current_age"] == (current_year + 1) - 1990

    # Global median from known years (1990, 1994, 1992) = 1992
    assert result.loc[3, "birth_year"] == 1992
    assert result.loc[3, "current_age"] == (current_year + 1) - 1992

    # Ensure dtype preserved as nullable integer
    assert str(result["birth_year"].dtype) == "Int64"
