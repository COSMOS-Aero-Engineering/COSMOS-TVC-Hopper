# #66·#218 생성물 검증

2026-10-22 Windows KiCad 10.0.7에서 회로도를 다시 생성하고 XML 넷리스트와 ERC JSON을 내보냈다. 개인 절대경로는 파일명 또는 저장소 상대경로로 치환했다.

- 부품 20개, 핀 84개. 생성원 COMPONENTS와 불일치 0개.
- BNO085 SPI 대조표 10행 모두 일치.
- ERC 위반 0개. `endpoint_off_grid`는 #218에서 103개에서 0개로 줄였다.
- 생성기는 심볼 원점을 가장 가까운 1.27 mm 연결 격자에 놓는다. 핀 간격 2.54 mm와 배선 스텁 5.08 mm도 같은 격자의 배수다.
- 수정 전 main의 회로도를 같은 KiCad에서 내보낸 대조군은 check_netlist.py가 실패한다.
- 핀 Y좌표와 수직 핀의 배선 방향을 함께 반전했다. Y좌표만 고치면 +5V와 +BATT가 합쳐지는 문제가 있었다.

이 검사는 회로도 파일의 연결표를 확인한 것이다. 실제 모듈의 핀 배열이나 실물 배선을 확인한 것은 아니다.

재현: gen_schematic.py 실행 후 kicad-cli sch export netlist --format kicadxml로 XML을 만들고, check_netlist.py로 읽는다. kicad-cli sch erc --format json으로 ERC를 확인한다. test_netlist.py도 커밋된 ERC JSON에 오류와 endpoint_off_grid가 없는지 검사한다.
