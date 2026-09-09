// cuts.json → cards/epN/cut_XX.png  (1920x1080, 흰 배경·붉은 강조, 자막 포함)
// 사용: NODE_PATH=/opt/node22/lib/node_modules node scripts/make_cards.js work/ep1/cuts.json cards/ep1
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path');
const [,, cutsPath, outDir] = process.argv;
const cuts = JSON.parse(fs.readFileSync(cutsPath, 'utf8'));
fs.mkdirSync(outDir, { recursive: true });
const ROOT = path.resolve(__dirname, '..');
function esc(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
function emph(text, word){ if(!word || word==='(없음)') return esc(text); return esc(text).split(esc(word)).join(`<span class="r">${esc(word)}</span>`); }
function bigNumber(screen){ const m = screen.match(/["“]([^"”]{1,12})["”]/); return m ? m[1] : null; }
function html(c){
  const chart = c.chart ? path.join(ROOT, 'charts', 'light', fs.readdirSync(path.join(ROOT,'charts','light')).find(f=>f.startsWith(c.chart+'_')) || '') : null;
  const big = bigNumber(c.screen);
  let body;
  if (chart && fs.existsSync(chart)) body = `<img class="chart" src="data:image/png;base64,${fs.readFileSync(chart).toString('base64')}">`;
  else if (c.emph && /[\d%조원억]/.test(c.emph)) body = `<div class="num">${esc(c.emph)}</div>`;
  else if (big) body = `<div class="num small">${esc(big)}</div>`;
  else body = `<div class="ph"><div class="word">${esc(c.emph && c.emph!=='(없음)' ? c.emph : '')}</div><div class="desc">${esc(c.screen)}</div><div class="tag">AI 클립 자리 · ${esc(c.prompt.slice(0,90))}</div></div>`;
  return `<!doctype html><meta charset="utf-8"><style>
  @font-face{font-family:NK;src:url(file:///root/.fonts/PbyxFmXiEBPT4ITbgNA5Cgms3VYcOA-vvnIzzkM1eLQ.ttf)}
  body{margin:0;width:1920px;height:1080px;background:#f4f4f2;font-family:"Noto Sans KR",NK,sans-serif;color:#1a1a19;overflow:hidden;position:relative}
  .top{position:absolute;left:80px;top:60px;font-size:30px;color:#8a8a86;letter-spacing:2px}
  .stage{position:absolute;left:0;right:0;top:130px;bottom:260px;display:flex;align-items:center;justify-content:center}
  .num{font-size:280px;font-weight:900;color:#e03a2f;letter-spacing:-6px}
  .num.small{font-size:160px;color:#1a1a19}
  .ph{text-align:center;max-width:1500px}.word{font-size:150px;font-weight:900;color:#1a1a19;letter-spacing:-3px;line-height:1.1}.desc{margin-top:30px;font-size:40px;color:#6b6b68;line-height:1.5}.tag{margin-top:26px;font-size:24px;color:#b5b5b2;border:2px dashed #c9c9c6;border-radius:12px;padding:10px 20px;display:inline-block}
  .chart{max-height:100%;max-width:92%;border-radius:12px}
  .sub{position:absolute;left:120px;right:120px;bottom:60px;text-align:center;font-size:56px;font-weight:900;line-height:1.4;color:#fff;-webkit-text-stroke:9px #000;paint-order:stroke fill;text-shadow:0 4px 10px rgba(0,0,0,.35)}
  .sub .r{color:#ff3b30}
  .bar{position:absolute;left:0;right:0;bottom:0;height:16px;background:#e03a2f}
  </style><body>
  
  <div class="stage">${body}</div>
  <div class="sub">${emph(c.narration, c.emph)}</div><div class="bar"></div></body>`;
}
(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  for (const c of cuts) {
    await page.setContent(html(c), { waitUntil: 'load' });
    await page.screenshot({ path: path.join(outDir, `cut_${String(c.n).padStart(2,'0')}.png`) });
  }
  await browser.close(); console.log('cards:', cuts.length);
})();
