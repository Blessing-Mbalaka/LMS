 const archiveData = JSON.parse(localStorage.getItem("assessmentArchive")) || [
      {
        id: "EISA-2040",
        qualification: "Maintenance Planner",
        paper: "1A",
        status: "Uploaded",
        date: "2024-11-14"
      },
      {
        id: "EISA-2041",
        qualification: "Quality Controller",
        paper: "1B",
        status: "Generated",
        date: "2024-11-16"
      },
      {
        id: "EISA-2042",
        qualification: "Quality Controller",
        paper: "2A",
        status: "Marked",
        date: "2024-11-20"
      }
    ];

    function renderArchiveTable(data) {
      const tbody = document.getElementById("archiveTableBody");
      tbody.innerHTML = "";
      data.forEach(item => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${item.id}</td>
          <td>${item.qualification}</td>
          <td>${item.paper}</td>
          <td>${item.status}</td>
          <td>${item.date}</td>
        `;
        tbody.appendChild(row);
      });
    }

    function applyFilters() {
      const qual = document.getElementById("filterQualification").value;
      const paper = document.getElementById("filterPaper").value.toLowerCase();
      const status = document.getElementById("filterStatus").value;

      const filtered = archiveData.filter(item =>
        (qual === "" || item.qualification === qual) &&
        (paper === "" || item.paper.toLowerCase().includes(paper)) &&
        (status === "" || item.status === status)
      );

      renderArchiveTable(filtered);
    }

    function exportArchive() {
      let csv = "EISA ID,Qualification,Paper,Status,Date\n";
      archiveData.forEach(item => {
        csv += `${item.id},${item.qualification},${item.paper},${item.status},${item.date}\n`;
      });

      const blob = new Blob([csv], { type: "text/csv" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "assessment_archive.csv";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }

    document.getElementById("filterQualification").addEventListener("change", applyFilters);
    document.getElementById("filterPaper").addEventListener("input", applyFilters);
    document.getElementById("filterStatus").addEventListener("change", applyFilters);

    window.onload = () => renderArchiveTable(archiveData);