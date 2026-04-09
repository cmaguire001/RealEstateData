let charts = [];

async function loadData() {
  const response = await fetch("data.json", { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load data.json");
  return response.json();
}

function formatDate(value) {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

function destroyCharts() {
  charts.forEach((c) => c.destroy());
  charts = [];
}

function createLineChart(ctx, label, labels, values, color) {
  const chart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label,
          data: values,
          borderColor: color,
          backgroundColor: color,
          tension: 0.25,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
    },
  });
  charts.push(chart);
}

function renderCity(seriesByCity, city) {
  const rows = seriesByCity[city] || [];
  destroyCharts();

  if (!rows.length) {
    document.getElementById("last-update").textContent = `No data yet for ${city}`;
    return;
  }

  const labels = rows.map((r) => formatDate(r.timestamp));
  const last = rows[rows.length - 1];
  document.getElementById("last-update").textContent = formatDate(last.timestamp);

  createLineChart(
    document.getElementById("listingsChart"),
    `Total Listings (${city})`,
    labels,
    rows.map((r) => r.total_listings),
    "#2563eb"
  );

  createLineChart(
    document.getElementById("avgPriceChart"),
    `Average Price (${city})`,
    labels,
    rows.map((r) => r.avg_price),
    "#16a34a"
  );

  createLineChart(
    document.getElementById("ppsfChart"),
    `Average Price / Sqft (${city})`,
    labels,
    rows.map((r) => r.avg_price_per_sqft),
    "#ea580c"
  );
}

async function main() {
  try {
    const payload = await loadData();
    const cities = payload.cities || [];
    const series = payload.series || {};

    if (!cities.length) {
      document.getElementById("last-update").textContent = "No data yet";
      return;
    }

    const select = document.getElementById("city-select");
    cities.forEach((city) => {
      const option = document.createElement("option");
      option.value = city;
      option.textContent = city;
      select.appendChild(option);
    });

    select.addEventListener("change", () => renderCity(series, select.value));
    renderCity(series, cities[0]);
  } catch (error) {
    document.getElementById("last-update").textContent = `Error: ${error.message}`;
  }
}

main();
