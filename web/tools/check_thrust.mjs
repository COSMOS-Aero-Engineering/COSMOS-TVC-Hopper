// 추력 곡선 CSV 읽기를 검사한다. 브라우저 없이 Node로 돈다. 실행: npm run check (web/ 폴더에서).
// 1. 예제 CSV(합성)는 경고 없이 11점이 나온다.
// 2. 잘못된 줄 예제는 어떤 줄이 왜 빠졌는지 줄 번호와 함께 경고로 나온다. 조용히 버리는 줄이 없다.
// 3. 필수 컬럼이 없으면 missing으로 알린다.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseThrust } from '../src/thrust_csv.js';

const examples = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'examples');
const read = (name) => fs.readFileSync(path.join(examples, name), 'utf8');
let failed = 0;
function check(ok, msg) {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${msg}`);
  if (!ok) failed += 1;
}

const good = parseThrust(read('thrust-curve-synthetic.csv'));
check(good.missing.length === 0 && good.warnings.length === 0, '예제: 경고 없음');
check(good.points.length === 11, `예제: 11점 (${good.points.length})`);
check(good.points.every((p, i) => i === 0 || good.points[i - 1].throttle_pct <= p.throttle_pct), '예제: 스로틀 오름차순');
check(good.points[0].line === 3, `예제: 첫 데이터 줄 번호는 주석을 센 3 (${good.points[0].line})`);

// 기대: 줄 번호는 파일의 실제 줄이다(주석 1줄 + 헤더 1줄 + 데이터). 빈 줄(8번째 줄)도 센다.
const bad = parseThrust(read('thrust-curve-synthetic-bad-lines.csv'));
const byLine = Object.fromEntries(bad.warnings.map((w) => [w.line, w.message]));
check(Object.keys(byLine).map(Number).join(',') === '6,11,13,14', `잘못된 줄 경고 줄 번호 6,11,13,14 (${Object.keys(byLine)})`);
check(/thrust_g="abc"/.test(byLine[6] ?? ''), '6줄: thrust_g="abc"');
check(/칸이 3개/.test(byLine[11] ?? ''), '11줄: 칸 수 부족');
check(/current_A=\(빈 칸\)/.test(byLine[13] ?? ''), '13줄: current_A 빈 칸');
check(/0~100 밖/.test(byLine[14] ?? ''), '14줄: throttle_pct 범위 밖');
check(bad.points.length === 7, `잘못된 줄 예제: 그려지는 점 7개 (${bad.points.length})`);
check(bad.points.length + bad.warnings.length === bad.dataLines, '읽은 줄 = 그린 점 + 경고 (조용히 버린 줄 없음)');

const noCol = parseThrust('throttle_pct,thrust_g\n10,5\n');
check(noCol.missing.join() === 'current_A' && noCol.points.length === 0, '컬럼 없음: current_A 보고');
check(parseThrust('').missing.length === 3, '빈 파일: 필수 컬럼 3개 없음으로 보고');
const crlf = parseThrust('﻿throttle_pct,thrust_g,current_A\r\n10,5,1\r\n');
check(crlf.points.length === 1 && crlf.warnings.length === 0, 'BOM + CRLF 처리');

if (failed) { console.log(`\n${failed}개 실패`); process.exit(1); }
console.log('\n전부 통과');
