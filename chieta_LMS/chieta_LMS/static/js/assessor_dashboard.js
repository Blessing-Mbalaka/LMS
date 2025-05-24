const assessments = JSON.parse(localStorage.getItem("submittedAssessments")) || [
    {
      id: "EISA 1",
      qualification: "Maintenance Planner",
      paper: "1A",
      moderator: "Pending",
      status: "Pending"
    },
    {
      id: "EISA 2",
      qualification: "Quality Controller",
      paper: "2A",
      moderator: "Approved",
      status: "Submitted"
    }
  ];

  const tbody = document.getElementById("assessmentTableBody");
  assessments.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td style="padding: 10px; text-align: center;">${row.id}</td>
      <td style="padding: 10px; text-align: center;">${row.qualification}</td>
      <td style="padding: 10px; text-align: center;">${row.paper}</td>
      <td style="padding: 10px; text-align: center;">${row.moderator}</td>
      <td style="padding: 10px; text-align: center;">${row.status}</td>
      <td style="padding: 10px; text-align: center;">
        <button class="gradient-button" style="padding: 6px 12px; font-size: 12px;" onclick="viewAssessment('${row.id}')">View</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  function viewAssessment(eisaId) {
    const all = JSON.parse(localStorage.getItem("submittedAssessments")) || [];
    const found = all.find(a => a.id === eisaId);
    if (!found) return alert("Assessment not found.");
    localStorage.setItem("selectedAssessment", JSON.stringify(found));
    window.location.href = "view_assessment.html";
  }