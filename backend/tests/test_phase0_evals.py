from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from backend.evals.stt_bench.bench import (
    MockSTTProvider,
    calculate_cer,
    calculate_wer,
    evaluate_entities,
    extract_entities,
    run_stt_benchmark,
)
from backend.evals.tts_bench.generate import (
    MockTTSProvider,
    run_tts_generation,
)
from backend.evals.llm_tool_bench.eval_tools import (
    MockLLMToolProvider,
    run_tool_bench,
)


class TestPhase0Evals(unittest.TestCase):
    def test_calculate_wer_exact_match(self) -> None:
        ref = "നമസ്കാരം ഡോക്ടർ മനോജ്"
        hyp = "നമസ്കാരം ഡോക്ടർ മനോജ്"
        self.assertEqual(calculate_wer(ref, hyp), 0.0)

    def test_calculate_wer_different_words(self) -> None:
        ref = "നമസ്കാരം ഡോക്ടർ മനോജ്"
        hyp = "നമസ്കാരം ഡോക്ടർ സുരേഷ്"
        wer = calculate_wer(ref, hyp)
        self.assertTrue(0.3 <= wer <= 0.35)

    def test_calculate_cer(self) -> None:
        ref = "അപ്പോയിന്റ്മെന്റ്"
        hyp = "അപ്പോയിന്റ്മെന്റ്"
        self.assertEqual(calculate_cer(ref, hyp), 0.0)

    def test_extract_phone_and_time(self) -> None:
        text = "എന്റെ നമ്പർ 9876543210 ആണ് നാളെ 10 AM ന് അപ്പോയിന്റ്മെന്റ് വേണം"
        entities = extract_entities(text)
        self.assertIn("9876543210", entities["phone_numbers"])
        self.assertTrue(any("10 AM" in t or "10" in t for t in entities["times"]))

    def test_evaluate_entities(self) -> None:
        ref = "ഡോക്ടർ മനോജ് നാളെ"
        hyp = "നാളെ ഡോക്ടർ മനോജിനെ കാണണം"
        expected = {"doctor": "മനോജ്", "date": "നാളെ"}
        res = evaluate_entities(ref, hyp, expected)
        self.assertTrue(res["doctor"])
        self.assertTrue(res["date"])

    def test_run_stt_benchmark_mock(self) -> None:
        data_dir = Path(__file__).resolve().parents[1] / "evals" / "stt_bench" / "data"
        result = asyncio.run(run_stt_benchmark(data_dir, MockSTTProvider(), language="ml-IN"))
        self.assertEqual(result["sample_count"], 4)
        self.assertLessEqual(result["avg_wer"], 0.1)
        self.assertGreaterEqual(result["entity_accuracy"], 0.8)

    def test_run_tts_generation_mock(self) -> None:
        sentences_file = Path(__file__).resolve().parents[1] / "evals" / "tts_bench" / "sentences.json"
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            asyncio.run(run_tts_generation(sentences_file, output_dir, MockTTSProvider()))

            generated_wavs = list(output_dir.glob("*.wav"))
            self.assertEqual(len(generated_wavs), 6)
            rating_sheet = output_dir / "ratings_sheet.md"
            self.assertTrue(rating_sheet.exists())
            content = rating_sheet.read_text(encoding="utf-8")
            self.assertIn("Sreerudra Ayurveda Hospital", content)

    def test_run_llm_tool_bench_mock(self) -> None:
        scenarios_file = Path(__file__).resolve().parents[1] / "evals" / "llm_tool_bench" / "test_scenarios.json"
        result = asyncio.run(run_tool_bench(scenarios_file, MockLLMToolProvider()))
        self.assertEqual(result["total_scenarios"], 9)
        self.assertEqual(result["tool_selection_accuracy"], 1.0)
        self.assertGreaterEqual(result["argument_accuracy"], 0.8)


if __name__ == "__main__":
    unittest.main()
