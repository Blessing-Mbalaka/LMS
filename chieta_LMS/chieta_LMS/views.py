# chieta_lms/views.py
import json, random
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, JSONParser
from google import genai

from .question_bank import QUESTION_BANK
from .utils import extract_text  # your PDF/DOCX helpers

genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)

@api_view(["POST"])
@parser_classes([MultiPartParser, JSONParser])
def generate_paper(request):
    qual       = request.data.get("qualification")
    target     = int(request.data.get("mark_target", 0))
    demo_file  = request.FILES.get("file", None)

    if demo_file:
        # 1) pull raw text from the uploaded PDF
        text = extract_text(demo_file, demo_file.content_type)

        # 2) build a prompt that includes 3 sample questions from your bank
        samples = QUESTION_BANK.get(qual, [])[:3]
        examples = "\n".join(f"- {q['text']}" for q in samples)
        prompt   = (
          f"You’re an assessment generator for **{qual}**.\n"
          f"Here are some example questions:\n{examples}\n\n"
          "Now, given the following past‐paper text, generate JSON under the key 'questions',\n"
          "where each item has 'text', 'marks' and 'case_study'.\n\n"
          f"Past‐Papers Text:\n{text}"
        )

        # 3) call Gemini
        try:
            resp = genai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt]
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

        # 4) parse its JSON payload
        try:
            all_qs = json.loads(resp.text)["questions"]
        except Exception:
            return JsonResponse({"error": "Couldn’t parse Gemini JSON", "raw": resp.text}, status=500)

        pool = all_qs

    else:
        # fallback: just grab from the demo bank
        pool = QUESTION_BANK.get(qual, [])

    # 5) randomize and pick until we hit the target marks
    random.shuffle(pool)
    selected, total = [], 0
    for q in pool:
        if total + q.get("marks", 0) <= target:
            selected.append(q)
            total += q.get("marks", 0)

    return JsonResponse({"questions": selected, "total": total})
