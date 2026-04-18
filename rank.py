from datetime import datetime
from groq import Groq

client = Groq(api_key="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")

# ─────────────────────────────────────────
# STUDENT PROFILE SHAPE (for reference)
# ─────────────────────────────────────────
#
# student = {
#     "name":             "Amina",
#     "gpa":              3.4,
#     "degree":           "CS",
#     "semester":         6,
#     "skills":           ["python", "ml", "c++"],
#     "interests":        ["AI", "research"],
#     "preferred_type":   ["internship", "competition"],
#     "preferences": {
#         "mode":         "remote",   # "remote" / "onsite" / "any"
#         "paid":         True,       # True = wants paid only
#         "max_hours":    20          # max hours per week they can give
#     },
#     "past_experiences": ["internship", "research"]
# }

# ─────────────────────────────────────────
# SCORE 1: FIT
# ─────────────────────────────────────────
def compute_fit(opportunity, student):
    prefs          = student.get("preferences", {})
    required       = opportunity.get("required_skills", [])
    student_skills = student.get("skills", [])

    if len(required) == 0:
        skill_match = 1.0
    else:
        matched     = set(r.lower() for r in required) & set(s.lower() for s in student_skills)
        skill_match = len(matched) / len(required)

    type_match = 1 if opportunity.get("type") in student.get("preferred_type", []) else 0

    gpa_match = 1 if student.get("gpa", 0) >= opportunity.get("min_gpa", 0) else 0

    opp_mode     = opportunity.get("mode", "any").lower()
    student_mode = prefs.get("mode", "any").lower()
    if student_mode == "any" or opp_mode == "any":
        mode_match = 1
    else:
        mode_match = 1 if opp_mode == student_mode else 0

    wants_paid = prefs.get("paid", False)
    opp_paid   = opportunity.get("paid", False)
    if not wants_paid:
        pay_match = 1
    else:
        pay_match = 1 if opp_paid else 0.2

    student_max_hours = prefs.get("max_hours", 99)
    opp_hours         = opportunity.get("hours_per_week", 0)
    if opp_hours == 0:
        hours_match = 1
    else:
        hours_match = 1 if opp_hours <= student_max_hours else 0

    min_sem          = opportunity.get("min_semester", 0)
    max_sem          = opportunity.get("max_semester", 99)
    student_semester = student.get("semester", 0)
    semester_match   = 1 if min_sem <= student_semester <= max_sem else 0

    fit = (
        0.35 * skill_match    +
        0.20 * type_match     +
        0.15 * gpa_match      +
        0.10 * mode_match     +
        0.10 * pay_match      +
        0.10 * hours_match    +
        0.10 * semester_match
    )
    return round(min(fit, 1.0), 3)


# ─────────────────────────────────────────
# SCORE 2: URGENCY
# ─────────────────────────────────────────
def compute_urgency(deadline_str):
    try:
        deadline  = datetime.strptime(deadline_str, "%Y-%m-%d")
        days_left = (deadline - datetime.now()).days

        if days_left < 0:     return 0.0
        elif days_left <= 3:  return 1.0
        elif days_left <= 7:  return 0.7
        elif days_left <= 30: return 0.4
        else:                 return 0.2
    except:
        return 0.3


# ─────────────────────────────────────────
# SCORE 3: COMPLETENESS
# ─────────────────────────────────────────
def compute_completeness(opportunity):
    fields = [
        opportunity.get("deadline"),
        opportunity.get("type"),
        opportunity.get("title"),
        opportunity.get("required_skills"),
        opportunity.get("mode"),
        opportunity.get("paid"),
        opportunity.get("hours_per_week"),
    ]
    filled = sum(1 for f in fields if f is not None and f != "" and f != [])
    return round(filled / len(fields), 3)


# ─────────────────────────────────────────
# COMBINE: Final score
# ─────────────────────────────────────────
def compute_score(opportunity, student):
    fit          = compute_fit(opportunity, student)
    urgency      = compute_urgency(opportunity.get("deadline", ""))
    completeness = compute_completeness(opportunity)

    final = (0.5 * fit) + (0.3 * urgency) + (0.2 * completeness)
    return round(final, 3)


# ─────────────────────────────────────────
# EXPLAIN: Reason sentence
# ─────────────────────────────────────────
def explain(opportunity, student):
    name    = student.get("name", "You")
    prefs   = student.get("preferences", {})
    reasons = []

    required       = opportunity.get("required_skills", [])
    matched_skills = (
        set(r.lower() for r in required) &
        set(s.lower() for s in student.get("skills", []))
    )
    if matched_skills:
        reasons.append(f"skills match ({', '.join(matched_skills)})")
    elif not required:
        reasons.append("no specific skills required — open to all")

    if opportunity.get("type") in student.get("preferred_type", []):
        reasons.append("matches preferred opportunity type")

    if student.get("gpa", 0) >= opportunity.get("min_gpa", 0):
        reasons.append("GPA requirement met")

    opp_mode     = opportunity.get("mode", "any").lower()
    student_mode = prefs.get("mode", "any").lower()
    if opp_mode == student_mode and opp_mode != "any":
        reasons.append(f"{opp_mode} mode matches preference")

    if prefs.get("paid") and opportunity.get("paid"):
        reasons.append("paid opportunity")
    elif prefs.get("paid") and not opportunity.get("paid"):
        reasons.append("unpaid — lower priority for you")

    student_max = prefs.get("max_hours", 99)
    opp_hours   = opportunity.get("hours_per_week", 0)
    if opp_hours > 0:
        if opp_hours <= student_max:
            reasons.append(f"{opp_hours} hrs/week fits your schedule")
        else:
            reasons.append(f"requires {opp_hours} hrs/week — exceeds your limit of {student_max}")

    past     = student.get("past_experiences", [])
    opp_type = opportunity.get("type", "")
    if "internship" in past and opp_type in ["fellowship", "research"]:
        reasons.append("past internship experience strengthens this application")

    try:
        days_left = (
            datetime.strptime(opportunity.get("deadline", ""), "%Y-%m-%d") - datetime.now()
        ).days
        if days_left < 0:
            reasons.append("deadline has already passed")
        elif days_left <= 3:
            reasons.append(f"deadline in {days_left} day(s) — act immediately")
        elif days_left <= 7:
            reasons.append(f"deadline in {days_left} days — act soon")
        else:
            reasons.append(f"deadline in {days_left} days")
    except:
        reasons.append("deadline not specified")

    return f"Ranked for {name} — " + ", ".join(reasons) + "."


# ─────────────────────────────────────────
# MAIN: Rank all opportunities
# ─────────────────────────────────────────
def rank_opportunities(opportunities, student):
    results = []

    for opp in opportunities:
        score  = compute_score(opp, student)
        reason = explain(opp, student)

        results.append({
            "title":          opp.get("opportunity_title"),
            "type":           opp.get("opportunity_type"),
            "deadline":       opp.get("deadline"),
            "paid":           opp.get("paid", False),
            "mode":           opp.get("mode", "unknown"),
            "hours_per_week": opp.get("hours_per_week", 0),
            "score":          score,
            "reason":         reason
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)


# ─────────────────────────────────────────
# BEAUTIFY: Groq-powered output formatter
# ─────────────────────────────────────────
def beautify_output(raw_output: str):
    prompt = f"""
You are a professional UI formatting assistant.

Your job is to convert raw AI ranking output into a clean, professional dashboard-style format.

STRICT RULES:
- DO NOT change any facts, scores, or data
- DO NOT add new information
- ONLY improve formatting and readability
- Keep everything concise and structured
- Make it look like a polished product UI for students
- Preserve ranking order exactly

FORMAT STYLE:

══════════════════════
#1 Title
══════════════════════

Type: ...
Deadline: ...
Score: ...

Fit Summary:
- Skills Match: ...
- Type Match: ...
- GPA Match: ...
- Mode Match: ...

Urgency: ...

Why Ranked:
- ...
- ...
- ...

Action:
→ ...

INPUT:
{raw_output}

Return ONLY the improved version.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


# ─────────────────────────────────────────
# TEST
# ─────────────────────────────────────────
if __name__ == "__main__":

    opportunities = [
        {
            "title":           "Google Summer Internship",
            "type":            "internship",
            "deadline":        "2026-04-22",
            "required_skills": ["python", "ml"],
            "min_gpa":         3.0,
            "mode":            "remote",
            "paid":            True,
            "hours_per_week":  15,
            "min_semester":    4,
            "max_semester":    8
        },
        {
            "title":           "HEC Need-Based Scholarship",
            "type":            "scholarship",
            "deadline":        "2026-06-15",
            "required_skills": [],
            "min_gpa":         2.5,
            "mode":            "any",
            "paid":            True,
            "hours_per_week":  0,
            "min_semester":    1,
            "max_semester":    8
        },
        {
            "title":           "ICPC Programming Contest",
            "type":            "competition",
            "deadline":        "2026-04-20",
            "required_skills": ["c++", "algorithms"],
            "min_gpa":         0,
            "mode":            "onsite",
            "paid":            False,
            "hours_per_week":  10,
            "min_semester":    1,
            "max_semester":    8
        },
        {
            "title":           "Research Fellowship - NLP",
            "type":            "fellowship",
            "deadline":        "2026-05-30",
            "required_skills": ["python", "nlp", "ml"],
            "min_gpa":         3.5,
            "mode":            "remote",
            "paid":            True,
            "hours_per_week":  25,
            "min_semester":    5,
            "max_semester":    8
        }
    ]

    student = {
        "name":             "Amina",
        "gpa":              3.4,
        "degree":           "CS",
        "semester":         6,
        "skills":           ["python", "ml", "c++"],
        "interests":        ["AI", "research"],
        "preferred_type":   ["internship", "competition"],
        "preferences": {
            "mode":         "remote",
            "paid":         True,
            "max_hours":    20
        },
        "past_experiences": ["internship", "research"]
    }

    results = rank_opportunities(opportunities, student)

    # Build raw output string
    raw_output = f"\n========== RANKED FOR {student['name'].upper()} ==========\n\n"
    for i, r in enumerate(results, 1):
        paid_label  = "Paid" if r["paid"] else "Unpaid"
        hours_label = f"{r['hours_per_week']} hrs/week" if r["hours_per_week"] else "hours unspecified"
        raw_output += f"#{i}  {r['title']}\n"
        raw_output += f"     Type:     {r['type']} | {paid_label} | {r['mode']} | {hours_label}\n"
        raw_output += f"     Deadline: {r['deadline']}\n"
        raw_output += f"     Score:    {r['score']}\n"
        raw_output += f"     Reason:   {r['reason']}\n\n"

    # Print raw then beautified
    print(raw_output)
    print("\n========== BEAUTIFIED OUTPUT ==========\n")
    print(beautify_output(raw_output))