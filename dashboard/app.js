const PERIOD = '202409';
const SOURCES = {
  expected: '../data/expected/ecl_by_segment_' + PERIOD + '.csv',
  output:   '../data/output/ecl_by_segment_' + PERIOD + '.csv',
};
const SEG_LABEL = {
  RETAIL_MORTGAGE: 'Retail mortgages',
  BTL_MORTGAGE: 'Buy to let',
  PERSONAL_LOAN: 'Personal loans',
  CREDIT_CARD: 'Credit cards',
  OVERDRAFT: 'Overdrafts',
  SME_TERM: 'SME lending',
};

const gbp = n => '\u00a3' + Number(n).toLocaleString('en-GB', {maximumFractionDigits: 0});
const pct = n => (100 * Number(n)).toFixed(2) + '%';

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  const head = lines[0].split(',');
  return lines.slice(1).map(l => {
    const cells = l.split(',');
    const o = {};
    head.forEach((h, i) => { o[h] = cells[i]; });
    o.STAGE = Number(o.STAGE);
    o.N_EXPOSURES = Number(o.N_EXPOSURES);
    o.TOTAL_EAD = Number(o.TOTAL_EAD);
    o.TOTAL_ECL = Number(o.TOTAL_ECL);
    o.COVERAGE = Number(o.COVERAGE);
    return o;
  });
}

async function load(kind) {
  const res = await fetch(SOURCES[kind], {cache: 'no-store'});
  if (!res.ok) throw new Error(kind + ' not available (' + res.status + ')');
  return parseCsv(await res.text());
}

function kpis(rows) {
  const ead = rows.reduce((a, r) => a + r.TOTAL_EAD, 0);
  const ecl = rows.reduce((a, r) => a + r.TOTAL_ECL, 0);
  const s23 = rows.filter(r => r.STAGE >= 2).reduce((a, r) => a + r.TOTAL_EAD, 0);
  document.getElementById('kpi-ead').textContent = gbp(ead);
  document.getElementById('kpi-ecl').textContent = gbp(ecl);
  document.getElementById('kpi-cov').textContent = pct(ecl / ead);
  document.getElementById('kpi-s23').textContent = gbp(s23);
}

function bySegment(rows) {
  const m = new Map();
  rows.forEach(r => m.set(r.SEGMENT, (m.get(r.SEGMENT) || 0) + r.TOTAL_ECL));
  return [...m.entries()].sort((a, b) => b[1] - a[1]);
}

function chart(rows, other) {
  const el = document.getElementById('chart');
  el.innerHTML = '';
  const a = bySegment(rows);
  const b = other ? new Map(bySegment(other)) : null;
  const max = Math.max(...a.map(x => x[1]), ...(b ? [...b.values()] : [0]));
  a.forEach(([seg, v]) => {
    const row = document.createElement('div');
    row.className = 'row';
    row.innerHTML = '<span>' + (SEG_LABEL[seg] || seg) + '</span>' +
      '<span><span class="bar" style="width:' + (100 * v / max) + '%"></span></span>' +
      '<span class="val">' + gbp(v) + '</span>';
    el.appendChild(row);
    if (b && b.has(seg)) {
      const r2 = document.createElement('div');
      const v2 = b.get(seg);
      r2.className = 'row';
      r2.innerHTML = '<span></span>' +
        '<span><span class="bar alt" style="width:' + (100 * v2 / max) + '%"></span></span>' +
        '<span class="val">' + gbp(v2) + '</span>';
      el.appendChild(r2);
    }
  });
}

function grid(rows, other) {
  const thead = document.querySelector('#grid thead');
  const tbody = document.querySelector('#grid tbody');
  const cols = other
    ? ['Segment', 'Stage', 'Exposures', 'EAD', 'ECL (legacy)', 'ECL (migrated)', 'Variance', 'Status']
    : ['Segment', 'Stage', 'Exposures', 'EAD', 'ECL', 'Coverage'];
  thead.innerHTML = '<tr>' + cols.map(c => '<th>' + c + '</th>').join('') + '</tr>';

  const key = r => r.SEGMENT + '|' + r.STAGE;
  const om = other ? new Map(other.map(r => [key(r), r])) : null;

  tbody.innerHTML = rows.map(r => {
    const label = (SEG_LABEL[r.SEGMENT] || r.SEGMENT);
    if (!om) {
      return '<tr><td>' + label + '</td><td>' + r.STAGE + '</td><td>' +
        r.N_EXPOSURES + '</td><td>' + gbp(r.TOTAL_EAD) + '</td><td>' +
        gbp(r.TOTAL_ECL) + '</td><td>' + pct(r.COVERAGE) + '</td></tr>';
    }
    const o = om.get(key(r));
    const nv = o ? o.TOTAL_ECL : null;
    const diff = nv === null ? null : nv - r.TOTAL_ECL;
    const ok = diff !== null && Math.abs(diff) < 0.01;
    return '<tr><td>' + label + '</td><td>' + r.STAGE + '</td><td>' +
      r.N_EXPOSURES + '</td><td>' + gbp(r.TOTAL_EAD) + '</td><td>' +
      gbp(r.TOTAL_ECL) + '</td><td>' + (nv === null ? '&mdash;' : gbp(nv)) + '</td><td>' +
      (diff === null ? '&mdash;' : gbp(diff)) + '</td><td class="' +
      (ok ? 'pass">match' : 'fail">differs') + '</td></tr>';
  }).join('');
}

async function render() {
  const mode = document.getElementById('source').value;
  const status = document.getElementById('status');
  try {
    if (mode === 'compare') {
      const [legacy, migrated] = await Promise.all([load('expected'), load('output')]);
      kpis(migrated);
      chart(legacy, migrated);
      grid(legacy, migrated);
      const n = legacy.length;
      const matched = legacy.filter(r => {
        const o = migrated.find(x => x.SEGMENT === r.SEGMENT && x.STAGE === r.STAGE);
        return o && Math.abs(o.TOTAL_ECL - r.TOTAL_ECL) < 0.01;
      }).length;
      status.innerHTML = matched === n
        ? '<span class="pass">Parity: ' + matched + '/' + n + ' segment-stage cells match to the penny.</span>'
        : '<span class="fail">Parity: ' + matched + '/' + n + ' cells match.</span>';
    } else {
      const rows = await load(mode);
      kpis(rows);
      chart(rows, null);
      grid(rows, null);
      status.textContent = 'Source: ' + SOURCES[mode];
    }
  } catch (e) {
    status.innerHTML = '<span class="fail">' + e.message + '</span>';
  }
}

document.getElementById('source').addEventListener('change', render);
render();
