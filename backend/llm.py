import os
import json
from typing import List, Optional
from dotenv import load_dotenv
import openai
from anthropic import Anthropic
from google import genai

load_dotenv()

class LLMService:
    def __init__(self, provider: str = "openai", model: str = None):
        self.provider = provider
        self.model = model
        
        if provider == "openai":
            self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.default_model = "gpt-4o"
        elif provider == "anthropic":
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.default_model = "claude-3-5-sonnet-20240620"
        elif provider == "gemini":
            self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            self.default_model = "gemini-2.0-flash"
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def generate_response(self, system_prompt: str, user_prompt: str) -> dict:
        model = self.model or self.default_model
        print(f"--- LLM REQUEST: Provider={self.provider}, Model={model} ---")

        
        try:
            if self.provider == "openai":
                messages = []
                # o1 models usually don't support 'system' role, or handle it differently.
                # Safe approach: merge system into user for o1 models
                if model.startswith("o1"):
                    messages = [{"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}]
                    # o1 doesn't support response_format="json_object" strictly in all versions yet, or it's beta.
                    # We'll rely on text generation and manual JSON extraction.
                    response = await self.client.chat.completions.create(
                        model=model,
                        messages=messages
                    )
                    content = response.choices[0].message.content
                    return self._extract_json(content)
                else:
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                    response = await self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        response_format={"type": "json_object"}
                    )
                    return json.loads(response.choices[0].message.content)

            
            elif self.provider == "anthropic":
                # Anthropic doesn't have an async client in the same way, but we'll use wraps or similar if needed.
                # For simplicity in this scratchpad, we'll assume a standard call or use a thread pool if async is critical.
                # Actually, anthropic has AsyncAnthropic.
                from anthropic import AsyncAnthropic
                async_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                response = await async_client.messages.create(
                    model=model,
                    max_tokens=1024,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                # Parse JSON from text
                content = response.content[0].text
                return self._extract_json(content)

            elif self.provider == "gemini":
                # Using new google-genai SDK
                # Note: google-genai's client.models.generate_content is not natively async in the current beta? 
                # Let's check. Actually, it uses a sync client usually unless specified.
                # For now, we'll use run_in_executor to keep it non-blocking if needed, or check if they added async.
                # The latest google-genai has an 'aio' property or similar.
                
                response = self.client.models.generate_content(
                    model=model,
                    config={
                        'system_instruction': system_prompt,
                        'response_mime_type': 'application/json',
                    },
                    contents=user_prompt
                )
                return json.loads(response.text)
                
        except Exception as e:
            print(f"LLM Error ({self.provider}): {e}")
            raise e

    def _extract_json(self, text: str) -> dict:
        try:
            # Simple extraction in case LLM wraps in markdown
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text.strip())
        except:
            return {}
