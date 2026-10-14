"""학습 자료의 내부 링크·ID·예제 데이터를 검사. 외부 재생/장치 시험은 하지 않는다."""
from pathlib import Path
import ast, csv, json, math, re
from urllib.parse import unquote, urlsplit

BASE = Path(__file__).resolve().parent

def check():
    records = json.loads((BASE/'resources.json').read_text(encoding='utf-8'))['resources']
    ids = [r['id'] for r in records]
    urls = [r['url'] for r in records]
    assert len(ids)==len(set(ids)), '자료 ID 중복'
    assert len(urls)==len(set(urls)), '외부 자료 URL 중복'
    catalog = (BASE/'resources.md').read_text(encoding='utf-8')
    for r in records:
        assert urlsplit(r['url']).scheme=='https', r['id']
        assert f"| {r['id']} ·" in catalog and f"]({r['url']})" in catalog, r['id']
        assert all(r[k].strip() for k in ['scope','exercise','title','level','language'])
    count=0
    for file in BASE.rglob('*.md'):
        text=file.read_text(encoding='utf-8')
        for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
            target=link.split('#',1)[0]
            if not target or '://' in target:
                continue
            path=(file.parent/unquote(target)).resolve()
            assert path.exists(), f'{file.relative_to(BASE)}: {link}'
            count+=1
        assert 'C:/Users/' not in text and 'C:\\Users\\' not in text, file.name
    for file in BASE.rglob('*.py'):
        ast.parse(file.read_text(encoding='utf-8'),filename=str(file))
    with (BASE/'starter/sample-synthetic.csv').open(encoding='utf-8',newline='') as stream:
        rows=list(csv.DictReader(stream))
    assert len(rows)==5
    assert all(r['source']=='SYNTHETIC' for r in rows)
    assert math.isclose(float(rows[2]['phi'])*180/math.pi,10,abs_tol=1e-6)
    assert [int(r['t_ms']) for r in rows]==[0,250,500,750,1000]
    assert len(list((BASE/'images').glob('*.png')))==9
    print(f'PASS: {len(records)} resources, {sum("영상" in r["kind"] for r in records)} video entries, {count} internal links, CSV, Python syntax, 9 diagrams')

if __name__=='__main__':
    check()
