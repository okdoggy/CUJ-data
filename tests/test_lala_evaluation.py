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
    def test_export_parameter_policy_rerun_preserves_existing_result(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp)
            relative_path = "01_example/image-a"
            case = root / "demo_backdata" / relative_path
            case.mkdir(parents=True)
            (case / "lala.jpg").write_bytes(b"existing-result")
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
            self.assertNotIn("prompt", json.dumps(metadata))

    def test_export_places_named_result_and_excludes_prompt(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp)
            case = root / "demo_backdata" / "01_example" / "image-a"
            case.mkdir(parents=True)
            (case / "before.jpg").write_bytes(b"before")
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
            self.assertNotIn("prompt", json.dumps(metadata))

    def test_build_html_references_case_lala_image(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp)
            case = root / "demo_backdata" / "01_example" / "image-a"
            case.mkdir(parents=True)
            for filename in ("before.jpg", "after.jpg", "lala.jpg", "lala_parameter_policy_1.1.0.jpg"):
                (case / filename).write_bytes(b"image")
            (case / "result_lala.json").write_text(
                json.dumps({"tool": "lut", "parameters": {"preset": "clean_modern"}}),
                encoding="utf-8",
            )
            (case / "evaluation_lala.json").write_text(
                json.dumps({"verdict": "limited", "review": "직접 시각 검토: 변화가 약함"}),
                encoding="utf-8",
            )
            (case / "result_lala_parameter_policy_1.1.0.json").write_text(
                json.dumps({"tool": "lut", "parameters": {"preset": "clean_modern"}}),
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
            self.assertIn("demo_backdata/01_example/image-a/lala.jpg", html)
            self.assertIn("LALA 1.1.0", html)
            self.assertIn(
                "demo_backdata/01_example/image-a/lala_parameter_policy_1.1.0.jpg", html
            )
            self.assertIn("직접 시각 검토: 변화가 약함", html)


if __name__ == "__main__":
    unittest.main()
