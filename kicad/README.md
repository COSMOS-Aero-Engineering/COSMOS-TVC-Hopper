# kicad/ — 회로도(스키매틱) 캡처

**아직 비어 있음.** [`docs/execution/semester-roadmap.md`](../docs/execution/semester-roadmap.md) Week 4에서
착수 예정 — 지금 이 폴더에 실물 파일은 없다(이 프로젝트는 "아직 안 된 걸 완료로 적지 않는다"는 원칙을
지킨다, `AGENTS.md` 참고).

## 왜 KiCad를 쓰나

이 프로젝트는 PCB를 새로 설계하지 않는다 — 아비오닉스는 만능기판(perfboard) 수작업 배선이 정본
(`docs/design/01-avionics-integration-final.md` §5). **KiCad는 새 회로를 설계하는 도구가 아니라, 이미
빵판에서 검증되고 만능기판에 납땜된 배선을 정식 회로도로 문서화하는 도구**로 쓴다:

- `01-avionics-integration-final.md` §2.2(Teensy 4.0 핀맵)·§5.3(만능기판 홀 좌표)이 소스 자료.
- 조립 중 오배선을 조기에 발견하는 대조 도구(Week 5, 전자 탑재 시 스키매틱과 실물 대조).
- 발표·인수인계 자료 — 다음 학기 팀이 "이 기체가 어떻게 배선됐는지"를 마크다운 표 대신 정식 회로도로 볼 수 있음.
- (스트레치) rev D에서 실제 커스텀 PCB로 갈 경우의 출발점 — `01-avionics-integration-final.md` §11
  고장모드 표의 "진동으로 커넥터 접촉 불량"·"빵판 접점 간헐적 이탈" 문제들이 PCB화로 해결될 수 있는
  지점이라, 스키매틱이 이미 있으면 그때 PCB 레이아웃만 추가하면 됨.

## 착수 순서 (Week 4, `semester-roadmap.md` 참고)

1. 만능기판 배선이 빵판(`01-avionics-integration-final.md` §4)에서 먼저 검증 완료돼 있어야 함(Week 3).
2. KiCad 설치(무료, [kicad.org](https://www.kicad.org/)).
3. 새 프로젝트 → 스키매틱에 Teensy 4.0·BNO085·서보×4·수신기(FS-iA6B)·ESC·UBEC 심볼 배치.
4. §2.2 핀맵 표를 그대로 넷(net) 이름으로 옮겨 연결 — 표의 각 행이 스키매틱의 넷 하나.
5. ERC(Electrical Rule Check) 돌려서 미연결·충돌 확인.
6. **PCB 레이아웃까지는 안 감** — 스키매틱만으로 이번 학기 목적은 충분.

커밋 태그: `[cad]` (전자 회로도도 기구·전자팀 소관이라 동일 태그 사용, `README.md` 협업 규칙 참고).
