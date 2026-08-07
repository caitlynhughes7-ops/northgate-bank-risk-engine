const PERIOD = '202409';
const SOURCES = {
  expected: '../data/expected/ecl_by_segment_' + PERIOD + '.csv',
  output:   '../data/output/ecl_by_segment_' + PERIOD + '.csv',
};
const SEG_LABEL = {
  RETAIL_MORTGAGE: 'Home mortgages',
  BTL_MORTGAGE: 'Landlord mortgages',
  PERSONAL_LOAN: 'Personal loans',
  CREDIT_CARD: 'Credit cards',
  OVERDRAFT: 'Overdrafts',
  SME_TERM: 'Small business loans',
};

// The three IFRS 9 stages, named by what they mean rather than numbered.
const STAGE_LABEL = {
  1: 'Performing',
  2: 'On the watchlist',
  3: 'In default',
};

const TOLERANCE = 0.01;
const withinTolerance = d => d !== null && Math.abs(d) <= TOLERANCE + 1e-9;

const gbp = n => '\u00a3' + Number(n).toLocaleString('en-GB', {maximumFractionDigits: 0});
const pct = n => (100 * Number(n)).toFixed(2) + '%';

// Variances are pennies, so they need full precision rather than gbp()'s rounding.
const variance = n => (n < 0 ? '\u2212\u00a3' : '\u00a3') +
  Math.abs(n).toLocaleString('en-GB', {minimumFractionDigits: 2, maximumFractionDigits: 2});

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
  if (!res.ok) {
    const which = kind === 'output' ? 'new' : 'old';
    throw new Error('The ' + which + " engine's figures could not be loaded from " +
      SOURCES[kind] + ' (' + res.status + ').');
  }
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
  if (b) {
    const legend = document.createElement('p');
    legend.className = 'legend';
    legend.innerHTML = '<span class="key"></span> The old engine' +
      '<span class="key alt"></span> The new engine';
    el.appendChild(legend);
  }
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
    ? ['Type of lending', 'Credit condition', 'Loans', 'Lending', 'Lending difference',
       'Provision, old', 'Provision, new', 'Provision difference', 'Result']
    : ['Type of lending', 'Credit condition', 'Loans', 'Lending', 'Provision', 'Provision rate'];
  thead.innerHTML = '<tr>' + cols.map(c => '<th>' + c + '</th>').join('') + '</tr>';

  const key = r => r.SEGMENT + '|' + r.STAGE;
  const om = other ? new Map(other.map(r => [key(r), r])) : null;

  tbody.innerHTML = rows.map(r => {
    const label = (SEG_LABEL[r.SEGMENT] || r.SEGMENT);
    const stage = (STAGE_LABEL[r.STAGE] || r.STAGE);
    if (!om) {
      return '<tr><td>' + label + '</td><td>' + stage + '</td><td>' +
        r.N_EXPOSURES + '</td><td>' + gbp(r.TOTAL_EAD) + '</td><td>' +
        gbp(r.TOTAL_ECL) + '</td><td>' + pct(r.COVERAGE) + '</td></tr>';
    }
    const o = om.get(key(r));
    const nv = o ? o.TOTAL_ECL : null;
    const diff = nv === null ? null : nv - r.TOTAL_ECL;
    const eadDiff = o ? o.TOTAL_EAD - r.TOTAL_EAD : null;
    const ok = !!o && withinTolerance(diff) && withinTolerance(eadDiff);
    return '<tr><td>' + label + '</td><td>' + stage + '</td><td>' +
      r.N_EXPOSURES + '</td><td>' + gbp(r.TOTAL_EAD) + '</td><td>' +
      (eadDiff === null ? '&mdash;' : variance(eadDiff)) + '</td><td>' +
      gbp(r.TOTAL_ECL) + '</td><td>' + (nv === null ? '&mdash;' : gbp(nv)) + '</td><td>' +
      (diff === null ? '&mdash;' : variance(diff)) + '</td><td class="' +
      (ok ? 'pass">agrees' : 'fail">differs') + '</td></tr>';
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
      const pairs = legacy.map(r => [r, migrated.find(x => x.SEGMENT === r.SEGMENT && x.STAGE === r.STAGE)]);
      const matched = pairs.filter(([r, o]) => o &&
        withinTolerance(o.TOTAL_ECL - r.TOTAL_ECL) &&
        withinTolerance(o.TOTAL_EAD - r.TOTAL_EAD)).length;
      const eclExact = pairs.filter(([r, o]) => o && o.TOTAL_ECL === r.TOTAL_ECL).length;
      status.innerHTML = matched === n
        ? '<span class="pass">The two engines agree: all ' + matched + ' of ' + n +
          ' rows are within the agreed £' + TOLERANCE.toFixed(2) + ' tolerance on both provision and lending' +
          (eclExact === n ? ', and the provision is identical to the penny in every row' : '') + '.</span>'
        : '<span class="fail">The two engines disagree: only ' + matched + ' of ' + n +
          ' rows are within the agreed tolerance.</span>';
    } else {
      const rows = await load(mode);
      kpis(rows);
      chart(rows, null);
      grid(rows, null);
      status.textContent = (mode === 'output' ? 'The new engine' : 'The old engine') +
        ', read from ' + SOURCES[mode];
    }
  } catch (e) {
    status.innerHTML = '<span class="fail">' + e.message + '</span>';
  }
}

document.getElementById('source').addEventListener('change', render);
render();
