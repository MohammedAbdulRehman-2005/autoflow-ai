def generate_questions(industry: str):

    if industry == "dental":
        return {
            "questions": [
                {
                    "id": "q1",
                    "text": "Which booking software do you use?",
                    "type": "text"
                },
                {
                    "id": "q2",
                    "text": "How many appointments do you handle daily?",
                    "type": "number"
                },
                {
                    "id": "q3",
                    "text": "Do you send appointment reminders manually?",
                    "type": "boolean"
                }
            ]
        }

    elif industry == "real_estate":
        return {
            "questions": [
                {
                    "id": "q1",
                    "text": "How do you collect leads currently?",
                    "type": "text"
                },
                {
                    "id": "q2",
                    "text": "Do you use a CRM system?",
                    "type": "boolean"
                }
            ]
        }

    elif industry == "fitness":
        return {
            "questions": [
                {
                    "id": "q1",
                    "text": "How many members do you manage?",
                    "type": "number"
                },
                {
                    "id": "q2",
                    "text": "Do you send workout reminders?",
                    "type": "boolean"
                }
            ]
        }

    return {
        "questions": [
            {
                "id": "q1",
                "text": "What process would you like to automate?",
                "type": "text"
            },
            {
                "id": "q2",
                "text": "Which tools are currently being used?",
                "type": "text"
            }
        ]
    }
