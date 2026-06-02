
def parse_user_intent(prompt: str):

    prompt = prompt.lower()

    if "dental" in prompt:
        return {
            "industry": "dental",
            "goal": "appointment_reminders",
            "confidence": 0.95
        }

    elif "real estate" in prompt:
        return {
            "industry": "real_estate",
            "goal": "lead_management",
            "confidence": 0.92
        }

    return {
        "industry": "generic",
        "goal": "automation",
        "confidence": 0.80
    }
