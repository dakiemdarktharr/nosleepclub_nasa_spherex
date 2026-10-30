"""Observed profile-objective curvature and constrained motion likelihood.

The Gauss-Newton Jacobian approximation omits residual second derivatives.
Linear flux/background nuisance parameters are already profiled out. IRLS
weights remain fixed here, so these are candidate conditional uncertainties,
not validated astronomical confidence regions.
"""
import numpy as np
from scipy.optimize import least_squares
from . import ablation_model as model

RULES = {"version": "0.10.0-profile-development.1", "steps_sky_px": [.002, .004],
         "maximum_hessian_relative_change": .05, "fit_bound_px": 2.5,
         "qualification": "fixed-final-IRLS-weight observed profile Hessian; no physical PSF/background/reference systematics"}


def hessian(residual, position, step):
    x = np.asarray(position, float); n = len(x); result = np.empty((n, n))
    def objective(p):
        r = np.asarray(residual(p), float)
        return float(r @ r) / 2
    center = objective(x); axes = np.eye(n) * step
    for i in range(n):
        result[i, i] = (objective(x + axes[i]) - 2 * center + objective(x - axes[i])) / step ** 2
        for j in range(i):
            result[i, j] = result[j, i] = (objective(x + axes[i] + axes[j]) - objective(x + axes[i] - axes[j])
                - objective(x - axes[i] + axes[j]) + objective(x - axes[i] - axes[j])) / (4 * step ** 2)
    return result


def residual_for(samples):
    return lambda p: np.concatenate([model.joint.residual_sample(s, p) for s in samples])


def covariance(fit):
    residual = residual_for(fit["samples"])
    matrices = [hessian(residual, fit["position"], step) for step in RULES["steps_sky_px"]]
    change = float(np.linalg.norm(matrices[0] - matrices[1]) / max(np.linalg.norm(matrices[1]), 1e-15))
    output = {"hessians": [m.tolist() for m in matrices], "relative_step_change": change, "supported": False}
    if not np.isfinite(matrices).all() or change > RULES["maximum_hessian_relative_change"]:
        return {**output, "reason": "unstable_profile_curvature"}
    information = (matrices[0] + matrices[0].T) / 2
    if np.linalg.eigvalsh(information).min() <= 0:
        return {**output, "reason": "nonpositive_profile_curvature"}
    return {**output, "supported": True, "covariance_px2": (np.linalg.inv(information) * max(1., fit["reduced_chi2"])).tolist()}


def motion_likelihood(fits, anchor, delta):
    """Profile two position nuisance parameters under a specified motion.

Comparing the sum of two truth-position costs to a two-degree threshold would
wrongly fix four parameters. This fits the common initial location at each
specified delta, so only two motion coordinates are constrained.
"""
    anchor = np.asarray(anchor, float); delta = np.asarray(delta, float)
    residuals = [residual_for(f["samples"]) for f in fits]
    low = np.maximum(anchor - RULES["fit_bound_px"], anchor - RULES["fit_bound_px"] - delta)
    high = np.minimum(anchor + RULES["fit_bound_px"], anchor + RULES["fit_bound_px"] - delta)
    if np.any(low >= high):
        return {"supported": False, "reason": "infeasible_motion"}
    def residual(p):
        return np.r_[residuals[0](p), residuals[1](p + delta)]
    midpoint = (fits[0]["position"] + fits[1]["position"] - delta) / 2
    start = np.clip(midpoint, low + 1e-6, high - 1e-6)
    fit = least_squares(residual, start, bounds=(low, high), ftol=1e-9, xtol=1e-9, gtol=1e-8, max_nfev=120)
    unconstrained = sum(float(r(f["position"]) @ r(f["position"])) for r, f in zip(residuals, fits))
    difference = float(fit.fun @ fit.fun - unconstrained)
    if not fit.success or difference < -1e-4:
        return {"supported": False, "reason": "constrained_better_mode" if difference < -1e-4 else "constrained_solver_failed",
                "delta_chi2": difference}
    return {"supported": True, "delta_chi2": max(0., difference), "profile_initial_position_px": fit.x.tolist(),
            "qualification": "motion likelihood with profiled initial position, conditional on final robust weights"}
