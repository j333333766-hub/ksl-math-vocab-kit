# 스토리라인 pptx: storyline_capture.mjs가 찍은 화면 → 한 화면 한 슬라이드
#   python storyline_pptx.py "차시 html 경로" ["담당 선생님 (학교)"]  →  html 옆 <html 이름>.pptx (html과 같은 이름)
import json, os, re, sys
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.oxml.ns import qn

SRC = os.path.abspath(sys.argv[1])
BASE = os.path.splitext(os.path.basename(SRC))[0]
SL = os.path.join(os.path.dirname(SRC), '스토리라인_임시')
OUT = os.path.join(os.path.dirname(SRC), BASE + '.pptx')   # 교수님 규칙(11/3): html과 pptx는 같은 이름
WHO = sys.argv[2] if len(sys.argv) > 2 else ''
FONT = '맑은 고딕'
NAVY, TEAL, GRAY, LIGHT, ORANGE = RGBColor(0x18, 0x36, 0x4A), RGBColor(0x3D, 0xBB, 0x9F), RGBColor(0x6B, 0x72, 0x80), RGBColor(0xF3, 0xF5, 0xF8), RGBColor(0xE8, 0x7A, 0x1E)

m = json.load(open(os.path.join(SL, 'manifest.json'), encoding='utf-8'))
shots = m['shots']
NAME = {x['id']: x.get('name') or x['id'] for x in shots}

# 같은 화면의 앞 컷에서 이미 나온 대사는 빼기(단계 코드가 앞 대사를 이어 기다리는 경우)
prev = {}
for s in shots:
    seen = prev.get(s['id'], set())
    rest = [l for l in s['lines'] if l.get('id') not in seen]
    s['show'] = rest if rest else s['lines']
    prev[s['id']] = seen | {l.get('id') for l in s['lines']}

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


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
            f = r.font
            f.name = FONT
            f.size = Pt(st.get('size', size))
            f.bold = st.get('bold', bold)
            f.color.rgb = st.get('color', color)
            rpr = r._r.get_or_add_rPr()  # 한글 글꼴도 맑은 고딕으로
            for tag in ('a:ea', 'a:cs'):
                el = rpr.find(qn(tag))
                if el is None:
                    el = rpr.makeelement(qn(tag), {})
                    rpr.append(el)
                el.set('typeface', FONT)
    return tb


def box(slide, x, y, w, h, fill=None, line=None, dash=False, shape=MSO_SHAPE.RECTANGLE):
    s = slide.shapes.add_shape(shape, x, y, w, h)
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid(); s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line; s.line.width = Pt(1.25)
        if dash:
            s.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    s.shadow.inherit = False
    return s


total = len(shots)
MODS = ['인트로', '오늘의 어휘', '뜻 알아보기', '교과서 맛보기', '연습하기', '정리하기', '아웃트로']

# 1) 표지
s = prs.slides.add_slide(BLANK)
box(s, 0, 0, prs.slide_width, Inches(7.5), fill=LIGHT)
box(s, 0, 0, Inches(0.35), Inches(7.5), fill=TEAL)
text(s, Inches(0.9), Inches(1.5), Inches(11.5), Inches(0.6), '이주배경 학생 교과 적응 수학 한국어 어휘 콘텐츠', size=18, color=GRAY)
text(s, Inches(0.9), Inches(2.1), Inches(11.5), Inches(1.2), BASE.replace('_', ' ') + ' — 화면 스토리라인', size=36, bold=True)
text(s, Inches(0.9), Inches(4.3), Inches(11.5), Inches(2.4), [
    f'· 화면 {total}장 — 모듈 7개의 장면(컷)과 활동한 뒤의 모습, 낱말 팝업까지 순서대로 담았습니다.',
    '· 슬라이드마다 왼쪽은 실제 화면, 아래는 그 장면의 대사·내레이션, 오른쪽은 검토 의견을 적는 칸입니다.',
    f'· 소리·움직임은 같은 폴더의 {BASE}.html 을 열어 확인할 수 있습니다.',
], size=15, color=NAVY)
text(s, Inches(0.9), Inches(6.7), Inches(11.5), Inches(0.4), WHO, size=13, color=GRAY)

# 2) 흐름 한눈에
s = prs.slides.add_slide(BLANK)
text(s, Inches(0.5), Inches(0.3), Inches(12), Inches(0.6), '학습 흐름 한눈에 보기', size=26, bold=True)
rows = []
first = {}
for i, sh in enumerate(shots):
    first.setdefault(sh['id'], i)
groups = []
for sh in shots:
    if not groups or groups[-1]['id'] != sh['id']:
        groups.append({'id': sh['id'], 'mod': sh['mod'], 'sub': sh['sub'], 'n': 0, 'start': shots.index(sh)})
    groups[-1]['n'] += 1
tbl = s.shapes.add_table(len(groups) + 1, 5, Inches(0.5), Inches(1.05), Inches(12.3), Inches(6.1)).table
for c, (w, h) in enumerate(zip([2.6, 1.0, 5.4, 1.5, 1.8], ['모듈', '화면', '내용', '장면 수', '슬라이드'])):
    tbl.columns[c].width = Inches(w)
    tbl.cell(0, c).text = h
for r, g in enumerate(groups, 1):
    vals = [f"{g['mod']}. {MODS[g['mod'] - 1]}", g['sub'] or '-', NAME.get(g['id'], g['id']), str(g['n']), f"{g['start'] + 3}~{g['start'] + 2 + g['n']}" if g['n'] > 1 else str(g['start'] + 3)]
    for c, v in enumerate(vals):
        tbl.cell(r, c).text = v
for r in range(len(groups) + 1):
    tbl.rows[r].height = Emu(int(Inches(6.1) / (len(groups) + 1)))
    for c in range(5):
        cell = tbl.cell(r, c)
        cell.margin_top = cell.margin_bottom = Emu(20000)
        for p in cell.text_frame.paragraphs:
            for run in p.runs:
                run.font.size = Pt(11.5 if r else 12)
                run.font.name = FONT
                run.font.bold = r == 0
                rpr = run._r.get_or_add_rPr()
                el = rpr.find(qn('a:ea'))
                if el is None:
                    el = rpr.makeelement(qn('a:ea'), {}); rpr.append(el)
                el.set('typeface', FONT)

# 3) 화면마다 한 장
IMG_W = Inches(8.85)
for k, sh in enumerate(shots, 1):
    s = prs.slides.add_slide(BLANK)
    box(s, 0, 0, prs.slide_width, Inches(0.72), fill=NAVY)
    head = [(f"모듈 {sh['mod']} · {MODS[sh['mod'] - 1]}", {'bold': True, 'color': RGBColor(255, 255, 255), 'size': 16}),
            (f"   화면 {sh['mod']}-{sh['sub'].split('/')[0] if sh['sub'] else ''} {NAME.get(sh['id'], sh['id'])}", {'color': RGBColor(0xDD, 0xE6, 0xEE), 'size': 15}),
            (f"   ·  {sh['state']}", {'color': RGBColor(0xF9, 0xB2, 0x33), 'size': 15, 'bold': True})]
    text(s, Inches(0.35), Inches(0.12), Inches(11), Inches(0.5), [head])
    text(s, Inches(11.3), Inches(0.16), Inches(1.75), Inches(0.45), f'{k + 2} / {total + 2}', size=13, color=RGBColor(0xDD, 0xE6, 0xEE), align=PP_ALIGN.RIGHT)
    # 화면 (캡처 아래쪽 빈 띠는 잘라 낸다)
    pic = s.shapes.add_picture(os.path.join(SL, 'shots', sh['file']), Inches(0.35), Inches(0.92), width=IMG_W)
    pic.crop_bottom = 0.105
    pic.height = int(pic.height * (1 - 0.105))
    pic.line.color.rgb = RGBColor(0xD5, 0xDA, 0xE1); pic.line.width = Pt(0.75)
    top = 0.92 + pic.height / 914400 + 0.15
    # 대사·내레이션
    box(s, Inches(0.35), Inches(top), IMG_W, Inches(7.5 - top - 0.25), fill=LIGHT)
    lines = [[('대사·내레이션', {'bold': True, 'size': 12, 'color': TEAL})]]
    if sh['show']:
        for l in sh['show']:
            lines.append([(f"{l['who']}  ", {'bold': True, 'size': 13}), (l['text'], {'size': 13})])
    else:
        lines.append([('(대사 없음 — 화면 조작·활동 장면)', {'size': 12, 'color': GRAY})])
    text(s, Inches(0.5), Inches(top + 0.05), IMG_W - Inches(0.3), Inches(7.5 - top - 0.35), lines)
    # 검토 의견 칸
    x0 = Inches(9.4)
    box(s, x0, Inches(0.92), Inches(3.6), Inches(6.33), fill=RGBColor(255, 255, 255), line=RGBColor(0xB8, 0xC0, 0xCC), dash=True)
    text(s, x0 + Inches(0.15), Inches(1.0), Inches(3.3), Inches(0.4), '검토 의견', size=14, bold=True, color=ORANGE)
    text(s, x0 + Inches(0.15), Inches(1.4), Inches(3.3), Inches(5.7), '', size=12)

prs.save(OUT)
print('저장:', os.path.basename(OUT), f'슬라이드 {len(prs.slides._sldIdLst)}장')
