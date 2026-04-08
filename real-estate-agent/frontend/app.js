async function loadData() {
  const response = await fetch("data.json", { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load data.json");
  return response.json();
}

function formatDate(value) {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

function createLineChart(ctx, label, labels, values, color) {
  return new Chart(ctx, {
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
}

async function main() {
  try {
    const rows = await loadData();
    if (!Array.isArray(rows) || rows.length === 0) {
      document.getElementById("last-update").textContent = "No data yet";
      return;
    }

    const labels = rows.map((r) => formatDate(r.timestamp));
    const last = rows[rows.length - 1];
    document.getElementById("last-update").textContent = formatDate(last.timestamp);

    createLineChart(
      document.getElementById("listingsChart"),
      "Total Listings",
      labels,
      rows.map((r) => r.total_listings),
      "#2563eb"
    );

    createLineChart(
      document.getElementById("avgPriceChart"),
      "Average Price",
      labels,
      rows.map((r) => r.avg_price),
      "#16a34a"
    );

    createLineChart(
      document.getElementById("ppsfChart"),
      "Average Price / Sqft",
      labels,
      rows.map((r) => r.avg_price_per_sqft),
      "#ea580c"
    );
  } catch (error) {
    document.getElementById("last-update").textContent = `Error: ${error.message}`;
  }
}

main();
