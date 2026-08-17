#!/usr/bin/env python3
"""Export Learnable Agent CUJ artifacts into case folders and build a comparison sheet.

Usage:
  python3 scripts/build_lala_evaluation.py \
    --repo-root . \
    --evaluation-root /path/to/cuj-20260817

The input directory is the private evaluator output. This script writes only final
LALA JPEGs and prompt-free result_lala.json metadata into CUJ case directories.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from PIL import Image

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _find_image(directory: Path, stem: str) -> Path | None:
    for extension in IMAGE_EXTENSIONS:
        candidate = directory / f"{stem}{extension}"
        if candidate.is_file():
            return candidate
    return None


def _write_jpeg(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        normalized = image.convert("RGB")
        normalized.save(destination, format="JPEG", quality=95, optimize=True)


def _execution_prompt(case_dir: Path) -> str:
    record = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
    turns = record.get("turns")
    turn = turns[-1] if isinstance(turns, list) and turns else record.get("turn")
    prompt = turn.get("prompt") if isinstance(turn, dict) else None
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError(f"missing execution prompt: {case_dir / 'result.json'}")
    return _redact_execution_prompt(prompt)


def _redact_execution_prompt(prompt: str) -> str:
    for pattern in (
        r"(?i)(?:api[_ -]?key|token|secret|password)\s*[:=]\s*\S+",
        r"\bsk-[A-Za-z0-9_-]{12,}\b",
        r"\bAKIA[0-9A-Z]{16}\b",
        r"-----BEGIN [A-Z ]+ PRIVATE KEY-----",
    ):
        prompt = re.sub(pattern, "[REDACTED]", prompt)
    return prompt


def backfill_execution_prompts(repo_root: Path) -> int:
    """Copy each case's planner input into user-approved LALA result metadata only."""
    updated = 0
    for metadata_path in sorted((repo_root / "demo_backdata").glob("*/*/result_lala*.json")):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        prompt = _execution_prompt(metadata_path.parent)
        if metadata.get("execution_prompt") == prompt:
            continue
        metadata["execution_prompt"] = prompt
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        updated += 1
    return updated


def _safe_metadata(record: dict[str, Any], tool: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "schema_version": "1.0",
        "runner": "Learnable Agent",
        "tool": tool,
        "status": "completed",
        "result_file": "lala.jpg",
        "request_id": record["request_id"],
        "output_sha256": record["output_sha256"],
        "evidence": record.get("evidence", []),
    }
    if tool == "lut":
        metadata["parameters"] = {
            key: record[key]
            for key in ("preset", "lut_intensity", "skin_protection", "grain_amount", "halation")
        }
    else:
        metadata["parameters"] = {
            "use_case": record["use_case"],
            "actual_size": record["actual_size"],
        }
    return metadata


def export_lala_results(repo_root: Path, evaluation_root: Path) -> int:
    """Place exactly one final LALA JPEG and prompt-free metadata in each completed case."""
    index = json.loads((evaluation_root / "lut-output-index.json").read_text(encoding="utf-8"))
    lut_records = {record["case_id"]: record for record in read_jsonl(evaluation_root / "lut-evaluation.jsonl")}
    generate_records = {
        record["case_id"]: record
        for record in read_jsonl(evaluation_root / "generate-evaluation.jsonl")
    }
    exported = 0
    for entry in index:
        case_id = entry["case_id"]
        case_dir = repo_root / "demo_backdata" / entry["source_relative_path"]
        lut_record = lut_records.get(case_id, {})
        generate_record = generate_records.get(case_id, {})
        if lut_record.get("status") == "COMPLETED":
            source = evaluation_root / "lut-results" / f"{case_id}.png"
            record, tool = lut_record, "lut"
        elif generate_record.get("status") == "COMPLETED":
            source = evaluation_root / "generate-results" / f"{case_id}.png"
            record, tool = generate_record, "generate_ai"
        else:
            continue
        if not source.is_file():
            raise FileNotFoundError(f"missing LALA output for {case_id}: {source}")
        _write_jpeg(source, case_dir / "lala.jpg")
        metadata = _safe_metadata(record, tool)
        metadata["execution_prompt"] = _execution_prompt(case_dir)
        (case_dir / "result_lala.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        exported += 1
    return exported


def _parameter_policy_metadata(record: dict[str, Any], tool: str, calibration_version: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "schema_version": "1.0",
        "runner": "Learnable Agent",
        "calibration_version": calibration_version,
        "tool": tool,
        "status": "completed",
        "result_file": f"lala_parameter_policy_{calibration_version}.jpg",
        "request_id": record["request_id"],
        "output_sha256": record["output_sha256"],
        "evidence": record.get("evidence", []),
    }
    if tool == "lut":
        metadata["parameters"] = {
            key: record[key]
            for key in ("preset", "lut_intensity", "grain_amount", "halation")
        }
    else:
        metadata["parameters"] = {}
    return metadata


def export_parameter_policy_rerun(repo_root: Path, rerun_root: Path) -> int:
    """Export named, prompt-free parameter-policy rerun artifacts without replacing baseline LALA."""
    selection = json.loads((rerun_root / "selection.json").read_text(encoding="utf-8"))
    calibration_version = str(selection["calibration_version"])
    records = {
        record["case_id"]: record
        for record in read_jsonl(rerun_root / "rerun.jsonl")
        if record.get("status") == "COMPLETED"
    }
    exported = 0
    data_root = (repo_root / "demo_backdata").resolve()
    for entry in selection["cases"]:
        relative_path = str(entry["relative_path"])
        case_id = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:16]
        record = records.get(case_id)
        if record is None:
            raise ValueError(f"missing completed rerun record for {case_id}")
        selected_tools = record.get("selected_tools", [])
        if len(selected_tools) != 1:
            raise ValueError(f"expected one selected tool for {case_id}")
        case_dir = (data_root / relative_path).resolve()
        if not case_dir.is_relative_to(data_root):
            raise ValueError(f"invalid selected case path: {relative_path}")
        source = rerun_root / record["output_path"]
        if not source.is_file():
            raise FileNotFoundError(f"missing rerun output for {case_id}: {source}")
        result_file = f"lala_parameter_policy_{calibration_version}.jpg"
        metadata_file = f"result_lala_parameter_policy_{calibration_version}.json"
        _write_jpeg(source, case_dir / result_file)
        metadata = _parameter_policy_metadata(record, selected_tools[0], calibration_version)
        metadata["execution_prompt"] = _execution_prompt(case_dir)
        (case_dir / metadata_file).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        exported += 1
    return exported


def _image_cell(
    label: str, relative_path: str | None, style: str = "", missing_text: str | None = None
) -> str:
    caption_style = f' style="{style}"' if style else ""
    if relative_path is None:
        return (
            '<figure class="missing"><figcaption>비교 제외</figcaption>'
            f'<div>{html.escape(missing_text or f"{label} 없음")}</div></figure>'
        )
    return (
        f'<figure><figcaption{caption_style}>{html.escape(label)}</figcaption>'
        f'<img src="{html.escape(relative_path, quote=True)}" loading="lazy"></figure>'
    )


def _latest_lala_artifact(case_dir: Path) -> tuple[Path, dict[str, Any]]:
    baseline_path = case_dir / "result_lala.json"
    if not baseline_path.is_file():
        raise FileNotFoundError(f"missing LALA metadata: {baseline_path}")
    baseline_metadata = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline_version = _calibration_version(baseline_metadata.get("calibration_version"))
    selected = (
        baseline_version,
        case_dir / "lala.jpg",
        baseline_metadata,
    )
    for metadata_path in case_dir.glob("result_lala_parameter_policy_*.json"):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        candidate_version = _calibration_version(metadata.get("calibration_version"))
        result_file = metadata.get("result_file")
        if not isinstance(result_file, str):
            continue
        candidate_image = case_dir / result_file
        if candidate_image.is_file() and candidate_version > selected[0]:
            selected = candidate_version, candidate_image, metadata
    return selected[1], selected[2]


def _calibration_version(value: object) -> tuple[int, int, int]:
    if not isinstance(value, str):
        return (0, 0, 0)
    try:
        version = tuple(int(part) for part in value.split("."))
    except ValueError:
        return (0, 0, 0)
    return version if len(version) == 3 else (0, 0, 0)


def build_lala_html(repo_root: Path) -> Path:
    """Build the primary five-column comparison sheet with the latest LALA artifact."""
    manifest = json.loads((repo_root / "manifest.json").read_text(encoding="utf-8"))
    data_root = repo_root / "demo_backdata"
    cards: list[str] = []
    for scenario in manifest["scenarios"]:
        for stem in scenario["images"]:
            case_dir = data_root / scenario["id"] / stem
            if not (case_dir / "lala.jpg").is_file():
                continue
            base = f"demo_backdata/{scenario['id']}/{stem}"
            before = _find_image(case_dir, "before")
            after = _find_image(case_dir, "after")
            lala, metadata = _latest_lala_artifact(case_dir)
            nano = _find_image(data_root / "_nano_banana" / scenario["id"], stem)
            fivek = _find_image(data_root / "_baseline_fivek", stem) if scenario.get("baseline") else None
            cells = [
                _image_cell("BEFORE", f"{base}/{before.name}" if before else None),
                _image_cell("Vibe AFTER", f"{base}/{after.name}" if after else None),
                _image_cell("LALA", f"{base}/{lala.name}", "background:rgba(14,165,233,.85)"),
                _image_cell(
                    "Nano Banana",
                    f"demo_backdata/_nano_banana/{scenario['id']}/{nano.name}" if nano else None,
                    "background:rgba(101,163,13,.85)",
                ),
                _image_cell(
                    "Expert (FiveK)",
                    f"demo_backdata/_baseline_fivek/{fivek.name}" if fivek else None,
                    "background:rgba(180,83,9,.85)",
                    "FiveK reference 없음",
                ),
            ]
            review_path = case_dir / "evaluation_lala.json"
            review = json.loads(review_path.read_text(encoding="utf-8")) if review_path.is_file() else None
            tool = metadata["tool"]
            details = metadata["parameters"]
            prompt = metadata.get("execution_prompt")
            if not isinstance(prompt, str):
                baseline_metadata_path = case_dir / "result_lala.json"
                if baseline_metadata_path.is_file():
                    prompt = json.loads(baseline_metadata_path.read_text(encoding="utf-8")).get(
                        "execution_prompt"
                    )
            prompt_html = (
                '<details class="prompt"><summary>실행 prompt</summary>'
                f'<pre>{html.escape(prompt)}</pre></details>'
                if isinstance(prompt, str)
                else '<aside class="prompt missing-prompt">실행 prompt 기록 없음</aside>'
            )
            review_html = (
                '<aside class="review">'
                f'<b>시각 평가: {html.escape(review["verdict"])}</b>'
                f'<span>{html.escape(review["review"])}</span>'
                '</aside>'
                if review
                else ''
            )
            cards.append(
                '<article class="card">'
                f'<header><b>{html.escape(str(scenario["section_num"]))}. {html.escape(scenario["section_title"])}</b>'
                f'<span>{html.escape(stem)}</span></header>'
                '<section class="images">' + "".join(cells) + "</section>"
                f'<footer><b>LALA: {html.escape(tool)}</b> · <b>사용 parameter:</b> <code>{html.escape(json.dumps(details, ensure_ascii=False, sort_keys=True))}</code>'
                + prompt_html
                + f'{review_html}</footer>'
                '</article>'
            )
    document = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>CUJ Learnable Agent 비교 결과</title><style>
body{margin:0;background:#0f172a;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1800px;margin:auto;padding:24px}h1{margin:0}.sub{color:#94a3b8;margin:8px 0 24px}
.card{background:#1e293b;border:1px solid #334155;border-radius:10px;margin:16px 0;overflow:hidden}
.card header{padding:12px}.card header span{color:#94a3b8;margin-left:10px;font-size:12px}
.images{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:2px;background:#0f172a}.images figure{margin:0;position:relative;min-height:120px}.images img{width:100%;display:block}
figcaption{position:absolute;top:6px;left:6px;background:rgba(0,0,0,.7);padding:2px 7px;border-radius:8px;font-size:11px;z-index:1}.missing{display:flex;align-items:center;justify-content:center;color:#64748b;border:1px dashed #475569;font-size:12px}.missing figcaption{background:#475569}
footer{padding:9px 12px;color:#94a3b8;font-size:12px;word-break:break-word}footer b{color:#7dd3fc}code{color:#cbd5e1}
.review{display:grid;grid-template-columns:110px 1fr;gap:8px;border-top:1px solid #334155;margin-top:9px;padding-top:9px;color:#cbd5e1}.review b{color:#facc15}
.prompt{margin-top:9px;padding-top:9px;border-top:1px solid #334155}.prompt summary{cursor:pointer;color:#7dd3fc}.prompt pre{white-space:pre-wrap;word-break:break-word;color:#cbd5e1;margin:8px 0 0;font-family:inherit}.missing-prompt{color:#94a3b8}
@media(max-width:1000px){.images{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style></head><body><main><h1>CUJ Learnable Agent 비교 결과</h1>
<div class="sub">BEFORE · Vibe AFTER · 최신 LALA · Nano Banana · Expert(FiveK)를 같은 case에서 비교합니다. FiveK는 제공된 case에만 표시됩니다.</div>"""
    document += "\n".join(cards) + "</main></body></html>\n"
    output = repo_root / "CUJ_LALA_결과.html"
    output.write_text(document, encoding="utf-8", newline="\n")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--evaluation-root", type=Path)
    parser.add_argument("--rerun-root", type=Path)
    parser.add_argument("--skip-export", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    if not args.skip_export and args.evaluation_root is None:
        parser.error("--evaluation-root is required unless --skip-export is set")
    exported = 0
    if args.evaluation_root is not None and not args.skip_export:
        exported += export_lala_results(repo_root, args.evaluation_root.resolve())
    if args.rerun_root is not None:
        exported += export_parameter_policy_rerun(repo_root, args.rerun_root.resolve())
    prompt_updates = backfill_execution_prompts(repo_root)
    output = build_lala_html(repo_root)
    print(f"exported={exported} prompt_updates={prompt_updates} html={output}")


if __name__ == "__main__":
    main()
