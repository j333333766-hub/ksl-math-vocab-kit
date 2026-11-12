# 스토리보드 pptx(업체 전달용): storyline_capture.mjs가 찍은 화면 + 스토리보드 메모(json) → 한 화면 한 슬라이드
#   python storyboard_pptx.py "차시 html 경로" ["담당 선생님 (학교)"]
#   → html 옆 <html 이름>_스토리보드.pptx
#   메모: html 옆 <html 이름>_스토리보드.json (없으면 html 이름에서 버전을 뗀 이름도 찾는다. 형식은 맨 아래 주석)
#
# 검토용 pptx(storyline_pptx.py)와 다른 점
#   - 오른쪽 칸이 ‘검토 의견’이 아니라 ‘화면 설명 / 조작 / 구현 요청’이다(업체가 그대로 만들 수 있게).
#   - 앞쪽에 ‘업체에 전하는 말’, ‘용어 정의(충남대 어휘목록과 비교)’, ‘검토 의견 반영 내역’ 슬라이드가 있다.
#   - 충남대 어휘목록 정의와 다르게 쓴 정의 내레이션 옆에 붉은 글씨 [충남대어휘목록 변형]을 붙인다(11/12 김수철 교수).
import json, os, re, sys
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn

SRC = os.path.abspath(sys.argv[1])
DIR = os.path.dirname(SRC)
BASE = os.path.splitext(os.path.basename(SRC))[0]
SL = os.path.join(DIR, '스토리라인_임시')
OUT = os.path.join(DIR, BASE + '_스토리보드.pptx')
FONT = '맑은 고딕'
NAVY, TEAL, GRAY, LIGHT, ORANGE, RED, WHITE = (RGBColor(0x18, 0x36, 0x4A), RGBColor(0x3D, 0xBB, 0x9F), RGBColor(0x6B, 0x72, 0x80),
                                               RGBColor(0xF3, 0xF5, 0xF8), RGBColor(0xE8, 0x7A, 0x1E), RGBColor(0xD6, 0x28, 0x28), RGBColor(255, 255, 255))
MODS = ['인트로', '오늘의 어휘', '뜻 알아보기', '교과서 맛보기', '연습하기', '정리하기', '아웃트로']
VARIANT = '[충남대어휘목록 변형]'

m = json.load(open(os.path.join(SL, 'manifest.json'), encoding='utf-8'))
if m.get('source') != os.path.basename(SRC):
    raise SystemExit(f"스토리라인_임시는 {m.get('source')}를 찍은 것입니다. 먼저 storyline_capture.mjs로 이 html을 찍으세요.")
shots = m['shots']
NAME = {x['id']: x.get('name') or x['id'] for x in shots}

memo_path = next((p for p in [os.path.join(DIR, BASE + '_스토리보드.json'),
                              os.path.join(DIR, re.sub(r'_v[\d\-]+$', '', BASE) + '_스토리보드.json')] if os.path.exists(p)), None)
MEMO = json.load(open(memo_path, encoding='utf-8')) if memo_path else {}
WHO = sys.argv[2] if len(sys.argv) > 2 else MEMO.get('담당', '')
SCR = MEMO.get('화면', {})
DEFS = MEMO.get('정의', [])
VAR_IDS = {i for d in DEFS if d.get('변형') for i in d.get('대사 id', [])}
missing = []

# 같은 화면의 앞 컷에서 이미 나온 대사는 빼기
prev = {}
for s in shots:
    seen = prev.get(s['id'], set())
    rest = [l for l in s['lines'] if l.get('id') not in seen]
    s['show'] = rest if rest else s['lines']
    prev[s['id']] = seen | {l.get('id') for l in s['lines']}

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def font(run, size, bold=False, color=NAVY):
    f = run.font
    f.name, f.size, f.bold = FONT, Pt(size), bold
    f.color.rgb = color
    rpr = run._r.get_or_add_rPr()
    for tag in ('a:ea', 'a:cs'):
        el = rpr.find(qn(tag))
        if el is None:
            el = rpr.makeelement(qn(tag), {})
            rpr.append(el)
        el.set('typeface', FONT)


def text(slide, x, y, w, h, runs, size=14, color=NAVY, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    """runs: 문자열 또는 [(글, {size,color,bold})...]의 줄 목록"""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for k, line in enumerate(runs if isinstance(runs, list) else [runs]):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        p.alignment = align
        for t, st in (line if isinstance(line, list) else [(line, {})]):
            r = p.add_run()
            r.text = t
            font(r, st.get('size', size), st.get('bold', bold), st.get('color', color))
    return tb


def box(slide, x, y, w, h, fill=None, line=None):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid(); s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line; s.line.width = Pt(1)
    s.shadow.inherit = False
    return s


def table(slide, x, y, w, rows, widths, size=11.5, head_fill=NAVY, red_col=None):
    t = slide.shapes.add_table(len(rows), len(widths), x, y, w, Inches(0.4) * len(rows)).table
    for c, wd in enumerate(widths):
        t.columns[c].width = Inches(wd)
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            cell = t.cell(r, c)
            cell.margin_top = cell.margin_bottom = Emu(30000)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = str(v)
            red = red_col is not None and r > 0 and c == red_col and str(v).startswith('변형')
            font(run, size if r else size + 0.5, bold=(r == 0) or red, color=WHITE if r == 0 else (RED if red else NAVY))
            if r == 0:
                cell.fill.solid(); cell.fill.fore_color.rgb = head_fill
            else:
                cell.fill.solid(); cell.fill.fore_color.rgb = WHITE if r % 2 else LIGHT
    return t


def title_bar(s, title, sub=''):
    box(s, 0, 0, prs.slide_width, Inches(0.8), fill=NAVY)
    text(s, Inches(0.4), Inches(0.14), Inches(12.5), Inches(0.55), [[(title, {'bold': True, 'size': 22, 'color': WHITE}), ('   ' + sub, {'size': 14, 'color': RGBColor(0xDD, 0xE6, 0xEE)})]])


def memo_for(sh):
    """화면 메모: 'id', 'id#컷번호', 'id@상태' 순서로 찾아 합친다(뒤의 것이 앞의 것을 덮음)"""
    out = {}
    cut = re.match(r'컷 (\d+)/', sh['state'])
    keys = [sh['id']] + ([f"{sh['id']}#{cut.group(1)}"] if cut else []) + [f"{sh['id']}@{sh['state']}"]
    for k in keys:
        if k in SCR:
            out.update(SCR[k])
    return out


# 1) 표지
s = prs.slides.add_slide(BLANK)
box(s, 0, 0, prs.slide_width, Inches(7.5), fill=LIGHT)
box(s, 0, 0, Inches(0.35), Inches(7.5), fill=ORANGE)
text(s, Inches(0.9), Inches(1.3), Inches(11.5), Inches(0.6), '이주배경 학생 교과 적응 수학 한국어 어휘 콘텐츠 · 업체 전달용', size=18, color=GRAY)
text(s, Inches(0.9), Inches(1.9), Inches(11.5), Inches(1.2), BASE.replace('_', ' ') + ' — 스토리보드', size=36, bold=True)
text(s, Inches(0.9), Inches(3.9), Inches(11.5), Inches(2.6), [
    f'· 검토 의견을 반영한 수정본입니다. 같은 폴더의 {BASE}.html 과 함께 봅니다(소리·움직임은 html에서 확인).',
    f'· 화면 {len(shots)}장 — 슬라이드마다 왼쪽은 원고 화면, 아래는 대사·내레이션, 오른쪽은 화면 설명·조작·구현 요청입니다.',
    '· html은 원고(시안)입니다. html과 이 스토리보드가 다르면 스토리보드의 ‘구현 요청’을 따라 주세요.',
    f'· 붉은 글씨 {VARIANT}: 충남대 어휘목록의 정의를 쉽게 고쳐 쓴 곳입니다(정의 비교는 다음 슬라이드).',
], size=15)
text(s, Inches(0.9), Inches(6.7), Inches(11.5), Inches(0.4), WHO, size=13, color=GRAY)

# 2) 업체에 전하는 말 + 용어 정의
s = prs.slides.add_slide(BLANK)
title_bar(s, '업체에 전하는 말과 용어 정의')
notes = MEMO.get('업체에 전하는 말', [])
y = 1.0
text(s, Inches(0.5), Inches(y), Inches(12.3), Inches(0.4), '업체에 전하는 말', size=15, bold=True, color=ORANGE)
body = [f'· {n}' for n in notes] or [[('(적은 것 없음)', {'color': GRAY})]]
text(s, Inches(0.5), Inches(y + 0.4), Inches(12.3), Inches(0.35 * max(1, len(notes)) + 0.1), body, size=13)
y += 0.6 + 0.35 * max(1, len(notes)) + 0.2
text(s, Inches(0.5), Inches(y), Inches(12.3), Inches(0.4), '용어 정의 — 화면에는 주어와 ‘~이에요’를 뺀 명사형, 성우는 주어를 넣은 해요체 문장으로 읽습니다', size=15, bold=True, color=ORANGE)
rows = [['낱말', '충남대 어휘목록 정의', '원고 정의(화면)', '성우가 읽는 말', '충남대와']]
for d in DEFS:
    rows.append([d.get('낱말', ''), d.get('충남대', ''), d.get('화면', ''), d.get('내레이션', ''),
                 ('변형 — ' + d.get('까닭', '')) if d.get('변형') else '그대로'])
if len(rows) == 1:
    rows.append(['(스토리보드 메모의 ‘정의’를 채우세요)', '', '', '', ''])
    missing.append('정의')
table(s, Inches(0.5), Inches(y + 0.45), Inches(12.3), rows, [1.4, 3.0, 2.8, 2.9, 2.2], size=11.5, red_col=4)

# 3) 검토 의견 반영 내역
rv = MEMO.get('검토 반영', [])
if rv:
    s = prs.slides.add_slide(BLANK)
    title_bar(s, '검토 의견 반영 내역', MEMO.get('검토 반영 근거', ''))
    rows = [['화면', '검토 의견', '반영']] + [[r.get('화면', ''), r.get('의견', ''), r.get('반영', '')] for r in rv]
    table(s, Inches(0.5), Inches(1.05), Inches(12.3), rows, [1.6, 5.4, 5.3], size=11)

# 4) 흐름 한눈에
s = prs.slides.add_slide(BLANK)
title_bar(s, '학습 흐름 한눈에 보기')
groups = []
for k, sh in enumerate(shots):
    if not groups or groups[-1]['id'] != sh['id']:
        groups.append({'id': sh['id'], 'mod': sh['mod'], 'sub': sh['sub'], 'kind': sh.get('kind'), 'n': 0, 'start': k})
    groups[-1]['n'] += 1
first = len(prs.slides._sldIdLst) + 1
rows = [['모듈', '화면', '내용', '형식', '장면 수', '슬라이드']]
for g in groups:
    a = g['start'] + first
    rows.append([f"{g['mod']}. {MODS[g['mod'] - 1]}", g['sub'] or '-', NAME.get(g['id'], g['id']),
                 '애니메이션' if g['kind'] == 'anim' else 'HTML(상호작용)', str(g['n']), f"{a}~{a + g['n'] - 1}" if g['n'] > 1 else str(a)])
t = table(s, Inches(0.5), Inches(1.0), Inches(12.3), rows, [2.4, 0.9, 4.6, 1.9, 1.0, 1.5], size=11 if len(rows) < 16 else 9.5)
for r in range(len(rows)):   # 표가 슬라이드 안에 들어가게
    t.rows[r].height = Emu(int(Inches(6.2) / len(rows)))
    for c in range(len(rows[0])):
        t.cell(r, c).margin_top = t.cell(r, c).margin_bottom = Emu(8000)

# 5) 화면마다 한 장
IMG_W = Inches(7.9)
X2 = Inches(8.45)
W2 = Inches(4.55)
for k, sh in enumerate(shots, 1):
    s = prs.slides.add_slide(BLANK)
    mm = memo_for(sh)
    box(s, 0, 0, prs.slide_width, Inches(0.72), fill=NAVY)
    head = [(f"모듈 {sh['mod']} · {MODS[sh['mod'] - 1]}", {'bold': True, 'color': WHITE, 'size': 16}),
            (f"   화면 {sh['mod']}-{sh['sub'].split('/')[0] if sh['sub'] else ''} {NAME.get(sh['id'], sh['id'])}", {'color': RGBColor(0xDD, 0xE6, 0xEE), 'size': 15}),
            (f"   ·  {sh['state']}", {'color': RGBColor(0xF9, 0xB2, 0x33), 'size': 15, 'bold': True}),
            ('   ' + ('애니메이션' if sh.get('kind') == 'anim' else 'HTML'), {'color': RGBColor(0xDD, 0xE6, 0xEE), 'size': 13})]
    text(s, Inches(0.35), Inches(0.12), Inches(11), Inches(0.5), [head])
    text(s, Inches(11.3), Inches(0.16), Inches(1.75), Inches(0.45), f"{len(prs.slides._sldIdLst)} / ", size=13, color=RGBColor(0xDD, 0xE6, 0xEE), align=PP_ALIGN.RIGHT)
    pic = s.shapes.add_picture(os.path.join(SL, 'shots', sh['file']), Inches(0.35), Inches(0.92), width=IMG_W)
    pic.crop_bottom = 0.105
    pic.height = int(pic.height * (1 - 0.105))
    pic.line.color.rgb = RGBColor(0xD5, 0xDA, 0xE1); pic.line.width = Pt(0.75)
    top = 0.92 + pic.height / 914400 + 0.12
    # 대사·내레이션
    box(s, Inches(0.35), Inches(top), IMG_W, Inches(7.5 - top - 0.2), fill=LIGHT)
    lines = [[('대사·내레이션', {'bold': True, 'size': 12, 'color': TEAL})]]
    for l in sh['show']:
        row = [(f"{l['who']}  ", {'bold': True, 'size': 12}), (l['text'], {'size': 12})]
        if l.get('id') in VAR_IDS:
            row.append(('  ' + VARIANT, {'size': 12, 'bold': True, 'color': RED}))
        lines.append(row)
    if not sh['show']:
        lines.append([('(대사 없음 — 화면 조작·활동 장면)', {'size': 11, 'color': GRAY})])
    text(s, Inches(0.5), Inches(top + 0.04), IMG_W - Inches(0.3), Inches(7.5 - top - 0.3), lines)
    # 오른쪽: 화면 설명 / 조작 / 구현 요청
    box(s, X2, Inches(0.92), W2, Inches(6.38), fill=WHITE, line=RGBColor(0xB8, 0xC0, 0xCC))
    parts = [('화면 설명', mm.get('화면 설명'), NAVY), ('조작·피드백', mm.get('조작'), NAVY), ('구현 요청', mm.get('구현 요청'), ORANGE)]
    if not mm.get('화면 설명'):
        missing.append(f"{sh['id']} {sh['state']}")
    body = []
    for h, v, col in parts:
        if not v and h != '화면 설명':
            continue
        body.append([(h, {'bold': True, 'size': 13, 'color': col})])
        for ln in (v if isinstance(v, list) else [v or '(작성 필요)']):
            body.append([(ln, {'size': 11.5, 'color': GRAY if not v else NAVY})])
        body.append([('', {'size': 6})])
    text(s, X2 + Inches(0.12), Inches(1.0), W2 - Inches(0.24), Inches(6.2), body)

total = len(prs.slides._sldIdLst)
for k, sl in enumerate(prs.slides, 1):
    for sp in sl.shapes:
        if sp.has_text_frame and sp.text_frame.text.endswith(' / '):
            r = sp.text_frame.paragraphs[0].runs[0]
            r.text = f'{k} / {total}'
prs.save(OUT)
print('저장:', os.path.basename(OUT), f'슬라이드 {total}장', '· 메모:', os.path.basename(memo_path) if memo_path else '없음')
if missing:
    print(f'화면 설명이 빈 장면 {len(missing)}곳:', ', '.join(missing[:12]) + (' …' if len(missing) > 12 else ''))

# ---------------------------------------------------------------- 스토리보드 메모 형식(<html 이름>_스토리보드.json)
# {
#   "담당": "조창현 (○○중학교)",
#   "업체에 전하는 말": ["모든 차시 공통 사항이나 이 차시에서 꼭 지켜 줄 것", "..."],
#   "정의": [ {"낱말": "소인수분해", "충남대": "충남대 어휘목록 정의", "화면": "화면에 보이는 명사형 정의",
#             "내레이션": "성우가 읽는 문장", "변형": true, "까닭": "왜 바꿨는지", "대사 id": ["m3_4", "m3_read"]} ],
#   "검토 반영 근거": "2주차 검토(11/16~21, 장미정·김수철)",
#   "검토 반영": [ {"화면": "3-1", "의견": "검토 의견 요약", "반영": "어떻게 고쳤는지"} ],
#   "화면": {
#     "mean1":   {"화면 설명": ["#1 …", "#2 …"], "구현 요청": "html 틀로는 안 되었지만 이렇게 만들어 주세요"},
#     "mean1#5": {"화면 설명": "이 컷에만 붙는 설명"},          ← 컷 번호
#     "click6@‘소인수’ 팝업": {"화면 설명": "…"},                ← 장면 상태 이름(슬라이드 머리의 ‘·’ 뒤 글)
#     "q1":      {"화면 설명": "…", "조작": ["정답: …", "기회 1번, 틀리면 …"]}
#   }
# }
