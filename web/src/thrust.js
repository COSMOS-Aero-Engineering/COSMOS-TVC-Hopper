// 실험 A 추력 곡선 화면 (이슈 #254). CSV를 읽어 스로틀 대 추력, 스로틀 대 전류를 그린다.
// 물리 계산은 하지 않는다(AGENTS.md §확정된 방향). Kf 계산과 실제 데이터 해석은 이 화면의 일이 아니다.
import {
  Chart, LinearScale, LineController, LineElement, PointElement, Legend, Tooltip,
} from 'chart.js';
import { parseThrust } from './thrust_csv.js';

Chart.register(LinearScale, LineController, LineElement, PointElement, Legend, Tooltip);

const $ = (id) => document.getElementById(id);
const MAX_SHOWN = 50; // 경고가 아주 많아도 화면이 밀리지 않게 앞쪽만 보인다. 나머지는 개수로 알린다.

// 예제 CSV는 web/examples/에 있다. 빌드 때 문자열로 묶는다.
const samples = import.meta.glob('../examples/*.csv', { query: '?raw', import: 'default', eager: true });
for (const path of Object.keys(samples).sort()) {
  const name = path.split('/').pop();
  const opt = document.createElement('option');
  opt.value = path;
  opt.textContent = name;
  $('sample').appendChild(opt);
}

function makeChart(canvasId, yTitle, color) {
  const css = getComputedStyle(document.documentElement);
  const text = css.getPropertyValue('--text').trim();
  const grid = css.getPropertyValue('--line').trim();
  const axis = (title) => ({
    type: 'linear',
    title: { display: true, text: title, color: text },
    ticks: { color: text },
    grid: { color: grid },
  });
  return new Chart($(canvasId), {
    type: 'line',
    data: { datasets: [{ label: yTitle, data: [], borderColor: color, backgroundColor: color, pointRadius: 4, tension: 0 }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      parsing: false,
      scales: { x: { ...axis('스로틀 (%)'), min: 0, max: 100 }, y: axis(yTitle) },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (c) => `스로틀 ${c.parsed.x}% → ${c.parsed.y} (CSV ${c.raw.line}줄)` } },
      },
    },
  });
}

const thrustChart = makeChart('chart-thrust', '추력 (gf)', '#0f6b6b');
const currentChart = makeChart('chart-current', '전류 (A)', '#b45309');

function showWarnings(name, warnings) {
  const box = $('warnings');
  const list = $('warning-list');
  list.replaceChildren();
  box.hidden = warnings.length === 0;
  if (!warnings.length) return;
  $('warnings-title').textContent = `경고 ${warnings.length}건: ${name}`;
  for (const w of warnings.slice(0, MAX_SHOWN)) {
    const li = document.createElement('li');
    const line = document.createElement('span');
    line.className = 'line';
    line.textContent = `${w.line}줄`;
    li.append(line, `: ${w.message}`);
    list.appendChild(li);
  }
  if (warnings.length > MAX_SHOWN) {
    const li = document.createElement('li');
    li.textContent = `... 외 ${warnings.length - MAX_SHOWN}건`;
    list.appendChild(li);
  }
}

function setData(points) {
  thrustChart.data.datasets[0].data = points.map((p) => ({ x: p.throttle_pct, y: p.thrust_g, line: p.line }));
  currentChart.data.datasets[0].data = points.map((p) => ({ x: p.throttle_pct, y: p.current_A, line: p.line }));
  thrustChart.update();
  currentChart.update();
}

function load(text, name) {
  const res = parseThrust(text);
  if (res.missing.length) {
    setData([]);
    showWarnings(name, []);
    $('status').textContent = `${name}: 필요한 컬럼 없음 (${res.missing.join(', ')})`;
    return;
  }
  setData(res.points);
  showWarnings(name, res.warnings);
  $('status').textContent = `${name}: ${res.points.length}점`
    + (res.warnings.length ? `, 그리지 않은 줄 ${res.warnings.length}` : '')
    + (res.dataLines === 0 ? ', 데이터 줄이 없다' : '');
}

$('file').addEventListener('change', async (e) => {
  const f = e.target.files[0];
  if (f) load(await f.text(), f.name);
});
$('sample').addEventListener('change', (e) => {
  if (e.target.value) load(samples[e.target.value], e.target.value.split('/').pop());
});
