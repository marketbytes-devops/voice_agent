from __future__ import annotations

import json
import logging
import os
from typing import Any
import httpx

logger = logging.getLogger("clinicvoice")


def get_hospital_knowledge() -> str:
    """Load hospital knowledge base dynamically from JSON."""
    from pathlib import Path
    kb_path = Path(__file__).resolve().parents[1] / "knowledge" / "hospital_knowledge.json"
    if kb_path.exists():
        try:
            data = json.loads(kb_path.read_text(encoding="utf-8"))
            h = data.get("hospital", {})
            docs = data.get("doctors", [])
            doc_str = "\n".join([f"- {d['name']} ({d.get('qualification')}), Specialties: {', '.join(d.get('specialties', []))}. Timings: {d.get('consultation_days')} {d.get('consultation_timings')}. Slots tomorrow: {', '.join(d.get('available_slots_tomorrow', []))}" for d in docs])
            treatments = "\n".join([f"- {t['name_ml']} ({t['name']}): {t['description']}" for t in data.get("treatments", [])])
            faqs = "\n".join([f"Q: {f['question_ml']} -> A: {f['answer_ml']}" for f in data.get("faqs", [])])
            return (
                f"Hospital: {h.get('name')} ({h.get('name_ml')}), {h.get('location')}\n"
                f"Address: {h.get('address')}\n"
                f"Hours: {h.get('working_hours')}\n\n"
                f"Doctors:\n{doc_str}\n\n"
                f"Treatments:\n{treatments}\n\n"
                f"Frequently Asked Questions (FAQs):\n{faqs}"
            )
        except Exception as e:
            logger.warning("Failed parsing hospital_knowledge.json: %s", e)
    return ""


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
        from backend.app.core.config import settings

        gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        if gemini_key:
            system_prompt = next((m["content"] for m in messages if m["role"] == "system"), "")
            user_msg = messages[-1]["content"] if messages else ""

            kb_context = get_hospital_knowledge()
            hospital_context = (
                "You are the warm, polite Malayalam voice receptionist at Sreerudra Ayurveda Hospital & Research Centre, Alappuzha.\n"
                f"Hospital Knowledge Base:\n{kb_context}\n\n"
                "Guardrails:\n"
                "1. Reply in 1-2 short, spoken sentences in natural Malayalam suited for telephone conversation.\n"
                "2. If the caller asks if Dr. Manoj is available tomorrow or wants an appointment, confirm he is available and ask which time slot (10:00 AM, 11:30 AM, 2:30 PM, or 4:00 PM) suits them best.\n"
                "3. Never prescribe or invent medicines. For emergency chest pain/breathing trouble, advise immediate emergency care.\n"
            )

            # Build conversation history snippet
            recent_turns = []
            for m in messages[-4:]:
                role = "Caller" if m["role"] == "user" else "Assistant"
                recent_turns.append(f"{role}: {m['content']}")
            history_str = "\n".join(recent_turns)

            combined_prompt = f"{hospital_context}\n\nConversation so far:\n{history_str}\n\nCaller: {user_msg}\nAssistant (in 1-2 spoken Malayalam sentences):"

            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={gemini_key}"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json={"contents": [{"parts": [{"text": combined_prompt}]}]})
                    if resp.status_code == 200:
                        data = resp.json()
                        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                        for p in parts:
                            if "text" in p and not p.get("thought", False):
                                text = p["text"].strip()
                                if text:
                                    logger.info("Gemini LLM generated reply: %s", text)
                                    return text, []
            except Exception as e:
                logger.warning("Gemini LLM call failed, falling back to local clinical rules: %s", e)

        if not self.api_key:
            # Deterministic mock rule response for local testing
            last_msg = messages[-1]["content"].lower() if messages else ""

            if "മരുന്ന്" in last_msg or "medicine" in last_msg or "പനി" in last_msg:
                return (
                    "ക്ഷമിക്കണം, എനിക്ക് മരുന്നുകൾ നിർദ്ദേശിക്കാൻ അനുവാദമില്ല. ഡോക്ടറെ നേരിട്ട് കണ്ട് സംസാരിക്കുന്നതിനായി കൺസൾട്ടേഷൻ ബുക്ക് ചെയ്യാം. നാളെ ലഭ്യമായ സമയം പരിശോധിക്കട്ടെ?",
                    [],
                )
            if "നെഞ്ചിൽ" in last_msg or "ശ്വാസം" in last_msg or "emergency" in last_msg:
                return (
                    "അടിയന്തിര സാഹചര്യങ്ങളിൽ ദയവായി തൊട്ടടുത്തുള്ള ആശുപത്രിയിലെ എമർജൻസി വിഭാഗത്തിൽ ഉടൻ ചികിത്സ തേടുക.",
                    [],
                )
            if "മനോജ്" in last_msg or "ഡോക്ടർ" in last_msg or "നാളെ" in last_msg or "ലഭ്യമാണോ" in last_msg:
                return (
                    "അതെ, ഡോക്ടർ മനോജ് നാളെ ലഭ്യമാണ്. രാവിലെ പത്ത് മണിക്കും, പതിനൊന്നരയ്ക്കും, ഉച്ചയ്ക്ക് രണ്ടരയ്ക്കും സ്ലോട്ടുകൾ ലഭ്യമാണ്. ഏത് സമയമാണ് സൗകര്യം?",
                    [],
                )

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
