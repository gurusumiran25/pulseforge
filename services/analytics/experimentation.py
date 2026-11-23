"""Two-arm binary-outcome A/B experiment analysis with explicit limitations.

Fixed-horizon, independent randomized units only. No sequential peeking,
multiple-comparison correction, covariate adjustment or causal guarantee.
"""
from math import erfc, isfinite, sqrt
from statistics import NormalDist


def analyze_binary_experiment(*, control_conversions, control_total,
                              treatment_conversions, treatment_total, alpha=0.05):
    """Compute two-sided pooled two-proportion z-test and unpooled Wald CI.

    The Wald interval is a simple approximation and can be inaccurate for
    small samples or rates near 0/1. The p-value is descriptive only when
    randomization and independence assumptions hold.
    """
    counts = (control_conversions, control_total, treatment_conversions, treatment_total)
    if any(not isinstance(n, int) or isinstance(n, bool) for n in counts):
        raise TypeError("Counts must be integers")
    if control_total <= 0 or treatment_total <= 0:
        raise ValueError("Experiment arms must have positive sample sizes")
    if not (0 <= control_conversions <= control_total and
            0 <= treatment_conversions <= treatment_total):
        raise ValueError("Conversions must be between zero and arm size")
    if not isinstance(alpha, (int, float)) or isinstance(alpha, bool) or not isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be between zero and one")
    control_rate = control_conversions / control_total
    treatment_rate = treatment_conversions / treatment_total
    lift = treatment_rate - control_rate
    pooled = (control_conversions + treatment_conversions) / (control_total + treatment_total)
    pooled_se = sqrt(pooled * (1 - pooled) * (1 / control_total + 1 / treatment_total))
    if pooled_se == 0:
        p_value = 1.0
        z_statistic = 0.0
    else:
        z_statistic = lift / pooled_se
        p_value = erfc(abs(z_statistic) / sqrt(2))
    unpooled_se = sqrt(
        control_rate * (1 - control_rate) / control_total +
        treatment_rate * (1 - treatment_rate) / treatment_total
    )
    critical = NormalDist().inv_cdf(1 - alpha / 2)
    lower = lift - critical * unpooled_se
    upper = lift + critical * unpooled_se
    return {
        "control": {"conversions": control_conversions, "total": control_total, "rate": control_rate},
        "treatment": {"conversions": treatment_conversions, "total": treatment_total, "rate": treatment_rate},
        "absolute_lift": lift,
        "relative_lift": lift / control_rate if control_rate else None,
        "z_statistic": z_statistic,
        "p_value_two_sided": p_value,
        "alpha": float(alpha),
        "significant": p_value < alpha,
        "difference_ci_wald": {"lower": lower, "upper": upper},
        "method": "pooled two-proportion z-test; unpooled Wald confidence interval",
        "limitations": "fixed-horizon independent randomized units; no peeking or multiple-testing correction",
    }
