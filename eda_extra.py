import sqlite3
from contextlib import closing

import pandas as pd

import config

PERIOD_QUERY = f"""
SELECT CASE WHEN pl_orbper < 3   THEN '1: under 3 d'
            WHEN pl_orbper < 10  THEN '2: 3-10 d'
            WHEN pl_orbper < 30  THEN '3: 10-30 d'
            WHEN pl_orbper < 100 THEN '4: 30-100 d'
            ELSE '5: over 100 d' END AS period_bin,
       COUNT(*) AS planets,
       ROUND(AVG({config.TARGET_COLUMN}), 2) AS terrestrial_share
FROM {config.TABLE_NAME}
WHERE {config.METHOD_COLUMN} = ?
  AND pl_orbper IS NOT NULL
GROUP BY period_bin
ORDER BY period_bin
"""


def period_bin_table() -> pd.DataFrame:
    with closing(sqlite3.connect(config.DB_PATH)) as conn:
        return pd.read_sql(PERIOD_QUERY, conn, params=(config.TRAINING_METHOD,))


def load_summary() -> dict:
    with closing(sqlite3.connect(config.DB_PATH)) as conn:
        row = pd.read_sql(f"SELECT * FROM {config.SUMMARY_TABLE}", conn).iloc[0]
    return {k: (v if k == "snapshot_date" else int(v)) for k, v in row.items()}


if __name__ == "__main__":
    print(period_bin_table())
    print(load_summary())