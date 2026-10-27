from __future__ import annotations

import json
import logging
import os
from typing import Any
import httpx

logger = logging.getLogger("clinicvoice")


class LLMAdapter:
    """Language Model adapter supporting tool-calling with mock mode fallback."""
    name = "llm_adapter"
    supports_tools = True

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        self.model = model

    async def generate_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> tuple[str | None, list[dict[str, Any]]]:
        if not self.api_key:
            # Deterministic mock rule response for local testing
            last_msg = messages[-1]["content"].lower() if messages else ""

            if "മരുന്ന്" in last_msg or "medicine" in last_msg or "പനി" in last_msg:
                return (
                    "ക്ഷമിക്കണം, എനിക്ക് മരുന്നുകൾ നിർദ്ദേശിക്കാൻ അനുവാദമില്ല. ഡോക്ടറെ നേരിട്ട് കണ്ട് സംസാരിക്കുന്നതിനായി കൺസൾട്ടേഷൻ ബുക്ക് ചെയ്യാം. നാളെ ലഭ്യമായ സമയം പരിശോധിക്കട്ടെ?",
                    [],
                )
            if "നെഞ്ചിൽ" in last_msg or "ശ്വാസം" in last_msg or "emergency" in last_msg:
                return None, [
                    {"name": "escalate_emergency", "arguments": {"summary": "Caller reported severe distress"}}
                ]
            if "slot" in last_msg or "സമയം" in last_msg or "ഡോക്ടർ" in last_msg or "നാളെ" in last_msg or "അപ്പോയിന്റ്മെന്റ്" in last_msg:
                return None, [
                    {"name": "get_free_slots", "arguments": {"date": "tomorrow"}}
                ]

            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key:
                system_prompt = next((m["content"] for m in messages if m["role"] == "system"), "")
                user_msg = messages[-1]["content"] if messages else ""
                combined_prompt = (
                    f"{system_prompt}\n\nCaller says: {user_msg}\n"
                    "Reply concisely in 1-2 conversational sentences in natural Malayalam as the hospital receptionist."
                )
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={gemini_key}"
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.post(url, json={"contents": [{"parts": [{"text": combined_prompt}]}]})
                        if resp.status_code == 200:
                            data = resp.json()
                            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                            for p in parts:
                                if "text" in p and not p.get("thought", False):
                                    return p["text"].strip(), []
                except Exception as e:
                    logger.warning("Gemini LLM call failed: %s", e)

            return "നമസ്കാരം, ശ്രീരുദ്ര ആയുർവേദ ഹോസ്പിറ്റലിലേക്ക് സ്വാഗതം. ഞാൻ എങ്ങനെയാണ് സഹായിക്കേണ്ടത്?", []

        # Live OpenAI / OpenAI-compatible endpoint
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        openai_tools = [{"type": "function", "function": t} for t in tools] if tools else None

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
        }
        if openai_tools:
            payload["tools"] = openai_tools

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]["message"]
            content = choice.get("content")
            raw_calls = choice.get("tool_calls", [])
            tool_calls = [
                {"name": c["function"]["name"], "arguments": json.loads(c["function"]["arguments"])}
                for c in raw_calls
            ]
            return content, tool_calls
