import json
from google import genai
from app.core.config import settings


class AIClient:
    def __init__(self):
        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

    def generate_json(self, prompt: str) -> dict:
        full_prompt = f"""
{SYSTEM_PROMPT}
Return ONLY valid JSON.

Schema:
{{
    "confidence": "",
    "reasoning": ""
}}

{prompt}
"""

        for attempt in range(2):
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_prompt,
            )

            text = response.text

            if not text:
                if attempt == 0:
                    continue
                raise ValueError("Gemini returned empty response")

            try:
                return json.loads(text)

            except json.JSONDecodeError:
                if attempt == 0:
                    full_prompt += """

Your previous response was not valid JSON.

Return ONLY raw JSON.
No markdown.
No explanations.
No code fences.
"""
                    continue

                raise ValueError(
                    f"Failed to parse Gemini response:\n{text}"
                )
        raise ValueError("Failed to generate valid JSON")
            
SYSTEM_PROMPT = """
You are an assistant for a rental deposit dispute platform.

Rules:

1. Never state that the user will win.
2. Never guarantee an outcome.
3. Use only one confidence label:

- supported
- weak
- unsupported
- unclear

4. Always provide reasoning.
5. Base conclusions only on supplied evidence.
6. If evidence is insufficient, use 'unclear'.
7. Return only valid JSON.
"""

