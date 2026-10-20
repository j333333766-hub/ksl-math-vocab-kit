// 영상 원본 공통 도우미. 각 html 이 draw(t)를 정의하고 start(draw, DUR)를 부른다. 도구/영상 만들기.ps1 이 1/30초마다 찍어 mp4 로 묶는다.
// 화면 메뉴와 겹치지 않게: 플랫폼이 영상 위에 위 막대(설정·다국어·지시문 띠·보상), 양옆 화살표, 아래 재생 막대를 얹는다(업체 SB 3쪽).
// 그래서 글자·인물은 SAFE 영역 안에만 둔다. 주소에 ?safe 를 붙이면 메뉴 자리를 빨갛게 덮어 확인할 수 있다.
const SAFE = { x0: 170, x1: 1750, y0: 175, y1: 905 };
const CHAR_DIR = document.currentScript.src.replace(/[^/]*$/, '') + '인물/';   // 도구/영상/인물/ (업체 SB 등장인물, 시안용 — 업체가 중학교용 인물로 바꾼다)
const $ = id => document.getElementById(id);
const P = (t, a, b) => Math.min(1, Math.max(0, (t - a) / (b - a)));
const out3 = x => 1 - Math.pow(1 - x, 3);
const back = x => { const c = 1.7; return x <= 0 ? 0 : 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
const mix = (a, b, k) => a + (b - a) * k;
const col = (c1, c2, k) => 'rgb(' + c1.map((v, i) => Math.round(mix(v, c2[i], k))).join(',') + ')';
function put(id, x, y, o = 1, s = 1, r = 0) { const e = $(id); e.style.transform = `translate(${x}px,${y}px) translate(-50%,-50%) scale(${s}) rotate(${r}deg)`; e.style.opacity = o; e.style.visibility = o > 0.001 ? 'visible' : 'hidden'; }
const pop = (t, a, d = 0.5) => { const k = P(t, a, a + d); return [out3(k), back(k) * 0.999 + 0.001]; };
const fadeIO = (t, a, b, d = 0.4) => out3(P(t, a, a + d)) * (1 - P(t, b - d, b));
const burst = (k, dx, dy) => [dx * out3(k), dy * out3(k) - Math.sin(Math.PI * k) * 40];
const bob = (t, a = 1) => Math.sin(t * 3) * 6 * a;   // 인물이 숨 쉬듯 살짝
const scene = (id, o) => { const e = $(id); e.style.opacity = o; e.style.display = o > 0.001 ? '' : 'none'; };
const INK = [29, 36, 51], PURPLE = [124, 58, 237], ORANGE = [245, 138, 31], TEAL = [13, 148, 136], BLUE = [37, 99, 235];
function strokeIn(id, d, t, a, dur = 0.6) { const e = $(id); e.setAttribute('d', d); const L = e.getTotalLength(); e.style.strokeDasharray = L; e.style.strokeDashoffset = L * (1 - out3(P(t, a, a + dur))); }
// 인물 그림 <img class="a ch" data-ch="10_이안(새 디자인)" style="height:560px">
document.querySelectorAll('img[data-ch]').forEach(im => { im.src = CHAR_DIR + im.dataset.ch + '.png'; });
if (location.search.includes('safe')) {
  const v = $('v'), z = (l, t, w, h) => { const d = document.createElement('div'); d.style.cssText = `position:absolute;left:${l}px;top:${t}px;width:${w}px;height:${h}px;background:rgba(255,0,0,.35);z-index:99;outline:2px solid red`; v.append(d); };
  z(0, 0, 1920, 150); z(0, 960, 1920, 120); z(0, 450, 130, 180); z(1790, 450, 130, 180);
  const s = document.createElement('div'); s.style.cssText = `position:absolute;left:${SAFE.x0}px;top:${SAFE.y0}px;width:${SAFE.x1 - SAFE.x0}px;height:${SAFE.y1 - SAFE.y0}px;outline:3px dashed #0a0;z-index:99`; v.append(s);
}
function start(draw, DUR) {
  window.draw = draw; window.DUR = DUR;
  const imgs = [...document.images].map(im => im.complete ? 0 : new Promise(r => { im.onload = im.onerror = r; }));
  window.ready = Promise.all([document.fonts.ready, ...imgs]);
  if (!location.search.includes('rec')) { window.ready.then(() => { const t0 = performance.now() - (parseFloat(location.hash.slice(1)) || 0) * 1000; const loop = () => { const t = (performance.now() - t0) / 1000; draw(Math.min(t, DUR)); if (t < DUR) requestAnimationFrame(loop); }; loop(); }); }
  else draw(0);
}
