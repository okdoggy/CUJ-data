# -*- coding: utf-8 -*-
"""evals/ 폴더의 평가 JSON을 모아 eval_data.js 생성 → CUJ_결과.html이 자동 로드.

사용법: 이 폴더에서 `평가취합.bat` 더블클릭 (또는 python collect_evals.py)

파일 접근 방식 안내:
    브라우저는 file:// 에서 fetch()로 로컬 파일을 읽지 못한다(CORS 차단).
    그래서 JSON을 <script>로 읽을 수 있는 eval_data.js 형태로 변환해 둔다.
    평가자가 JSON을 evals/ 에 넣고 이 스크립트를 한 번 실행하면
    CUJ_결과.html을 새로고침하는 것만으로 반영된다.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVALS = ROOT / "evals"
OUT = ROOT / "eval_data.js"

EVALS.mkdir(exist_ok=True)
files = sorted(EVALS.glob("*.json"))

collected, skipped = [], []
for f in files:
    try:
        o = json.loads(f.read_text(encoding="utf-8"))
    except Exception as exc:
        skipped.append((f.name, f"JSON 파싱 실패 — {exc}"))
        continue
    entries = o.get("entries")
    if not isinstance(entries, dict):
        skipped.append((f.name, "entries 필드 없음"))
        continue
    name = str(o.get("evaluator") or f.stem).strip() or f.stem
    n_done = sum(1 for e in entries.values() if e.get("inst") and e.get("qual"))
    # 같은 평가자가 여러 번 내보냈으면 더 많이 채운 쪽을 남긴다
    prev = next((c for c in collected if c["evaluator"] == name), None)
    if prev:
        if n_done <= prev["_done"]:
            skipped.append((f.name, f"'{name}' 이전 파일이 더 많이 채워져 있어 건너뜀"))
            continue
        collected.remove(prev)
    collected.append({"evaluator": name, "ts": o.get("ts"), "entries": entries,
                      "_done": n_done, "_file": f.name})

payload = [{"evaluator": c["evaluator"], "ts": c["ts"], "entries": c["entries"]}
           for c in collected]
OUT.write_text(
    "// collect_evals.py 자동 생성 — 직접 수정하지 말 것\n"
    "window.CUJ_EVALS = " + json.dumps(payload, ensure_ascii=False) + ";\n",
    encoding="utf-8")

print(f"evals/ 폴더 JSON {len(files)}개 검사")
if not files:
    print("  (비어 있음) 평가자가 내보낸 eval_*.json 을 evals/ 폴더에 넣어 주세요.")
for c in collected:
    print(f"  OK   {c['_file']:38s} {c['evaluator']:12s} 평가완료 {c['_done']}장")
for name, why in skipped:
    print(f"  SKIP {name:38s} {why}")
print(f"\n생성: {OUT.name}  (평가자 {len(payload)}명)")
print("→ CUJ_결과.html 을 새로고침하면 반영됩니다.")

if skipped and not collected:
    sys.exit(1)
