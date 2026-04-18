"""
SOFTEC 2026 — Opportunity Inbox Copilot
Part 2: Email Extraction & Structuring
---------------------------------------
Handles:
  - .eml file upload only
  - Noise removal
  - Structured field extraction via Gemini
  - Fills a standard opportunity form (the "blank form")
  - Generates pros/cons summary
"""

import google.generativeai as genai
import os, json, re, email, argparse
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
# API key inside the file
API_KEY = "AIzaSyDTQwEfP73NbIlSJ6CDa6OPL_lEYnM5sbQ"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash-preview-04-17")

# ─────────────────────────────────────────────────────────────────────────────
# THE BLANK FORM — every opportunity maps onto this schema
# ─────────────────────────────────────────────────────────────────────────────
BLANK_FORM = {
    "opportunity_title":    None,   # e.g. "Chevening Scholarship 2026"
    "organization":         None,   # e.g. "UK Foreign Commonwealth Office"
    "opportunity_type":     None,   # scholarship | internship | competition | fellowship | other
    "location":             None,   # remote | city, country | null
    "deadline":             None,   # ISO date YYYY-MM-DD or null
    "duration":             None,   # e.g. "3 months", "1 year"

    # ── Eligibility ──────────────────────────────────────────────────
    "min_cgpa":             None,   # float e.g. 3.5
    "eligible_degrees":     [],     # ["CS", "EE", "Business", ...]
    "eligible_semesters":   [],     # [4, 5, 6, 7, 8]
    "eligible_genders":     "all",  # "all" | "female" | "male"
    "nationality_required": None,   # e.g. "Pakistani" or null
    "age_limit":            None,   # e.g. "under 30" or null

    # ── Requirements ─────────────────────────────────────────────────
    "required_documents":   [],     # ["CV", "Transcript", "SOP", ...]
    "skills_needed":        [],     # ["Python", "Research", ...]
    "language_requirement": None,   # e.g. "IELTS 6.5" or null
    "experience_needed":    None,   # e.g. "1 year internship" or null

    # ── Application ──────────────────────────────────────────────────
    "apply_link":           None,
    "contact_email":        None,
    "financial_benefit":    None,   # e.g. "PKR 50,000/month stipend" or null
    "covers_tuition":       None,   # true | false | null

    # ── Analysis ─────────────────────────────────────────────────────
    "specificity_score":    None,   # 0–10 how detailed/specific the email is
    "pros":                 [],     # list of strings
    "cons":                 [],     # list of strings
    "one_line_summary":     None,   # single sentence
    "raw_red_flags":        [],     # vague language, missing fields, etc.
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: .EML PARSING
# ─────────────────────────────────────────────────────────────────────────────
def extract_text_from_eml(uploaded_file) -> str:
    """Parses a .eml file and returns plain text with headers."""
    raw = uploaded_file.read()
    msg = email.message_from_bytes(raw)

    # grab key headers — useful context for the LLM
    subject = msg.get("Subject", "")
    sender  = msg.get("From", "")
    date    = msg.get("Date", "")

    plain_parts = []
    html_parts  = []

    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype == "text/plain":
            plain_parts.append(
                part.get_payload(decode=True).decode("utf-8", errors="ignore")
            )
        elif ctype == "text/html":
            html_parts.append(
                part.get_payload(decode=True).decode("utf-8", errors="ignore")
            )

    # prefer plain text, fall back to HTML with tags stripped
    if plain_parts:
        body = "\n".join(plain_parts)
    elif html_parts:
        body = re.sub(r"<[^>]+>", " ", "\n".join(html_parts))
        body = re.sub(r"\s{2,}", " ", body)
    else:
        body = ""

    # prepend headers so LLM has sender + date context
    header = f"From: {sender}\nDate: {date}\nSubject: {subject}\n\n"
    return header + body


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: NOISE REMOVAL (fast, no LLM needed)
# ─────────────────────────────────────────────────────────────────────────────
_NOISE_PATTERNS = [
    r"unsubscribe.*",
    r"view (this email|in browser).*",
    r"if you (no longer|don.t) wish.*",
    r"you('re| are) receiving this (because|email).*",
    r"follow us on.*",
    r"©.*",
    r"all rights reserved.*",
    r"this email (was sent|is intended).*",
    r"confidentiality notice.*",
    r"<[^>]+>",                     # HTML tags if any leaked through
    r"http\S+",                     # bare URLs (keep apply_link separately)
    r"\s{3,}",                      # 3+ consecutive whitespace
]

def clean_email_text(raw: str) -> str:
    text = raw
    for pat in _NOISE_PATTERNS:
        text = re.sub(pat, " ", text, flags=re.IGNORECASE)
    # collapse blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 + 4: LLM EXTRACTION — fills the blank form
# ─────────────────────────────────────────────────────────────────────────────
EXTRACTION_PROMPT = """
You are an expert opportunity analyst. Extract structured information from the email below.

Return ONLY a valid JSON object. Do NOT include markdown, code fences, or explanation.
Map every field you find. Use null for missing fields, empty [] for missing lists.

JSON schema to fill:
{{
  "opportunity_title":    string or null,
  "organization":         string or null,
  "paid":                   boolean,
  "mode":                  "remote" | "in-person" | "hybrid" | null,
  "opportunity_type":     "scholarship" | "internship" | "competition" | "fellowship" | "other",
  "location":             string or null,
  "deadline":             "YYYY-MM-DD" or null,
  "hours_per_week":       string or null, 
  "duration":             string or null,
  "min_cgpa":             number or null,
  "eligible_degrees":     [strings],
  "eligible_semesters":   [integers],
  "eligible_genders":     "all" | "female" | "male",
  "nationality_required": string or null,
  "age_limit":            string or null,
  "required_documents":   [strings],
  "skills_needed":        [strings],
  "language_requirement": string or null,
  "experience_needed":    string or null,
  "apply_link":           string or null,
  "contact_email":        string or null,
  "financial_benefit":    string or null,
  "covers_tuition":       true | false | null,
  "specificity_score":    integer 0-10,
  "pros":                 [strings, max 4],
  "cons":                 [strings, max 4],
  "one_line_summary":     string (1 sentence, under 20 words),
  "raw_red_flags":        [strings]
}}

Specificity score guide:
  0–3 = very vague, no deadline or eligibility
  4–6 = some details but missing key fields
  7–9 = detailed with most fields present
  10  = complete, all fields clear

Email text:
---
{email_text}
---
"""

def extract_structured_data(cleaned_text: str) -> dict:
    """Calls Gemini, returns filled form dict."""
    prompt = EXTRACTION_PROMPT.format(email_text=cleaned_text[:12000])  # token guard
    try:
        response = model.generate_content(prompt)
        raw_json = response.text.strip()
        # strip accidental code fences
        raw_json = re.sub(r"^```[a-z]*\n?", "", raw_json)
        raw_json = re.sub(r"\n?```$", "", raw_json)
        data = json.loads(raw_json)
        # merge with blank form so missing keys always exist
        result = BLANK_FORM.copy()
        result.update(data)
        return result
    except json.JSONDecodeError as e:
        return {**BLANK_FORM, "raw_red_flags": [f"JSON parse error: {e}"]}
    except Exception as e:
        return {**BLANK_FORM, "raw_red_flags": [f"API error: {e}"]}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def days_until(deadline_str: str | None) -> int | None:
    if not deadline_str:
        return None
    try:
        d = datetime.strptime(deadline_str, "%Y-%m-%d")
        return (d - datetime.now()).days
    except ValueError:
        return None

def urgency_label(days: int | None) -> tuple[str, str]:
    """Returns (label, color) for urgency badge."""
    if days is None:
        return "No deadline", "gray"
    if days < 0:
        return "Expired", "red"
    if days <= 7:
        return f"{days}d left — URGENT", "red"
    if days <= 21:
        return f"{days}d left — Soon", "orange"
    return f"{days}d left", "green"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PROCESSING FUNCTION
# ─────────────────────────────────────────────────────────────────────────────
def process_eml(eml_file_path: str) -> dict:
    """Process a .eml file and return the extracted structured data."""
    try:
        with open(eml_file_path, 'rb') as f:
            email_text = extract_text_from_eml(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"File '{eml_file_path}' not found.")
    except Exception as e:
        raise Exception(f"Error reading file: {e}")

    if not email_text.strip():
        raise ValueError("Could not extract text from the .eml file. The file may be empty or corrupted.")

    # Pipeline
    print("Removing noise...")
    cleaned = clean_email_text(email_text)

    print("Extracting structured fields via Gemini...")
    data = extract_structured_data(cleaned)

    return data


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT — run: python model.py email1.eml email2.eml email3.eml
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract structured opportunity data from multiple .eml files")
    parser.add_argument("eml_files", nargs="+", help="Path(s) to one or more .eml files")
    args = parser.parse_args()

    for eml_file in args.eml_files:
        try:
            print(f"\nProcessing: {eml_file}")
            data = process_eml(eml_file)
            
            # Output to JSON file (named after the input file)
            base_name = os.path.splitext(os.path.basename(eml_file))[0]
            output_file = f"{base_name}_extracted.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✓ Extracted data saved to {output_file}")
        except Exception as e:
            print(f"✗ Error processing {eml_file}: {e}")