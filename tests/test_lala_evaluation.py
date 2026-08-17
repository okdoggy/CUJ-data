from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_lala_evaluation.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_lala_evaluation", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load build_lala_evaluation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LalaEvaluationExportTests(unittest.TestCase):
    def test_execution_prompt_redacts_credential_pattern(self) -> None:
        module = load_module()

        redacted = module._redact_execution_prompt("token: sk-abcdefghijklmnop 사진을 보정해줘")

        self.assertEqual(redacted, "[REDACTED] 사진을 보정해줘")

    def test_backfill_adds_execution_prompt_to_existing_lala_metadata(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp)
            case = root / "demo_backdata" / "01_example" / "image-a"
            case.mkdir(parents=True)
            (case / "result.json").write_text(
                json.dumps({"turn": {"prompt": "색은 유지하고 명암만 보정해줘"}}),
                encoding="utf-8",
            )
            (case / "result_lala.json").write_text(
                json.dumps({"tool": "lut", "parameters": {}}), encoding="utf-8"
            )

            updated = module.backfill_execution_prompts(root)

            self.assertEqual(updated, 1)
            metadata = json.loads((case / "result_lala.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["execution_prompt"], "색은 유지하고 명암만 보정해줘")

    def test_export_parameter_policy_rerun_preserves_existing_result(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp)
            relative_path = "01_example/image-a"
            case = root / "demo_backdata" / relative_path
            case.mkdir(parents=True)
            (case / "lala.jpg").write_bytes(b"existing-result")
            (case / "result.json").write_text(
                json.dumps({"turn": {"prompt": "피사체를 유지하며 대비를 정리해줘"}}),
                encoding="utf-8",
            )
            rerun = root / "rerun"
            (rerun / "results").mkdir(parents=True)
            case_id = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:16]
            Image.new("RGB", (2, 2), "blue").save(
                rerun / "results" / f"{case_id}.png", format="PNG"
            )
            (rerun / "selection.json").write_text(
                json.dumps({"calibration_version": "1.1.0", "cases": [{"relative_path": relative_path}]}),
                encoding="utf-8",
            )
            (rerun / "rerun.jsonl").write_text(
                json.dumps(
                    {
                        "case_id": case_id,
                        "status": "COMPLETED",
                        "request_id": "rerun_policy_example",
                        "selected_tools": ["lut"],
                        "preset": "clean_modern",
                        "lut_intensity": 0.45,
                        "grain_amount": 0.0,
                        "halation": 0.0,
                        "output_path": f"results/{case_id}.png",
                        "output_sha256": "b" * 64,
                        "evidence": [{"skill_id": "test-note", "version": "1.0.0"}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            exported = module.export_parameter_policy_rerun(root, rerun)

            self.assertEqual(exported, 1)
            self.assertEqual((case / "lala.jpg").read_bytes(), b"existing-result")
            with Image.open(case / "lala_parameter_policy_1.1.0.jpg") as image:
                self.assertEqual(image.format, "JPEG")
            metadata = json.loads(
                (case / "result_lala_parameter_policy_1.1.0.json").read_text(encoding="utf-8")
            )
            self.assertEqual(metadata["calibration_version"], "1.1.0")
            self.assertEqual(metadata["execution_prompt"], "피사체를 유지하며 대비를 정리해줘")

    def test_export_copies_case_execution_prompt_into_result_metadata(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp)
            case = root / "demo_backdata" / "01_example" / "image-a"
            case.mkdir(parents=True)
            (case / "before.jpg").write_bytes(b"before")
            (case / "result.json").write_text(
                json.dumps({"turn": {"prompt": "창문 빛은 유지하고 사진을 또렷하게 해줘"}}),
                encoding="utf-8",
            )
            artifacts = root / "evaluations" / "lala-artifacts"
            (artifacts / "lut-results").mkdir(parents=True)
            Image.new("RGB", (2, 2), "red").save(
                artifacts / "lut-results" / "case000000000001.png", format="PNG"
            )
            (artifacts / "lut-output-index.json").write_text(
                json.dumps(
                    [
                        {
                            "case_id": "case000000000001",
                            "source_relative_path": "01_example/image-a",
                            "status": "COMPLETED",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (artifacts / "lut-evaluation.jsonl").write_text(
                json.dumps(
                    {
                        "case_id": "case000000000001",
                        "status": "COMPLETED",
                        "request_id": "eval_lut_case000000000001",
                        "preset": "clean_modern",
                        "lut_intensity": 0.5,
                        "grain_amount": 0.0,
                        "halation": 0.0,
                        "skin_protection": True,
                        "output_sha256": "a" * 64,
                        "evidence": [{"skill_id": "test-note", "version": "1.0.0"}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (artifacts / "generate-evaluation.jsonl").write_text("", encoding="utf-8")

            exported = module.export_lala_results(root, artifacts)

            self.assertEqual(exported, 1)
            with Image.open(case / "lala.jpg") as image:
                self.assertEqual(image.format, "JPEG")
                self.assertEqual(image.size, (2, 2))
            metadata = json.loads((case / "result_lala.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["tool"], "lut")
            self.assertEqual(metadata["result_file"], "lala.jpg")
            self.assertEqual(metadata["execution_prompt"], "창문 빛은 유지하고 사진을 또렷하게 해줘")

    def test_build_html_shows_only_latest_lala_and_escaped_execution_prompt(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp)
            case = root / "demo_backdata" / "01_example" / "image-a"
            case.mkdir(parents=True)
            for filename in ("before.jpg", "after.jpg", "lala.jpg", "lala_parameter_policy_1.1.0.jpg"):
                (case / filename).write_bytes(b"image")
            (case / "result_lala.json").write_text(
                json.dumps(
                    {
                        "tool": "lut",
                        "calibration_version": "1.2.0",
                        "parameters": {"preset": "clean_modern"},
                        "execution_prompt": "밝게 <자연스럽게> 보정해줘",
                    }
                ),
                encoding="utf-8",
            )
            (case / "evaluation_lala.json").write_text(
                json.dumps({"verdict": "limited", "review": "직접 시각 검토: 변화가 약함"}),
                encoding="utf-8",
            )
            (case / "result_lala_parameter_policy_1.1.0.json").write_text(
                json.dumps(
                    {
                        "tool": "lut",
                        "parameters": {"preset": "clean_modern"},
                        "calibration_version": "1.1.0",
                        "result_file": "lala_parameter_policy_1.1.0.jpg",
                    }
                ),
                encoding="utf-8",
            )
            manifest = {
                "scenarios": [
                    {
                        "id": "01_example",
                        "section_num": 1,
                        "section_title": "Example",
                        "cat": "Test",
                        "prompt": "existing prompt",
                        "baseline": None,
                        "images": ["image-a"],
                    }
                ]
            }
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            output = module.build_lala_html(root)

            html = output.read_text(encoding="utf-8")
            self.assertIn("LALA", html)
            self.assertIn("demo_backdata/01_example/image-a/lala.jpg\"", html)
            self.assertNotIn(
                "demo_backdata/01_example/image-a/lala_parameter_policy_1.1.0.jpg", html
            )
            self.assertNotIn("LALA 1.1.0", html)
            self.assertIn("실행 prompt", html)
            self.assertIn("사용 parameter", html)
            self.assertIn("밝게 &lt;자연스럽게&gt; 보정해줘", html)
            self.assertIn("grid-template-columns:repeat(5,minmax(0,1fr))", html)
            self.assertIn("직접 시각 검토: 변화가 약함", html)


if __name__ == "__main__":
    unittest.main()
