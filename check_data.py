import sqlite3
from contextlib import closing

import config

with closing(sqlite3.connect(config.DB_PATH)) as conn:
    def one(sql):
        return conn.execute(sql).fetchone()[0]

    t = config.TABLE_NAME
    total = one(f"SELECT COUNT(*) FROM {t}")
    assert total > 5000, "too few planets"
    assert one(f"SELECT COUNT(DISTINCT pl_name) FROM {t}") == total, "duplicate planets"
    assert one(f"SELECT COUNT(*) FROM {t} WHERE pl_rade <= 0") == 0, "bad radius"
    assert one(f"SELECT COUNT(*) FROM {t} WHERE is_terrestrial != (pl_rade < {config.RADIUS_THRESHOLD})") == 0, "label mismatch"
    assert one(f"SELECT loaded_rows FROM {config.SUMMARY_TABLE}") == total, "summary does not match table"
print("All checks passed")