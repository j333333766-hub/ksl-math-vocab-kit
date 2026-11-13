// 스토리라인용 화면 캡처: 차시 html의 모든 화면·컷·활동 후 상태·낱말 팝업을 찍고 대사를 붙인다.
//   node storyline_capture.mjs "차시 html 경로"  →  html 옆 스토리라인_임시/ (shots/*.jpg + manifest.json)
//   필요한 것: Node, Chrome, playwright-core (이 폴더에서 npm i playwright-core)
import fs from 'fs';
import path from 'path';
import os from 'os';
import { fileURLToPath, pathToFileURL } from 'url';
import { createRequire } from 'module';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.resolve(process.argv[2] || '');
if (!process.argv[2] || !fs.existsSync(SRC)) { console.log('차시 html 경로를 주세요'); process.exit(2); }
const OUT = path.join(path.dirname(SRC), '스토리라인_임시');
const SHOTS = path.join(OUT, 'shots');
const { chromium } = createRequire(path.join(HERE, 'x.js'))('playwright-core');

// 대사: html의 TTS 표에서 읽는다
const WHO = { nar: '성우', ian: '이안', anna: '안나', tch: '선생님', chorok: '초록이', chk: '초록이' };
const LINES = {};
const HTML = fs.readFileSync(SRC, 'utf8');
const t0 = HTML.indexOf('  const TTS = {'), ttsTab = HTML.slice(t0, HTML.indexOf('\n  };', t0));
for (const m of ttsTab.matchAll(/(\w+): \{ t: '([^']*)', r: '(\w+)'/g)) LINES[m[1]] = { who: WHO[m[3]] || m[3], text: m[2] };
// 문장 대사: 플레이어의 SENTS(id → clip) — 단계 코드가 SN.ans처럼 문장으로 부르는 대사도 찾는다
const SENT_CLIP = {};
for (const m of HTML.matchAll(/\{ id: '(\w+)', tag: '\w+', parts: .*?clip: '(\w+)' \}/g)) SENT_CLIP[m[1]] = m[2];
const said = (src) => {
  const ids = [...String(src).matchAll(/['"](\w+)['"]|SN\.(\w+)/g)].map((m) => m[1] || SENT_CLIP[m[2]]);
  return [...new Set(ids)].filter((id) => id && LINES[id]).map((id) => ({ id, ...LINES[id] }));
};

// 활동 화면의 데모 상태 이름
const DEMO = {
  live: '녹음하는 중', done: '녹음을 마친 뒤', seen: '세 낱말을 모두 본 뒤', open: '빈칸 고르기(한 번 틀린 뒤)', ask: '설명 두 개를 채운 뒤',
  fin: '빈칸을 모두 채운 뒤', wrong: '틀렸을 때', right: '맞혔을 때', sel: '낱말을 고른 상태', bad: '틀렸을 때', half: '두 개 확인한 뒤', hear: '첫 말풍선을 들을 때', one: '첫 문장을 녹음한 뒤(둘째 녹음 중)', dialog: '두 문장을 모두 녹음한 뒤', hint1: '힌트를 누른 뒤', wait: '쓴 글자를 확인하는 중', self: '스스로 확인하기', skip: '녹음을 건너뛴 뒤',
};
const DEMO_ARGS = { hear: [0] }; // 데모 함수에 넘길 값
const DEMO_PAGE = { 'rec1.done': '두 낱말을 모두 들은 뒤', 'click6.seen': '‘소인수’를 누른 뒤' }; // 화면마다 다른 이름
// 팝업: 화면에서 실제로 누를 수 있는 낱말(kw('키', …))만 찍는다(2026-11-13: 열리지 않는 옛 팝업은 찍지 않음)
const POPS = [...new Map([...HTML.matchAll(/kw\('(\w+)', '([^']+)'\)/g)].map((m) => [m[1], m[2]])).entries()];
const MODS = ['인트로', '오늘의 어휘', '뜻 알아보기', '교과서 맛보기', '연습하기', '정리하기', '아웃트로'];

// 캡처 훅에 쪽 목록·현재 화면을 내보내는 줄만 더한 임시 사본
const tmp = path.join(os.tmpdir(), `storyline_${Date.now()}.html`);
// 연습 문제 함수에 문제 정보를 남기는 줄도 더한다(정답·오답 때 나오는 말을 스토리보드에 적으려고, 2026-11-13)
const QHOOK = (s) => s
  .replace(/function listenQ\([^)]*\) \{/, (m) => m + ' (window.__QA = window.__QA || {})[arguments[0]] = { t: 1 };')
  .replace(/function blankQ\(cfg\) \{/, (m) => m + ' (window.__QA = window.__QA || {})[cfg.id] = { t: 2, full: cfg.full || [] };')
  .replace(/function writeQ\(cfg\) \{/, (m) => m + ' (window.__QA = window.__QA || {})[cfg.id] = { t: 3, ok: cfg.okClip, ans: cfg.ansClip };');
fs.writeFileSync(tmp, QHOOK(HTML).replace('window.__S = {', 'window.__PAGES = PAGES; window.__CUR = () => cur;\n  window.__S = {'));
// 주의: Node 24의 fs.rmSync는 한글 경로에서 프로그램이 죽는다(0xC0000409) → 파일을 하나씩 지운다
fs.mkdirSync(SHOTS, { recursive: true });
for (const x of fs.readdirSync(SHOTS)) fs.unlinkSync(path.join(SHOTS, x));

const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1.5 });
const errors = [];
page.on('pageerror', (e) => errors.push(e.message));
await page.goto(`${pathToFileURL(tmp).href}?shot`);
await page.waitForFunction(() => window.__S && document.fonts.status === 'loaded');
await page.waitForTimeout(800);

const pages = await page.evaluate(() => window.__S.pages);
const shots = [];
let n = 0;
async function snap(meta) {
  await page.waitForTimeout(450);
  const file = `${String(++n).padStart(3, '0')}.jpg`;
  await page.screenshot({ path: path.join(SHOTS, file), type: 'jpeg', quality: 88 });
  shots.push({ file, ...meta });
}

for (const [i, P] of pages.entries()) {
  const base = { page: i + 1, id: P.id, mod: P.m, modName: MODS[P.m - 1], sub: P.sub, kind: P.kind };
  const src = await page.evaluate((k) => {
    const p = window.__PAGES[k];
    return { name: p.name || '', steps: (p.steps || []).map((f) => f.toString()), other: Object.entries(p).filter(([key, v]) => typeof v === 'function' && key !== 'build').map(([, v]) => v.toString()).join('\n'), build: (p.build ? p.build.toString() : '') + ' ' + (p.ids || []).map((i) => `'${i}'`).join(' '), instr: p.instr ? p.instr[0] : '' };
  }, i);
  base.name = src.name || src.instr || '';
  if (P.steps) {
    for (let k = 0; k < P.steps; k++) {
      await page.evaluate(([a, b]) => window.__S.go(a, b), [i, k]);
      await snap({ ...base, state: `컷 ${k + 1}/${P.steps}`, lines: said(src.steps[k]) });
    }
  } else {
    await page.evaluate((a) => window.__S.go(a), i);
    const instr = src.instr ? [{ who: '지시문', text: src.instr }] : [];
    await snap({ ...base, state: '처음 화면', lines: [...instr, ...said(src.other + ' ' + (src.build.match(/( '\w+')+$/) || [''])[0]).filter((l) => !l.id.startsWith('i_'))] });
    // 활동 후 상태
    const keys = await page.evaluate(() => Object.keys((window.__CUR().ctx || {}).demo || {}));
    for (const key of keys) {
      await page.evaluate((a) => window.__S.go(a), i);
      try { await page.evaluate(([k, a]) => window.__S.demo(k, ...a), [key, DEMO_ARGS[key] || []]); } catch (e) { errors.push(`${P.id}.${key}: ${e.message}`); continue; }
      await snap({ ...base, state: DEMO_PAGE[`${P.id}.${key}`] || DEMO[key] || key, lines: [] });
    }
    // 낱말 팝업 (3-3 화면)
    if (P.id === 'click6') {
      for (const [kind, word] of POPS) {
        await page.evaluate((a) => window.__S.go(a), i);
        const last = await page.evaluate((kd) => window.__S.popup(kd, 99).then(() => true), kind).catch((e) => { errors.push(`popup ${kind}: ${e.message}`); return false; });
        if (!last) continue;
        await snap({ ...base, state: `‘${word}’ 팝업`, lines: Object.entries(LINES).filter(([id]) => id.startsWith(`p_${kind}_`) && HTML.includes(`play('${id}'`)).map(([id, l]) => ({ id, ...l })) });
      }
    }
  }
}
// 정답·오답 때 나오는 말(11/13 단톡방 김수철 교수: 내레이션에 들어가는 말은 스토리보드에도 넣는다)
//   문제마다 첫 장면(처음 화면)에 fb: [{ when, who, text, id }]를 붙이고, 처음 대사(lines)에서는 뺀다.
const QA = await page.evaluate(() => window.__QA || {});
// 틀에 정해진 반응 말: 대사 표에 없고 녹음으로만 들어 있는 차시(샘플 v6-5 등)도 있어 기본 문장을 둔다(화면 글과 같음)
for (const [id, text] of [['fb_ok', '참 잘했어요!'], ['fb_ans', '정답을 확인해 보세요.'], ['fb_write_retry', '다시 듣고 써 보세요.'], ['fb_write_unclear', '한 칸에 한 글자씩 크게 써 보세요.']]) if (!LINES[id]) LINES[id] = { who: '초록이', text };
const FL = (id, when) => (LINES[id] ? { id, when, ...LINES[id] } : null);
const FEEDBACK = (q) => (q.t === 1 ? [FL('fb_ok', '맞혔을 때'), FL('fb_ans', '틀렸을 때 (기회 1번을 다 써서 정답을 보여 줌)')]
  : q.t === 2 ? [FL('fb_ok', '맞혔을 때 (화면 글: ‘참 잘했어요!’ 뒤에 완성된 문장)'), FL('fb_ans', '틀렸을 때 (빈칸에 정답을 넣어 보여 줌)'), ...q.full.map((id) => FL(id, '틀렸을 때 이어서 (완성된 문장)'))]
  : [FL(q.ok, '맞혔을 때'), FL('fb_write_retry', '틀렸을 때 (기회가 남음, 3번까지)'), FL('fb_write_unclear', '글자를 알아보기 어려울 때'), FL(q.ans, '세 번 틀렸을 때 (칸에 연한 글자로 정답을 보여 줌)')]).filter(Boolean);
for (const id of Object.keys(QA)) {
  const first = shots.find((s) => s.id === id);
  if (first) { first.fb = FEEDBACK(QA[id]); first.lines = first.lines.filter((l) => !(l.id || '').startsWith('fb_')); }
}
await browser.close();
fs.unlinkSync(tmp);
fs.writeFileSync(path.join(OUT, 'manifest.json'), JSON.stringify({ source: path.basename(SRC), sourceTime: fs.statSync(SRC).mtime, shots, errors }, null, 1));
console.log(`화면 ${shots.length}장, 오류 ${errors.length}개`);
errors.forEach((e) => console.log(' !', e));
