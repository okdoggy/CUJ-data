#!/usr/bin/env python3
"""Write the 2026-08-17 curator's contact-sheet visual review into each LALA case.

The text in this file is a human/agent visual assessment, not a pixel metric.
It deliberately does not read or copy result.json prompts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REVIEWS = {
    "01_음식_색감_강화": ("limited", "음식 색과 테이블 디테일은 보존됐지만 LALA 결과는 원본 대비 변화가 작고 중간톤이 평평한 case가 있다. Vibe/Nano는 식재료의 색 분리와 대비가 더 뚜렷하다. Generate AI case는 구도는 유지했으나 재생성 결과이므로 원본 동일성 확인이 필요하다."),
    "02_티안나는_자연스러운_보정": ("limited", "LALA는 장면 구조와 피부를 안전하게 보존하지만, 노출·화이트밸런스 개선량이 작아 저대비·회색 막처럼 보이는 case가 있다. FiveK가 있는 case는 더 균형 잡힌 명암 기준을 보이며, Nano는 변화를 과장하는 경향이 있다."),
    "03_화이트밸런스_교정": ("negative", "LALA는 색 편향을 충분히 교정하지 못하고 밝기와 채도도 낮게 남았다. Vibe와 FiveK는 중립 회색과 피부/백색 물체의 균형이 더 낫다. Nano는 일부 장면에서 과도한 색온도 이동이 있다."),
    "04_흐릿한_사진_선명하게": ("mixed", "Generate AI가 선택된 인물 저조도 case는 얼굴과 의복의 가시성이 크게 좋아졌지만, 재생성 기반이라 미세 텍스처 동일성은 별도 확대 확인이 필요하다. LUT case는 선명도 향상이 거의 보이지 않아 Vibe/Nano보다 열세다."),
    "05_역광_보정": ("negative", "LALA는 역광 인물/건물의 암부를 충분히 들어 올리지 못했고, 일부 case에서 전체가 흐리고 회색으로 남는다. Nano는 밝은 피사체를 강하게 복원하지만 하이라이트가 과해질 수 있다. FiveK는 가능한 case에서 더 자연스러운 노출 균형이다."),
    "06_저노출_보정": ("negative", "LALA LUT 결과는 저노출 복원 목표에 비해 어두운 암부와 낮은 중간톤 대비가 유지된다. Vibe와 Nano가 주 피사체를 더 읽기 쉽게 만들며, Nano는 과노출·색온도 과장이 동반될 수 있다."),
    "07_예쁘게_해줘": ("limited", "LALA는 원본 구조를 보존하나 미적 강화의 체감 변화가 약하다. Vibe는 더 선명한 색·명암을 주고, Nano는 더 드라마틱하지만 자연스러움이 낮아질 수 있다. FiveK는 제공 case에서 덜 과장된 기준점이다."),
    "08_인생샷_복합자동": ("limited", "LALA는 전반적으로 원본보다 더 깊거나 선명해지지 않고, 여러 case에서 저대비·haze가 보인다. Vibe는 의도한 인물/풍경의 분리를 더 잘 만들며 Nano는 분위기 효과가 강하지만 과보정 위험이 있다."),
    "09_여행스냅_살리기": ("limited", "LALA는 여행 장면의 실제 색과 구도를 안전하게 유지하지만 결과가 원본과 매우 가깝거나 탁하다. Vibe/Nano는 하늘·조명·색감의 인상이 더 살아나며, Nano는 현실성보다 스타일을 우선한다."),
    "10_크롭_인물기준": ("positive", "LALA Generate AI 결과는 인물을 더 크게 배치해 요청 유형에 맞는 구도를 만들었다. Vibe도 크롭 결과가 있으나 LALA가 피사체 중심 프레이밍은 더 분명하다. 다만 생성 크롭은 원본 픽셀 보존 결과가 아니므로 가장자리와 얼굴 디테일을 확대 검수해야 한다."),
    "10_크롭_음식기준": ("positive", "LALA Generate AI는 음식/테이블을 중심으로 프레이밍을 재구성해 원본보다 목적성이 분명하다. Nano 대비 물체 배치가 덜 과장됐지만, 출력이 재생성 방식이므로 실제 식재료의 미세 형태 보존 여부는 확대 검수가 필요하다."),
    "10_크롭_메인피사체": ("positive", "LALA Generate AI는 메인 피사체를 화면 중심으로 확대한 결과가 명확해 원본 전체 장면보다 목적 적합성이 높다. Vibe와 Nano에도 유사 크롭이 있으나 LALA는 덜 장식적이다. 생성 기반 프레이밍의 동일성 리스크는 남는다."),
    "11_감성_무드_연출": ("limited", "LALA는 의도된 감성 톤을 약하게만 적용해 원본보다 살짝 탈색·저대비로 보이는 경향이 있다. Vibe는 톤 방향이 더 뚜렷하고 Nano는 따뜻한 빛·색을 과감하게 추가한다. FiveK는 자연스러운 참조로서 LALA보다 명암 분리가 낫다."),
    "12_깔끔모던": ("limited", "LALA는 구조 보존은 좋지만 clean/modern 목표에 필요한 중립 화이트와 선명한 중간톤 분리가 부족하다. Vibe가 더 밝고 정돈된 결과를 내며, Nano는 경우에 따라 장면을 실제와 다르게 단순화한다."),
    "13_느와르_흑백영화": ("negative", "LALA는 흑백화되지만 대비와 블랙 레벨이 약해 느와르의 깊이가 부족하고 회색으로 뜬다. Vibe는 더 강한 흑백 대비를 만들며 Nano는 극적인 음영을 만들지만 장면 재구성 artifact가 보이는 case가 있다."),
    "14_무겁고_어두운_무드": ("limited", "LALA는 어두운 톤의 방향은 맞지만 블랙을 깊게 만들기보다 전체를 탁하게 낮춰 무드의 밀도가 부족하다. Vibe는 더 의도적인 대비를, Nano는 더 강한 암부를 만들지만 디테일 손실 위험이 크다."),
    "15_매트_필름_감성": ("limited", "LALA의 낮은 대비가 매트 필름과 일부 맞지만, 하이라이트 롤오프·색 분리보다 haze가 먼저 보인다. Vibe는 필름 효과가 더 읽히고, Nano는 필름 톤을 과도하게 연출하는 경우가 있다."),
    "16_빈티지_필름": ("limited", "LALA는 약한 탈색 외에 빈티지 필름 특유의 색 이동과 톤 곡선이 충분하지 않다. Vibe가 더 뚜렷한 빈티지 방향을 보이며 Nano는 효과가 강한 대신 원본 색의 사실성이 낮다."),
    "17_청량한_여름": ("limited", "LALA는 하늘·물·녹색을 과하게 만들지 않는 장점은 있으나 청량한 여름의 명료한 청색/녹색과 대비가 부족하다. Vibe와 Nano는 더 선명하며, Nano는 특정 case에서 인물·배경을 재생성한다."),
    "18_시네마틱_컬러_그레이딩": ("limited", "LALA는 장면을 보존하면서도 시네마틱한 색 대비와 하이라이트 설계가 약하다. Vibe는 더 분명한 룩을 만들고 Nano는 광원·색을 크게 바꿔 의도성은 강하지만 현실 장면 보존성은 낮다."),
    "19_애플스타일_뉴트럴_그레이딩": ("limited", "LALA는 과포화를 피하지만, 중립적이면서도 깨끗한 밝기·피부·백색 균형 대신 약간의 저대비/회색화가 남는다. FiveK가 있는 case는 더 자연스러운 중립 기준이고, Nano는 밝기를 높이는 대신 중립성을 잃는 case가 있다."),
    "20_주파수분리_피부_리터치": ("mixed", "LALA Generate AI는 저조도 인물에서 얼굴 가시성과 피부 밝기를 개선하는 case가 있으며, 과도한 플라스틱 피부는 비교적 적다. 그러나 주파수 분리처럼 국소 질감을 보존해야 하는 작업에는 생성 모델 출력의 동일성 리스크가 있어 확대 검수가 필수다."),
    "21_대화형_강도절반": ("positive", "LALA는 변화 강도가 작고 원본 구도를 보존해 ‘절반’ 성격의 미세 보정에 비교적 적합하다. Nano는 변화가 더 크므로 이 요구에는 과한 편이다."),
    "21_대화형_강도조율": ("mixed", "LALA는 원본 보존성은 좋지만 톤 조율의 체감 변화가 약하다. Nano는 방향은 더 뚜렷하나 강도 제어와 원본 동일성 측면에서 과해질 수 있다."),
    "21_대화형_미세조정": ("positive", "LALA는 원본의 인물·배경 구조를 바꾸지 않고 미세한 톤 변화만 보여 대화형 미세 조정의 안전성은 좋다. 다만 확대 인쇄나 명확한 편집 차이를 원하면 변화량을 높일 필요가 있다."),
    "21_대화형_방향반전": ("mixed", "LALA의 방향 전환은 제한적으로 보이며 원본에 가까운 안전한 결과다. Nano는 방향이 더 뚜렷하지만 실제 장면의 색·질감을 바꿀 수 있어 단순 반전 요구에는 과도하다."),
    "21_대화형_은은하게톤다운": ("positive", "LALA는 채도와 밝기를 과격하게 낮추지 않고 부드럽게 톤다운해 원본 보존과 요청 강도 사이의 균형이 좋다. Nano는 더 강한 연출 톤으로 보인다."),
    "21_대화형_자연스럽게마무리": ("positive", "LALA는 자연스러운 마무리에서 원본의 피부·배경 구조를 유지하고, 비교군보다 변화가 억제돼 안전하다. 결과가 너무 미약하다고 느껴지면 요청 강도만 단계적으로 높이는 것이 적절하다."),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    data_root = args.repo_root.resolve() / "demo_backdata"
    written = 0
    for result_path in data_root.rglob("result_lala.json"):
        scenario = result_path.relative_to(data_root).parts[0]
        verdict, review = REVIEWS[scenario]
        result = json.loads(result_path.read_text(encoding="utf-8"))
        evaluation = {
            "schema_version": "1.0",
            "review_method": "direct_contact_sheet_visual_review",
            "reviewer": "Hermes Agent",
            "review_scope": ["before", "vibe_after", "lala", "nano_banana", "baseline_fivek_when_available"],
            "lala_tool": result["tool"],
            "verdict": verdict,
            "review": review,
            "limitations": "비교 시트의 육안 검토다. FiveK는 제공된 case에만 비교했으며, 생성형 결과는 원본 해상도 확대 검수가 추가로 필요하다.",
        }
        (result_path.parent / "evaluation_lala.json").write_text(
            json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        written += 1
    print(f"written={written}")


if __name__ == "__main__":
    main()
