"""Regression tests for deterministic script quality checks."""

from __future__ import annotations

import importlib
import json
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_FILE = Path(__file__).resolve().parent / "fixtures" / "quality_gate_cases.json"


def install_import_stubs():
    """Keep unit tests independent of local media/model dependencies."""
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: None
    sys.modules.setdefault("dotenv", dotenv)

    requests = types.ModuleType("requests")
    requests.post = lambda *args, **kwargs: None
    sys.modules.setdefault("requests", requests)

    whisperx = types.ModuleType("whisperx")
    sys.modules.setdefault("whisperx", whisperx)

    pil = types.ModuleType("PIL")
    pil.__path__ = []
    sys.modules.setdefault("PIL", pil)
    for name in ["Image", "ImageDraw", "ImageFont"]:
        module_name = f"PIL.{name}"
        module = types.ModuleType(module_name)
        sys.modules.setdefault(module_name, module)
        setattr(sys.modules["PIL"], name, sys.modules[module_name])


install_import_stubs()
sys.path.insert(0, str(ROOT))
generate_short = importlib.import_module("generate_short")


QUALITY_SETTINGS = generate_short.quality_gate_config({
    "quality_gate": {
        "min_script_words": 1,
        "hard_min_script_words": 1,
        "max_script_words": 300,
        "hard_max_script_words": 400,
        "min_complete_sentences": 1,
    }
})


def quality_issues(case):
    meta = {
        "title": case["title"],
        "description": case["description"],
        "script": case["script"],
    }
    return generate_short.heuristic_quality_issues(meta, QUALITY_SETTINGS)


class QualityGateFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))

    def test_fixture_cases_report_expected_blocking_issues(self):
        for case in self.cases:
            expected_issue = case.get("expected_issue")
            if not expected_issue:
                continue

            with self.subTest(case=case["name"]):
                issues = quality_issues(case)
                blocking = generate_short.blocking_quality_issues(issues)
                self.assertIn(expected_issue, "\n".join(blocking))

    def test_clean_fixture_has_no_blocking_issues(self):
        clean_case = next(
            case for case in self.cases
            if case["name"] == "clean_short_script"
        )

        issues = quality_issues(clean_case)
        blocking = generate_short.blocking_quality_issues(issues)

        self.assertEqual([], blocking)

    def test_metadata_normalization_repairs_spoken_number_notation(self):
        normalized = generate_short.normalize_metadata(
            {
                "title": "Emergency fund notation",
                "description": "Simple personal finance education.",
                "script": (
                    "A $1,000 emergency fund with 4% yield in a 401(k) "
                    "account is not simple. Follow for more practical money tips."
                ),
            },
            "Emergency fund notation",
            [],
        )

        script = normalized["script"]

        self.assertNotRegex(script, r"[$%]|\b401\b")
        self.assertIn("emergency fund of one thousand dollars", script)
        self.assertIn("four percent", script)
        self.assertIn("four oh one k", script)


if __name__ == "__main__":
    unittest.main()
