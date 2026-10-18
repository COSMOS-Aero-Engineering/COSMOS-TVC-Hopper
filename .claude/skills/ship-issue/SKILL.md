---
name: ship-issue
description: COSMOS 저장소에서 GitHub 이슈 하나를 맡아 PR까지 끝낼 때 쓴다(예: "ship issue 12", "#12 처리해줘", "이슈 29 작업해줘"). 이슈 선점, worktree, Best practice 조사, 검사, PR, 교차 리뷰, CI를 순서대로 하고 머지 전에 멈춘다.
---

# ship-issue (COSMOS)

정본 절차는 `AGENTS.md` §작업 순서다. 이 스킬은 그 절차를 명령 단위로 실행하는 순서표다. 둘이 다르면 `AGENTS.md`를 따르고 이 파일을 고친다.

단계 사이에 멈추지 않는다. 멈추는 경우는 아래에 적은 것뿐이다.

1. **도구 확인.** `python ship.py tools`. gh 로그인이 없다고 나오면 멈추고 사람에게 `gh auth login`을 부탁한다.
2. **읽기.** `gh issue view <n> --comments`로 본문과 댓글을 전부 읽는다.
   - 다른 사람의 `claimed by ...`가 있거나 이슈가 닫혔으면 멈추고 알린다.
   - 사람만 하는 일(`AGENTS.md` §핵심 규칙 8)이면 라벨 `agent physically incapable`을 달고, 사람이 정할 것을 댓글로 쓰고 멈춘다.
3. **worktree.** `python ship.py wt <n>`을 실행한다. 출력의 마지막 줄이 폴더, 그 앞 줄이 브랜치 이름이다. 그 폴더로 이동해서 `AGENTS.md`를 읽는다.
   - 이어서 `gh issue comment <n> --body "claimed by <브랜치 이름>"`.
   - `wt`는 본문 `### 상위 PRD` 칸의 PRD 아래 sub-issue로도 잇는다. 출력에 `[잇지 않음]`이 있으면 worktree는 그대로 쓰고, 원인(칸의 값, 권한)을 고칠 수 있으면 고친 뒤 `python ship.py link <n>`을 다시 실행한다. 고칠 수 없으면 9단계에서 후속 이슈로 남긴다.
4. **조사 후 구현.** Best practice를 먼저 조사한다(공식 문서, 데이터시트, 쓰는 도구가 권장하는 방식, 잘 관리된 참고 프로젝트, 이 저장소의 기존 코드). 출처는 PR "근거"에 적는다. 이슈 범위만 고친다. 범위 밖 문제는 새 이슈로 남긴다.
5. **검사.** 바꾼 영역의 검사를 돌린다(`python tasks.py check`, `pio run` 등). 무거운 명령은 `python ship.py capped 8G -- <명령>`. 통과할 때까지 고친다. 커밋 제목은 `[태그] 무엇을 바꿨는지`.
6. **PR.** `git push -u origin HEAD` 후 `gh pr create --base main`. 본문은 `.github/pull_request_template.md`를 채우고 `Closes #<n>`을 넣는다. 실제로 해 본 확인만 체크한다. 작성자가 김민찬·김준원이 아니면 `--reviewer junwonkim07`을 붙인다. 본문을 쓰기 전에 `ste-ko` 스킬을 불러온다.
7. **교차 리뷰.** `python ship.py review --author <지금 쓰는 모델>`. 맞는 지적은 고쳐서 푸시하고, 받아들이지 않는 지적은 이유를 한 줄 남긴다. 결과를 PR 본문 "교차 리뷰"에 쓴다.
8. **CI.** `gh pr checks --watch`. 실패하면 `gh run view --log-failed`로 로그를 읽고 고친다.
9. **마무리.** 남은 일, 확인하지 못한 항목, 미룬 결정을 하나씩 `gh issue create`로 만든다. 사람만 확인할 수 있으면 라벨 `agent physically incapable`을 단다. 번호를 PR 본문 "후속 이슈"에 적는다. PR 본문 "알게 된 것"을 채운다. 모든 에이전트가 알아야 할 교훈이면 `AGENTS.md` §교훈에 한 줄 추가한다. PR 링크를 알리고 멈춘다. 머지하지 않는다.
