
def parse_user_intent(prompt: str):

    prompt = prompt.lower()

    if "dental" in prompt or "clinic" in prompt:
        return {
            "industry": "dental",
            "goal": "appointment_reminders",
            "confidence": 0.95
        }

    elif "real estate" in prompt or "property" in prompt:
        return {
            "industry": "real_estate",
            "goal": "lead_management",
            "confidence": 0.92
        }

    elif "gym" in prompt or "fitness" in prompt:
        return {
            "industry": "fitness",
            "goal": "member_engagement",
            "confidence": 0.90
        }

    elif "restaurant" in prompt or "food" in prompt:
        return {
            "industry": "restaurant",
            "goal": "customer_notifications",
            "confidence": 0.91
        }

    elif "school" in prompt or "college" in prompt:
        return {
            "industry": "education",
            "goal": "student_updates",
            "confidence": 0.89
        }

    return {
        "industry": "generic",
        "goal": "automation",
        "confidence": 0.80
    }
