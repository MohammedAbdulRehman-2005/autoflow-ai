def generate_questions(industry: str):

    if industry == "dental":
        return {
            "questions": [
                {
                    "id": "q1",
                    "text": "Which booking software do you use?",
                    "type": "text"
                }
            ]
        }

    return {
        "questions": [
            {
                "id": "q1",
                "text": "What do you want to automate?",
                "type": "text"
            }
        ]
    }
