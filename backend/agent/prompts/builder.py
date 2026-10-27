from __future__ import annotations

from pathlib import Path
from typing import Any

PROMPT_DIR = Path(__file__).parent


def build_system_prompt(clinic_context: dict[str, Any], language: str = "ml-IN") -> str:
    """Build dynamic system prompt with active clinic, doctor, and treatment context."""
    sub_dir = "ml" if language == "ml-IN" else "en"
    template_path = PROMPT_DIR / sub_dir / "system_prompt.txt"

    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = "You are the AI receptionist for {clinic_name}."

    clinic_name = clinic_context.get("clinic_name", "Sreerudra Ayurveda Hospital")
    base_prompt = template.format(clinic_name=clinic_name)

    # Append active doctors context
    doctors = clinic_context.get("doctors", [])
    if doctors:
        doc_lines = [f"- {d['name']} ({d.get('qualification') or 'Ayurveda Doctor'})" for d in doctors]
        base_prompt += f"\n\nActive Doctors:\n" + "\n".join(doc_lines)

    # Append prompt additions from database
    prompt_additions = clinic_context.get("prompt_additions")
    if prompt_additions:
        base_prompt += f"\n\nClinic Specific Notes:\n{prompt_additions}"

    return base_prompt
