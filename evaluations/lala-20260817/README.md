# Learnable Agent 평가 결과 — 2026-08-17

이 디렉터리는 CUJ-data의 114개 case에 대해 Learnable Agent를 실행해 생성한 결과입니다.
기준 데이터 commit은 `17cb9486e44a454a2e7e55c482c83aa2e6fac4d9`입니다.

## 결과 요약

| 경로 | 대상 | 정상 PNG |
|---|---:|---:|
| `lut-results/` | LUT 전역 색감·톤·무드 보정 | 100 |
| `generate-results/` | LUT로 수행 불가한 생성형 편집 | 14 |

총 114개 결과를 생성했고, 모든 결과 PNG를 디코딩 검증했습니다.

Generate AI 14건은 `gpt-image-2`, `low`, PNG 계약으로 생성했습니다. 실제 응답 크기는
`1536x1024` 7건, `1024x1536` 7건입니다.

## 비교 방법

1. `lut-output-index.json`에서 `case_id`와 `source_relative_path`를 찾습니다.
2. 기존 `demo_backdata/<source_relative_path>/before.jpg`와 `after.jpg`를 엽니다.
3. `lut-results/<case_id>.png` 또는 `generate-results/<case_id>.png`를 함께 비교합니다.
4. LUT 결과는 기존 Vibe `after`와 같은 전역 색감·톤·무드 보정 범위에서 비교합니다.
   크롭·피부 리터치·국소 객체 수정처럼 LUT가 할 수 없는 요청은 Generate AI 결과를 비교합니다.

## 기록 파일

- `lut-evaluation-summary.json`: LUT 100건의 항목별 상태와 preset 분포
- `generate-evaluation-summary.json`: Generate AI 14건의 항목별 상태·실제 크기·use case 분포
- `lut-output-index.json`: 기존 CUJ case 경로와 LUT 결과 파일의 대응표
- `generate-evaluation.jsonl`: Generate AI 결과의 비식별 실행 메타데이터

## 개인정보 및 재현 경계

이 branch에는 `before`, 기존 Vibe `after`, `result.json`의 프롬프트 원문을 새로 복사하지 않았습니다.
기존 CUJ-data에 이미 존재하는 case 경로를 참조하고, 이번 실행의 결과 PNG와 비식별 메타데이터만 추가합니다.
평가 결과를 production calibration에 반영하려면 별도의 benchmark 검토와 명시적 승인이 필요합니다.
