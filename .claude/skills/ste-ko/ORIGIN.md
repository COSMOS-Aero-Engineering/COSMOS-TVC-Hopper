# ste-ko 스킬 복사본의 출처

이 폴더는 원본 저장소의 복사본입니다. 여기서 직접 고치지 않습니다. 원본을 고친 다음 다시 복사합니다.

- 원본: https://github.com/junwonkim07/ste-ko-skill (MIT, `LICENSE`)
- 기준 커밋: `30a46fefbba791cd7f0995fd57d0c52f3caf3231` (2026-10-12, 플러그인 버전 1.0.1)
- 제3자 저작물: `NOTICE.md` 참고 (beamonic/ste-ko, MIT)

## 복사한 파일

`SKILL.md`, `LICENSE`, `NOTICE.md`, `references/`, `scripts/ste-ko-lint.py`

## 원본과 다른 곳

원본을 고치기 전에 이 저장소에서 먼저 고친 곳이다. 원본에 같은 수정이 들어가면 다시 복사하고 이 목록에서 지운다.

- `scripts/ste-ko-lint.py`: 지적 메시지 3개의 em dash(—)를 콜론이나 마침표로 바꿨다. 출력 스트림의 오류 처리를 `backslashreplace`로 바꾸고, `--json` 출력은 출력 인코딩에 없는 글자를 `\uXXXX`로 쓴다. 한국어 Windows에서 출력을 파일이나 파이프로 돌리면 cp949로 쓰는데, 고치기 전에는 `UnicodeEncodeError`로 멈췄다(#169).
- `scripts/ste-ko-lint.py`: 표준 입력(`-`)을 바이트로 읽고 UTF-8(BOM 포함)로 먼저 바꾼다. UTF-8이 아니면 파이썬의 표준 입력 인코딩으로 읽고 stderr에 그 이름을 쓴다. 둘 다 아니면 종료 코드 2를 낸다. 한국어 Windows에서 파이프 입력은 cp949로 읽는데, 고치기 전에는 UTF-8 글을 주면 `UnicodeDecodeError`로 멈췄다(#187, 원본 junwonkim07/ste-ko-skill#4).
- `SKILL.md` §검사기: 표준 입력을 읽는 방식과 Windows PowerShell 5.1의 `$OutputEncoding` 주의를 더했다(#187).
- `scripts/ste-ko-lint.py`: 파일을 `utf-8-sig`로 읽어서 맨 앞의 BOM을 뗀다(`read_file`). 고치기 전에는 BOM이 붙은 파일의 첫 줄 코드 펜스와 frontmatter를 알아보지 못해서 그 안의 글에 틀린 hard 지적을 냈다. Windows PowerShell 5.1이 UTF-8로 저장한 파일은 앞에 BOM이 있다. `SKILL.md` §검사기에도 이 동작을 적었다(#195, 원본 junwonkim07/ste-ko-skill#5).

## 복사하지 않은 파일

`assets/`(배너 이미지), `tests/`, `output-styles/`, `.claude-plugin/`, `README.md`. 스킬 동작에 필요 없습니다.

## 이 폴더를 읽는 도구

- Claude Code: 프로젝트의 `.claude/skills/`를 스킬로 읽습니다.
- OpenCode: `.claude/skills/<name>/SKILL.md`를 스킬로 읽습니다 ([opencode.ai/docs/skills](https://opencode.ai/docs/skills/)).
- 스킬 기능이 없는 도구: `SKILL.md`를 파일로 직접 읽습니다.
