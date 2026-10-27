from __future__ import annotations

# Tool definitions adhering directly to docs/SPEC.md Section 4.6

CLINIC_TOOLS: list[dict[str, any]] = [
    {
        "name": "find_or_create_patient",
        "description": "Look up existing patient by phone within the clinic or register a new one. Requires confirmed=True.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Full name of the patient"},
                "phone": {"type": "string", "description": "10-digit Indian phone number or E.164"},
                "age": {"type": "integer", "description": "Patient age"},
                "gender": {"type": "string", "enum": ["male", "female", "other"]},
                "place": {"type": "string", "description": "Town or locality in Kerala (e.g. Alappuzha)"},
                "preferred_language": {"type": "string", "enum": ["ml-IN", "en-IN"]},
                "confirmed": {"type": "boolean", "description": "True if details were read back and confirmed by caller"},
            },
            "required": ["name", "phone", "confirmed"],
        },
    },
    {
        "name": "get_free_slots",
        "description": "Query available appointment slots for a doctor or treatment on a specified date or range.",
        "parameters": {
            "type": "object",
            "properties": {
                "doctor_id": {"type": "string", "description": "UUID or name of the doctor"},
                "treatment_id": {"type": "string", "description": "Optional treatment UUID"},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD or relative like 'tomorrow'"},
            },
            "required": ["date"],
        },
    },
    {
        "name": "book_appointment",
        "description": "Book a verified appointment slot. All bookings are validated inside a DB transaction.",
        "parameters": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "UUID of the patient"},
                "doctor_id": {"type": "string", "description": "UUID of the doctor"},
                "treatment_id": {"type": "string", "description": "Optional treatment UUID"},
                "start": {"type": "string", "description": "Start timestamp ISO 8601"},
                "reason": {"type": "string", "description": "Short visit reason"},
                "visit_type": {"type": "string", "enum": ["in_person", "consultation"]},
            },
            "required": ["patient_id", "doctor_id", "start"],
        },
    },
    {
        "name": "reschedule_appointment",
        "description": "Reschedule an existing appointment to a new validated slot.",
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {"type": "string", "description": "Existing appointment UUID"},
                "new_start": {"type": "string", "description": "New ISO 8601 timestamp"},
            },
            "required": ["appointment_id", "new_start"],
        },
    },
    {
        "name": "cancel_appointment",
        "description": "Cancel an existing appointment after patient confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {"type": "string", "description": "Appointment UUID to cancel"},
            },
            "required": ["appointment_id"],
        },
    },
    {
        "name": "get_clinic_info",
        "description": "Answer caller inquiries strictly from approved hospital FAQs and treatments.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Keyword topic (e.g. treatments, working_hours, address, fees)"},
                "question": {"type": "string", "description": "Original question asked by caller"},
            },
            "required": ["question"],
        },
    },
    {
        "name": "transfer_call",
        "description": "Transfer caller to human staff. Allowed during clinic working hours only.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Reason for transfer"},
            },
            "required": ["reason"],
        },
    },
    {
        "name": "request_callback",
        "description": "Create a callback task for hospital reception staff when transfer is unavailable or outside hours.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Summary of what the caller needs"},
                "preferred_time": {"type": "string", "description": "Preferred callback time window"},
            },
            "required": ["reason"],
        },
    },
    {
        "name": "escalate_emergency",
        "description": "Emergency trigger for severe medical distress. Returns urgent disclaimer and alerts staff.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Description of emergency reported by caller"},
            },
            "required": ["summary"],
        },
    },
]
