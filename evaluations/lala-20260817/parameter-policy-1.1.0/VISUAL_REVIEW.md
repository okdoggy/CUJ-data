# CUJ 열세 case 재생성 시각 검토 — parameter-policy-1.1.0

## 범위와 방법

- 대상: 2026-08-17 직접 시각 검토에서 `limited`로 판정된 72개 case.
- 실행: production commit `3b7a0719401fb89e575ac429586aaa27997e1901`.
- 비교: BEFORE, Vibe, 기존 LALA, 새 LALA, 제공된 Nano 및 FiveK.
- 검토: 13개 category comparison sheet를 직접 육안으로 비교했다. pixel score가 아닌 정성 평가다.
- 개인정보 경계: 이 보고서에는 source prompt, 원본 이미지, 사용자 콘텐츠를 넣지 않았다.

## 실행 무결성

- 완료: 72 / 72, 출력 decode: 72 / 72.
- 새 route: LUT 62, Generate AI 10.
- 이전 결과 대비 route: LUT → LUT 62, LUT → Generate AI 9, Generate AI → Generate AI 1.
- 기존 nonzero grain → zero: LUT 34건.
- 기존 nonzero halation → zero: LUT 42건.
- 새 nonzero grain 또는 halation: 17건. 17건 모두 active `restrained-atmospheric-softness` evidence를 기록했고 위반은 0건이다.

## 직접 시각 검토 결과

### 확인된 개선

- 음식·여행·범용 자동 보정에서 기존의 blue/gray veil이 대체로 줄었다. 원본 구조 보존을 유지하면서 피사체 분리, 음식 색, 건축 윤곽, 하늘 톤이 더 읽힌다.
- 새 policy는 grain/halation을 자동으로 누적하지 않는다. 이로써 의도하지 않은 haze가 줄고, atmosphere effect가 저대비를 스타일처럼 가리는 일이 감소했다.
- 기존 LUT route 9건이 Generate AI로 전환됐다. planner가 global grading으로 해결하기 어렵다고 판단한 경우에 더 정직한 route다.

### 남은 한계

- 자연 보정·저조도·흐린 날 case는 여전히 보수적이며 Vibe/FiveK 대비 평평하거나 변화가 부족한 경우가 있다.
- 음식 일부는 새 색 분리에서 orange/red가 과해질 수 있다. 보존성은 좋지만 saturation calibration이 균일하게 절제된 것은 아니다.
- clean modern과 Apple neutral은 veil은 줄었지만 crisp neutral contrast 및 highlight/midtone 분리가 부족하다.
- dark mood는 의도적인 어두운 룩을 유지하기보다 neutral하고 subdued하게 끝나는 case가 있다.
- matte·vintage·cinematic은 global haze를 스타일 대용으로 쓰는 문제는 줄었지만, 의도한 endpoint, warm/cool separation, texture가 Vibe보다 약하다. 이는 즉시 LUT cube 변경의 근거가 아니라 style-profile 문제다.
- summer는 Vibe의 cyan/green 과장을 피하지만, 맑은 여름 색 분리가 너무 neutral하게 끝나는 case가 있다.

## Calibration 결정

이 rerun만으로 approved LUT cube 또는 manifest를 변경하지 않는다.

다음 offline 후보에서는 승인 LUT cube를 고정하고, 라이선스가 확인된 fixed TC에서 style별 parameter profile만 비교한다.

1. clean/Apple neutral: neutral WB, black point, highlight/midtone separation;
2. dark/cinematic: 읽을 수 있는 shadow floor와 절제된 warm/cool separation;
3. matte/vintage: global haze 없는 의도적 endpoint lift와 texture;
4. food/summer: saturation restraint와 hue separation.

promotion에는 반복된 독립 evidence, visual TC 비교, benchmark 무회귀, rollback metadata, 명시적 승인이 계속 필요하다.
