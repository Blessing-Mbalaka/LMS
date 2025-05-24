
  const data = [
    { qualification: "Maintenance Planner", toolsGenerated: 10, toolsSubmitted: 8, questionsAdded: 5 },
    // { qualification: "Quality Controller", toolsGenerated: 15, toolsSubmitted: 12, questionsAdded: 9 }
  ];

  let chartInstance;

  function updateCounts(filtered) {
    document.getElementById("toolsGenerated").innerText = filtered.reduce((sum, r) => sum + r.toolsGenerated, 0);
    document.getElementById("toolsSubmitted").innerText = filtered.reduce((sum, r) => sum + r.toolsSubmitted, 0);
    document.getElementById("questionsAdded").innerText = filtered.reduce((sum, r) => sum + r.questionsAdded, 0);
  }

  function renderChart(filtered) {
    const labels = filtered.map(d => d.qualification);
    const generated = filtered.map(d => d.toolsGenerated);
    const submitted = filtered.map(d => d.toolsSubmitted);
    const added = filtered.map(d => d.questionsAdded);

    const ctx = document.getElementById("assessorChart").getContext("2d");
    if (chartInstance) chartInstance.destroy();

    chartInstance = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "Tools Generated", data: generated, backgroundColor: "#734e94" },
          { label: "Tools Submitted", data: submitted, backgroundColor: "#c7811f" },
          { label: "Questions Added", data: added, backgroundColor: "#360459" }
        ]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: "top" } },
        scales: { y: { beginAtZero: true } }
      }
    });
  }

  function filterChart() {
    const selected = document.getElementById("qualificationFilter").value;
    const filtered = selected ? data.filter(d => d.qualification === selected) : data;
    updateCounts(filtered);
    renderChart(filtered);
  }

  function exportCSV() {
    const csvHeader = "Qualification,Tools Generated,Tools Submitted,Questions Added\n";
    const rows = data.map(r => `${r.qualification},${r.toolsGenerated},${r.toolsSubmitted},${r.questionsAdded}`).join("\n");
    const blob = new Blob([csvHeader + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "assessor_developer_reports.csv";
    link.click();
  }

  filterChart();