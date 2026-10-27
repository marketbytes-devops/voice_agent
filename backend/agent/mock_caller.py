from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.agent.main import VoiceAgentWorker

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logger = logging.getLogger("clinicvoice")


async def run_mock_call(dialed_number: str, caller_number: str, api_url: str) -> None:
    print("============================================================")
    print("        CLINICVOICE LOCAL TELEPHONY MOCK (PHASE 1)         ")
    print("============================================================")
    print(f"Simulating incoming telephony call from {caller_number} to {dialed_number}...")

    worker = VoiceAgentWorker(api_base_url=api_url)

    try:
        result = await worker.handle_call(dialed_number=dialed_number, caller_number=caller_number)
        print("\n[SUCCESS] CALL CONNECTED SUCCESSFULLY!")
        print(f"Call ID         : {result['call_id']}")
        print(f"Clinic Tenant   : {result['clinic_name']} ({result['clinic_id']})")
        print(f"Bilingual Audio : {result['greeting']}")
        print(f"Database Record : Stored in 'calls' and 'call_events' tables.")
        print("============================================================\n")
    except Exception as e:
        print(f"\n[FAIL] CALL FAILED: {e}")
        print("Ensure the FastAPI backend is running at:", api_url)
        print("Tip: Run `uvicorn backend.app.main:app --port 8000` in another terminal.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="ClinicVoice Local Telephony Mock Caller")
    parser.add_argument("--dialed", default="+919876500001", help="Dialed number (E.164)")
    parser.add_argument("--caller", default="+919876543210", help="Caller number (E.164)")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Backend API URL")
    args = parser.parse_args()

    asyncio.run(run_mock_call(args.dialed, args.caller, args.api_url))


if __name__ == "__main__":
    main()
