# paper_forwarding.py
# Responsible for forwarding the paper through the approval pipeline,
# reusing the status strings already used across the repo/templates.

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from core.models import Assessment

# --- Canonical status strings used across templates/views in this project ---
S_UPLOADED        = "Uploaded"
S_PENDING         = "Pending"
S_TO_ASSESSOR     = "Submitted to Assessor"
S_TO_MODERATOR    = "Submitted to Moderator"
S_TO_QCTO         = "Submitted to QCTO"
S_TO_ETQA         = "Submitted to ETQA"
S_APPROVED_ETQA   = "Approved by ETQA"

# Normalize any legacy/mixed variants to the canonical strings above
NORMALIZE_MAP = {
    # uploaded/pending
    "uploaded": S_UPLOADED,
    "upload": S_UPLOADED,
    "pending": S_PENDING,

    # assessor
    "submitted_to_assessor": S_TO_ASSESSOR,
    "to_assesor": S_TO_ASSESSOR,   # typo variant seen before
    "to_assessor": S_TO_ASSESSOR,
    "toassessor": S_TO_ASSESSOR,
    "toassesordeveloper": S_TO_ASSESSOR,
    "submitted to assessor": S_TO_ASSESSOR,
    "toassesor": S_TO_ASSESSOR,    # another typo
    "toassessordeveloper": S_TO_ASSESSOR,

    # moderator
    "submitted_to_moderator": S_TO_MODERATOR,
    "to_moderator": S_TO_MODERATOR,
    "tomoderator": S_TO_MODERATOR,
    "submitted to moderator": S_TO_MODERATOR,

    # qcto
    "submitted_to_qcto": S_TO_QCTO,
    "to_qcto": S_TO_QCTO,
    "toqcto": S_TO_QCTO,
    "submitted to qcto": S_TO_QCTO,

    # etqa
    "submitted_to_etqa": S_TO_ETQA,
    "to_etqa": S_TO_ETQA,
    "toetqa": S_TO_ETQA,
    "submitted to etqa": S_TO_ETQA,

    # approved
    "approved": S_APPROVED_ETQA,
    "approved by etqa": S_APPROVED_ETQA,
}

def normalize_status(value: str | None) -> str:
    if not value:
        return S_UPLOADED
    key = str(value).strip()
    # Already canonical?
    if key in {S_UPLOADED, S_PENDING, S_TO_ASSESSOR, S_TO_MODERATOR, S_TO_QCTO, S_TO_ETQA, S_APPROVED_ETQA}:
        return key
    # Normalize by lowercase + underscores removed
    lk = key.lower().replace("-", "_").strip()
    return NORMALIZE_MAP.get(lk, key)

# Allowed transitions in order
ALLOWED = {
    S_UPLOADED:       {S_TO_ASSESSOR},
    S_PENDING:        {S_TO_ASSESSOR},
    S_TO_ASSESSOR:    {S_TO_MODERATOR},
    S_TO_MODERATOR:   {S_TO_QCTO},
    S_TO_QCTO:        {S_TO_ETQA},
    S_TO_ETQA:        {S_APPROVED_ETQA},
    S_APPROVED_ETQA:  set(),  # terminal
}

def _advance(a: Assessment, next_status: str, request) -> Assessment:
    """Enforce allowed transitions, update, and toast a message."""
    current = normalize_status(a.status)
    desired = normalize_status(next_status)

    allowed = ALLOWED.get(current, set())
    if allowed and desired not in allowed:
        messages.error(request, f"Cannot move from '{current}' to '{desired}'.")
        # Raise to catch accidental jumps; comment out if you prefer silent ignore
        raise PermissionDenied(f"Transition {current} -> {desired} not allowed.")

    a.status = desired
    a.save(update_fields=["status"])

    label = desired
    messages.success(request, f"Status updated: {label}")
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
    _advance(a, S_APPROVED_ETQA, request)
    return redirect("assessment_detail", pk=a.pk)
