let map;
let markers = [];
let mode = "click"; // "click" or "coords"
let numVehicles = 3;
let clickIndex = 0; // 0..numVehicles for accident as last
let locations = {
  vehicles: [], // [{name, lat, lon}]
  accident: null,
};

window.addEventListener("load", () => {
  initUI();
  initMap();
  applyVehicleCount(); // initial 3 vehicles
});

function initUI() {
  const modeClick = document.getElementById("mode-click");
  const modeCoords = document.getElementById("mode-coords");
  const applyBtn = document.getElementById("apply-vehicles");
  const resetBtn = document.getElementById("reset-btn");
  const runBtn = document.getElementById("run-btn");
    document.getElementById("acc-lat").addEventListener("input", validateReady);
    document.getElementById("acc-lon").addEventListener("input", validateReady);

  modeClick.addEventListener("click", () => setMode("click"));
  modeCoords.addEventListener("click", () => setMode("coords"));
  applyBtn.addEventListener("click", applyVehicleCount);
  resetBtn.addEventListener("click", resetAll);
  runBtn.addEventListener("click", runAlgorithms);
}

function setMode(newMode) {
  mode = newMode;
  const clickBtn = document.getElementById("mode-click");
  const coordsBtn = document.getElementById("mode-coords");
  const coordPanel = document.getElementById("coord-mode-panel");
  const instr = document.getElementById("instruction");

  if (newMode === "click") {
    clickBtn.classList.add("active");
    coordsBtn.classList.remove("active");
    coordPanel.classList.add("hidden");
    instr.textContent =
      "Click Mode: Click on the map to set each vehicle start, then the accident location.";
  } else {
    coordsBtn.classList.add("active");
    clickBtn.classList.remove("active");
    coordPanel.classList.remove("hidden");
    instr.textContent =
      "Coordinate Mode: Enter lat/lon for each vehicle and the accident, then Run.";
  }

  validateReady();
}

function applyVehicleCount() {
  const n = parseInt(document.getElementById("num-vehicles").value, 10);
  if (isNaN(n) || n < 1) return;
  numVehicles = n;
  locations.vehicles = Array.from({ length: numVehicles }, (_, i) => ({
    name: `Vehicle ${i + 1}`,
    lat: null,
    lon: null,
  }));
  locations.accident = null;
  clickIndex = 0;
  clearMarkers();
  buildVehicleNameInputs();
  buildCoordInputs();
  updateStatus("Set all locations and click Run.");
  document.getElementById("run-btn").disabled = true;
}

function buildVehicleNameInputs() {
  const container = document.getElementById("vehicle-name-container");
  container.innerHTML = "";
  locations.vehicles.forEach((v, i) => {
    const row = document.createElement("div");
    row.className = "vehicle-row";
    row.innerHTML = `
      <label>Vehicle ${i + 1}:</label>
      <input type="text" value="${v.name}" data-index="${i}">
    `;
    row.querySelector("input").addEventListener("input", (e) => {
      locations.vehicles[i].name = e.target.value || `Vehicle ${i + 1}`;
      // also update coord mode labels if needed
      const nameLabel = document.getElementById(`coord-name-${i}`);
      if (nameLabel) nameLabel.textContent = locations.vehicles[i].name;
    });
    container.appendChild(row);
  });
}

function buildCoordInputs() {
  const vContainer = document.getElementById("coord-vehicles");
  vContainer.innerHTML = "";
  locations.vehicles.forEach((v, i) => {
    const row = document.createElement("div");
    row.className = "coord-row";
    row.innerHTML = `
      <span id="coord-name-${i}" style="min-width:80px; font-weight:600;">
        ${v.name}
      </span>
      <label>Lat</label>
      <input type="number" step="0.000001" id="v${i}-lat" class="coord-input">
      <label>Lon</label>
      <input type="number" step="0.000001" id="v${i}-lon" class="coord-input">
    `;
    vContainer.appendChild(row);
  });

  // ADD THIS: listen for changes and revalidate
  document.querySelectorAll(".coord-input").forEach((input) => {
    input.addEventListener("input", validateReady);
  });
}


function initMap() {
  map = L.map("map").setView([44.9778, -93.2650], 12);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(map);

  map.on("click", onMapClick);
}


function onMapClick(e) {
  if (mode !== "click") return;
  if (clickIndex > numVehicles) return; // already done (vehicles + accident)

  const { lat, lng } = e.latlng;

  if (clickIndex < numVehicles) {
    // vehicle i
    locations.vehicles[clickIndex].lat = lat;
    locations.vehicles[clickIndex].lon = lng;
    addMarker(lat, lng, locations.vehicles[clickIndex].name);
    updateStatus(
      `Set ${locations.vehicles[clickIndex].name} at (${lat.toFixed(
        5
      )}, ${lng.toFixed(5)}).`
    );
  } else {
    // accident
    locations.accident = { lat, lon: lng };
    addMarker(lat, lng, "Accident", "gold");
    updateStatus(
      `Accident at (${lat.toFixed(5)}, ${lng.toFixed(
        5
      )}). All locations set, click "Run All Algorithms".`
    );
  }

  clickIndex += 1;
  validateReady();
}

function addMarker(lat, lon, label, color = "red") {
  const marker = L.marker([lat, lon], {
    title: label,
  }).addTo(map);
  marker.bindPopup(label);
  markers.push(marker);
}

function clearMarkers() {
  markers.forEach((m) => map.removeLayer(m));
  markers = [];
}

/* -------------- state helpers -------------- */

function validateReady() {
  const runBtn = document.getElementById("run-btn");
  if (mode === "click") {
    const allVehiclesSet = locations.vehicles.every(
      (v) => v.lat !== null && v.lon !== null
    );
    const accSet = locations.accident && locations.accident.lat !== null;
    runBtn.disabled = !(allVehiclesSet && accSet);
  } else {
    // coordinate mode
    const vs = [];
    for (let i = 0; i < numVehicles; i++) {
      const lat = parseFloat(document.getElementById(`v${i}-lat`).value);
      const lon = parseFloat(document.getElementById(`v${i}-lon`).value);
      if (isNaN(lat) || isNaN(lon)) {
        document.getElementById("run-btn").disabled = true;
        return;
      }
      vs.push({ lat, lon });
    }
    const accLat = parseFloat(document.getElementById("acc-lat").value);
    const accLon = parseFloat(document.getElementById("acc-lon").value);
    if (isNaN(accLat) || isNaN(accLon)) {
      document.getElementById("run-btn").disabled = true;
      return;
    }
    document.getElementById("run-btn").disabled = false;
  }
}

function updateStatus(msg) {
  const el = document.getElementById("status-message");
  el.textContent = msg;
}

function resetAll() {
  locations.vehicles = [];
  locations.accident = null;
  clickIndex = 0;
  clearMarkers();
  document.getElementById("results-panel").classList.add("hidden");
  document.getElementById("visualize-container").classList.add("hidden");
  updateStatus('Set all locations and click "Run All Algorithms".');
  applyVehicleCount();
}

/* -------------- main: run algorithms -------------- */

async function runAlgorithms() {
  updateStatus("Running algorithms...");
  const runBtn = document.getElementById("run-btn");
  runBtn.disabled = true;

  let accident;
  let vehicles;

  if (mode === "click") {
    vehicles = locations.vehicles.map((v) => ({
      name: v.name,
      lat: v.lat,
      lon: v.lon,
    }));
    accident = locations.accident;
  } else {
    // coordinate mode
    vehicles = [];
    for (let i = 0; i < numVehicles; i++) {
      const name = locations.vehicles[i].name || `Vehicle ${i + 1}`;
      const lat = parseFloat(document.getElementById(`v${i}-lat`).value);
      const lon = parseFloat(document.getElementById(`v${i}-lon`).value);
      vehicles.push({ name, lat, lon });
    }
    accident = {
      lat: parseFloat(document.getElementById("acc-lat").value),
      lon: parseFloat(document.getElementById("acc-lon").value),
    };
  }

  try {
    const resp = await fetch("/run_algorithms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accident, vehicles }),
    });
    const data = await resp.json();
    if (!data.ok) {
      updateStatus("Error: " + data.error);
      runBtn.disabled = false;
      return;
    }
    renderResults(data.results);
    document.getElementById("visualize-container").classList.remove("hidden");
    updateStatus("Done. See results and open the visualization map.");
  } catch (err) {
    console.error(err);
    updateStatus("Error calling backend.");
  } finally {
    runBtn.disabled = false;
  }
}

function renderResults(results) {
  const panel = document.getElementById("results-panel");
  panel.innerHTML = "";

  // Independent A*
  const indep = results.independent;
  const indepSection = document.createElement("div");
  indepSection.className = "results-section";
  indepSection.innerHTML = `
    <h3>1️⃣ ${indep.algo}</h3>
    <p>Runtime: ${indep.time_ms.toFixed(2)} ms</p>
  `;
  const indepList = document.createElement("ul");
  indep.vehicles.forEach((v) => {
    const li = document.createElement("li");
    li.textContent = `${v.vehicle}: steps=${v.steps}, ETA≈${v.eta_min.toFixed(
      2
    )} min`;
    indepList.appendChild(li);
  });
  indepSection.appendChild(indepList);
  panel.appendChild(indepSection);

  // Cooperative
  const coop = results.cooperative;
  const coopSection = document.createElement("div");
  coopSection.className = "results-section";
  coopSection.innerHTML = `
    <h3>2️⃣ ${coop.algo}</h3>
    <p>Runtime: ${coop.time_ms.toFixed(2)} ms</p>
  `;
  const coopList = document.createElement("ul");
  coop.vehicles.forEach((v) => {
    const li = document.createElement("li");
    li.textContent = `${v.vehicle}: steps=${v.steps}, ETA≈${v.eta_min.toFixed(
      2
    )} min`;
    coopList.appendChild(li);
  });
  coopSection.appendChild(coopList);
  panel.appendChild(coopSection);

  // D*-Lite
  const dstar = results.dstar || {};
  const dstarSection = document.createElement("div");
  dstarSection.className = "results-section";
  if (dstar.vehicle) {
    dstarSection.innerHTML = `
      <h3>3️⃣ D*-Lite Replanning</h3>
      <p>Vehicle: ${dstar.vehicle}</p>
      <p>Initial path length: ${dstar.initial_len}</p>
      <p>After blocking & replanning: ${dstar.replanned_len}</p>
    `;
  } else {
    dstarSection.innerHTML = `
      <h3>3️⃣ D*-Lite Replanning</h3>
      <p>No agent available for demo.</p>
    `;
  }
  panel.appendChild(dstarSection);

  panel.classList.remove("hidden");
}
