from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from backend.evals.stt_bench.bench import (
    MockSTTProvider,
    SarvamSTTProvider,
    run_stt_benchmark,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="ClinicVoice STT Benchmark Runner")
    parser.add_argument(
        "--provider",
        choices=["mock", "sarvam"],
        default="mock",
        help="STT provider to benchmark (default: mock)",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path(__file__).parent / "data",
        help="Path to folder containing audio files and ground_truth.json",
    )
    parser.add_argument(
        "--language",
        default="ml-IN",
        help="Language code (default: ml-IN)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional path to write benchmark JSON report",
    )

    args = parser.parse_args()

    if args.provider == "sarvam":
        api_key = os.getenv("SARVAM_API_KEY")
        if not api_key:
            print("ERROR: SARVAM_API_KEY environment variable not set. To run offline, use --provider mock.")
            sys.exit(1)
        provider = SarvamSTTProvider(api_key=api_key)
    else:
        provider = MockSTTProvider()

    print(f"============================================================")
    print(f"Starting STT Benchmark: Provider='{provider.name}', Lang='{args.language}'")
    print(f"Dataset: {args.dataset_dir}")
    print(f"============================================================")

    result = asyncio.run(run_stt_benchmark(args.dataset_dir, provider, args.language))

    print("\n--- RESULTS SUMMARY ---")
    print(f"Samples Evaluated : {result['sample_count']}")
    print(f"Average WER       : {result['avg_wer'] * 100:.2f}%")
    print(f"Average CER       : {result['avg_cer'] * 100:.2f}%")
    print(f"Entity Accuracy   : {result['entity_accuracy'] * 100:.2f}%")
    print("------------------------------------------------------------\n")

    for detail in result["details"]:
        print(f"File: {detail['file']} | WER: {detail['wer']*100:.1f}% | CER: {detail['cer']*100:.1f}%")
        print(f"  Ref : {detail['reference']}")
        print(f"  Hyp : {detail['hypothesis']}")
        print(f"  Entities: {detail['entities']}")
        print()

    if args.out:
        args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved full report to {args.out}")


if __name__ == "__main__":
    main()
