"""Montrasio & Valentino (2008) SLIP model, discrete rainfall increments.

All times in seconds, rainfall depths in metres, stresses in kPa,
water unit weight in kN/m3. N, C, W and F are forces per unit
reference sliding area (numerically in kPa).
"""

from dataclasses import dataclass
from math import radians, sin, cos, tan, exp, isfinite


@dataclass
class SoilParameters:
    H: float
    beta: float
    n: float
    Gs: float
    phi: float
    c: float
    A: float
    lam: float
    alpha: float
    theta: float
    KT: float
    gamma_w: float = 9.81


def calculate_slip(p, rainfall, time_s):
    """Evaluate SLIP at time_s using rainfall [(event_time_s, depth_m), ...].

    Discrete rainfall depths are applied at their event timestamps.
    The physical upper bound m=1 is applied to the stability calculation;
    m_raw is returned so exceedance can be diagnosed.
    """
    parameters = (
        p.H, p.beta, p.n, p.Gs, p.phi, p.c, p.A,
        p.lam, p.alpha, p.theta, p.KT, p.gamma_w, time_s,
    )
    if not all(isfinite(x) for x in parameters):
        raise ValueError("Soil, geometry and time inputs must be finite.")
    if not (p.H > 0 and 0 < p.n < 1 and 0 <= p.theta < p.n and
            0 < p.beta < 90 and 0 <= p.phi < 90 and p.KT >= 0 and
            p.Gs > 0 and p.gamma_w > 0 and p.A >= 0 and
            p.lam >= 0 and p.alpha >= 0 and p.c >= 0):
        raise ValueError("Invalid soil or geometry inputs.")
    if time_s < 0 or any(
        not isfinite(t) or not isfinite(h) or t < 0 or h < 0
        for t, h in rainfall
    ):
        raise ValueError("Invalid rainfall or evaluation time.")

    beta = radians(p.beta)
    phi = radians(p.phi)
    Sr = p.theta / p.n

    # Montrasio & Valentino (2008), Eq. (22).
    decay = p.KT * sin(beta) / (p.n * (1 - Sr))
    m_raw = sum(
        h / (p.n * p.H * (1 - Sr)) * exp(-decay * (time_s - t))
        for t, h in rainfall if t <= time_s
    )
    exceeded = m_raw > 1.0
    m = min(m_raw, 1.0)

    # Published Eqs. (3), (4), (6), (12), reference area = 1 m2.
    B = m * (p.n - 1) + p.Gs * (1 - p.n) + p.n * Sr * (1 - m)
    W = cos(beta) * p.H * p.gamma_w * B
    N = cos(beta) ** 2 * p.H * p.gamma_w * B
    F = p.gamma_w * sin(beta) * cos(beta) * m * p.H
    C = p.c + p.A * Sr * (1 - Sr) ** p.lam * (1 - m) ** p.alpha

    denominator = W * sin(beta) + F
    if denominator <= 0:
        raise ValueError("SLIP equilibrium denominator is nonpositive.")
    FS = (N * tan(phi) + C) / denominator

    return {
        "time_s": time_s,
        "m": m,
        "m_raw": m_raw,
        "FS": FS,
        "N": N,
        "C": C,
        "W": W,
        "F": F,
        "saturation_limit_exceeded": exceeded,
    }


if __name__ == "__main__":
    soil = SoilParameters(
        H=0.30, beta=35, n=0.50, Gs=2.65, phi=30,
        c=0, A=40, lam=0.4, alpha=3.4,
        theta=0.15, KT=7.5e-7,
    )
    rainfall = [(i * 120, 57.5 / 1000 * (2 / 60)) for i in range(1, 21)]
    for minute in range(0, 41, 5):
        result = calculate_slip(soil, rainfall, minute * 60)
        print(f"Time: {minute:2d} min | m = {result['m']:.6f} | FS = {result['FS']:.4f}")
