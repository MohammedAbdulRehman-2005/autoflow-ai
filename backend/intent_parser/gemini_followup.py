import os
from dotenv import load_dotenv
import json
from google import genai
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def generate_followup_questions(user_prompt: str, workflow: dict):
    prompt = f"""
You are a Senior Business Analyst.

user request:

{user_prompt}

workflow :

{json.dumps(workflow, indent=2)}

Your job is NOT to explain the workflow.

Your job is to think like a business analyst and ask ONLY the missing questions required to execute this workflow successfully.

Rules:

- Ask between 0 and 5 questions.
- If everything is already clear, return an empty list.
- Don't ask unnecessary questions.
- Don't repeat information already present.
- Questions should be short.
- Ask business questions, not technical questions.

Examples:

Email Approval:
- Who should approve the request?
- What happens if approval is rejected?

Invoice Workflow:
- Which folder contains invoices?
- What file formats should be accepted?

Slack Notification:
- Which Slack channel should receive notifications?

Return ONLY valid JSON.

Example:

{{
  "questions":[
      "Who should approve the request?",
      "Which Slack channel should receive notifications?"
  ]
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        text = response.text.strip()

        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()

        data = json.loads(text)

        return data.get("questions", [])

    except Exception as e:
        print(e)
        return []
