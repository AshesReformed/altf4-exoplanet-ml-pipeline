import os
import sys
import tempfile
import threading
from functools import lru_cache
from pathlib import Path

# Matplotlib needs a headless backend and a writable cache folder on Vercel.
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib"))

ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

from flask import Flask, jsonify, render_template_string, request, send_from_directory

import config
from data_access import load_dataframe
from eda_analysis import generate_plots

app = Flask(__name__)

ROW_LIMITS = [25, 50, 100, 250, 500]
DEFAULT_LIMIT = 50

PLOT_LOCK = threading.Lock()

PLOTS = [
    {
        "file": "radius_distribution.png",
        "title": "Planetary Radius Valley (Fulton Gap)",
        "caption": "Transit planets. The red line is the 2.0 Earth-radius class boundary.",
        "wide": False,
    },
    {
        "file": "correlation_heatmap.png",
        "title": "Feature Correlation Heatmap",
        "caption": "Spearman correlations, transit planets.",
        "wide": False,
    },
    {
        "file": "method_comparison.png",
        "title": "Discovery Methods",
        "caption": "Share of terrestrial planets and share with a measured mass, all planets.",
        "wide": True,
    },
    {
        "file": "feature_by_class.png",
        "title": "Feature Distributions by Class",
        "caption": "Transit planets.",
        "wide": True,
    },
    {
        "file": "period_vs_radius.png",
        "title": "Orbital Period vs. Planetary Radius",
        "caption": "Coloured by radius, so the boundary is built in. It shows where planets sit, not how well the other features separate them.",
        "wide": False,
    },
    {
        "file": "data_overview.png",
        "title": "Class Balance and Missing Values",
        "caption": "Transit planets.",
        "wide": False,
    },
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>ALT-F4 Exoplanet Pipeline</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { background-color: #f8f9fa; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .card { border-radius: 12px; border: 1px solid #e9ecef; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
        .stat-number { font-size: 2rem; font-weight: 700; }
        .table-container { max-height: 550px; overflow: auto; }
        .plot-img { width: 100%; height: auto; border-radius: 8px; border: 1px solid #dee2e6; background: #fff; }
    </style>
</head>
<body class="py-4">
    <div class="container">
        <div class="bg-white p-4 p-md-5 rounded-4 shadow-sm mb-4">

            <div class="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
                <div>
                    <h1 class="h2 mb-1 fw-bold text-dark">🪐 ALT-F4 NASA Exoplanet Pipeline</h1>
                    <p class="text-secondary mb-0">Automated ETL &amp; EDA Dashboard (Project 1 of 3)</p>
                </div>
                <span class="badge bg-primary fs-6 px-3 py-2">Group: ALT-F4</span>
            </div>

            <hr class="my-4">

            <div class="row g-3 text-center mb-4">
                <div class="col-6 col-md-3">
                    <div class="card p-3 bg-light">
                        <div class="stat-number text-dark">{{ total }}</div>
                        <div class="text-muted small">Total Confirmed Planets</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card p-3 bg-light">
                        <div class="stat-number text-primary">{{ transit }}</div>
                        <div class="text-muted small">{{ method }} Method Planets</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card p-3 bg-light">
                        <div class="stat-number text-danger">{{ terrestrial }}</div>
                        <div class="text-muted small">Terrestrial (&lt; {{ threshold }} R_Earth)</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card p-3 bg-light">
                        <div class="stat-number text-secondary">{{ larger }}</div>
                        <div class="text-muted small">Larger (&ge; {{ threshold }} R_Earth)</div>
                    </div>
                </div>
            </div>

            <ul class="nav nav-tabs mb-4" id="mainTab" role="tablist">
                <li class="nav-item">
                    <button class="nav-link active fw-bold" id="graphs-tab" data-bs-toggle="tab" data-bs-target="#graphs" type="button" role="tab">📊 Visual EDA Graphs</button>
                </li>
                <li class="nav-item">
                    <button class="nav-link fw-bold" id="table-tab" data-bs-toggle="tab" data-bs-target="#table" type="button" role="tab">📁 Validated Database Table</button>
                </li>
            </ul>

            <div class="tab-content">

                <div class="tab-pane fade show active" id="graphs" role="tabpanel">
                    <div class="row g-4">
                        {% for plot in plots %}
                        <div class="{{ 'col-12' if plot.wide else 'col-lg-6' }}">
                            <h5 class="fw-bold mb-1 text-secondary">{{ plot.title }}</h5>
                            <p class="text-muted small mb-2">{{ plot.caption }}</p>
                            {% if plot.available %}
                            <img src="/plots/{{ plot.file }}" alt="{{ plot.title }}" class="plot-img" loading="lazy">
                            {% else %}
                            <div class="alert alert-warning mb-0">This plot could not be generated. Check the deployment logs.</div>
                            {% endif %}
                        </div>
                        {% endfor %}
                    </div>
                </div>

                <div class="tab-pane fade" id="table" role="tabpanel">
                    <div class="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
                        <h5 class="mb-0 fw-bold">SQLite Table View (first {{ limit }} planets by name)</h5>
                        <div class="btn-group btn-group-sm" role="group">
                            <span class="btn btn-outline-secondary disabled">Show:</span>
                            {% for option in limits %}
                            <a href="/?limit={{ option }}#table" class="btn btn-outline-primary {% if option == limit %}active{% endif %}">{{ option }}</a>
                            {% endfor %}
                        </div>
                    </div>
                    <div class="table-container border rounded">
                        {{ table_html | safe }}
                    </div>
                </div>

            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        if (window.location.hash === "#table") {
            bootstrap.Tab.getOrCreateInstance(document.getElementById("table-tab")).show();
        }
    </script>
</body>
</html>
"""

ERROR_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>ALT-F4 Exoplanet Pipeline</title></head>
<body style="font-family: sans-serif; max-width: 40rem; margin: 3rem auto;">
    <h1>Dashboard unavailable</h1>
    <p>{{ message }}</p>
</body>
</html>
"""


@lru_cache(maxsize=1)
def get_dataframe():
    return load_dataframe()


def ensure_plots(df):
    """Draw the EDA plots once per server instance, then reuse the saved files."""
    with PLOT_LOCK:
        if all((config.PLOTS_DIR / plot["file"]).exists() for plot in PLOTS):
            return
        generate_plots(df)


def parse_limit(value):
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    return limit if limit in ROW_LIMITS else DEFAULT_LIMIT


@app.route("/")
def home():
    try:
        df = get_dataframe()
    except FileNotFoundError:
        message = "The database was not found. Run python main.py, then commit exoplanets.db and redeploy."
        return render_template_string(ERROR_TEMPLATE, message=message), 503

    subset = df[df[config.METHOD_COLUMN] == config.TRAINING_METHOD]
    terrestrial = int(subset[config.TARGET_COLUMN].sum())
    limit = parse_limit(request.args.get("limit"))

    try:
        ensure_plots(df)
    except Exception as error:
        app.logger.error("Plot generation failed: %s", error)

    plots = [{**plot, "available": (config.PLOTS_DIR / plot["file"]).exists()} for plot in PLOTS]
    table_html = df.head(limit).to_html(classes="table table-striped table-hover mb-0", index=False)

    return render_template_string(
        HTML_TEMPLATE,
        total=f"{len(df):,}",
        transit=f"{len(subset):,}",
        terrestrial=f"{terrestrial:,}",
        larger=f"{len(subset) - terrestrial:,}",
        method=config.TRAINING_METHOD,
        threshold=config.RADIUS_THRESHOLD,
        plots=plots,
        table_html=table_html,
        limit=limit,
        limits=ROW_LIMITS,
    )


@app.route("/plots/<path:filename>")
def plot_file(filename):
    try:
        ensure_plots(get_dataframe())
    except Exception as error:
        app.logger.error("Plot generation failed: %s", error)
    return send_from_directory(config.PLOTS_DIR, filename, max_age=3600)


@app.route("/health")
def health():
    return jsonify(
        database=config.DB_PATH.exists(),
        plots=sorted(path.name for path in config.PLOTS_DIR.glob("*.png")),
    )


if __name__ == "__main__":
    app.run(debug=True)
