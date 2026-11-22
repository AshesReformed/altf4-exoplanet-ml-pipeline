# 🪐 ALT-F4 | Exoplanet Structural Classification Pipeline

An ETL (Extract, Transform, Load) and Exploratory Data Analysis (EDA) pipeline for confirmed exoplanets using data from the [NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/).

This is **Project 1 of 3**. It retrieves, validates, and processes exoplanet data, stores it in an SQLite database, and explores it. **No model is trained in this project.** The resulting dataset is the foundation for the classification models developed in Projects 2 and 3.

**Live dashboard:** https://altf4-exoplanet-ml-pipeline.vercel.app

## Dataset

This project uses the NASA Exoplanet Archive's `pscomppars` table, which holds one row per confirmed exoplanet. Data is retrieved through NASA's Table Access Protocol (TAP) API without requiring an API key.

The dataset includes planetary measurements such as:

- Planetary radius
- Planetary mass
- Orbital period
- Semi-major axis
- Equilibrium temperature
- Insolation flux

It also includes host-star properties such as:

- Stellar temperature
- Stellar radius
- Stellar mass
- Stellar metallicity

Planet names, host-star names, discovery methods, and discovery years are stored as well.

## ETL Pipeline

The pipeline consists of five main stages.

### 1. Extract

- Retrieve data from the NASA TAP API using the `pscomppars` table.
- Request the required fields configured in `config.py`.
- Save the raw response to `data/raw/pscomppars.json` (this folder is not committed to Git).
- If the API request fails, use the previously saved snapshot if available.

### 2. Validate

Records are validated using Pydantic.

- Remove records without a valid planet name or a positive planetary radius.
- Count and report the reasons for every dropped record.
- Convert invalid optional numerical measurements to `NULL`.
- Preserve valid negative metallicity values.

### 3. Clean

- Remove planetary mass estimates that NASA derived from the planetary radius (identified through the `pl_bmassprov` field).
- Remove duplicate planet names.

Radius-derived masses would leak the classification label into the features, so they are set to `NULL`.

### 4. Create Target Labels

A binary target variable named `is_terrestrial` is created from planetary radius:

- `1` — radius below 2.0 Earth radii.
- `0` — radius of 2.0 Earth radii or greater.

This is a size-based rule. It does not establish a planet's composition or confirm that every planet below the threshold is rocky.

### 5. Load

The cleaned dataset is stored in an SQLite database named `exoplanets.db`.

- Table `exoplanets`: one row per planet, with `pl_name` as the primary key, a positive-radius constraint, and a constraint that `is_terrestrial` is `0` or `1`. Missing feature values stay `NULL` for later preprocessing.
- Table `pipeline_summary`: one row with the counts from the latest run (rows from NASA, rows dropped, duplicates removed, masses removed, rows loaded, transit rows, and the snapshot date).

### Data flow of the current snapshot (2026-11-22)

| Step | Rows |
|---|---|
| Rows returned by NASA | 6,473 |
| Dropped (missing name or radius) | 50 |
| Duplicate planet names removed | 0 |
| Loaded into `exoplanets` | 6,423 |
| Transit-discovered planets (analysis scope) | 4,799 |
| Masses estimated from radius and removed | 3,035 |

The archive keeps growing, so these numbers change when the pipeline is re-run.

## Analysis Scope: Transit Planets

The database keeps planets from every discovery method, but the analysis and the default classification workflow use **transit planets only**.

- Transit surveys measure planet radius directly, which is what the label is built from.
- Every other method has few terrestrial planets (11% or fewer in the method comparison plot) and a measured mass for every planet. Their radii are probably derived from mass rather than measured, which would leak the label into the features.

Other methods stay in the database and can be loaded with `load_xy(method=None)`.

**Important for Project 2:** planets orbiting the same star share stellar properties, so training and test sets should be split by `hostname`, not by row.

## Exploratory Data Analysis

`eda_analysis.py` prints summary statistics and saves six plots to `plots/` (not committed, drawn on demand). `eda_extra.py` adds a SQL summary table.

| Output | Description |
|---|---|
| `method_comparison.png` | Terrestrial share and mass availability per discovery method (all planets). |
| `data_overview.png` | Class balance and missing values per feature. |
| `radius_distribution.png` | Radius histogram with a zoom around the 2.0 boundary. |
| `feature_by_class.png` | Each feature's distribution for the two classes. |
| `period_vs_radius.png` | Orbital period against radius, coloured by class. |
| `correlation_heatmap.png` | Spearman correlations between the features, the radius and the label. |
| `eda_extra.py` table | Terrestrial share by orbital-period bin (transit planets). |

`method_comparison.png` uses all planets. Everything else uses transit planets only.

## Key Findings

- **Class balance:** about 35% of transit planets are terrestrial (under 2.0 Earth radii) and about 65% are larger. A model that always guesses "larger" would score about 65%, so any later model must beat that.
- **Orbital period:** the terrestrial share falls steadily as the period grows.

  | Orbital period | Planets | Terrestrial share |
  |---|---|---|
  | under 3 days | 794 | 56% |
  | 3 to 10 days | 1,948 | 38% |
  | 10 to 30 days | 1,296 | 30% |
  | 30 to 100 days | 566 | 16% |
  | over 100 days | 195 | 10% |

  This trend is consistent with real planet physics, but it is also partly detection bias: small planets on long orbits are hard to find. The data cannot separate the two.
- **Radius distribution:** the zoomed histogram shows a shallow dip near 1.8 to 1.9 Earth radii between a peak near 1.5 and a higher peak near 2.4, which is consistent with the known radius valley. The 2.0 boundary sits at the upper edge of the dip. The dip has not been tested statistically.
- **Feature redundancy:** several features are computed from each other. Orbital period and semi-major axis correlate at 0.99, insolation and equilibrium temperature at 0.97, and the three star properties at 0.88 to 0.94, so the nine features carry fewer independent signals than their number suggests.
- **Weak separation:** apart from planet mass, every feature correlates with the label at 0.26 or less, and the class distributions overlap heavily. Mass separates the classes best, but it is missing for about 64% of transit planets, and measured masses exist mostly for the larger planets.

## Data Checks

`check_data.py` runs sanity checks on the finished database: enough planets, no duplicate names, positive radii, labels that match the radius threshold, and a summary row that matches the table. It prints `All checks passed` or stops with the failing check.

## Flask Dashboard

The dashboard (`api/index.py`) is built with **Flask** and deployed on **Vercel**. It reads `exoplanets.db` and draws the EDA plots when they are first requested.

### Dashboard Features

- **Dataset overview:** counts for all planets, transit planets, and both classes, plus the pipeline funnel line and the snapshot date.
- **EDA plots:** the six plots above, each with a caption that states its limits.
- **Orbital-period table:** terrestrial share per period bin.
- **Database viewer:** browse the stored records, with a row-limit selector (25 to 500) and a discovery-method filter (Transit by default).
- **Limitations and NASA acknowledgement** at the bottom of the page.

### Vercel Deployment

`vercel.json` points Vercel at `api/index.py` and routes all requests to the Flask app.

Vercel's filesystem is read-only, so the deployed app does not download data or write to the database. `exoplanets.db` is committed to the repository, and the dashboard only reads it. To update the data:

1. Run `python main.py` locally.
2. Commit the new `exoplanets.db`.
3. Push to `main`. Vercel redeploys automatically.

## Project Structure

| File / Directory | Purpose |
|---|---|
| `config.py` | Shared settings, paths, column names, feature definitions, and the radius threshold. |
| `etl_pipeline.py` | Extraction, validation, cleaning, target creation, database loading, and the run summary. |
| `data_access.py` | Loads records, features, target labels, and host-star groups for later projects. |
| `eda_analysis.py` | Summary statistics and six plots. |
| `eda_extra.py` | Orbital-period summary table and the pipeline summary loader. |
| `check_data.py` | Sanity checks on the finished database. |
| `main.py` | Runs the ETL pipeline, then the EDA. |
| `api/index.py` | Flask dashboard and Vercel entry point. |
| `vercel.json` | Vercel Python runtime and routing. |
| `requirements.txt` | Python dependencies. |
| `exoplanets.db` | SQLite database (committed so the deployed dashboard can read it). |
| `data/raw/`, `plots/` | Generated locally, ignored by Git. |

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/AshesReformed/altf4-exoplanet-ml-pipeline.git
cd altf4-exoplanet-ml-pipeline
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it:

**Windows:**

```bash
.venv\Scripts\activate
```

**macOS / Linux:**

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Pipeline

```bash
python main.py
```

This builds the SQLite database and saves the EDA plots.

### 5. Check the Data and Print the Period Table

```bash
python check_data.py
python eda_extra.py
```

### 6. Run the Dashboard Locally

```bash
python api/index.py
```

Open the address shown in the terminal.

## Using the Dataset in Later Projects

`data_access.py` loads features, labels, and host-star groups.

```python
from data_access import load_xy, load_groups

# Transit planets (default); radius is never included
X, y = load_xy()

# Host star of each row, for a grouped train/test split
groups = load_groups()

# Planets from every discovery method
X_all, y_all = load_xy(method=None)

# Without planet mass (as a comparison run)
X_nomass, y_nomass = load_xy(include_mass=False)
```

The radius is excluded from the features because the label is computed from it. The default feature list is defined in `config.py`.

## Limitations

- **Detection bias:** transit surveys favour large, close-in planets, so the data does not represent all planets in the galaxy. Part of the falling terrestrial share at long periods is a survey effect.
- **The label is a size rule:** the 2.0 Earth-radius threshold is a convention and does not establish composition. In the period-versus-radius plot, the boundary between the classes is the label itself, not a discovered separation.
- **Weak features:** most features overlap heavily between the classes and several are computed from each other, so models that exclude radius should not be expected to separate the classes cleanly.
- **Missing and removed masses:** mass is missing for about 64% of transit planets after radius-derived masses were removed, and the planets that keep a measured mass are mostly larger. Imputing it needs care in Project 2.
- **Mixed measurement quality:** archive measurements come from different sources with different uncertainties, which probably blurs the radius valley.
- **Frozen snapshot:** the deployed dashboard shows the data as of the snapshot date. The archive changes over time.

## Project Contributors

**Team ALT-F4**

| Contributor | GitHub Profile |
|---|---|
| **AshesReformed** | [@AshesReformed](https://github.com/AshesReformed) |
| **velnox-m** | [@velnox-m](https://github.com/velnox-m) |
| **kamranbashir56** | [@kamranbashir56](https://github.com/kamranbashir56) |
| **hanzla269** | [@hanzla269](https://github.com/hanzla269) |

## Data Source

[NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/) — dataset table: `pscomppars`.

This research has made use of the NASA Exoplanet Archive, which is operated by the California Institute of Technology, under contract with the National Aeronautics and Space Administration under the Exoplanet Exploration Program.
