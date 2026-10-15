"""resources.json의 목록을 resources.md로 반영. --check는 파일을 바꾸지 않는다."""
from pathlib import Path
import argparse, json, re

def render():
    base=Path(__file__).parent
    target=base/'resources.md'
    old=target.read_text(encoding='utf-8')
    data=json.loads((base/'resources.json').read_text(encoding='utf-8'))
    records=data['resources']
    introduction=old.split('\n## ',1)[0]
    introduction=re.sub(r'외부 자료 \d+개',f'외부 자료 {len(records)}개',introduction)
    lines=[introduction.rstrip(),'']
    for track in dict.fromkeys(r['track'] for r in records):
        lines += ['## '+track,'','| ID · 단계 · 형식 · 언어 | 자료와 볼 범위 | 보고 나서 할 일 · 적용 한계 |','|---|---|---|']
        for r in records:
            if r['track']==track:
                lines.append(f"| {r['id']} · {r['level']} · {r['kind']} · {r['language']} | [{r['title']}]({r['url']})<br>{r['scope']} | {r['exercise']}<br>{r['note']} |")
        lines.append('')
    return target,old,'\n'.join(lines)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    target,old,new=render()
    if args.check:
        assert old==new,'자료 목록을 render_catalog.py로 갱신하세요.'
        print('PASS: catalog matches resources.json')
    else:
        target.write_text(new,encoding='utf-8')
        print('Updated resources.md')
