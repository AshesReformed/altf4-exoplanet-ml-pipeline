const PAGE_SIZE = 50;

const COLUMNS = [
  { key: "pl_name", label: "Planet" },
  { key: "hostname", label: "Host star" },
  { key: "discoverymethod", label: "Method" },
  { key: "disc_year", label: "Year", numeric: true, plain: true },
  { key: "pl_rade", label: "Radius (Earth radii)", numeric: true },
  { key: "pl_bmasse", label: "Mass (Earth masses)", numeric: true },
  { key: "pl_orbper", label: "Period (days)", numeric: true },
  { key: "is_terrestrial", label: "Class" },
];

const FEATURE_LABELS = {
  pl_bmasse: "Planet mass (Earth masses)",
  pl_orbper: "Orbital period (days)",
  pl_orbsmax: "Orbit size (AU)",
  pl_insol: "Starlight received (Earth = 1)",
  pl_eqt: "Equilibrium temperature (K)",
  st_teff: "Star temperature (K)",
  st_rad: "Star radius (Sun = 1)",
  st_mass: "Star mass (Sun = 1)",
  st_met: "Star metallicity",
};

const state = { rows: [], search: "", method: "", planetClass: "", sortKey: "pl_name", sortDir: 1, page: 0 };

const $ = (id) => document.getElementById(id);

function formatNumber(value, plain = false) {
  if (value === null || value === undefined) return "–";
  if (plain) return String(value);
  return value.toLocaleString("en-US", { maximumSignificantDigits: 4 });
}

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

function fillSummary(summary) {
  const text = {
    total_planets: summary.total_planets.toLocaleString("en-US"),
    training_planets: summary.training_planets.toLocaleString("en-US"),
    terrestrial: summary.terrestrial.toLocaleString("en-US"),
    larger: summary.larger.toLocaleString("en-US"),
    radius_threshold: summary.radius_threshold.toFixed(1),
    training_method: summary.training_method,
    built_on: summary.built_on,
  };
  document.querySelectorAll("[data-field]").forEach((element) => {
    const value = text[element.dataset.field];
    if (value !== undefined) element.textContent = value;
  });
}

function fillMedians(medians) {
  const body = document.querySelector("#medians tbody");
  body.replaceChildren();
  Object.entries(FEATURE_LABELS).forEach(([key, label]) => {
    if (!medians[key]) return;
    const row = body.insertRow();
    row.insertCell().textContent = label;
    [medians[key].larger, medians[key].terrestrial].forEach((value) => {
      const cell = row.insertCell();
      cell.className = "num";
      cell.textContent = formatNumber(value);
    });
  });
}

function fillMethodFilter(methods) {
  const select = $("method");
  methods.forEach(({ method, planets }) => {
    const option = document.createElement("option");
    option.value = method;
    option.textContent = `${method} (${planets.toLocaleString("en-US")})`;
    select.append(option);
  });
}

function filteredRows() {
  const text = state.search.trim().toLowerCase();
  return state.rows.filter((row) =>
    (!state.method || row.discoverymethod === state.method) &&
    (state.planetClass === "" || String(row.is_terrestrial) === state.planetClass) &&
    (!text || row.pl_name.toLowerCase().includes(text) || (row.hostname || "").toLowerCase().includes(text))
  );
}

function compare(a, b) {
  const x = a[state.sortKey];
  const y = b[state.sortKey];
  if (x === null && y === null) return 0;
  if (x === null) return 1;
  if (y === null) return -1;
  const order = typeof x === "number" ? x - y : String(x).localeCompare(String(y));
  return order * state.sortDir;
}

function renderHeader() {
  const head = $("planets-head");
  head.replaceChildren();
  COLUMNS.forEach((column) => {
    const th = document.createElement("th");
    th.scope = "col";
    if (column.numeric) th.className = "num";
    th.setAttribute("aria-sort", column.key === state.sortKey ? (state.sortDir === 1 ? "ascending" : "descending") : "none");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = column.label;
    button.addEventListener("click", () => {
      state.sortDir = state.sortKey === column.key ? -state.sortDir : 1;
      state.sortKey = column.key;
      state.page = 0;
      render();
    });
    th.append(button);
    head.append(th);
  });
}

function renderRow(row) {
  const tr = document.createElement("tr");
  COLUMNS.forEach((column) => {
    const td = tr.insertCell();
    if (column.numeric) td.className = "num";
    if (column.key === "is_terrestrial") {
      const tag = document.createElement("span");
      tag.className = `tag ${row.is_terrestrial === 1 ? "terrestrial" : "larger"}`;
      tag.textContent = row.is_terrestrial === 1 ? "Terrestrial" : "Larger";
      td.append(tag);
    } else if (column.numeric) {
      td.textContent = formatNumber(row[column.key], column.plain);
    } else {
      td.textContent = row[column.key] ?? "–";
    }
  });
  return tr;
}

function render() {
  const rows = filteredRows().sort(compare);
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  state.page = Math.min(state.page, pages - 1);
  const start = state.page * PAGE_SIZE;

  renderHeader();
  $("planets").tBodies[0].replaceChildren(...rows.slice(start, start + PAGE_SIZE).map(renderRow));

  $("table-status").textContent = rows.length
    ? `${rows.length.toLocaleString("en-US")} planets match.`
    : "No planets match these filters. Clear the search or choose another method.";
  $("page-info").textContent = `Page ${state.page + 1} of ${pages}`;
  $("prev").disabled = state.page === 0;
  $("next").disabled = state.page >= pages - 1;
}

function bindControls() {
  $("search").addEventListener("input", (event) => { state.search = event.target.value; state.page = 0; render(); });
  $("method").addEventListener("change", (event) => { state.method = event.target.value; state.page = 0; render(); });
  $("class").addEventListener("change", (event) => { state.planetClass = event.target.value; state.page = 0; render(); });
  $("prev").addEventListener("click", () => { state.page -= 1; render(); });
  $("next").addEventListener("click", () => { state.page += 1; render(); });
}

async function init() {
  bindControls();
  try {
    const [summary, planets] = await Promise.all([fetchJson("data/summary.json"), fetchJson("data/planets.json")]);
    fillSummary(summary);
    fillMedians(summary.medians);
    fillMethodFilter(summary.methods);
    state.rows = planets.data.map((values) =>
      Object.fromEntries(planets.columns.map((name, index) => [name, values[index]]))
    );
    render();
  } catch (error) {
    $("table-status").textContent = "Planet data could not be loaded. Run python main.py, commit public/data, and redeploy.";
    console.error(error);
  }
}

init();
