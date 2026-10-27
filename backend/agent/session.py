from __future__ import annotations

import asyncio
import logging
from typing import Any

from backend.agent.language import LanguageManager
from backend.agent.prompts.builder import build_system_prompt
from backend.agent.providers.base import ProviderSet
from backend.agent.recording import ConsentGatedRecorder
from backend.agent.tools import AgentToolExecutor
from backend.evals.llm_tool_bench.tools_spec import CLINIC_TOOLS

logger = logging.getLogger("clinicvoice")


class CallSession:
    """Manages full streaming lifecycle for an active call."""

    def __init__(
        self,
        call_id: str,
        clinic_context: dict[str, Any],
        providers: ProviderSet,
        api_base_url: str = "http://localhost:8000",
        service_token: str = "dev_internal_service_token_123",
        initial_language: str = "ml-IN",
    ) -> None:
        self.call_id = call_id
        self.clinic_context = clinic_context
        self.clinic_id = str(clinic_context["clinic_id"])
        self.providers = providers
        self.lang_manager = LanguageManager(initial_language)
        self.recorder = ConsentGatedRecorder(api_base_url, service_token, self.clinic_id, call_id)
        self.tool_executor = AgentToolExecutor(api_base_url, service_token, self.clinic_id, call_id)

        self.messages: list[dict[str, Any]] = []
        self.consecutive_silence_count = 0
        self.is_active = True
        self.is_speaking = False

        # Interruption config
        interruption_cfg = clinic_context.get("interruption") or {}
        self.min_speech_duration_ms = interruption_cfg.get("min_speech_duration_ms", 250)
        self.silence_threshold_ms = interruption_cfg.get("silence_threshold_ms", 600)

        # Initialize conversation with system prompt
        self._refresh_system_prompt()

    def _refresh_system_prompt(self) -> None:
        sys_prompt = build_system_prompt(self.clinic_context, language=self.lang_manager.current_language)
        if not self.messages:
            self.messages.append({"role": "system", "content": sys_prompt})
        else:
            self.messages[0] = {"role": "system", "content": sys_prompt}

    async def handle_caller_utterance(self, caller_text: str) -> dict[str, Any]:
        """
        Process a single speech turn from caller:
        1. Check interruption (if agent was speaking, immediately stop)
        2. Detect & switch language if needed
        3. Send context to LLM with tools
        4. Execute any tools returned
        5. Generate audio via TTS
        """
        if not caller_text.strip():
            self.consecutive_silence_count += 1
            if self.consecutive_silence_count >= 2:
                # Ending call politely after repeated silence
                farewell = (
                    "താങ്കൾ സംസാരിക്കുന്നത് വ്യക്തമല്ല. ഞങ്ങൾ കുറച്ചു കഴിഞ്ഞ് തിരികെ വിളിക്കാം. നന്ദി."
                    if self.lang_manager.current_language == "ml-IN"
                    else "I could not hear any response. We will create a callback for you. Thank you."
                )
                await self.tool_executor.execute_tool("request_callback", {"reason": "Call disconnected due to silence"})
                self.is_active = False
                return {"type": "hangup", "text": farewell}

            prompt_user = (
                "ഹലോ? ഞാൻ പറയുന്നത് കേൾക്കാമോ?"
                if self.lang_manager.current_language == "ml-IN"
                else "Hello? Are you still on the line?"
            )
            return {"type": "speech", "text": prompt_user}

        self.consecutive_silence_count = 0

        # Handle Interruption: cut off in-flight speech
        if self.is_speaking:
            logger.info("Caller interrupted agent mid-sentence. Halting playback and cancelling current stream.")
            self.is_speaking = False

        # Dynamic Language Switching
        active_lang, did_switch = self.lang_manager.process_turn(caller_text)
        if did_switch:
            logger.info("Language dynamically switched to: %s", active_lang)
            self._refresh_system_prompt()

        # Check for consent answer if pending
        lower = caller_text.lower()
        if self.recorder.consent_given is None:
            if any(w in lower for w in ["yes", "ശരി", "സമ്മതം", "record", "okay", "ഓക്കെ"]):
                await self.recorder.log_consent(True)
            elif any(w in lower for w in ["no", "വേണ്ട", "പാടില്ല", "don't"]):
                await self.recorder.log_consent(False)

        # Append caller message
        self.messages.append({"role": "user", "content": caller_text})

        # Generate LLM response with tool calling
        reply_text, tool_calls = await self.providers.llm.generate_response(self.messages, CLINIC_TOOLS)

        tool_results = []
        if tool_calls:
            for call in tool_calls:
                logger.info("Executing tool '%s' with args %s", call["name"], call["arguments"])
                res = await self.tool_executor.execute_tool(call["name"], call["arguments"])
                tool_results.append({"tool": call["name"], "result": res})
                self.messages.append(
                    {"role": "assistant", "content": f"[Executed tool {call['name']}: {res}]"}
                )

                # Formulate natural response if LLM provided tool only
                if not reply_text:
                    if call["name"] == "get_free_slots":
                        slots = res.get("slots", [])
                        if slots:
                            slot_times = ", ".join(s["time_str"] for s in slots[:3])
                            reply_text = f"ലഭ്യമായ സമയം: {slot_times}. ഇതിൽ ഏത് സമയമാണ് സൗകര്യം?"
                        else:
                            reply_text = "ക്ഷമിക്കണം, ആ ദിവസം സമയങ്ങൾ ലഭ്യമല്ല. മറ്റൊരു ദിവസം നോക്കട്ടെ?"
                    elif call["name"] == "escalate_emergency":
                        reply_text = res.get("disclaimer_ml", "അടിയന്തിര സഹായം ലഭ്യമാക്കുന്നു.")

        if reply_text:
            self.messages.append({"role": "assistant", "content": reply_text})
            # Synthesize audio bytes via TTS
            self.is_speaking = True
            audio_bytes = await self.providers.tts.synthesize(reply_text, language=active_lang)
            self.is_speaking = False
            return {
                "type": "speech",
                "text": reply_text,
                "language": active_lang,
                "tool_results": tool_results,
                "audio_bytes": audio_bytes,
            }

        return {"type": "none", "tool_results": tool_results}
