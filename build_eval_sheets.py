# -*- coding: utf-8 -*-
"""manifest.json + demo_backdata → 결과 시트와 블라인드 평가 시트를 생성한다.

과거에는 이 두 HTML을 수작업으로 만들었다. 데이터셋을 교체할 때마다 같은 작업을
반복하게 되므로 스크립트로 고정한다. 시나리오·이미지·비교군 정의는 전부
manifest.json 이 권위이며 이 파일에는 하드코딩하지 않는다.

출력:
  CUJ_결과.html    — AI 평가 + 사람 평가 집계 (eval_data.js 를 읽어 렌더)
  CUJ_평가용.html  — 블라인드 입력용 (AI 점수·타 평가자 점수 미포함)

비교군(baseline)이 있는 시나리오만 3단 카드(BEFORE/AFTER/Expert)와 승패 문항을
가진다. 나머지 시나리오도 Nano Banana 열은 붙지만 승패 문항 없이 지시이행·품질 2축만 평가한다.

사용법 (프로젝트 루트 또는 이 폴더에서):
    backend/venv/Scripts/python.exe 260807_cuj_results/build_eval_sheets.py
"""
import html as H
import io
import json
import sys
from collections import OrderedDict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "demo_backdata"
MANIFEST = ROOT / "manifest.json"
AI_EVAL = ROOT / "claude_eval.json"

IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp")
CAT_COLORS = ["#f59e0b", "#db2777", "#9333ea", "#0ea5e9"]

STYLE = """
 body{font-family:-apple-system,'Segoe UI',sans-serif;margin:0;background:#0f172a;color:#e2e8f0}
 header{padding:24px 32px;background:#1e293b;border-bottom:1px solid #334155}
 h1{margin:0;font-size:22px} .sub{color:#94a3b8;font-size:13px;margin-top:6px}
 nav{position:sticky;top:0;background:#0f172a;padding:8px 32px;border-bottom:1px solid #334155;z-index:10}
 nav a{color:#7dd3fc;margin-right:10px;text-decoration:none;font-size:12px}
 .track{padding:8px 32px;margin:0} .track h2{font-size:16px;margin:20px 0 4px}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(980px,1fr));gap:16px;padding:4px 32px 12px}
 .card{background:#1e293b;border:1px solid #334155;border-radius:10px;overflow:hidden}
 .cardhead{padding:10px 12px;border-bottom:1px solid #334155}
 .id{font-weight:700;font-size:13px}
 .prompt{font-size:13px;color:#cbd5e1;margin:6px 0 0;font-style:italic}
 .imgs{display:grid;gap:2px;background:#0f172a}
 .imgs figure{margin:0;position:relative} .imgs img{width:100%;display:block}
 .imgs figure.noref{background:#0f172a}
 .nobox{height:100%;min-height:120px;box-sizing:border-box;display:flex;align-items:center;justify-content:center;
        text-align:center;color:#475569;font-size:12px;line-height:1.9;border:1px dashed #334155}
 .imgs figcaption{position:absolute;top:6px;left:6px;background:rgba(0,0,0,.6);color:#fff;font-size:10px;padding:1px 6px;border-radius:6px}
 .meta{padding:8px 12px;font-size:12px;color:#94a3b8;border-top:1px solid #334155}
 .tools{font-family:ui-monospace,monospace;font-size:11px;color:#cbd5e1;word-break:break-all}

 .ev{padding:8px 12px 10px;border-top:1px solid #334155;background:#182234}
 .evrow{display:flex;align-items:center;gap:5px;margin:4px 0;flex-wrap:wrap}
 .evlab{font-size:11px;color:#94a3b8;min-width:88px}
 .evb{cursor:pointer;font-size:11px;padding:2px 9px;border:1px solid #475569;border-radius:6px;color:#cbd5e1;background:#0f172a;user-select:none}
 .evb:hover{border-color:#7dd3fc}
 .evb.on{background:#7dd3fc;border-color:#7dd3fc;color:#0f172a;font-weight:700}
 .evmemo{width:100%;margin-top:5px;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#e2e8f0;font-size:11px;padding:4px 6px;box-sizing:border-box}
 .card.done{border-color:#22c55e}
 .evnote{padding:10px 32px;background:#172033;color:#94a3b8;font-size:12px;border-bottom:1px solid #334155;line-height:1.7}
 .evnote b{color:#e2e8f0}
 #evbar{position:fixed;bottom:0;left:0;right:0;background:#1e293b;border-top:1px solid #475569;padding:8px 16px;display:flex;align-items:center;gap:10px;font-size:12px;z-index:50}
 #evbar input[type=text]{background:#0f172a;border:1px solid #334155;border-radius:6px;color:#e2e8f0;padding:4px 8px;font-size:12px;width:120px}
 #evbar button{cursor:pointer;background:#334155;border:1px solid #475569;border-radius:6px;color:#e2e8f0;font-size:12px;padding:4px 10px}
 #evbar button:hover{border-color:#7dd3fc}
 #evprog{color:#7dd3fc;font-weight:700}
 body{padding-bottom:56px}

 .aieval{padding:7px 12px;border-top:1px solid #334155;background:#141c2b;font-size:11.5px;color:#cbd5e1;line-height:1.6}
 .aitag{background:#7c3aed;color:#fff;font-size:10px;font-weight:700;padding:1px 6px;border-radius:5px}
 .aicom{color:#94a3b8}
 .hres{padding:7px 12px;border-top:1px solid #334155;background:#111a27;font-size:11.5px;line-height:1.7}
 .htag{background:#0ea5e9;color:#fff;font-size:10px;font-weight:700;padding:1px 6px;border-radius:5px}
 .hres .hmemo{color:#94a3b8;padding-left:2px}
 .hres .hnone{color:#475569}
 .hbadge{display:inline-block;margin-left:6px;font-size:11px;font-weight:400;color:#a5b4c4;background:#0f172a;border:1px solid #0ea5e9;border-radius:6px;padding:2px 8px;vertical-align:middle}
"""


def esc(s) -> str:
    return H.escape(str(s), quote=True)


def find_image(directory: Path, stem: str):
    for ext in IMG_EXTS:
        p = directory / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def load_result(card_dir: Path) -> dict:
    """result.json 을 읽어 {turns: [...]} 로 정규화한다.

    러너 세대에 따라 세 가지 형태가 존재한다:
      {"turn": {...}} / {"turns": [...]} / {"tools_used": [...]}  (구 run_demo_backdata)
    """
    p = card_dir / "result.json"
    if not p.exists():
        return {"turns": []}
    r = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(r.get("turns"), list):
        return {"turns": r["turns"], "ok": r.get("ok", True)}
    if isinstance(r.get("turn"), dict):
        return {"turns": [r["turn"]], "ok": r.get("ok", True)}
    return {"turns": [{"tools_used": r.get("tools_used", [])}], "ok": r.get("ok", True)}


def render_tools(turns: list) -> str:
    lines = []
    for i, t in enumerate(turns, start=1):
        chain = ", ".join(
            f'{x.get("tool_name")}({json.dumps(x.get("params", {}), ensure_ascii=False)})'
            for x in t.get("tools_used", [])
        ) or "(툴 없음)"
        prefix = f"T{i} " if len(turns) > 1 else ""
        lines.append(f"{prefix}tool: {esc(chain)}")
    return "<br>".join(lines)


NOREF_CELL = (
    '<figure class="noref"><figcaption style="background:rgba(71,85,105,.85)">Expert 비교 제외</figcaption>'
    '<div class="nobox">목표가 달라<br>비교하지 않음</div></figure>'
)


def card_figures(entry: dict, stem: str, turns: list) -> str:
    """카드 이미지 열. 열 수를 카드마다 고정한다 — 열 수가 들쭉날쭉하면 같은 행에서
    이미지 표시 크기가 달라져 비교가 어렵다. BEFORE · AFTER(턴별) · Nano Banana ·
    Expert 순이며, 목표가 달라 비교하지 않는 시나리오는 Expert 자리를 안내 문구로 채운다."""
    base = f"demo_backdata/{entry['id']}/{stem}"
    figs = [("BEFORE", f"{base}/before.jpg", "")]

    if len(turns) > 1:
        for i in range(1, len(turns) + 1):
            figs.append((f"T{i}", f"{base}/after_{i}.jpg", ""))
    else:
        figs.append(("AFTER", f"{base}/after.jpg", ""))

    # Nano Banana — 같은 프롬프트를 gemini-2.5-flash-image 에 그대로 넣은 결과
    nb = find_image(DATA / "_nano_banana" / entry["id"], stem)
    if nb:
        figs.append(("Nano Banana", f"demo_backdata/_nano_banana/{entry['id']}/{nb.name}",
                     "background:rgba(101,163,13,.85)"))

    baseline_cell = None
    if entry.get("baseline"):
        p = find_image(DATA / "_baseline_fivek", stem)
        if p:
            baseline_cell = ("Expert (FiveK)", f"demo_backdata/_baseline_fivek/{p.name}",
                             "background:rgba(180,83,9,.85)")

    cells = []
    for cap, src, style in figs:
        attr = ' style="{}"'.format(style) if style else ""
        cells.append(
            '<figure><figcaption{}>{}</figcaption>'
            '<img src="{}" loading="lazy"></figure>'.format(attr, esc(cap), esc(src))
        )

    if baseline_cell:
        cap, src, style = baseline_cell
        cells.append(
            '<figure><figcaption style="{}">{}</figcaption>'
            '<img src="{}" loading="lazy"></figure>'.format(style, esc(cap), esc(src))
        )
    elif len(cells) < 4:
        cells.append(NOREF_CELL)

    return ('<div class="imgs" style="grid-template-columns:repeat(%d,1fr)">%s</div>'
            % (len(cells), "".join(cells)))


def ai_block(key: str, ai: dict) -> str:
    e = ai.get(key)
    if not e:
        return '<div class="aieval"><span class="aitag">AI</span> <span class="aicom">미평가</span></div>'
    color = lambda v: "#22c55e" if (v or 0) >= 4 else ("#fbbf24" if (v or 0) == 3 else "#f87171")
    bits = (f'지시이행 <b style="color:{color(e.get("inst"))}">{e.get("inst","-")}</b>'
            f'<span style="color:#64748b">/5</span> · '
            f'품질 <b style="color:{color(e.get("qual"))}">{e.get("qual","-")}</b>'
            f'<span style="color:#64748b">/5</span>')
    if e.get("vexp"):
        label = {"vibe": "Vibe승", "tie": "비슷", "exp": "Expert승"}.get(e["vexp"], e["vexp"])
        bits += f' · <span style="color:#94a3b8">{esc(label)}</span>'
    com = f' <span class="aicom">— {esc(e["comment"])}</span>' if e.get("comment") else ""
    return f'<div class="aieval"><span class="aitag">AI</span> {bits}{com}</div>'


def eval_widget(has_baseline: bool) -> str:
    def group(field, options):
        btns = "".join(f'<b class="evb" data-v="{esc(v)}">{esc(lab)}</b>' for v, lab in options)
        return f'<span class="evg" data-f="{field}">{btns}</span>'

    score = [(str(i), str(i)) for i in range(1, 6)]
    rows = [
        f'<div class="evrow"><span class="evlab">지시이행</span>{group("inst", score)}</div>',
        f'<div class="evrow"><span class="evlab">품질</span>{group("qual", score)}</div>',
    ]
    if has_baseline:
        rows.append(
            '<div class="evrow"><span class="evlab">Expert 대비</span>'
            + group("vexp", [("vibe", "Vibe승"), ("tie", "비슷"), ("exp", "Expert승")])
            + "</div>"
        )
    return ('<div class="ev">' + "".join(rows)
            + '<input class="evmemo" type="text" placeholder="메모 (선택)"></div>')


def build_sections(manifest: dict):
    """manifest 항목을 표시 섹션(section_num)으로 묶는다. 09 크롭·20 대화형처럼
    프롬프트가 다른 여러 폴더가 한 섹션에 들어간다."""
    cats = OrderedDict()
    for e in manifest["scenarios"]:
        cats.setdefault(e["cat"], OrderedDict()).setdefault(
            (e["section_num"], e["section_title"]), []).append(e)
    return cats


def build(manifest: dict, ai: dict, blind: bool) -> str:
    cats = build_sections(manifest)
    total_cards = sum(len(e["images"]) for e in manifest["scenarios"])
    n_baseline = sum(len(e["images"]) for e in manifest["scenarios"] if e.get("baseline"))

    nav_parts, body = [], []
    for ci, (cat, sections) in enumerate(cats.items()):
        color = CAT_COLORS[ci % len(CAT_COLORS)]
        nav_parts.append(f'<b style="color:{color}">{esc(cat)}:</b>')
        cat_cards = sum(len(e["images"]) for secs in sections.values() for e in secs)
        body.append(f'<div class="track" id="cat{ci+1}"><h2 style="color:{color}">{esc(cat)}'
                    f'<span style="font-size:12px;color:#94a3b8;font-weight:400">'
                    f' ({len(sections)}개 시나리오 · {cat_cards}카드)</span></h2></div>')

        for (num, title), entries in sections.items():
            has_baseline = any(e.get("baseline") for e in entries)
            n = sum(len(e["images"]) for e in entries)
            nav_parts.append(f'<a href="#sc{num}">{num}. {esc(title)}</a>')
            tag = ""
            body.append(f'<div class="track" id="sc{num}"><h2>{num}. {esc(title)}'
                        f'<span style="font-size:12px;color:#94a3b8;font-weight:400">'
                        f' ({n}개)</span>{tag}</h2></div>')

            cards = []
            for entry in entries:
                for stem in entry["images"]:
                    key = f'{entry["id"]}/{stem}'
                    res = load_result(DATA / entry["id"] / stem)
                    turns = res["turns"] or [{}]
                    prompts = [entry["prompt"]] + ([entry["prompt_t2"]] if entry.get("prompt_t2") else [])
                    ptxt = " → ".join(f'&quot;{esc(p)}&quot;' for p in prompts)
                    tail = (eval_widget(bool(entry.get("baseline"))) if blind
                            else ai_block(key, ai) + '<div class="hres"></div>')
                    cards.append(
                        f'<div class="card" data-key="{esc(key)}">\n'
                        f' <div class="cardhead"><span class="id">{esc(entry["section_title"])}</span>'
                        f'<div class="prompt">{ptxt} — {esc(stem)}</div></div>\n'
                        f' {card_figures(entry, stem, turns)}\n'
                        f' <div class="meta"><span class="tools">{render_tools(turns)}</span></div>'
                        f'{tail}\n</div>'
                    )
            body.append('<div class="grid">' + "\n".join(cards) + "</div>")

    title = "Vibe Editor 평가 — 블라인드 입력" if blind else "Vibe Editor 평가 결과 (취합)"
    sub = (f'{len(cats)}개 분류 · 시나리오 {sum(len(s) for s in cats.values())}개 · '
           f'총 {total_cards}개 카드 · Expert(Adobe FiveK) 비교 {n_baseline}카드 / '
           f'Expert 없음 {total_cards - n_baseline}카드 · 전 카드 Nano Banana 비교 열 포함)')

    note = (
        '<div class="evnote">평가 대상은 <b>Vibe Editor의 AFTER 결과</b>입니다. '
        '<b>지시이행</b>(프롬프트가 요구한 변화가 일어났는가)과 <b>품질</b>(결과물 자체의 완성도)이 주 지표입니다.<br>'
        '<b>Nano Banana</b> 열은 모든 카드에 있습니다 — 같은 프롬프트를 gemini-2.5-flash-image 에 '
        '그대로 넣은 생성형 결과이며 참고용입니다. 일부 시나리오에는 맨 오른쪽에 <b>Expert (Adobe FiveK)</b> '
        '열이 함께 표시됩니다 — 사진가가 직접 리터치한 참조본이며 심사 대상이 아닙니다. 이 열이 있는 '
        '카드에서만 <b>Expert 대비</b> 승패를 골라 주세요. 없는 카드는 지시이행·품질만 평가합니다.<br>'
        '<b style="color:#fbbf24">이 시트는 블라인드 평가용입니다.</b> AI 평가 결과와 다른 평가자의 점수는 '
        '이 파일에 들어 있지 않습니다. 평가를 마치면 하단의 <b>JSON 내보내기</b>로 저장한 뒤 '
        '<code>evals/</code> 폴더에 넣어 주세요.</div>'
    ) if blind else ""

    bar = (
        '<div id="evbar"><span>평가자</span><input type="text" id="evname" placeholder="이름">'
        f'<span>진행 <span id="evprog">0/{total_cards}</span></span>'
        '<button id="evimport">JSON 불러오기</button>'
        '<input type="file" id="evfile" accept=".json,application/json" style="display:none">'
        '<button id="evexport">JSON 내보내기</button>'
        '<button id="evreset" style="margin-left:auto;border-color:#7f1d1d">내 평가 초기화</button></div>'
    ) if blind else (
        '<div id="evbar"><b>평가 참여</b><span id="rsrc" style="color:#94a3b8"></span>'
        '<span id="rstat" style="color:#7dd3fc;font-weight:700"></span>'
        '<button id="rload" style="margin-left:auto">JSON 직접 열기</button>'
        '<input type="file" id="rfile" accept=".json,application/json" multiple style="display:none"></div>'
    )

    script = BLIND_JS.replace("__TOTAL__", str(total_cards)) if blind else RESULT_JS

    return (
        f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>{esc(title)}</title>"
        f"<style>{STYLE}</style></head><body>"
        f"<header><h1>{esc(title)}</h1><div class='sub'>{sub}</div></header>"
        f"<nav>{' '.join(nav_parts)}</nav>{note}"
        + "\n".join(body) + bar + script + "</body></html>"
    )


BLIND_JS = """
<script>
(function(){
  var TOTAL = __TOTAL__;
  var cards = [].slice.call(document.querySelectorAll('.card[data-key]'));
  var nameEl = document.getElementById('evname');
  var progEl = document.getElementById('evprog');
  var state = {};
  var LAST = 'cuj_eval_lastname';

  function skey(){ return 'cuj_eval::' + (nameEl.value.trim() || '_default'); }
  function load(){
    state = {};
    try { var raw = localStorage.getItem(skey());
          if (raw) { state = (JSON.parse(raw).entries) || {}; } } catch(e) { state = {}; }
  }
  function save(){
    try {
      localStorage.setItem(skey(), JSON.stringify({
        evaluator: nameEl.value.trim(), ts: new Date().toISOString(), entries: state}));
      localStorage.setItem(LAST, nameEl.value.trim());
    } catch(e){}
  }
  function ent(k){ if (!state[k]) state[k] = {}; return state[k]; }
  function done(e){ return e && e.inst && e.qual; }
  function progress(){
    var n = 0; for (var k in state) if (done(state[k])) n++;
    progEl.textContent = n + '/' + TOTAL;
  }
  function renderCard(card){
    var e = state[card.getAttribute('data-key')] || {};
    [].forEach.call(card.querySelectorAll('.evg'), function(g){
      var f = g.getAttribute('data-f');
      [].forEach.call(g.querySelectorAll('.evb'), function(bt){
        bt.classList.toggle('on', String(e[f] || '') === bt.getAttribute('data-v'));
      });
    });
    var memo = card.querySelector('.evmemo');
    if (document.activeElement !== memo) memo.value = e.memo || '';
    card.classList.toggle('done', !!done(e));
  }
  function renderAll(){ cards.forEach(renderCard); progress(); }

  cards.forEach(function(card){
    var k = card.getAttribute('data-key');
    [].forEach.call(card.querySelectorAll('.evg'), function(g){
      var f = g.getAttribute('data-f');
      g.addEventListener('click', function(evt){
        var bt = evt.target;
        if (!bt.classList || !bt.classList.contains('evb')) return;
        var v = bt.getAttribute('data-v'), e = ent(k);
        if (String(e[f] || '') === v) delete e[f]; else e[f] = v;
        save(); renderCard(card); progress();
      });
    });
    card.querySelector('.evmemo').addEventListener('input', function(){
      var e = ent(k);
      if (this.value) e.memo = this.value; else delete e.memo;
      save();
    });
  });

  nameEl.addEventListener('change', function(){ load(); renderAll(); });

  document.getElementById('evexport').addEventListener('click', function(){
    var name = nameEl.value.trim();
    if (!name) { alert('평가자 이름을 먼저 입력해 주세요.'); nameEl.focus(); return; }
    var d = new Date();
    var stamp = d.getFullYear() + ('0'+(d.getMonth()+1)).slice(-2) + ('0'+d.getDate()).slice(-2);
    var blob = new Blob([JSON.stringify(
      {evaluator: name, ts: d.toISOString(), total: TOTAL, entries: state}, null, 2)],
      {type:'application/json'});
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'eval_' + name + '_' + stamp + '.json';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  });

  var fileEl = document.getElementById('evfile');
  document.getElementById('evimport').addEventListener('click', function(){ fileEl.click(); });
  fileEl.addEventListener('change', function(){
    var f = fileEl.files[0]; fileEl.value = '';
    if (!f) return;
    var rd = new FileReader();
    rd.onload = function(){
      var o;
      try { o = JSON.parse(rd.result); } catch(e){ alert('읽을 수 없는 파일: ' + f.name); return; }
      if (!o || !o.entries) { alert('평가 데이터가 없는 파일입니다: ' + f.name); return; }
      var cur = 0; for (var k in state) cur++;
      if (cur && !confirm('현재 입력 ' + cur + '건을 파일 내용으로 덮어씁니다. 계속할까요?')) return;
      if (o.evaluator) nameEl.value = o.evaluator;
      state = o.entries;
      save(); renderAll();
      alert('불러왔습니다 — ' + (o.evaluator || '이름없음') + ' · ' + progEl.textContent);
    };
    rd.readAsText(f);
  });

  document.getElementById('evreset').addEventListener('click', function(){
    if (!confirm('현재 평가자(' + (nameEl.value.trim() || '_default') + ')의 평가를 모두 지웁니다.')) return;
    state = {}; save(); renderAll();
  });

  try { nameEl.value = localStorage.getItem(LAST) || ''; } catch(e){}
  load(); renderAll();
})();
</script>
"""

RESULT_JS = """
<script src="eval_data.js" onerror="window.CUJ_EVALS=window.CUJ_EVALS||[]"></script>
<script>
(function(){
  // 개인별 점수는 노출하지 않는다 — 집계값과 익명 메모만 표시하고, 참여자 명단은 하단 바에만.
  var VS = {vibe:'Vibe승', tie:'비슷', exp:'Expert승'};
  var cards = [].slice.call(document.querySelectorAll('.card[data-key]'));
  var srcEl = document.getElementById('rsrc');
  var statEl = document.getElementById('rstat');
  var evals = [];

  function esc(s){ return String(s).replace(/[&<>"]/g,
    function(c){ return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]; }); }
  function avg(x){ return (x.reduce(function(s,v){return s+v;},0)/x.length).toFixed(1); }

  var scenGroups = [], catGroups = [], curScen = null, curCat = null;
  [].forEach.call(document.querySelectorAll('.track, .grid'), function(el){
    if (el.classList.contains('track')) {
      var h2 = el.querySelector('h2');
      if (/^cat/.test(el.id)) { curCat = {h2: h2, keys: []}; catGroups.push(curCat); }
      else { curScen = {h2: h2, keys: []}; scenGroups.push(curScen); }
    } else {
      var ks = [].map.call(el.querySelectorAll('.card[data-key]'),
                           function(c){ return c.getAttribute('data-key'); });
      if (curScen) curScen.keys = curScen.keys.concat(ks);
      if (curCat) curCat.keys = curCat.keys.concat(ks);
    }
  });

  function collect(keys){
    var insts = [], quals = [], raters = {};
    keys.forEach(function(k){
      evals.forEach(function(src){
        var e = (src.entries || {})[k];
        if (!e) return;
        if (e.inst) { insts.push(+e.inst); raters[src.evaluator] = 1; }
        if (e.qual) { quals.push(+e.qual); raters[src.evaluator] = 1; }
      });
    });
    return {insts: insts, quals: quals, raters: Object.keys(raters).length};
  }

  function groupBadge(g){
    var old = g.h2.querySelector('.hbadge');
    if (old) old.remove();
    var s = collect(g.keys);
    if (!s.insts.length && !s.quals.length) return;
    var span = document.createElement('span');
    span.className = 'hbadge';
    span.textContent = '사람 지시 ' + (s.insts.length ? avg(s.insts) : '-')
                     + ' · 품질 ' + (s.quals.length ? avg(s.quals) : '-')
                     + ' (' + s.raters + '명 참여)';
    g.h2.appendChild(span);
  }

  function render(){
    var scored = 0;
    cards.forEach(function(card){
      var k = card.getAttribute('data-key');
      var box = card.querySelector('.hres');
      if (!box) return;
      var insts = [], quals = [], vc = {vibe:0, tie:0, exp:0}, memos = [], n = 0;
      evals.forEach(function(src){
        var e = (src.entries || {})[k];
        if (!e || (!e.inst && !e.qual && !e.vexp && !e.memo)) return;
        n++;
        if (e.inst) insts.push(+e.inst);
        if (e.qual) quals.push(+e.qual);
        if (e.vexp && vc[e.vexp] !== undefined) vc[e.vexp]++;
        if (e.memo) memos.push(String(e.memo));
      });
      if (!n) { box.innerHTML = '<div class="hnone">사람 평가 없음</div>'; return; }
      scored++;

      var bits = [];
      if (insts.length) bits.push('지시이행 <b>' + avg(insts) + '</b>/5');
      if (quals.length) bits.push('품질 <b>' + avg(quals) + '</b>/5');
      var vparts = [];
      ['vibe','tie','exp'].forEach(function(key){
        if (vc[key]) vparts.push(VS[key] + ' ' + vc[key]);
      });
      if (vparts.length) bits.push('Expert 대비 ' + vparts.join(' · '));

      var out = ['<div><span class="htag">사람 ' + n + '명</span> ' + bits.join(' · ') + '</div>'];
      if (memos.length) {
        out.push('<div class="hmemo">메모 · ' +
          memos.sort().map(function(m){ return '“' + esc(m) + '”'; }).join(' / ') + '</div>');
      }
      box.innerHTML = out.join('');
    });

    scenGroups.forEach(groupBadge);
    catGroups.forEach(groupBadge);

    srcEl.textContent = evals.length
      ? '참여자 ' + evals.length + '명 — ' +
        evals.map(function(s){ return s.evaluator; }).sort().join(', ') +
        ' (개별 점수는 공개하지 않고 평균만 표시합니다)'
      : 'evals/ 폴더에 JSON을 넣고 평가취합.bat 실행 (또는 우측 버튼으로 직접 열기)';
    statEl.textContent = evals.length ? ('평가된 카드 ' + scored + '/' + cards.length) : '';
  }

  function add(list){
    list.forEach(function(o){
      if (!o || !o.entries) return;
      var nm = o.evaluator || '이름없음';
      evals = evals.filter(function(s){ return s.evaluator !== nm; });
      evals.push({evaluator: nm, entries: o.entries});
    });
    render();
  }

  var fileEl = document.getElementById('rfile');
  document.getElementById('rload').addEventListener('click', function(){ fileEl.click(); });
  fileEl.addEventListener('change', function(){
    var files = [].slice.call(fileEl.files), left = files.length, acc = [];
    fileEl.value = '';
    if (!left) return;
    files.forEach(function(f){
      var rd = new FileReader();
      rd.onload = function(){
        try { acc.push(JSON.parse(rd.result)); } catch(e){}
        if (--left === 0) add(acc);
      };
      rd.readAsText(f);
    });
  });

  add(window.CUJ_EVALS || []);
})();
</script>
"""


# ---------------------------------------------------------------------------
# 자립형 export — 이미지를 data URI 로 굽고 script 를 걷어낸 배포본
#
# 예전에는 export_standalone.py 가 CUJ_결과.html 을 정규식으로 재파싱했는데,
# 시트 마크업이 바뀔 때마다 조용히 깨졌다. manifest 에서 직접 만든다.
# ---------------------------------------------------------------------------

_uri_by_path: dict = {}
_uri_by_hash: dict = {}
_enc_stats = {"encoded": 0, "reused": 0, "bytes": 0}


def data_uri(rel: str, max_px: int, use_jpeg: bool) -> str:
    if rel in _uri_by_path:
        _enc_stats["reused"] += 1
        return _uri_by_path[rel]
    import base64
    import hashlib
    from PIL import Image, ImageFile, ImageOps
    ImageFile.LOAD_TRUNCATED_IMAGES = True

    p = ROOT / rel
    raw = p.read_bytes()
    h = hashlib.md5(raw).hexdigest()
    if h in _uri_by_hash:                      # 내용이 같은 이미지는 한 번만 인코딩
        _uri_by_path[rel] = _uri_by_hash[h]
        _enc_stats["reused"] += 1
        return _uri_by_hash[h]

    im = Image.open(io.BytesIO(raw))
    im = ImageOps.exif_transpose(im)           # 회전을 픽셀에 구워 넣는다
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    im.thumbnail((max_px, max_px), Image.LANCZOS)
    buf = io.BytesIO()
    if use_jpeg:
        im.save(buf, "JPEG", quality=82, optimize=True)
        mime = "image/jpeg"
    else:
        im.save(buf, "WEBP", quality=80, method=4)
        mime = "image/webp"
    uri = f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode()
    _uri_by_hash[h] = uri
    _uri_by_path[rel] = uri
    _enc_stats["encoded"] += 1
    _enc_stats["bytes"] += buf.tell()
    if _enc_stats["encoded"] % 40 == 0:
        print(f"    인코딩 {_enc_stats['encoded']}장", flush=True)
    return uri


def human_stats(keys, evals):
    insts, quals, vc, raters, memos = [], [], {"vibe": 0, "tie": 0, "exp": 0}, set(), []
    for k in keys:
        for src in evals:
            e = (src.get("entries") or {}).get(k)
            if not e:
                continue
            if e.get("inst"):
                insts.append(int(e["inst"])); raters.add(src["evaluator"])
            if e.get("qual"):
                quals.append(int(e["qual"])); raters.add(src["evaluator"])
            if e.get("vexp") in vc:
                vc[e["vexp"]] += 1
            if e.get("memo"):
                memos.append(str(e["memo"]))
    return insts, quals, vc, raters, memos


def human_block(key: str, evals) -> str:
    insts, quals, vc, raters, memos = human_stats([key], evals)
    n = sum(1 for src in evals if (src.get("entries") or {}).get(key))
    if not n:
        return '<div class="hres"><div class="hnone">사람 평가 없음</div></div>'
    avg = lambda x: f"{sum(x)/len(x):.1f}"
    bits = []
    if insts:
        bits.append(f"지시이행 <b>{avg(insts)}</b>/5")
    if quals:
        bits.append(f"품질 <b>{avg(quals)}</b>/5")
    labels = {"vibe": "Vibe승", "tie": "비슷", "exp": "Expert승"}
    vparts = [f"{labels[k]} {v}" for k, v in vc.items() if v]
    if vparts:
        bits.append("Expert 대비 " + " · ".join(vparts))
    out = f'<div><span class="htag">사람 {n}명</span> ' + " · ".join(bits) + "</div>"
    if memos:
        # 작성자를 밝히지 않고 순서로도 추정되지 않게 정렬해서 익명 표시
        out += ('<div class="hmemo">메모 · '
                + " / ".join(f"“{esc(m)}”" for m in sorted(memos)) + "</div>")
    return f'<div class="hres">{out}</div>'


def build_export(manifest: dict, ai: dict, evals: list, max_px: int, use_jpeg: bool):
    import re
    cats = build_sections(manifest)
    out_dir = ROOT / "export"
    out_dir.mkdir(exist_ok=True)
    names = {}
    for i, cat in enumerate(cats, start=1):
        slug = re.sub(r"[^0-9A-Za-z가-힣]", "", cat)
        names[cat] = f"CUJ_결과_{i}_{slug}.html"

    written = []
    for ci, (cat, sections) in enumerate(cats.items()):
        color = CAT_COLORS[ci % len(CAT_COLORS)]
        body, nav_parts, all_keys = [], [], []

        for (num, title), entries in sections.items():
            has_baseline = any(e.get("baseline") for e in entries)
            n = sum(len(e["images"]) for e in entries)
            nav_parts.append(f'<a href="#sc{num}">{num}. {esc(title)}</a>')
            tag = ""
            body.append(f'<div class="track" id="sc{num}"><h2>{num}. {esc(title)}'
                        f'<span style="font-size:12px;color:#94a3b8;font-weight:400">'
                        f' ({n}개)</span>{tag}</h2></div>')
            cards = []
            for entry in entries:
                for stem in entry["images"]:
                    key = f'{entry["id"]}/{stem}'
                    all_keys.append(key)
                    res = load_result(DATA / entry["id"] / stem)
                    turns = res["turns"] or [{}]
                    prompts = [entry["prompt"]] + ([entry["prompt_t2"]] if entry.get("prompt_t2") else [])
                    ptxt = " → ".join(f'&quot;{esc(p)}&quot;' for p in prompts)
                    figs = card_figures(entry, stem, turns)
                    figs = re.sub(r'src="((?!data:)[^"]+)"',
                                  lambda m: 'src="%s"' % data_uri(m.group(1), max_px, use_jpeg), figs)
                    figs = figs.replace(' loading="lazy"', "")
                    cards.append(
                        f'<div class="card" data-key="{esc(key)}">\n'
                        f' <div class="cardhead"><span class="id">{esc(entry["section_title"])}</span>'
                        f'<div class="prompt">{ptxt} — {esc(stem)}</div></div>\n'
                        f' {figs}\n'
                        f' <div class="meta"><span class="tools">{render_tools(turns)}</span></div>'
                        f'{ai_block(key, ai)}{human_block(key, evals)}\n</div>'
                    )
            body.append('<div class="grid">' + "\n".join(cards) + "</div>")

        others = " · ".join(f'<a href="{f}">{esc(c)}</a>'
                            for c, f in names.items() if c != cat)
        summary = summary_block(cat, all_keys, ai, evals, others)
        title = f"Vibe Editor 평가 결과 — {cat}"
        doc = (
            f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>{esc(title)}</title>"
            f"<style>{STYLE}{EXPORT_CSS}</style></head><body>"
            f"<header><h1>{esc(title)}</h1>"
            f"<div class='sub'>시나리오 {len(sections)}개 · {len(all_keys)}개 카드</div></header>"
            f"<nav><b style=\"color:{color}\">{esc(cat)}:</b> {' '.join(nav_parts)}</nav>"
            f"{summary}" + "\n".join(body) + "</body></html>"
        )
        p = out_dir / names[cat]
        p.write_text(doc, encoding="utf-8")
        mb = p.stat().st_size / 1024 / 1024
        written.append((names[cat], mb, len(all_keys)))
        print(f"  {names[cat]:38s} {mb:6.1f} MB  (카드 {len(all_keys)})")
    return written


def summary_block(cat: str, keys, ai: dict, evals: list, others: str) -> str:
    a = [ai[k] for k in keys if k in ai]
    rows = [f"<b>{esc(cat)}</b> · 카드 {len(keys)}개"]
    if a:
        vc = {"vibe": 0, "tie": 0, "exp": 0}
        for x in a:
            if x.get("vexp") in vc:
                vc[x["vexp"]] += 1
        line = (f'<b>AI</b> 지시이행 {sum(x.get("inst",0) for x in a)/len(a):.2f} · '
                f'품질 {sum(x.get("qual",0) for x in a)/len(a):.2f}')
        if sum(vc.values()):
            line += (f' · Expert 대비 Vibe승 {vc["vibe"]} / 비슷 {vc["tie"]} / Expert승 {vc["exp"]}')
        rows.append(line)
    else:
        rows.append('<b>AI</b> 미평가')
    insts, quals, vc, raters, _ = human_stats(keys, evals)
    if insts or quals:
        line = (f'<b>사람</b> ({len(raters)}명: {", ".join(sorted(raters))}) '
                f'지시이행 {sum(insts)/len(insts):.2f} · 품질 {sum(quals)/len(quals):.2f}')
        if sum(vc.values()):
            line += f' · Expert 대비 Vibe승 {vc["vibe"]} / 비슷 {vc["tie"]} / Expert승 {vc["exp"]}'
        rows.append(line)
    else:
        rows.append("<b>사람</b> 평가 없음")
    rows.append('<span class="note">평가 대상은 Vibe Editor의 AFTER 결과입니다. '
                'Nano Banana(gemini-2.5-flash-image)는 같은 프롬프트를 그대로 넣은 생성형 비교군, '
                'Expert (Adobe FiveK)는 사진가가 직접 리터치한 참조본이며 둘 다 심사 대상이 아닙니다. '
                '목표가 같은 시나리오에만 Expert 열이 붙고, 나머지는 승패 문항 없이 지시이행·품질만 평가합니다. '
                '사람 평가는 개별 점수를 공개하지 않고 평균·분포만 표시합니다.</span>')
    if others:
        rows.append(f'<span class="note">다른 분류: {others} (같은 폴더에 함께 두면 링크가 동작합니다)</span>')
    return '<div class="sumbox">' + "".join(f"<div>{r}</div>" for r in rows) + "</div>"


EXPORT_CSS = """
 .sumbox{margin:14px 32px;padding:14px 18px;background:#172033;border:1px solid #334155;
         border-radius:10px;font-size:13px;line-height:1.9;color:#cbd5e1}
 .sumbox .note{color:#94a3b8;font-size:12px;line-height:1.7;display:block;margin-top:6px}
 .sumbox a{color:#7dd3fc}
 body{padding-bottom:0}
"""


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ai = {}
    if AI_EVAL.exists():
        ai = json.loads(AI_EVAL.read_text(encoding="utf-8")).get("entries", {})

    if "--export" in sys.argv:
        max_px = 800
        if "--px" in sys.argv:
            max_px = int(sys.argv[sys.argv.index("--px") + 1])
        use_jpeg = "--jpeg" in sys.argv
        evals = []
        for f in sorted((ROOT / "evals").glob("*.json")):
            o = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(o.get("entries"), dict):
                evals.append({"evaluator": o.get("evaluator") or f.stem, "entries": o["entries"]})
        print(f"자립형 export — 평가자 {len(evals)}명, 장변 {max_px}px "
              f"{'JPEG' if use_jpeg else 'WebP'}")
        written = build_export(manifest, ai, evals, max_px, use_jpeg)
        print(f"\n인코딩 {_enc_stats['encoded']}장 (재사용 {_enc_stats['reused']}회) · "
              f"합계 {sum(m for _, m, _ in written):.1f} MB")
        return 0

    for blind, name in [(False, "CUJ_결과.html"), (True, "CUJ_평가용.html")]:
        doc = build(manifest, ai, blind)
        (ROOT / name).write_text(doc, encoding="utf-8")
        print(f"  {name:20s} {len(doc)/1024:7.0f} KB")

    # 검증 — 참조 이미지가 실제로 존재하는지
    import re
    missing = 0
    for name in ("CUJ_결과.html", "CUJ_평가용.html"):
        t = (ROOT / name).read_text(encoding="utf-8")
        for src in set(re.findall(r'<img src="((?!data:)[^"]+)"', t)):
            if not (ROOT / src).exists():
                missing += 1
                if missing <= 5:
                    print(f"    누락: {src}")
    print(f"\n이미지 참조 누락: {missing}")
    print(f"AI 평가 보유: {len(ai)}건")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
