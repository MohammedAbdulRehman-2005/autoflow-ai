from backend.intent_parser.gemini_followup import generate_followup_questions

def parse_user_intent(prompt: str):
    prompt = prompt.lower()

    result = {
        "industry": None,
        "goal": None,
        "apps": [],
        "confidence": 0.8
    }

    if "gmail" in prompt:
        result["apps"].append("gmail")

    if "slack" in prompt:
        result["apps"].append("slack")

    if "google drive" in prompt:
        result["apps"].append("google_drive")

    if "google sheets" in prompt:
        result["apps"].append("google_sheets")

    if "calendar" in prompt:
        result["apps"].append("google_calendar")

    return result


