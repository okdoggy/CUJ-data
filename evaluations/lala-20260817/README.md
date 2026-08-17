# Learnable Agent 평가 결과 — 2026-08-17

이 branch는 CUJ-data의 114개 case에 대해 Learnable Agent를 실행한 결과와 **직접 시각 비교 평가**를 담습니다.
기준 데이터 commit은 `17cb9486e44a454a2e7e55c482c83aa2e6fac4d9`입니다.

## 보기

브라우저에서 repository root의 `CUJ_LALA_결과.html`을 여세요. 각 card는 같은 case의 다음을 나란히 표시합니다.

1. BEFORE
2. 기존 Vibe AFTER
3. LALA
4. Nano Banana
5. Expert/FiveK — 제공된 case에만 표시

LALA 결과 아래에는 직접 시각 검토로 작성한 verdict와 관찰을 표시합니다.
전체 결론과 개선 우선순위는 [VISUAL_REVIEW.md](VISUAL_REVIEW.md)를 참조하세요.

## full-remaster-1.2.0 전체 재생성

114개 전체 case를 `remaster`, `remaster → lut`, `lut`, `generate_ai` production route로 one-case-per-process 실행했습니다. 모든 결과는 디코딩 검증을 통과했습니다. 기본 viewer는 항상 최신 LALA 하나만 표시합니다. version 간 calibration 비교는 private review artifact에서만 수행합니다.

- 새 결과 JPEG: `lala.jpg`
- 새 실행 metadata: `result_lala.json` (`calibration_version: 1.2.0`)
- 실행 경로: `remaster → lut` 63개, `remaster` 26개, `generate_ai` 18개, `lut` 7개
- 실행 prompt와 모든 step parameter는 case별 HTML/metadata에서 확인할 수 있습니다. credential 패턴은 `[REDACTED]`로 처리합니다.

이 branch에서는 사용자 요청에 따라 기존 `lala.jpg`와 `result_lala.json`을 full-remaster-1.2.0 결과로 갱신합니다. 이전 1.1 version artifact는 별도 파일로 유지합니다.

## case별 결과 구조

이제 hash 파일을 찾아갈 필요가 없습니다. 각 완료 case에서 결과와 기록을 함께 확인할 수 있습니다.

```text
demo_backdata/<scenario>/<case>/
├── before.jpg                 # 기존 CUJ 입력
├── after.jpg                  # 기존 Vibe 결과
├── lala.jpg                   # LALA 최종 결과 (실제 JPEG)
├── result_lala.json           # 실행 metadata; execution_prompt 포함
└── evaluation_lala.json       # 직접 시각 비교 평가
```

- `result_lala.json`: LUT 또는 Generate AI 도구, 파라미터, evidence, output hash와 실행에 사용한 `execution_prompt`를 기록합니다.
- `evaluation_lala.json`: BEFORE/Vibe/LALA/Nano/FiveK를 비교한 verdict, 관찰, 한계를 기록합니다.
- 전체 결과는 114개이며 모든 최종 LALA artifact는 디코딩 검증을 통과했습니다.
- Generate AI 18건은 `gpt-image-2`, `low`, PNG 계약으로 생성됐습니다.

## 재현 가능한 export/HTML 생성

평가 artifact가 private evaluator workspace에 있을 때 다음으로 case 구조와 HTML을 재생성합니다.

```bash
uv run --with pillow python scripts/build_lala_evaluation.py \
  --repo-root . \
  --evaluation-root /path/to/private/cuj-evaluation
uv run --with pillow python scripts/write_lala_visual_reviews.py --repo-root .
```

그 뒤 첫 명령을 다시 실행하면 `CUJ_LALA_결과.html`에 시각 평가가 표시됩니다.
`tests/test_lala_evaluation.py`는 `lala.jpg`가 실제 JPEG인지, `result_lala.json`에 실행 prompt가 기록되는지, HTML이 최신 LALA 하나와 case별 실행 prompt·평가 문구를 참조하는지 검증합니다.

## 개인정보 및 재현 경계

이 branch에는 `before` 및 기존 Vibe `after`를 새로 복사하지 않습니다. 사용자 요청에 따라 case-local `result.json`의 마지막 실행 prompt를 LALA 결과 metadata의 `execution_prompt`로 복사해, 결과와 함께 prompt-level feedback을 남길 수 있게 합니다. API key·token·비밀·runtime audit log·private workspace는 포함하지 않습니다.

생성형 결과는 원본 픽셀을 그대로 보존하는 결과가 아닐 수 있습니다. 얼굴·문자·경계·국소 텍스처가 중요한 결과는 원본 크기로 별도 확대 검수해야 합니다. 평가 결과를 production calibration에 반영하려면 별도의 benchmark 검토와 명시적 승인이 필요합니다.
