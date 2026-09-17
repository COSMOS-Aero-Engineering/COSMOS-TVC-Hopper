# 논문 3장(Modelling) 정리 — 운동방정식·베인 공력식

원문: Jacobsen, E.B. *Modelling and Control of Thrust Vectoring Mono-copter*, Aalborg University, 2021,
Chapter 3 "Modelling" (원문 18–33쪽 / PDF 24–39쪽) — `docs/design/references/Jacobsen2021_*.pdf`.

**목적**: 이 장의 수식을 `sim/sim_stage1/hopper_aviary.py`가 그대로 코드화했다. 이 문서는 그 대응관계를
명시하고, 코드가 논문과 어디서 일부러(또는 실수로) 다른지 기록해둔다 — **params.yaml 값을 실측치로
교체할 때 반드시 다시 볼 것.**

> ⚠️ 이 문서는 2026-09-17에 (재)작성됐다. 원래 같은 이름으로 존재했다고 기록돼 있었으나 실제 파일은
> 어디에도 없었다(Codex 세션 안에서만 만들어지고 export가 안 된 것으로 추정) — 이번에 논문 PDF에서
> 다시 추출해 새로 썼다.

---

## 1. 좌표계 (§3.1)

- **월드 프레임 W**: 관성 고정 좌표계(flat earth).
- **바디 프레임 B**: 기체 무게중심(COM)에 고정, 같이 움직임. **xb·yb축이 베인과 나란히, zb축이
  모터 회전축(=배기 방향)과 나란**하도록 잡음 — 우리 좌표계(설계도 §4, "Z=0 배기면, +Z 위")와
  같은 관례.
- **자세**: Tait-Bryan 각 η=[φ,θ,ψ](roll,pitch,yaw), **ZYX 순서** 회전행렬 R^w_b(ψ,θ,φ) (식 3.2–3.3).
- **바디 각속도 ω_B ↔ 오일러각 변화율 η̇**: 변환행렬 W_η (식 3.4–3.5). **θ=±90°에서 특이점** —
  코드(`hopper_aviary.py`)도 `cos_theta`를 `max(abs(cos_theta), 1e-3)`로 클리핑해서 방어(논문은
  "정상 운용 범위 밖이라 안 다룸"이라고만 하고 넘어감 — 우리 코드가 더 방어적).
- **관성행렬 대각 가정** (식 3.7): 질량이 로컬 축 기준 고르게 분포하면 비대각항(product of inertia)이
  0에 가까워짐 — 논문은 CAD 질량속성 계산으로 검증했다고 함. **우리도 나중에 Onshape/CAD 질량속성으로
  이 가정이 맞는지 확인 필요** (지금은 Jxx=Jyy≈같은 값으로 대칭 가정만 하고 있음, params.yaml 주석 참고).

## 2. 힘·모멘트 구성 (§3.2)

3차원 자유물체도(Fig 3.2): 추력 Ft(모터) + 베인 제어력 F1..F4 + 베인 항력 Fd1..Fd4 + 중력.
**공력(동체 자체의 양력·항력)은 호버 근처에서 무시** — 우리도 동일 가정.

### 2.1 추진력 모델 (§3.2.1)

```
모터 1차계:  ωt(s)/ut(s) = Kt / (τt·s + 1)      (τt = 0.0345s, "충분히 빠름"이라 무시 가능)
추력:        Ft = Kf · ωt²                        (식 3.9)
```

→ 코드 대응: `params.yaml`의 `Kf`. 단, **코드는 실제 RPM(ωt) 대신 `omega_t_equiv = throttle*3000`
(throttle 기반 임시 스케일)을 씀** — 논문처럼 진짜 각속도가 아니다. **실험 A(EDF 추력곡선) 이후엔
DShot에서 읽은 실제 RPM으로 교체해야 논문 식 그대로가 됨.** 모터 1차계(시상수 τt)는 지금 코드에
아예 없음 — Stage 1 목표(파이프라인 검증)엔 불필요하다고 판단해 생략된 것으로 보임, 실기 이식 전엔
넣을지 검토.

### 2.2 베인 공력 모델 (§3.2.2) — ⚠️ 코드와 논문이 다른 지점

베인은 "대칭 날개(에어포일)"로 취급, 양력(제어력)·항력(손실) 표준식:

```
F_lift = ½ρv²·Cl·A_fin        (3.11)
F_drag = ½ρv²·Cd·A_fin        (3.12)
```

Cl·Cd를 각도 α의 함수로: 대칭 익형이라 ±10° 이내에서 **선형 근사**(Fig 3.6, XFoil 시뮬레이션값 회귀):

```
Cl(α) = CLα·α     Cd(α) = CD0     (식 3.13–3.14)
CLα = 0.008905, CD0 = 0.001054   ← 논문 저자의 "실제 베인" XFoil 회귀값. 우리 베인(25×45×2.5mm)
                                    형상이 다르므로 그대로 쓰면 안 됨 — params.yaml에 이미 PLACEHOLDER로 표시됨
```

**공기 속도 v는 직접 못 재니, 추력 Ft에서 역산** (배기 단면적 A_duct 가정, 식 3.15):

```
v² = Ft / (A_duct·ρ)
```

이걸 대입해서 **최종적으로 베인력을 "모터 추력 Ft에 비례하는 형태"로 정리**(식 3.16–3.17):

```
F_n  = Ft · [ CLα·A_fin / (2·A_duct) ] · α_n   =  Ft · CL · α_n     ← CL은 "뭉쳐진" 상수 (lumped)
F_dn = Ft · [ CD0·A_fin / (2·A_duct) ]          =  Ft · CD
```

**⚠️ 코드 확인 결과 (2026-09-17)**: `hopper_aviary.py`의
```python
F1, F2, F3, F4 = self.CLalpha * Ft * alpha
```
는 `params.yaml`의 `CLalpha`(=논문의 raw `CLα`, 즉 A_fin/A_duct 기하 비율이 **안 곱해진** 값)를
마치 식 3.16의 **뭉쳐진 CL**(=`CLα·A_fin/(2·A_duct)`)인 것처럼 그대로 쓰고 있다. 즉 코드에
`A_fin/(2·A_duct)` 기하 인자가 아예 빠져 있다.

**지금 당장은 문제 없음** — 값 자체가 전부 PLACEHOLDER라 절대 크기가 의미 없고, Stage 1의 목표는
"파이프라인이 도는가"만 확인하는 것이기 때문. **하지만 실험 A 이후 값을 채울 때 둘 중 하나로 명확히
할 것**:
- (A) 실측 추력-베인각-복원모멘트 데이터를 **직접 회귀**해서 "뭉쳐진 CL"을 바로 구한다 → 지금 코드
  구조(`CLalpha`를 뭉쳐진 CL로 취급) 그대로 써도 됨. **다만 `params.yaml`의 변수명 `CLalpha`를
  `CL_lumped`같은 걸로 바꿔서 혼동 방지 권장.**
- (B) 논문처럼 raw `CLα`(에어포일 자체 특성) + `A_fin`(베인 면적, 실측 가능: 25×45mm) + `A_duct`
  (EDF 배기 단면적, `cad/hopper_params.scad`의 `edf_clamp_id` 근처 값으로 근사 가능)를 따로 구해서
  식 3.16대로 곱한다 → 코드에 `A_fin/(2*A_duct)` 항을 추가해야 함.

## 3. 회전 동역학 (§3.3)

**바디 프레임 토크** (Fig 3.7, l=COM~베인 조인트 거리, r=z축~베인 중심 거리):

```
τx = (F1+F3)·l
τy = -(F2+F4)·l
τz = (F1-F2-F3+F4)·r          (식 3.19)
```

**오일러 방정식**(대각 관성 가정 대입, 식 3.22):

```
ω̇x = (1/Jxx)[(F1+F3)l + (Jyy-Jzz)ωy·ωz]
ω̇y = (1/Jyy)[-(F2+F4)l + (Jzz-Jxx)ωx·ωz]
ω̇z = (1/Jzz)[(F1-F2-F3+F4)r + (Jxx-Jyy)ωx·ωy]
```

**월드(오일러각) 변환** — ZYX Tait-Bryan (식 3.24):

```
φ̇ = ωx + ωz·cosφ·tanθ + ωy·sinφ·tanθ
θ̇ = ωy·cosφ - ωz·sinφ
ψ̇ = (ωz·cosφ + ωy·sinφ) / cosθ
```

→ **코드 대응 확인 완료**: `hopper_aviary.py`의 `tau_x/tau_y/tau_z`, `wx_dot/wy_dot/wz_dot`,
`phi_dot/theta_dot/psi_dot` 모두 위 식과 **정확히 일치**(부호 포함). 여기는 논문 그대로 잘 옮겨졌다.

무게중심-추력축 오프셋(`cg_offset_x/y`, `params.yaml`의 `domain_rand.cg_offset_mm`)은 **논문엔 없는
우리 자체 추가**— 조립 오차로 인한 잔류 토크를 근사하려고 넣은 것(τx += cg_offset_y·Ft 등). 타당한
확장이지만 "논문에 없는 부분"이라는 것만 기록.

## 4. 병진 동역학 (§3.4) — Stage 1엔 미사용, Stage 2용 참고

바디프레임(식 3.29) → 월드프레임(식 3.31) 가속도/속도 식. **위치(x,y,z)까지 제어하는 건 Stage 2**
(위치 구속 M1을 풀고 자유비행 갈 때) — Stage 1(`HopperAttitudeEnv`)은 자세(φ,θ,ψ,ωx,ωy,ωz) 6개
상태만 쓰고 위치·속도는 없음. Stage 2 만들 때 이 절을 그대로 가져다 쓰면 됨.

## 5. 선형화 · 상태공간 (§3.5) — 논문은 LQR용, 우리는 지금 안 씀

논문은 호버점(φ=θ=0, Ft=mg)에서 야코비안 선형화해 12차원 상태공간 모델(식 3.41–3.43)을 만들고
Ch.4에서 LQR 게인을 설계한다. **우리 Stage 1은 이 선형화를 안 거치고 비선형 방정식을 numpy로 직접
적분**(오일러 적분, dt=0.01s) — RL(PPO)은 선형 모델이 필요 없어서다. 이 절은:
- 나중에 **LQR을 PID 대신/추가로 baseline에 넣고 싶으면** 그때 필요 (`AGENTS.md` PID vs RL 프로토콜
  참고 — 지금은 PID 또는 LQR 둘 다 "baseline" 후보로 열어둠).
- 제어 입력 벡터 정의 `u=[α1,α2,α3,α4,ωt]`(식 3.37)는 **우리 action space(5차원, `hopper_aviary.py`)와
  구조가 동일** — 단 우리는 ωt 대신 정규화된 throttle을 씀.

## 6. 코드 ↔ 논문 대응표

| 논문 기호 | 코드 변수 (`hopper_aviary.py`) | 상태 |
|---|---|---|
| `φ,θ,ψ,ωx,ωy,ωz` | `phi,theta,psi,wx,wy,wz` (state) | 일치 |
| `α1..α4` | `a1..a4` → `alpha` (action×alpha_max) | 일치 |
| `ωt` | `omega_t_equiv = throttle*3000` | **근사 — 실제 RPM 아님, 실험 A 후 교체 필요** |
| `Kf` | `params.yaml: Kf` | PLACEHOLDER |
| `Jxx,Jyy,Jzz` | `params.yaml: Jxx,Jyy,Jzz` | PLACEHOLDER |
| `l, r` | `params.yaml: vane_arm_l, vane_arm_r` | **실측 아님 표시돼 있었으나 실제로는 `cad/hopper_params.scad`(베인링 반경 96mm) 기반값 — PLACEHOLDER 아님** |
| `CLα, CD0` (raw) | `params.yaml: CLalpha, CD0` | PLACEHOLDER, **§2의 lumped-CL 이슈 있음 — 교체 시 위 (A)/(B) 중 택1 명시할 것** |
| `Cn = CLα·A_fin/(2A_duct)` (lumped) | 코드에 없음(위와 동일 취급 중) | 위 참고 |
| `τx,τy,τz` | `tau_x,tau_y,tau_z` | 일치 |
| Tait-Bryan 변환 W_η | `phi_dot,theta_dot,psi_dot` 계산부 | 일치(특이점 클리핑은 코드가 더 방어적) |
| 무게중심 오프셋 | `cg_offset_x/y` | **논문에 없음, 우리 자체 추가**(도메인 랜덤화용) |
| 병진 동역학 (§3.4) | 미구현 | Stage 2용 |
| 선형화/상태공간 (§3.5) | 미구현 | LQR 채택 시 필요 |

## 7. 다음에 할 일

1. 실험 A(EDF 추력곡선) → `Kf` 실측, `omega_t_equiv`를 실제 DShot RPM으로 교체.
2. 베인 힌지모멘트·제어효과 실측(TC-2, 마스터 설계도 §11) → §2의 (A) 직접회귀 또는 (B) 기하기반 중 결정.
3. 조립 후 CAD 질량속성으로 §1의 "관성 대각 가정"이 우리 기체에서도 맞는지 확인.
4. Stage 2 착수 시 §4(병진 동역학) 이식.
