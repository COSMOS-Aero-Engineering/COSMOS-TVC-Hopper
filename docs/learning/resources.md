# 담당별 글·그림·영상 자료실

외부 자료 64개. 확인일: 2026-10-14. [처음 오면 학습 안내부터](README.md).

여기는 자료를 찾는 목록이다. **첫날에는 담당 안내서의 필수 자료만 보고 실습한다.** 나머지는 막힌 개념을 찾아보거나 다음 과제로 넘어갈 때 사용한다. 영상 링크가 강좌 입구인 경우 회차 목록을 가리키며 개별 영상 수로 부풀리지 않았다.

확인 범위: 공식·제작자·대학 페이지의 제목, 소개, 강의 목록과 문서 내용을 확인했다. 개별 영상 전체를 시청하거나 학교·중국 네트워크에서 재생되는지 시험한 결과는 아니다. YouTube 검색에서 제목·설명만 확인된 자료와 직접 페이지 열기가 실패한 KOCW 자료는 아래에 별도로 표시했다. 영어 영상의 한국어 자막 제공도 보장하지 않는다.

접근이 막히면 영상만 기다리지 말고 [한국어 개념 설명](concepts.md), [그림 모음](visuals.md), [동봉 실습](starter/README.md)으로 진행한다. MathWorks 공식 페이지에는 중국 사이트 선택 기능도 있으나 현지 플레이어 재생은 확인하지 않았다. YouTube 우회·비공식 재업로드는 이 안내의 일부가 아니다.

본문의 활동·과제는 COSMOS용으로 작성했다. 외부 강의의 내용 전체를 복제한 것이 아니다. 외부 영상·슬라이드는 링크로 제공하고 저자의 이용조건을 따른다.

## 전자·펌웨어

| ID · 단계 · 형식 · 언어 | 자료와 볼 범위 | 보고 나서 할 일 · 적용 한계 |
|---|---|---|
| F01 · 입문 · 글·사진 · 영어 | [PJRC Teensy 첫 실습](https://www.pjrc.com/teensy/tutorial.html)<br>First Hardware Check, Load LED Blink | Build와 Upload의 차이를 한 문장으로 설명한다.<br>Arduino IDE 예제다. 우리 프로젝트는 PlatformIO를 사용한다. |
| F02 · 입문 · 도면 PDF · 영어 | [Teensy 4.0 핀 카드 앞면](https://www.pjrc.com/teensy/card10a_rev2_web.pdf)<br>3.3V, GND, SPI 핀, LED 표기 | 핀맵 표와 SPI 핀 번호를 대조한다.<br>Teensy 4.1 카드와 혼용하지 않는다. |
| F03 · 입문 · 도면 PDF · 영어 | [Teensy 4.0 핀 카드 뒷면](https://www.pjrc.com/teensy/card10b_rev2_web.pdf)<br>뒤쪽 패드와 USB 커넥터 위치 | 보드 앞·뒷면 방향을 구분한다.<br>뒤쪽 패드에 임의로 납땜하거나 단락하지 않는다. |
| F04 · 입문 · 글·사진 · 영어 | [PlatformIO VS Code 안내](https://docs.platformio.org/en/latest/integration/ide/vscode.html)<br>Quick Start, Toolbar, Project Tasks | imu_test 프로젝트에서 Build를 실행하고 마지막 로그를 저장한다.<br> |
| F05 · 입문 · 영상 · 영어 | [DroneBot Workshop: Getting Started with PlatformIO](https://www.youtube.com/watch?v=JmvMvIphMnY)<br>Windows 설치·플러그인: 10:13–13:56. platformio.ini: 46:44부터 | 우리 platformio.ini에서 board와 framework를 찾는다.<br>2021년 UI다. Uno·ESP32·서보 실물 배선은 따라 하지 않는다. 제작자 글과 공식 PlatformIO 추천 링크로 확인. |
| F06 · 첫 실습 · 글·그림 · 영어 | [위 영상의 제작자 설명·코드](https://dronebotworkshop.com/platformio/)<br>PlatformIO Basics, Creating Your First Project | 프로젝트별 라이브러리가 필요한 이유를 설명한다.<br>영상이 안 열릴 때 이 글로 진행한다. 예제 보드·전원은 우리 것과 다르다. |
| F07 · 첫 실습 · 글·사진 · 영어 | [PJRC Windows Teensy Loader](https://www.pjrc.com/teensy/loader_win10.html)<br>설치와 프로그램 로딩 설명 | 빌드 파일과 보드 업로드가 각각 어느 단계인지 적는다.<br>USB 장치 인식·실물 업로드 성공은 별도 확인이다. |
| F08 · 첫 실습 · 글·그림 · 영어 | [PJRC Servo 라이브러리](https://www.pjrc.com/teensy/td_libs_Servo.html)<br>서보 전원, 제어 신호, 함수 설명 | 서보 전원과 신호를 다른 선으로 표시한다.<br>서보를 Teensy 3.3V 핀에서 구동하지 않는다. 실제 서보 사양·전원계통 확인 후 시험한다. |
| F09 · 첫 실습 · 글·사진 · 영어 | [Adafruit BNO085 핀 설명](https://learn.adafruit.com/adafruit-9-dof-orientation-imu-fusion-breakout-bno085/pinouts)<br>SPI 관련 핀의 역할 | CS·SCK·MOSI·MISO의 역할을 표로 쓴다.<br>Adafruit 보드 설명이다. 우리 GY 모듈의 실크·전원 허용 범위·모드 설정에 그대로 대입하지 않는다. |
| F10 · 입문 · 영상 · 중국어 | [PlatformIO 개발환경 공개 강의](https://www.bilibili.com/video/BV1Fi421d7Bj/)<br>VS Code와 PlatformIO 설치 과정 | Build 메뉴의 위치를 찾는다.<br>恰同学少年创客工坊 제작. STM32·ESP32 예제이며 우리 Teensy 설정은 저장소를 따른다. 현지 재생 여부 미확인. |
| F11 · 입문 · 글·사진 · 영어 | [PJRC 브레드보드 첫 회로](https://www.pjrc.com/teensy/tutorial2.html)<br>브레드보드 연결과 회로 그림 | 그림의 전원·접지·신호를 서로 다른 색으로 표시한다.<br>이 예제의 LED 회로를 IMU 또는 서보 배선으로 해석하지 않는다. |

## CAD·실측

| ID · 단계 · 형식 · 언어 | 자료와 볼 범위 | 보고 나서 할 일 · 적용 한계 |
|---|---|---|
| C01 · 입문 · 글 · 영어 | [OpenSCAD 공식 문서 입구](https://openscad.org/documentation.html)<br>User Manual, Tutorials로 이동 | cube와 cylinder를 찾고 크기 인자의 뜻을 설명한다.<br> |
| C02 · 첫 실습 · 그림·코드 · 영어 | [OpenSCAD CheatSheet](https://openscad.org/cheatsheet/)<br>translate, rotate, difference, module | 연습용 링에서 외경 변수 하나만 바꾼다.<br>개발 버전 전용 기능보다 2021.01에서도 쓰는 기본 구문부터 사용한다. |
| C03 · 입문 · 영상 · 영어 | [mathcodeprint: OpenSCAD Beginners Quickstart](https://www.youtube.com/watch?v=oTCu2hCuqfg)<br>cube·sphere·cylinder, translate·rotate, for 소개 | 원통을 만든 뒤 이동과 회전을 한 번씩 적용한다.<br>영상 제목·설명 확인. 전체 재생 검증은 하지 않았다. |
| C04 · 첫 실습 · 영상 · 영어 | [Mitutoyo: How to Read a Dial Caliper](https://www.mitutoyo.com/video/how-to-read-a-dial-caliper-mitutoyo-america/)<br>캘리퍼스 구조와 읽기 시연 | 외측·내측·깊이 측정면을 실제 도구에서 찾는다.<br>다이얼식이다. 디지털 캘리퍼스의 표시 읽기와 다르다. |
| C05 · 심화 · 영상 · 영어 | [Mitutoyo: Caliper Calibration](https://www.mitutoyo.com/video/caliper-calibration-how-to-calibrate-a-caliper/)<br>캘리퍼스 오차와 교정 개념 | 영점 확인과 정식 교정의 차이를 적는다.<br>교정용 표준기가 없으면 정식 교정을 수행했다고 기록하지 않는다. |

## KiCad

| ID · 단계 · 형식 · 언어 | 자료와 볼 범위 | 보고 나서 할 일 · 적용 한계 |
|---|---|---|
| K01 · 입문 · 글·그림 · 영어 | [KiCad 10 공식 첫 프로젝트](https://docs.kicad.org/10.0/en/getting_started_in_kicad/getting_started_in_kicad.html)<br>Schematic Editor, Electrical Rules Check | 기존 회로도를 열고 CS 넷 하나를 추적한다.<br>설치된 버전과 문서 버전을 확인한다. ERC는 실제 전압·기능 시험을 대신하지 않는다. |
| K02 · 입문 · 영상 · 영어 | [DigiKey KiCad 9.0 1: Intro & Download](https://www.youtube.com/watch?v=0WCi1rhueH4)<br>프로젝트와 편집기 소개 | 프로젝트 파일과 회로도 파일을 구분한다.<br>영상은 KiCad 9.0 기준이다. 설치는 KiCad 10으로 한다. KiCad 9는 팀 회로도 `cosmos-avionics.kicad_sch`를 열지 못한다([KiCad README](../../kicad/README.md), #139). 수분 경보기 예제다. 우리 회로·전원·PCB 제조 승인을 뜻하지 않는다. KiCad 10과 UI가 다를 수 있다. |
| K03 · 첫 실습 · 영상 · 영어 | [DigiKey KiCad 9.0 2: Schematic Layout](https://www.youtube.com/watch?v=0Q6gU7-QqUg)<br>심볼 선택, 배치, 값 수정, 넷 연결 | 별도 연습 프로젝트에서 커넥터 두 개를 연결한다.<br>수분 경보기 예제다. 우리 회로·전원·PCB 제조 승인을 뜻하지 않는다. KiCad 10과 UI가 다를 수 있다. |
| K04 · 첫 실습 · 영상 · 영어 | [DigiKey KiCad 9.0 3: Custom Schematic Symbol](https://www.digikey.com/en/videos/d/digi-key-electronics/kicad-9-0-getting-started-part-3-create-a-custom-schematic-symbol-digikey)<br>심볼 라이브러리와 핀 속성 | 심볼 핀 번호와 실제 보드 핀 번호의 차이를 적는다.<br>수분 경보기 예제다. 우리 회로·전원·PCB 제조 승인을 뜻하지 않는다. KiCad 10과 UI가 다를 수 있다. |
| K05 · 첫 실습 · 영상 · 영어 | [DigiKey KiCad 9.0 4: Finishing the Schematic](https://www.youtube.com/watch?v=KN3fHXhNkTU)<br>넷 이름, 외부 부품, ERC | ERC 오류 하나의 원인을 기록한다.<br>수분 경보기 예제다. 우리 회로·전원·PCB 제조 승인을 뜻하지 않는다. KiCad 10과 UI가 다를 수 있다. |
| K06 · 심화 · 영상 · 영어 | [DigiKey KiCad 9.0 5: Assigning & Creating Custom Footprints](https://www.digikey.com/en/videos/d/digi-key-electronics/kicad-9-0-getting-started-part-5-assigning-creating-custom-footprints)<br>데이터시트 치수와 풋프린트 매칭 | 2.54mm 핀 간격을 데이터시트와 실물로 대조한다.<br>수분 경보기 예제다. 우리 회로·전원·PCB 제조 승인을 뜻하지 않는다. KiCad 10과 UI가 다를 수 있다. |
| K07 · 심화 · 영상 · 영어 | [DigiKey KiCad 9.0 6: Laying Out Your First PCB](https://www.youtube.com/watch?v=zdieFtrvjew)<br>배치, Edge.Cuts, 배선, DRC | ERC와 DRC가 검사하는 대상을 구분한다.<br>수분 경보기 예제다. 우리 회로·전원·PCB 제조 승인을 뜻하지 않는다. KiCad 10과 UI가 다를 수 있다. |
| K08 · 심화 · 영상 · 영어 | [DigiKey KiCad 9.0 7: Images, Gerber Files and BOM](https://www.digikey.com/en/videos/d/digi-key-electronics/kicad-90-getting-started-part-7-images-gerber-files-and-bom-digikey)<br>Gerber, 드릴 파일, BOM | PCB 외주 제출 파일의 종류를 적는다.<br>수분 경보기 예제다. 우리 회로·전원·PCB 제조 승인을 뜻하지 않는다. KiCad 10과 UI가 다를 수 있다. |
| K09 · 심화 · 영상 · 영어 | [Phil’s Lab #65: KiCad 6 STM32 PCB](https://www.youtube.com/watch?v=aVUqaB0IMh4)<br>42:54–49:25: ERC와 annotation | 넷 이름과 연결점 오류 사례를 노트로 남긴다.<br>KiCad 6·STM32 예제다. 회로와 칩을 그대로 복사하지 않는다. |
| K10 · 심화 · 영상 · 영어 | [Phil’s Lab #165: KiCad 9 MSPM0 Schematic](https://www.youtube.com/watch?v=O-zNn5k5Bn4)<br>회로도 설계 과정을 비교용으로 참고 | 우리 회로에서 아직 데이터시트 근거가 없는 항목을 찾는다.<br>제목·소개 확인 범위다. 상세 시청 구간 미검증. Teensy 모듈과 다른 MCU 설계다. |

## 제어·PID

| ID · 단계 · 형식 · 언어 | 자료와 볼 범위 | 보고 나서 할 일 · 적용 한계 |
|---|---|---|
| P01 · 입문 · 글·그림 · 영어 | [WPILib Introduction to PID](https://docs.wpilib.org/en/stable/docs/software/advanced-controls/introduction/introduction-to-pid.html)<br>목표, 측정, 오차, P와 D | 교육용 PD 예제에서 +10도 입력의 출력 부호를 예측한다.<br>로봇의 라이브러리·게인을 우리 기체에 복사하지 않는다. |
| P02 · 첫 실습 · 글·코드 · 영어 | [WPILib PIDController](https://docs.wpilib.org/en/stable/docs/software/advanced-controls/controllers/pidcontroller.html)<br>제어 주기, 적분 제한, reset | 모드 전환 시 적분값을 어떻게 처리할지 설명한다.<br>수식 이해용이다. 우리 MCU 구현은 별도 검토한다. |
| P03 · 입문 · 영상 · 영어 | [MathWorks PID 1: What Is PID Control?](https://www.mathworks.com/videos/understanding-pid-control-part-1-what-is-pid-control--1527089264373.html)<br>11:41 전체. 피드백과 P·I·D | 센서값이 제어기로 돌아가는 화살표를 그린다.<br>개념 학습에는 MATLAB 설치가 필요 없다. 영상 속 설계·게인은 우리 기체의 검증 결과가 아니다. |
| P04 · 첫 실습 · 영상 · 영어 | [MathWorks PID 2: Anti-windup](https://www.mathworks.com/videos/understanding-pid-control-part-2-expanding-beyond-a-simple-integral-1528310418260.html)<br>10:43 전체. 출력 포화와 적분 누적 | 서보 제한에 걸렸을 때 I 항이 왜 문제가 되는지 설명한다.<br>개념 학습에는 MATLAB 설치가 필요 없다. 영상 속 설계·게인은 우리 기체의 검증 결과가 아니다. |
| P05 · 첫 실습 · 영상 · 영어 | [MathWorks PID 3: Beyond a Simple Derivative](https://www.mathworks.com/videos/understanding-pid-control-part-3-expanding-beyond-a-simple-derivative-1531120808026.html)<br>11:52 전체. 노이즈와 미분 필터 | 각속도 측정값과 각도 차분의 차이를 적는다.<br>개념 학습에는 MATLAB 설치가 필요 없다. 영상 속 설계·게인은 우리 기체의 검증 결과가 아니다. |
| P06 · 첫 실습 · 영상 · 영어 | [MathWorks PID 4: A PID Tuning Guide](https://www.mathworks.com/videos/understanding-pid-control-part-4-a-pid-tuning-guide-1531124725727.html)<br>12:04 전체. 시스템 특성에 따른 튜닝 선택 | 튜닝 전 필요한 측정 항목 두 개를 정한다.<br>개념 학습에는 MATLAB 설치가 필요 없다. 영상 속 설계·게인은 우리 기체의 검증 결과가 아니다. |
| P07 · 심화 · 영상 · 영어 | [MathWorks PID 5: 3 Ways to Build a Model](https://www.mathworks.com/videos/understanding-pid-control-part-5-3-ways-to-build-a-model-1533113098587.html)<br>13:44 전체. 시스템 모델을 얻는 방법 | 실측·계산·가정 값을 구분한다.<br>개념 학습에는 MATLAB 설치가 필요 없다. 영상 속 설계·게인은 우리 기체의 검증 결과가 아니다. |
| P08 · 심화 · 영상 · 영어 | [MathWorks PID 6: Manual and Automatic Tuning](https://www.mathworks.com/videos/understanding-pid-control-part-6-manual-and-automatic-tuning-methods-1533639047484.html)<br>13:30 전체. 모델 기반 튜닝 방법 | 우리 환경에 적용하기 위한 선행조건을 적는다.<br>개념 학습에는 MATLAB 설치가 필요 없다. 영상 속 설계·게인은 우리 기체의 검증 결과가 아니다. |
| P09 · 첫 실습 · 영상 · 영어 | [MathWorks PID 7: Important PID Concepts](https://www.mathworks.com/videos/understanding-pid-control-part-7-important-pid-concepts-1533639185431.html)<br>12:28 전체. 다중 루프와 이산시간 | 자세 루프와 각속도 루프의 입력·출력을 구분한다.<br>개념 학습에는 MATLAB 설치가 필요 없다. 영상 속 설계·게인은 우리 기체의 검증 결과가 아니다. |
| P10 · 입문 · 영상·강의자료 · 한국어 | [건국대학교 강철구: 제어공학](https://www.kocw.net/home/search/kemView.do?kemId=1332271)<br>차시별 목록의 오리엔테이션·서론, PID 제어 | 피드백과 오차를 한국어로 설명한다.<br>2018년 2학기 강의. 일부 차시는 자료만 제공된다. 구형 재생 안내가 있어 실제 재생은 별도 확인. |
| P11 · 심화 · 영상 · 한국어 | [국립목포대학교 김성환: 제어공학2](https://www.kocw.net/home/search/kemView.do?kemId=1044501)<br>차시별 목록의 PD·PI·PID 제어 | P/PD/PID가 같은 뜻이 아닌 이유를 설명한다.<br>강의 목록 검색 결과 확인. 직접 페이지 열기 실패, 현지 재생 미확인. 접근 실패 시 P03–P09와 P01로 진행. |

## 시뮬레이션·RL

| ID · 단계 · 형식 · 언어 | 자료와 볼 범위 | 보고 나서 할 일 · 적용 한계 |
|---|---|---|
| R01 · 입문 · 글·그림 · 영어 | [Gymnasium Basic Usage](https://gymnasium.farama.org/introduction/basic_usage/)<br>reset, step, observation, action, 종료 신호 | step 반환값 다섯 개의 뜻을 적는다.<br>공식 설치 명령 대신 저장소 uv.lock을 사용한다. |
| R02 · 첫 실습 · 글·코드 · 영어 | [Gymnasium Create a Custom Environment](https://gymnasium.farama.org/introduction/create_custom_env/)<br>관측·행동 공간과 reset/step | 우리 환경의 관측 7개와 행동 5개를 코드에서 찾는다.<br>예제 GridWorld는 호퍼의 물리 모델이 아니다. |
| R03 · 입문 · 글·코드 · 영어 | [SB3 Quickstart](https://stable-baselines3.readthedocs.io/en/master/guide/quickstart.html)<br>learn와 predict의 구분 | 학습과 평가에서 바뀌는 것이 무엇인지 적는다.<br>공식 첫 예제는 A2C다. 우리 코드의 PPO와 구분하고 의존성은 lock을 따른다. |
| R04 · 첫 실습 · 글·코드 · 영어 | [SB3 PPO 문서](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html)<br>PPO 생성자, learn, predict | 우리 학습 코드의 n_steps와 batch_size 위치를 찾는다.<br>최신 master 문서와 고정된 설치 버전은 다를 수 있다. |
| R05 · 첫 실습 · 글 · 영어 | [SB3 RL Tips and Tricks](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html)<br>평가 환경, 여러 실행, 정규화 | 훈련 seed와 평가 seed를 구분한 평가 계획을 쓴다.<br> |
| R06 · 심화 · 글·그림 · 영어 | [Spinning Up PPO](https://spinningup.openai.com/en/latest/algorithms/ppo.html)<br>clipped objective와 정책 업데이트 | PPO의 clip이 서보 출력 제한과 다른 이유를 적는다.<br>구형 구현 설치 안내는 사용하지 않고 수식·개념을 읽는다. |
| R07 · 심화 · 논문 · 영어 | [Proximal Policy Optimization Algorithms](https://arxiv.org/abs/1707.06347)<br>초록, 목적함수, 알고리즘 | PPO가 해결하려는 업데이트 문제를 요약한다.<br>정책 최적화 논문이며 우리 기체의 Sim-to-Real 성공을 증명하지 않는다. |
| R08 · 입문 · 글·그림 · 영어 | [Hugging Face Deep RL Unit 1](https://huggingface.co/learn/deep-rl-course/unit1/introduction)<br>Unit 1의 기본 학습 흐름 | agent, environment, reward를 호퍼에 대응시킨다.<br>클라우드 실습·설치 절차를 저장소 환경에 섞지 않는다. |
| R09 · 입문 · 영상 · 영어 | [MathWorks RL 1: What Is Reinforcement Learning?](https://www.mathworks.com/videos/reinforcement-learning-part-1-what-is-reinforcement-learning-1551974943006.html)<br>14:05 전체. 제어 문제로 보는 RL | RL이 받는 입력과 내보내는 출력을 그린다.<br>MATLAB 기반 사례다. 우리 하드웨어 배포 절차·추론 시간을 검증한 자료는 아니다. |
| R10 · 첫 실습 · 영상 · 영어 | [MathWorks RL 2: Environment and Rewards](https://www.mathworks.com/videos/reinforcement-learning-part-2-understanding-the-environment-and-rewards-1551976590603.html)<br>13:27 전체. 환경·보상·정책 | 우리 reward가 기울기와 제어 사용량을 어떻게 다루는지 찾는다.<br>MATLAB 기반 사례다. 우리 하드웨어 배포 절차·추론 시간을 검증한 자료는 아니다. |
| R11 · 첫 실습 · 영상 · 영어 | [MathWorks RL 3: Policies and Learning Algorithms](https://www.mathworks.com/videos/reinforcement-learning-part-3-policies-and-learning-algorithms-1554395009678.html)<br>17:51 전체. 정책과 신경망 | 학습된 가중치와 환경 파라미터의 차이를 적는다.<br>MATLAB 기반 사례다. 우리 하드웨어 배포 절차·추론 시간을 검증한 자료는 아니다. |
| R12 · 심화 · 영상 · 영어 | [MathWorks RL 4: The Walking Robot Problem](https://www.mathworks.com/videos/reinforcement-learning-part-4-the-walking-robot-problem-1557482052319.html)<br>14:50 전체. 로봇 문제의 환경 구성 | 걷는 로봇과 호퍼의 행동 공간 차이를 쓴다.<br>MATLAB 기반 사례다. 우리 하드웨어 배포 절차·추론 시간을 검증한 자료는 아니다. |
| R13 · 심화 · 영상 · 영어 | [MathWorks RL 5: Practical Challenges](https://www.mathworks.com/videos/reinforcement-learning-part-5-overcoming-the-practical-challenges-of-reinforcement-learning-1558604830037.html)<br>16:07 전체. 학습 해의 검증 문제 | 높은 보상이 물리적 성공과 다를 수 있는 사례를 적는다.<br>MATLAB 기반 사례다. 우리 하드웨어 배포 절차·추론 시간을 검증한 자료는 아니다. |
| R14 · 심화 · 영상 · 영어 | [MathWorks RL Model-Based RL](https://www.mathworks.com/videos/why-choose-model-based-reinforcement-learning-1657878550459.html)<br>15:00 전체. model-free와 model-based 비교 | 물리 시뮬레이터 사용과 model-based 정책 학습을 구별한다.<br>MATLAB 기반 사례다. 우리 하드웨어 배포 절차·추론 시간을 검증한 자료는 아니다. |
| R15 · 심화 · 영상 · 영어 | [MathWorks RL RL on Hardware](https://www.mathworks.com/videos/reinforcement-learning-on-hardware-1765346150358.html)<br>18:09 전체. 하드웨어 학습·배포 접근 | Teensy 이식 전 필요한 측정과 제한 항목을 적는다.<br>MATLAB 기반 사례다. 우리 하드웨어 배포 절차·추론 시간을 검증한 자료는 아니다. |
| R16 · 심화 · 영상 강좌 · 영어 | [David Silver RL 강의 입구](https://davidstarsilver.wordpress.com/teaching/)<br>Video-lectures 링크: Lecture 1 이후 2, 7 순서 | MDP와 policy gradient를 우리 상태·행동에 대응시킨다.<br>저자 페이지에서 연결한 강좌다. 영상 전체를 첫날 숙제로 지정하지 않는다. |
| R17 · 심화 · 슬라이드 PDF · 영어 | [David Silver Lecture 1: Introduction](https://davidstarsilver.wordpress.com/wp-content/uploads/2025/04/intro_rl.pdf)<br>agent/environment 기본 도식 | 도식을 보고 우리 학습 루프를 다시 그린다.<br> |
| R18 · 심화 · 슬라이드 PDF · 영어 | [David Silver Lecture 2: MDP](https://davidstarsilver.wordpress.com/wp-content/uploads/2025/04/lecture-2-mdp.pdf)<br>상태·행동·전이·보상 정의 | 센서 지연이 관측에 끼치는 영향을 적는다.<br> |
| R19 · 심화 · 슬라이드 PDF · 영어 | [David Silver Lecture 7: Policy Gradient](https://davidstarsilver.wordpress.com/wp-content/uploads/2025/04/lecture-7-policy-gradient-methods.pdf)<br>정책 파라미터 최적화 | 정책 가중치를 학습한다는 말을 수식과 연결한다.<br> |

## 웹·3D·데이터

| ID · 단계 · 형식 · 언어 | 자료와 볼 범위 | 보고 나서 할 일 · 적용 한계 |
|---|---|---|
| W01 · 입문 · 글·코드 · 영어 | [MDN What is JavaScript?](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Scripting/What_is_JavaScript)<br>브라우저 코드의 역할 | HTML, CSS, JavaScript가 맡는 일을 각각 적는다.<br> |
| W02 · 입문 · 글·코드 · 영어 | [MDN Functions](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Scripting/Functions)<br>함수 호출과 재사용 | starter의 reset 처리를 찾고 호출 시점을 설명한다.<br> |
| W03 · 입문 · 글·그림·실행 예제 · 영어 | [Three.js Fundamentals](https://threejs.org/manual/pages/fundamentals.html)<br>scene, camera, renderer, mesh | starter에서 네 객체를 찾는다.<br>웹 화면은 물리 시뮬레이터나 제어기가 아니다. |
| W04 · 첫 실습 · 글·실행 예제 · 영어 | [Three.js Responsive Design](https://threejs.org/manual/pages/responsive.html)<br>캔버스 크기와 camera aspect | 창 크기를 바꾸며 기체가 찌그러지는지 확인한다.<br> |
| W05 · 입문 · 영상 · 영어 | [freeCodeCamp: JavaScript Programming Full Course](https://www.youtube.com/watch?v=jS4aFq5-91M)<br>변수·함수·배열 관련 강의부터. 처음부터 완강하지 않는다. | 팬 색 변수를 바꾸고 브라우저를 새로고침한다.<br>제목·소개 검색 확인. 정확한 챕터 시각 미확인, 없는 타임스탬프를 만들지 않았다. |
| W06 · 첫 실습 · 영상 · 영어 | [freeCodeCamp: Learn Three.js by Building 5 Projects](https://www.youtube.com/watch?v=UMqNHi1GDAE)<br>Getting Started 프로젝트부터 | 우리 starter의 scene/camera/mesh 구조와 비교한다.<br>다른 프로젝트의 Rapier 물리는 우리 EDF·베인 모델을 제공하지 않는다. 영상 소개 확인, 전체 재생 미검증. |
| W07 · 첫 실습 · 글·실행 예제 · 영어 | [Chart.js Getting Started](https://www.chartjs.org/docs/latest/getting-started/)<br>첫 차트 생성 | 합성 CSV의 시간과 phi를 선 그래프 입력으로 정한다.<br>공식 예제는 막대 그래프다. 자세 시계열은 선 그래프로 바꾸고 단위를 붙인다. |
| W08 · 첫 실습 · 글·코드 · 영어 | [Papa Parse 문서](https://www.papaparse.com/docs)<br>Parse local files, header, errors | CSV 헤더와 숫자 변환 실패를 어떻게 표시할지 적는다.<br>starter에는 이 라이브러리를 설치하지 않았다. 정식 웹 구현 단계에서 버전을 정한다. |
