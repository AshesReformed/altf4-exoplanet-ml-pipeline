import os
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).parent

# On Vercel (read-only filesystem), fall back to /tmp if local DB does not exist
if (BASE_DIR / "exoplanets.db").exists():
    DB_PATH = BASE_DIR / "exoplanets.db"
elif os.environ.get("VERCEL"):
    DB_PATH = Path(tempfile.gettempdir()) / "exoplanets.db"
else:
    DB_PATH = BASE_DIR / "exoplanets.db"

# Raw snapshot path setup
if (BASE_DIR / "data" / "raw" / "pscomppars.json").exists():
    RAW_SNAPSHOT_PATH = BASE_DIR / "data" / "raw" / "pscomppars.json"
elif os.environ.get("VERCEL"):
    RAW_SNAPSHOT_PATH = Path(tempfile.gettempdir()) / "pscomppars.json"
else:
    RAW_SNAPSHOT_PATH = BASE_DIR / "data" / "raw" / "pscomppars.json"

TABLE_NAME = "exoplanets"

NASA_TAP_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
NASA_SOURCE_TABLE = "pscomppars"

ID_COLUMN = "pl_name"
HOST_COLUMN = "hostname"
METHOD_COLUMN = "discoverymethod"
YEAR_COLUMN = "disc_year"
RADIUS_COLUMN = "pl_rade"
TARGET_COLUMN = "is_terrestrial"
FEATURE_COLUMNS = [
    "pl_bmasse",
    "pl_orbper",
    "pl_orbsmax",
    "pl_insol",
    "pl_eqt",
    "st_teff",
    "st_rad",
    "st_mass",
    "st_met",
]

TRAINING_METHOD = "Transit"
RADIUS_THRESHOLD = 2.0

MASS_PROVENANCE_COLUMN = "pl_bmassprov"
ESTIMATED_MASS_KEYWORD = "relationship"

RANDOM_STATE = 42
TEST_SIZE = 0.2
