const DATA_URL = './data/ownership_above1_all.csv';
let rows = [];
let filteredTickers = [];

const $ = (id) => document.getElementById(id);
const fmt = new Intl.NumberFormat('id-ID');
const pctFmt = new Intl.NumberFormat('id-ID', {maximumFractionDigits: 2});

function parseCSV(text) {
  const out = [];
  let row = [], cur = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i], n = text[i + 1];
    if (c === '"' && q && n === '"') { cur += '"'; i++; }
    else if (c === '"') q = !q;
    else if (c === ',' && !q) { row.push(cur); cur = ''; }
    else if ((c === '\n' || c === '\r') && !q) {
      if (c === '\r' && n === '\n') i++;
      row.push(cur); cur = '';
      if (row.some(v => v.trim() !== '')) out.push(row);
      row = [];
    } else cur += c;
  }
  if (cur || row.length) { row.push(cur); out.push(row); }
  const headers = out.shift().map(h => h.trim());
  return out.map(r => Object.fromEntries(headers.map((h, i) => [h, (r[i] ?? '').trim()])));
}

function normalize(records) {
  return records.map(r => ({
    date: r.date || r.Date || r.tanggal || '',
    share_code: (r.share_code || r.code || r.kode || '').toUpperCase(),
    issuer_name: r.issuer_name || r.company_name || r.nama_emiten || '',
    investor_name: r.investor_name || r.shareholder_name || r.pemegang_saham || '',
    investor_type: r.investor_type || '',
    local_foreign: r.local_foreign || '',
    nationality: r.nationality || '',
    domicile: r.domicile || '',
    total_holding_shares: Number(String(r.total_holding_shares || r.holding || r.shares || '0').replace(/[^0-9.-]/g,'')) || 0,
    percentage: Number(String(r.percentage || r.percent || r.persentase || '0').replace('%','').replace(',','.')) || 0
  })).filter(r => r.date && r.share_code && r.percentage > 0);
}

function dateKey(d) {
  const m = {Jan:0,Feb:1,Mar:2,Apr:3,May:4,Jun:5,Jul:6,Aug:7,Sep:8,Oct:9,Nov:10,Dec:11};
  const p = String(d).replace(/\s+/g,'-').split('-');
  if (p.length === 3 && m[p[1]] !== undefined) return new Date(Number(p[2]), m[p[1]], Number(p[0])).getTime();
  const t = Date.parse(d); return Number.isFinite(t) ? t : 0;
}

function getDates() { return [...new Set(rows.map(r => r.date))].sort((a,b)=>dateKey(a)-dateKey(b)); }
function getTickers() {
  const map = new Map();
  rows.forEach(r => { if (!map.has(r.share_code)) map.set(r.share_code, r.issuer_name); });
  return [...map.entries()].map(([code,name])=>({code,name})).sort((a,b)=>a.code.localeCompare(b.code));
}
function byTickerDate(code, date) { return rows.filter(r => r.share_code === code && r.date === date); }
function stats(records) {
  const ge1 = records.filter(r => r.percentage >= 1);
  const ge5 = records.filter(r => r.percentage >= 5);
  return {count1: ge1.length, count5: ge5.length, pct1: ge1.reduce((s,r)=>s+r.percentage,0), pct5: ge5.reduce((s,r)=>s+r.percentage,0)};
}
function deltaText(series, key) {
  if (series.length < 2) return 'butuh >1 tanggal';
  const d = series.at(-1)[key] - series.at(-2)[key];
  return `${d >= 0 ? '+' : ''}${d} vs snapshot sebelumnya`;
}

function initControls() {
  const dates = getDates();
  $('dateSelect').innerHTML = dates.map(d => `<option value="${d}">${d}</option>`).join('');
  $('dateSelect').value = dates.at(-1) || '';
  updateTickerOptions();
}

function updateTickerOptions() {
  const q = $('tickerSearch').value.trim().toUpperCase();
  filteredTickers = getTickers().filter(t => !q || t.code.includes(q) || t.name.toUpperCase().includes(q));
  $('tickerSelect').innerHTML = filteredTickers.slice(0, 300).map(t => `<option value="${t.code}">${t.code} — ${t.name}</option>`).join('');
  if (filteredTickers.length) $('tickerSelect').value = filteredTickers[0].code;
  render();
}

function escapeHTML(x) { return String(x).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }

function render() {
  const code = $('tickerSelect').value || getTickers()[0]?.code;
  const date = $('dateSelect').value || getDates().at(-1);
  if (!code || !date) return;
  const dates = getDates();
  const series = dates.map(d => ({date:d, ...stats(byTickerDate(code, d))}));
  const current = stats(byTickerDate(code, date));
  $('mCount1').textContent = current.count1;
  $('mCount5').textContent = current.count5;
  $('mPct1').textContent = pctFmt.format(current.pct1) + '%';
  $('mPct5').textContent = pctFmt.format(current.pct5) + '%';
  $('mDelta1').textContent = deltaText(series, 'count1');
  $('mDelta5').textContent = deltaText(series, 'count5');
  const selected = getTickers().find(t=>t.code===code);
  $('chartCaption').textContent = `${code} — ${selected?.name || ''}`;
  drawLineChart(series);
  renderTables(code, date);
  drawDonut(byTickerDate(code, date));
}

function drawLineChart(series) {
  const svg = $('lineChart'), W=900,H=360,l=58,r=24,t=28,b=58, iw=W-l-r, ih=H-t-b;
  const maxY = Math.max(5, ...series.flatMap(s=>[s.count1,s.count5]));
  const x = i => l + (series.length === 1 ? iw/2 : i * iw/(series.length-1));
  const y = v => t + ih - (v/maxY)*ih;
  const path = key => series.map((s,i)=>`${i?'L':'M'}${x(i)},${y(s[key])}`).join(' ');
  if (!series.length) { svg.innerHTML = '<text x="450" y="180" class="empty">Tidak ada data</text>'; return; }
  const grid = [0,.25,.5,.75,1].map(p=>`<line class="gridline" x1="${l}" x2="${W-r}" y1="${t+ih*p}" y2="${t+ih*p}"/><text class="chart-label" x="12" y="${t+ih*p+4}">${Math.round(maxY*(1-p))}</text>`).join('');
  svg.innerHTML = `${grid}<line class="axis" x1="${l}" y1="${H-b}" x2="${W-r}" y2="${H-b}"/><line class="axis" x1="${l}" y1="${t}" x2="${l}" y2="${H-b}"/><path class="line1" d="${path('count1')}"/><path class="line5" d="${path('count5')}"/>${series.map((s,i)=>`<circle class="dot1" cx="${x(i)}" cy="${y(s.count1)}" r="5"><title>${s.date}: ≥1% ${s.count1}</title></circle><circle class="dot5" cx="${x(i)}" cy="${y(s.count5)}" r="5"><title>${s.date}: ≥5% ${s.count5}</title></circle><text class="chart-label" x="${x(i)-36}" y="330">${s.date}</text>`).join('')}<circle class="dot1" cx="650" cy="25" r="6"/><text class="legend" x="664" y="30">≥1%</text><circle class="dot5" cx="735" cy="25" r="6"/><text class="legend" x="749" y="30">≥5%</text>`;
}

function drawDonut(records) {
  const svg = $('donutChart');
  const local = records.filter(r => r.local_foreign.toUpperCase()==='L').reduce((s,r)=>s+r.percentage,0);
  const asing = records.filter(r => r.local_foreign.toUpperCase()==='A').reduce((s,r)=>s+r.percentage,0);
  const total = Math.max(local+asing, 0.0001), lp = local/total, ap = asing/total;
  const c=2*Math.PI*78;
  svg.innerHTML = `<circle cx="210" cy="135" r="78" fill="none" stroke="#243752" stroke-width="34"/><circle cx="210" cy="135" r="78" fill="none" stroke="#49d6a7" stroke-width="34" stroke-dasharray="${c*lp} ${c}" transform="rotate(-90 210 135)"/><circle cx="210" cy="135" r="78" fill="none" stroke="#6aa7ff" stroke-width="34" stroke-dasharray="${c*ap} ${c}" stroke-dashoffset="-${c*lp}" transform="rotate(-90 210 135)"/><text x="210" y="132" text-anchor="middle" class="legend">Lokal</text><text x="210" y="158" text-anchor="middle" class="chart-label">${pctFmt.format(local)}%</text><circle cx="105" cy="270" r="7" fill="#49d6a7"/><text x="120" y="275" class="legend">Lokal ${pctFmt.format(local)}%</text><circle cx="250" cy="270" r="7" fill="#6aa7ff"/><text x="265" y="275" class="legend">Asing ${pctFmt.format(asing)}%</text>`;
}

function renderTables(code, date) {
  const threshold = Number($('thresholdSelect').value);
  const records = byTickerDate(code, date).sort((a,b)=>b.percentage-a.percentage);
  $('holdersTable').innerHTML = records.map(r => `<tr><td>${escapeHTML(r.investor_name)}</td><td><span class="badge">${escapeHTML(r.investor_type)}</span></td><td>${escapeHTML(r.local_foreign || '-')}</td><td class="num">${fmt.format(r.total_holding_shares)}</td><td class="num">${pctFmt.format(r.percentage)}%</td></tr>`).join('');
  const grouped = new Map();
  rows.filter(r=>r.date===date && r.percentage>=threshold).forEach(r => {
    const g = grouped.get(r.share_code) || {code:r.share_code, name:r.issuer_name, count:0, pct:0};
    g.count++; g.pct += r.percentage; grouped.set(r.share_code, g);
  });
  $('rankingTable').innerHTML = [...grouped.values()].sort((a,b)=>b.count-a.count || b.pct-a.pct).slice(0,40).map(g=>`<tr><td><strong>${g.code}</strong></td><td>${escapeHTML(g.name)}</td><td class="num">${g.count}</td><td class="num">${pctFmt.format(g.pct)}%</td></tr>`).join('');
}

async function loadDefault() {
  const text = await fetch(DATA_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.text(); });
  rows = normalize(parseCSV(text));
  initControls();
  render();
}

$('tickerSearch').addEventListener('input', updateTickerOptions);
$('tickerSelect').addEventListener('change', render);
$('thresholdSelect').addEventListener('change', render);
$('dateSelect').addEventListener('change', render);
$('csvUpload').addEventListener('change', async (e) => {
  for (const f of e.target.files) rows.push(...normalize(parseCSV(await f.text())));
  rows = rows.filter((r, i, a) => i === a.findIndex(x => x.date===r.date && x.share_code===r.share_code && x.investor_name===r.investor_name && x.percentage===r.percentage));
  initControls();
});

loadDefault().catch(err => {
  document.body.insertAdjacentHTML('afterbegin', `<div style="padding:14px;background:#7a2d2d;color:white">Gagal load data: ${escapeHTML(err.message)}. Jalankan lewat server lokal, bukan file://</div>`);
});
