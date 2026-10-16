// CSV 읽기 (데이터 계약: docs/design/02-web-dashboard-design.md §4).
// 컬럼은 순서가 아니라 헤더 이름으로 찾는다. 숫자가 아닌 칸·빈 칸(batt_v, rpm은 시뮬레이션에서 빈 칸)은 null.
import Papa from 'papaparse';

export const REQUIRED = ['t_ms', 'qw', 'qx', 'qy', 'qz'];
const NUMERIC = ['t_ms', 'phi', 'theta', 'psi', 'qw', 'qx', 'qy', 'qz', 'wx', 'wy', 'wz',
  'servo1', 'servo2', 'servo3', 'servo4', 'throttle', 'batt_v', 'rpm', 'reward'];

function num(v) {
  if (v === undefined || v === null || String(v).trim() === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

// text: CSV 문자열. 돌려주는 값: { rows, missing, skipped }
export function parseLog(text) {
  const out = Papa.parse(text, { header: true, skipEmptyLines: true, transformHeader: (h) => h.trim() });
  const fields = out.meta.fields ?? [];
  const missing = REQUIRED.filter((c) => !fields.includes(c));
  const rows = [];
  let skipped = 0;
  for (const raw of out.data) {
    const row = { source: raw.source ?? null, mode: raw.mode ?? null };
    for (const c of NUMERIC) row[c] = num(raw[c]);
    if (REQUIRED.some((c) => row[c] === null)) { skipped += 1; continue; }
    rows.push(row);
  }
  rows.sort((a, b) => a.t_ms - b.t_ms);
  return { rows, missing, skipped };
}
