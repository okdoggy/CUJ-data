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

## parameter-policy-1.1.0 재생성

기존 직접 시각 검토에서 `limited`였던 72개 case를 새 parameter policy로 다시 생성했습니다.
`CUJ_LALA_결과.html`의 **LALA 1.1.0** column에서 기존 LALA와 나란히 확인할 수 있습니다.

- 새 결과 JPEG: `lala_parameter_policy_1.1.0.jpg`
- 새 prompt-free 실행 metadata: `result_lala_parameter_policy_1.1.0.json`
- 직접 시각 검토와 calibration 결정: [parameter-policy-1.1.0/VISUAL_REVIEW.md](parameter-policy-1.1.0/VISUAL_REVIEW.md)

기존 `lala.jpg` 및 `result_lala.json`은 비교 기준으로 보존하며 덮어쓰지 않습니다.

## case별 결과 구조

이제 hash 파일을 찾아갈 필요가 없습니다. 각 완료 case에서 결과와 기록을 함께 확인할 수 있습니다.

```text
demo_backdata/<scenario>/<case>/
├── before.jpg                 # 기존 CUJ 입력
├── after.jpg                  # 기존 Vibe 결과
├── lala.jpg                   # LALA 최종 결과 (실제 JPEG)
├── result_lala.json           # 실행 metadata; prompt 미복사
└── evaluation_lala.json       # 직접 시각 비교 평가
```

- `result_lala.json`: LUT 또는 Generate AI 도구, 파라미터, evidence, output hash를 기록합니다.
- `evaluation_lala.json`: BEFORE/Vibe/LALA/Nano/FiveK를 비교한 verdict, 관찰, 한계를 기록합니다.
- 전체 결과는 LUT 100개, Generate AI 14개이며 모든 입력 artifact는 디코딩 검증을 통과했습니다.
- Generate AI 14건은 `gpt-image-2`, `low`, PNG 계약으로 생성됐으며 실제 응답 크기는 `1536x1024` 7건, `1024x1536` 7건입니다.

## 재현 가능한 export/HTML 생성

평가 artifact가 private evaluator workspace에 있을 때 다음으로 case 구조와 HTML을 재생성합니다.

```bash
uv run --with pillow python scripts/build_lala_evaluation.py \
  --repo-root . \
  --evaluation-root /path/to/private/cuj-evaluation
uv run --with pillow python scripts/write_lala_visual_reviews.py --repo-root .
```

그 뒤 첫 명령을 다시 실행하면 `CUJ_LALA_결과.html`에 시각 평가가 표시됩니다.
`tests/test_lala_evaluation.py`는 `lala.jpg`가 실제 JPEG인지, `result_lala.json`에 prompt가 없는지, HTML이 case LALA 결과 및 평가 문구를 참조하는지 검증합니다.

## 개인정보 및 재현 경계

이 branch에는 `before`, 기존 Vibe `after`, `result.json`의 프롬프트 원문을 새로 복사하지 않았습니다. 기존 CUJ-data에 이미 존재하는 case 경로를 참조하고, 이번 실행의 LALA 결과·prompt-free metadata·시각 평가만 추가합니다.

생성형 결과는 원본 픽셀을 그대로 보존하는 결과가 아닐 수 있습니다. 얼굴·문자·경계·국소 텍스처가 중요한 결과는 원본 크기로 별도 확대 검수해야 합니다. 평가 결과를 production calibration에 반영하려면 별도의 benchmark 검토와 명시적 승인이 필요합니다.
