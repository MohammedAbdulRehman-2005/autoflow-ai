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

def generate_followup_questions(intent):
    questions = []

    apps = intent.get("apps", [])

    if "google_drive" in apps:
        questions.append(
            "Which Google Drive folder should I use?"
        )

    if "slack" in apps:
        questions.append(
            "Which Slack channel should receive notifications?"
        )

    if "gmail" in apps:
        questions.append(
            "Which Gmail account should I monitor?"
        )

    if "google_forms" in apps:
        questions.append("Which Google Form should trigger this workflow?")

    if "google_calendar" in apps:
        questions.append("Which calendar should I use?")

    if "google_sheets" in apps:
        questions.append("Which spreadsheet should I read data from?")

    if "whatsapp" in apps:
        questions.append("Which WhatsApp number should receive messages?")

    if "webhook" in apps:
        questions.append("Which webhook endpoint should trigger this workflow?")

    if not questions:
        questions = [
            "what should trigger this workflow?",
            "What action should happen after the trigger?",
            "Which apps or services should be involved?"
        ]  

    return questions


def detect_missing_fields(workflow: dict):
    missing = []

    workflow_str = str(workflow).lower()

    if "google_drive" in workflow_str and "folder" not in workflow_str:
        missing.append("google drive folder")

    if "slack" in workflow_str and "channel" not in workflow_str:
        missing.append("slack channel")

    if "gmail" in workflow_str and "recipient" not in workflow_str:
        missing.append("email recipient")

    return missing
