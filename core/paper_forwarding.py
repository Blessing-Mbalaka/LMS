# paper_forwarding.py
#This logic is responsible for forwarding the paper






from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied

# adjust this import if your model lives elsewhere
from core.models import Assessment

# canonical status strings (keep in one place)
S_UPLOADED = "uploaded"
S_TO_ASSESSOR = "submitted_to_assessor"
S_TO_MODERATOR = "submitted_to_moderator"
S_TO_QCTO = "submitted_to_qcto"
S_TO_ETQA = "submitted_to_etqa"
S_APPROVED = "approved"

# minimal transition map (optional safety)
ALLOWED = {
    S_UPLOADED: {S_TO_ASSESSOR},
    S_TO_ASSESSOR: {S_TO_MODERATOR},
    S_TO_MODERATOR: {S_TO_QCTO},
    S_TO_QCTO: {S_TO_ETQA},
    S_TO_ETQA: {S_APPROVED},
}

def _advance(a: Assessment, next_status: str, request, note: str = "") -> Assessment:
    """Tiny helper: enforce allowed transitions, update, flash a message."""
    current = a.status or S_UPLOADED
    allowed = ALLOWED.get(current, set())
    if allowed and next_status not in allowed:
        # allow silently, or raise; raising helps catch accidental jumps
        messages.error(request, f"Cannot move from '{current}' to '{next_status}'.")
        raise PermissionDenied(f"Transition {current} -> {next_status} not allowed.")

    a.status = next_status
    a.save(update_fields=["status"])
    # toast for UX (safe if messages framework is on)
    try:
        labels = {
            S_UPLOADED: "Uploaded",
            S_TO_ASSESSOR: "Submitted to Assessor",
            S_TO_MODERATOR: "Submitted to Moderator",
            S_TO_QCTO: "Submitted to QCTO",
            S_TO_ETQA: "Submitted to ETQA",
            S_APPROVED: "Approved",
        }
        messages.success(request, f"Status updated: {labels.get(next_status, next_status)}")
    except Exception:
        pass
    return a

@require_POST
def send_to_assessor(request, pk):
    a = get_object_or_404(Assessment, pk=pk)
    _advance(a, S_TO_ASSESSOR, request)
    return redirect("assessment_detail", pk=a.pk)

@require_POST
def send_to_moderator(request, pk):
    a = get_object_or_404(Assessment, pk=pk)
    _advance(a, S_TO_MODERATOR, request)
    return redirect("assessment_detail", pk=a.pk)

@require_POST
def send_to_qcto(request, pk):
    a = get_object_or_404(Assessment, pk=pk)
    _advance(a, S_TO_QCTO, request)
    return redirect("assessment_detail", pk=a.pk)

@require_POST
def send_to_etqa(request, pk):
    a = get_object_or_404(Assessment, pk=pk)
    _advance(a, S_TO_ETQA, request)
    return redirect("assessment_detail", pk=a.pk)

@require_POST
def approve_etqa(request, pk):
    a = get_object_or_404(Assessment, pk=pk)
    _advance(a, S_APPROVED, request)
    return redirect("assessment_detail", pk=a.pk)
