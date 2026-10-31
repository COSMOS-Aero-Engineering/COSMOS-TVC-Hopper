// 실험 A 추력 곡선 CSV 읽기 (컬럼: data/README.md, 이슈 #244).
// 컬럼은 순서가 아니라 헤더 이름으로 찾는다. 화면에 쓰는 것은 throttle_pct, thrust_g, current_A 셋이다.
// 줄 번호는 파일의 실제 줄(1부터)이다. `#`로 시작하는 줄과 빈 줄은 읽지 않지만 줄 번호에는 센다.
// 쓰지 못한 줄은 조용히 버리지 않고 warnings에 줄 번호와 이유를 남긴다.
// 칸 안에 줄바꿈이 있는 따옴표 칸(notes)은 지원하지 않는다. 그런 줄은 칸 수 경고로 드러난다.
import Papa from 'papaparse';

export const REQUIRED = ['throttle_pct', 'thrust_g', 'current_A'];

// 빈 칸과 숫자가 아닌 칸은 null. Number('')는 0이라서 빈 칸을 따로 걸러야 한다.
function num(v) {
  if (v === undefined || v === null || String(v).trim() === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

// text: CSV 문자열. 돌려주는 값: { points, missing, warnings, dataLines }
//   points: [{ line, throttle_pct, thrust_g, current_A }] 스로틀 오름차순(같은 값은 파일 순서)
//   missing: 없는 필수 컬럼 이름. 하나라도 있으면 points는 비어 있다.
//   warnings: [{ line, message }]
//   dataLines: 읽으려고 시도한 데이터 줄 수(경고 줄 포함)
export function parseThrust(text) {
  const lines = text.replace(/^﻿/, '').split(/\r\n|\n|\r/);
  const warnings = [];
  let header = null;
  let headerLine = 0;
  const points = [];
  let dataLines = 0;

  for (let i = 0; i < lines.length; i += 1) {
    const lineNo = i + 1;
    const raw = lines[i];
    if (raw.trim() === '' || raw.trimStart().startsWith('#')) continue;
    const cells = Papa.parse(raw, { header: false }).data[0] ?? [];

    if (header === null) {
      header = cells.map((h) => h.trim());
      headerLine = lineNo;
      const missing = REQUIRED.filter((c) => !header.includes(c));
      if (missing.length) return { points: [], missing, warnings, dataLines: 0 };
      continue;
    }

    dataLines += 1;
    if (cells.length !== header.length) {
      warnings.push({ line: lineNo, message: `칸이 ${cells.length}개다(헤더 ${headerLine}줄은 ${header.length}개). 이 줄은 그리지 않았다.` });
      continue;
    }
    const row = {};
    const bad = [];
    for (const c of REQUIRED) {
      const cell = cells[header.indexOf(c)];
      row[c] = num(cell);
      if (row[c] === null) bad.push(`${c}=${cell.trim() === '' ? '(빈 칸)' : JSON.stringify(cell.trim())}`);
    }
    if (bad.length) {
      warnings.push({ line: lineNo, message: `숫자가 아닌 칸: ${bad.join(', ')}. 이 줄은 그리지 않았다.` });
      continue;
    }
    if (row.throttle_pct < 0 || row.throttle_pct > 100) {
      warnings.push({ line: lineNo, message: `throttle_pct=${row.throttle_pct}가 0~100 밖이다. 이 줄은 그리지 않았다.` });
      continue;
    }
    points.push({ line: lineNo, ...row });
  }

  if (header === null) return { points: [], missing: [...REQUIRED], warnings, dataLines: 0 };
  // Array.prototype.sort는 안정 정렬이라 같은 스로틀은 파일 순서를 지킨다.
  points.sort((a, b) => a.throttle_pct - b.throttle_pct);
  return { points, missing: [], warnings, dataLines };
}
