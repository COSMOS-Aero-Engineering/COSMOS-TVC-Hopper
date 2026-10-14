"""입문용 P/PD 부호 연습. 호퍼 물리 모델·PWM·비행 제어기가 아닙니다."""
import math

def exercise(angle_deg, rate_deg_s, target_deg=0.0):
    # 아래 계수는 교육 예제용이며 실제 기체에 사용하는 게인이 아니다.
    kp, kd = 1.0, 0.1
    error = math.radians(target_deg - angle_deg)
    rate_error = math.radians(-rate_deg_s)  # 고정 목표의 목표 각속도는 0
    p = kp * error
    d = kd * rate_error
    return p, d, max(-1.0, min(1.0, p + d))

def main():
    print("Teaching only: outputs are normalized requests, not servo PWM.")
    print("angle_deg rate_deg_s P D clipped_PD")
    for angle, rate in [(0,0),(10,0),(-10,0),(10,30),(10,-30),(180,0)]:
        p, d, request = exercise(angle, rate)
        print(f"{angle:9.1f} {rate:10.1f} {p: .4f} {d: .4f} {request: .4f}")
    assert exercise(0, 0)[2] == 0
    assert exercise(10, 0)[2] < 0 < exercise(-10, 0)[2]
    assert exercise(10, 30)[2] < exercise(10, 0)[2]
    assert exercise(10, -30)[2] > exercise(10, 0)[2]
    assert exercise(180, 0)[2] == -1.0
    print("PASS: zero error, restoring sign, damping and output limit.")

if __name__ == "__main__":
    main()
