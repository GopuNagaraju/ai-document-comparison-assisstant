"""
LLM Document Comparison Module.
Uses Google Gemini API (supports both google-genai and google-generativeai SDKs)
to generate document summaries, similarities, differences, key details comparison,
and overall conclusion with strict JSON validation and fallback handling.
"""

import os
import re
import json
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gemini-2.5-flash"

REQUIRED_KEYS = [
    "document_a_summary",
    "document_b_summary",
    "similarities",
    "differences",
    "key_details_comparison",
    "overall_conclusion",
    "limitations",
]


class LLMComparisonError(Exception):
    """Custom exception for LLM API failures, timeouts, or malformed outputs."""
    pass


def get_api_key(user_supplied_key: Optional[str] = None) -> str:
    """
    Retrieves the Gemini API key from user input or environment variables.
    """
    if user_supplied_key and user_supplied_key.strip():
        return user_supplied_key.strip()
    env_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if env_key and env_key.strip() and env_key.strip() != "your_gemini_api_key_here":
        return env_key.strip()
    raise LLMComparisonError(
        "Missing Gemini API Key. Please set GEMINI_API_KEY in your .env file "
        "or enter it in the sidebar configuration."
    )


def build_comparison_prompt(
    doc_a_name: str,
    doc_a_text: str,
    doc_b_name: str,
    doc_b_text: str,
    extraction_limitations: Optional[str] = None,
) -> str:
    """
    Constructs a strict, evidence-grounded prompt fulfilling Section 10 requirements.
    """
    limitations_context = (
        extraction_limitations
        if extraction_limitations
        else "Both PDF documents were extracted completely with no unreadable pages."
    )

    return f"""You are an expert, objective AI Document Comparison Assistant.
Your task is to compare two PDF documents based strictly and exclusively on their extracted text provided below.

CRITICAL INSTRUCTIONS & EVIDENCE RULES:
1. Use ONLY the supplied document text as evidence for the comparison. Do NOT assume, extrapolate, or invent any outside facts.
2. Keep facts from Document A ("{doc_a_name}") strictly separate from facts from Document B ("{doc_b_name}").
3. Identify similarities and meaningful differences (additions, removals, changes, or contradictions) WITHOUT inventing details. If two documents have mostly identical content, do NOT invent artificial differences.
4. Quote or reference short supporting excerpts and page numbers (e.g., "[Page 1]") where useful to ground your points.
5. State "Not found in the provided text" whenever a specific detail (such as a date, price, deadline, or requirement) is absent from one or both documents.
6. Scope Note: This is an informational comparison tool. Do NOT claim that either document is legally safe, compliant, or legally equivalent.
7. Return the output strictly as a valid JSON object matching the exact schema below (do not wrap in markdown text outside the JSON block).

REQUIRED JSON SCHEMA:
{{
  "document_a_summary": "A clear, comprehensive summary of Document A ({doc_a_name}), referencing key sections and page numbers.",
  "document_b_summary": "A clear, comprehensive summary of Document B ({doc_b_name}), referencing key sections and page numbers.",
  "similarities": [
    "Point supported by both documents with brief reference/excerpt (e.g., Both documents specify ... [Doc A Page 1, Doc B Page 1])."
  ],
  "differences": [
    {{
      "topic": "Name of topic or clause",
      "change_type": "Modified | Added in Document B | Removed in Document B | Contradiction",
      "document_a_detail": "Exact fact/excerpt from Document A (or 'Not found in the provided text')",
      "document_b_detail": "Exact fact/excerpt from Document B (or 'Not found in the provided text')",
      "explanation": "Brief neutral explanation of how the two documents differ on this point."
    }}
  ],
  "key_details_comparison": [
    {{
      "field": "Category/Field (e.g., Effective Date, Submission Deadline, Pricing/Fee, Eligibility Criteria, Contact/Owner, Key Requirement)",
      "document_a_value": "Value in Document A with page ref, or 'Not found in the provided text'",
      "document_b_value": "Value in Document B with page ref, or 'Not found in the provided text'",
      "status": "Same | Changed | Added | Removed"
    }}
  ],
  "overall_conclusion": "A short, neutral explanation of the main changes and relationship between Document A and Document B.",
  "limitations": "Note any unreadable pages, missing information, or content limitations. Extraction notes: {limitations_context}"
}}

==================== DOCUMENT A: {doc_a_name} ====================
{doc_a_text}

==================== DOCUMENT B: {doc_b_name} ====================
{doc_b_text}
"""


def parse_and_validate_llm_json(raw_response_text: str, extraction_limitations: Optional[str] = None) -> Dict[str, Any]:
    """
    Extracts JSON from the model output, validates required fields, and normalizes data structures
    so the UI and report generator never crash on malformed model output.
    """
    if not raw_response_text or not raw_response_text.strip():
        raise LLMComparisonError("The LLM returned an empty response. Please try again.")

    cleaned = raw_response_text.strip()
    # Strip markdown code fences if present
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    else:
        # Locate outermost JSON braces
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            cleaned = cleaned[first_brace : last_brace + 1]

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMComparisonError(
            f"The AI model returned malformed JSON that could not be parsed ({str(exc)}). "
            "Please click 'Compare Documents' to retry."
        ) from exc

    if not isinstance(data, dict):
        raise LLMComparisonError("Expected a JSON object from the model, but received a different format.")

    # Validate and normalize each required key
    validated: Dict[str, Any] = {}

    validated["document_a_summary"] = str(
        data.get("document_a_summary") or "Not found in the provided text."
    ).strip()
    validated["document_b_summary"] = str(
        data.get("document_b_summary") or "Not found in the provided text."
    ).strip()

    # Similarities list
    raw_sim = data.get("similarities", [])
    if isinstance(raw_sim, list):
        validated["similarities"] = [str(item).strip() for item in raw_sim if str(item).strip()]
    elif isinstance(raw_sim, str) and raw_sim.strip():
        validated["similarities"] = [raw_sim.strip()]
    else:
        validated["similarities"] = ["No specific similarities identified in the provided text."]

    # Differences list of dicts
    raw_diff = data.get("differences", [])
    normalized_diffs: List[Dict[str, str]] = []
    if isinstance(raw_diff, list):
        for item in raw_diff:
            if isinstance(item, dict):
                normalized_diffs.append({
                    "topic": str(item.get("topic", "General Difference")).strip(),
                    "change_type": str(item.get("change_type", "Modified")).strip(),
                    "document_a_detail": str(item.get("document_a_detail", "Not found in the provided text")).strip(),
                    "document_b_detail": str(item.get("document_b_detail", "Not found in the provided text")).strip(),
                    "explanation": str(item.get("explanation", "")).strip(),
                })
            elif isinstance(item, str) and item.strip():
                normalized_diffs.append({
                    "topic": "Identified Difference",
                    "change_type": "Modified",
                    "document_a_detail": "See explanation",
                    "document_b_detail": "See explanation",
                    "explanation": item.strip(),
                })
    validated["differences"] = normalized_diffs

    # Key details comparison list of dicts
    raw_details = data.get("key_details_comparison", [])
    normalized_details: List[Dict[str, str]] = []
    if isinstance(raw_details, list):
        for item in raw_details:
            if isinstance(item, dict):
                normalized_details.append({
                    "field": str(item.get("field", "Detail")).strip(),
                    "document_a_value": str(item.get("document_a_value", "Not found in the provided text")).strip(),
                    "document_b_value": str(item.get("document_b_value", "Not found in the provided text")).strip(),
                    "status": str(item.get("status", "Compared")).strip(),
                })
    validated["key_details_comparison"] = normalized_details

    validated["overall_conclusion"] = str(
        data.get("overall_conclusion")
        or "Comparison completed based on the extracted text from both documents."
    ).strip()

    model_limitations = str(data.get("limitations") or "").strip()
    if extraction_limitations and extraction_limitations not in model_limitations:
        combined_lim = f"{extraction_limitations} {model_limitations}".strip()
    else:
        combined_lim = model_limitations or (
            "No unreadable pages or missing content detected during extraction. "
            "This tool is for informational comparison only and does not constitute legal advice."
        )
    validated["limitations"] = combined_lim

    return validated


def _call_gemini_api(prompt: str, api_key: str, model_name: str = DEFAULT_MODEL) -> str:
    """
    Calls the Gemini API using either `google-genai` (new SDK) or `google-generativeai` (legacy SDK).
    """
    # Try google-genai SDK first
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        if response and response.text:
            return response.text
    except ImportError:
        pass
    except Exception as exc:
        raise LLMComparisonError(f"Gemini API error ({model_name}): {str(exc)}") from exc

    # Fallback to google-generativeai SDK
    try:
        import google.generativeai as genai_legacy

        genai_legacy.configure(api_key=api_key)
        model = genai_legacy.GenerativeModel(
            model_name=model_name,
            generation_config={"temperature": 0.1, "response_mime_type": "application/json"},
        )
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text
        raise LLMComparisonError("Empty response received from Gemini API.")
    except ImportError as exc:
        raise LLMComparisonError(
            "Neither 'google-genai' nor 'google-generativeai' is installed. "
            "Run `pip install -r requirements.txt`."
        ) from exc
    except Exception as exc:
        raise LLMComparisonError(f"Gemini API request failed: {str(exc)}") from exc


def compare_documents(
    doc_a_data: Dict[str, Any],
    doc_b_data: Dict[str, Any],
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """
    Main entry point to compare two validated PDF document dicts.
    """
    resolved_key = get_api_key(api_key)

    limitations_list: List[str] = []
    if doc_a_data.get("limitations_note"):
        limitations_list.append(doc_a_data["limitations_note"])
    if doc_b_data.get("limitations_note"):
        limitations_list.append(doc_b_data["limitations_note"])
    extraction_limitations = " | ".join(limitations_list) if limitations_list else None

    prompt = build_comparison_prompt(
        doc_a_name=doc_a_data["filename"],
        doc_a_text=doc_a_data["full_text"],
        doc_b_name=doc_b_data["filename"],
        doc_b_text=doc_b_data["full_text"],
        extraction_limitations=extraction_limitations,
    )

    raw_output = _call_gemini_api(prompt=prompt, api_key=resolved_key, model_name=model_name)
    validated_result = parse_and_validate_llm_json(
        raw_response_text=raw_output,
        extraction_limitations=extraction_limitations,
    )
    validated_result["document_a_name"] = doc_a_data["filename"]
    validated_result["document_b_name"] = doc_b_data["filename"]
    return validated_result
