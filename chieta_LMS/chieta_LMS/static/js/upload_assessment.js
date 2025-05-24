
  document.getElementById("uploadForm").addEventListener("submit", function (e) {
    e.preventDefault();

    const qualification = document.getElementById("qualification").value;
    const paperNumber = document.getElementById("paperNumber").value;
    const saqaID = document.getElementById("saqaID").value;
    const fileName = document.getElementById("fileInput").files[0]?.name || "Not uploaded";
    const memoName = document.getElementById("memoFile").files[0]?.name || "Not uploaded";
    const comment = document.getElementById("commentBox").value || "No comment provided";
    const forward = document.getElementById("forwardToModerator").checked ? "Yes" : "No";

    const newRecord = {
      id: `EISA-${Date.now().toString().slice(-4)}`,
      qualification,
      paper: paperNumber,
      saqaID,
      file: fileName,
      memo: memoName,
      comment: comment,
      forwardToModerator: forward,
      internal: "Pending",
      external: "Not Yet Sent",
      qcto: "Not Yet Sent"
    };

    const existing = JSON.parse(localStorage.getItem("submittedAssessments")) || [];
    existing.push(newRecord);
    localStorage.setItem("submittedAssessments", JSON.stringify(existing));

    alert("Assessment uploaded and submitted successfully!");
    window.location.href = "assessor_dashboard.html";
  });

  window.onload = function () {
    const tbody = document.getElementById("submittedListBody");
    const list = JSON.parse(localStorage.getItem("submittedAssessments")) || [];
    list.forEach(assessment => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <tr style="vertical-align: middle;">
          <td><strong>${assessment.id}</strong></td>
          <td>${assessment.qualification}</td>
          <td>${assessment.paper}</td>
          <td><span class="badge ${getStatusClass(assessment.internal)}">${assessment.internal}</span></td>
          <td><button class="gradient-button btn-sm" style="font-size: 13px; padding: 5px 12px;" onclick="viewAssessment('${assessment.id}')">✏️ View/Edit</button></td>
        </tr>
      `;
      tbody.appendChild(tr);
    });
  }

  function viewAssessment(eisaId) {
    const all = JSON.parse(localStorage.getItem("submittedAssessments")) || [];
    const found = all.find(a => a.id === eisaId);
    if (!found) return alert("Assessment not found.");
    localStorage.setItem("selectedAssessment", JSON.stringify(found));
    window.location.href = "view_assessment.html";
  }

  function getStatusClass(status) {
    const lower = status.toLowerCase();
    if (lower.includes("pending")) return "bg-warning text-dark";
    if (lower.includes("approved")) return "bg-success";
    if (lower.includes("rejected")) return "bg-danger";
    return "bg-secondary";
  }
