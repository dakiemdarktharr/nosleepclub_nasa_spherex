"""Sample a fixed-weight residual profile without optimizing a position.

Costs are r.T @ r, not scipy's half-cost. Finite differences and sampled
connectivity are diagnostics; they provide neither coverage nor a global
minimum certificate. Failed samples remain explicit missing grid nodes.
"""
from collections import deque
from functools import lru_cache
from numbers import Real

import numpy as np
from astropy import units as u


def numeric(value, name, ndim):
    def reject(item):
        if isinstance(item, (u.Quantity, bool, np.bool_)):
            raise ValueError(name+' must be real numeric values without units or booleans')
        if isinstance(item, (list, tuple)):
            for child in item: reject(child)
    reject(value)
    a = np.asarray(value)
    if a.ndim != ndim or a.dtype.kind not in 'iuf':
        raise ValueError(name+' has invalid dimensions or numeric type')
    a = np.asarray(a, float)
    if not np.isfinite(a).all(): raise ValueError(name+' must be finite')
    return a


def positive(value, name):
    if isinstance(value, (bool, np.bool_, u.Quantity)) or not isinstance(value, Real) or not np.isfinite(value) or value <= 0:
        raise ValueError(name+' must be positive finite numeric')
    return float(value)


class ResidualSampler:
    """One residual family, fixed dimensionality, and a finite search square."""
    def __init__(self, callback, anchor, bound):
        if not callable(callback): raise ValueError('residual callback required')
        self.callback = callback
        self.anchor = numeric(anchor, 'anchor', 1).copy()
        if self.anchor.shape != (2,): raise ValueError('anchor needs two coordinates')
        self.bound = positive(bound, 'bound')
        self.dimension = None

    @lru_cache(maxsize=256)
    def _at(self, x, y):
        point = np.asarray([x, y], float)
        if np.any(np.abs(point-self.anchor) > self.bound+1e-12):
            return {'error_code': 'outside_search_square'}
        try:
            raw = self.callback(point.copy())
        except Exception:
            return {'error_code': 'callback_failed'}
        try:
            r = numeric(raw, 'residual', 1)
            if not len(r): raise ValueError('empty residual')
        except (ValueError, TypeError, OverflowError):
            return {'error_code': 'invalid_residual'}
        if self.dimension is not None and len(r) != self.dimension:
            return {'error_code': 'residual_dimension_changed'}
        with np.errstate(over='ignore', invalid='ignore'):
            cost = float(r@r)
        if not np.isfinite(cost): return {'error_code': 'nonfinite_cost'}
        self.dimension = len(r)
        return {'residual': r.copy(), 'cost': cost}

    def at(self, point):
        p = numeric(point, 'position', 1)
        if p.shape != (2,): raise ValueError('position needs two coordinates')
        item = self._at(float(p[0]), float(p[1]))
        return {**item, 'residual': item['residual'].copy()} if 'residual' in item else dict(item)


def probe(sampler, point, steps):
    """Central residual/cost derivatives at declared steps, without clipping."""
    if not isinstance(sampler, ResidualSampler): raise ValueError('ResidualSampler required')
    p = numeric(point, 'position', 1)
    if p.shape != (2,): raise ValueError('position needs two coordinates')
    steps = numeric(steps, 'steps', 1)
    if not len(steps) or np.any(steps <= 0) or len(set(steps)) != len(steps):
        raise ValueError('distinct positive steps required')
    middle = sampler.at(p)
    output = {'position': p.tolist(), 'cost': middle.get('cost'), 'steps': []}
    if 'error_code' in middle:
        output['error_code'] = middle['error_code']; return output
    for h in steps:
        offsets = [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        values = {k: sampler.at(p+h*np.asarray(k)) for k in offsets}
        errors = sorted({v['error_code'] for v in values.values() if 'error_code' in v})
        row = {'step_common_px': float(h)}
        if errors:
            output['steps'].append({**row, 'error_codes': errors}); continue
        f = lambda key: values[key]['cost']
        r = lambda key: values[key]['residual']
        J = np.column_stack(((r((1, 0))-r((-1, 0)))/(2*h), (r((0, 1))-r((0, -1)))/(2*h)))
        gradient_r = 2*J.T@r((0, 0))
        gradient_f = np.asarray([(f((1, 0))-f((-1, 0)))/(2*h), (f((0, 1))-f((0, -1)))/(2*h)])
        off = (f((1, 1))-f((1, -1))-f((-1, 1))+f((-1, -1)))/(4*h*h)
        H = np.asarray([[(f((1, 0))-2*f((0, 0))+f((-1, 0)))/(h*h), off],
                        [off, (f((0, 1))-2*f((0, 0))+f((0, -1)))/(h*h)]])
        GN = 2*J.T@J
        if not all(np.isfinite(a).all() for a in (J, gradient_r, gradient_f, H, GN)):
            output['steps'].append({**row, 'error_codes': ['nonfinite_derivative']}); continue
        norms = np.linalg.norm(J, axis=0)
        if not np.isfinite(norms).all():
            output['steps'].append({**row, 'error_codes': ['nonfinite_derivative']}); continue
        present = norms > 0
        singular = np.linalg.svd(J[:, present]/norms[present], compute_uv=False) if np.any(present) else np.asarray([])
        rank = int(np.sum(singular > 1e-10*singular[0])) if len(singular) else 0
        row.update(gradient_residual=gradient_r.tolist(), gradient_cost=gradient_f.tolist(),
            gradient_infinity=float(np.max(np.abs(gradient_f))),
            gradient_disagreement_infinity=float(np.max(np.abs(gradient_f-gradient_r))),
            hessian_cost=H.tolist(), hessian_cost_eigenvalues=np.linalg.eigvalsh(H).tolist(),
            gauss_newton=GN.tolist(), gauss_newton_eigenvalues=np.linalg.eigvalsh(GN).tolist(),
            residual_jacobian_column_norms=norms.tolist(), residual_jacobian_scaled_rank=rank,
            residual_jacobian_scaled_condition=float(singular[0]/singular[-1]) if rank == 2 else None)
        output['steps'].append(row)
    return output


def components(costs, levels):
    """4/8-connected sampled sublevel sets, relative to the sampled minimum."""
    message = 'rectangular nonnegative finite cost grid required; only None denotes missing'
    if isinstance(costs, np.ndarray) and costs.ndim != 2: raise ValueError(message)
    if isinstance(costs, u.Quantity) or not isinstance(costs, (list, tuple, np.ndarray)) or not len(costs):
        raise ValueError(message)
    checked = []; width = None
    for row in costs:
        if isinstance(row, np.ndarray) and row.ndim != 1: raise ValueError(message)
        if isinstance(row, u.Quantity) or not isinstance(row, (list, tuple, np.ndarray)) or not len(row):
            raise ValueError(message)
        if width is None: width = len(row)
        if len(row) != width: raise ValueError(message)
        values = []
        for value in row:
            if value is None: values.append(np.nan); continue
            if (isinstance(value, (bool, np.bool_, u.Quantity)) or not isinstance(value, Real)
                    or not np.isfinite(value) or value < 0): raise ValueError(message)
            values.append(float(value))
        checked.append(values)
    a = np.asarray(checked, float)
    levels = numeric(levels, 'levels', 1)
    if not len(levels) or np.any(levels < 0) or len(set(levels)) != len(levels): raise ValueError('distinct nonnegative levels required')
    good = np.isfinite(a)
    if not np.any(good): return {'minimum_cost': None, 'valid_nodes': 0, 'missing_nodes': int(a.size), 'levels': []}
    minimum = float(np.min(a[good])); rows = []
    for level in levels:
        mask = good & (a-minimum <= level)
        for connectivity in (4, 8):
            seen = set(); groups = []
            neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            if connectivity == 8: neighbors += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            for y, x in zip(*np.nonzero(mask)):
                if (y, x) in seen: continue
                seen.add((y, x)); queue = deque([(y, x)]); size = 0; edge = False; missing = False
                while queue:
                    yy, xx = queue.popleft(); size += 1
                    edge |= yy in (0, a.shape[0]-1) or xx in (0, a.shape[1]-1)
                    for dy, dx in neighbors:
                        ny, nx = yy+dy, xx+dx
                        if 0 <= ny < a.shape[0] and 0 <= nx < a.shape[1]:
                            missing |= not good[ny, nx]
                            if mask[ny, nx] and (ny, nx) not in seen:
                                seen.add((ny, nx)); queue.append((ny, nx))
                groups.append({'nodes': size, 'touches_grid_boundary': bool(edge), 'touches_missing_node': bool(missing)})
            rows.append({'delta_cost': float(level), 'connectivity': connectivity, 'component_count': len(groups), 'components': groups})
    return {'minimum_cost': minimum, 'valid_nodes': int(good.sum()), 'missing_nodes': int(a.size-good.sum()), 'levels': rows}


def grid(sampler, x_values, y_values, levels):
    if not isinstance(sampler, ResidualSampler): raise ValueError('ResidualSampler required')
    axes = [numeric(axis, 'grid axis', 1) for axis in (x_values, y_values)]
    if any(len(a) < 2 or len(a) > 101 or np.any(np.diff(a) <= 0) for a in axes):
        raise ValueError('strictly increasing grid axes of 2 to 101 entries required')
    costs = []; failures = []
    for iy, y in enumerate(axes[1]):
        row = []
        for ix, x in enumerate(axes[0]):
            item = sampler.at([x, y]); row.append(item.get('cost'))
            if 'error_code' in item: failures.append({'ix': ix, 'iy': iy, 'error_code': item['error_code']})
        costs.append(row)
    return {'x_common_px': axes[0].tolist(), 'y_common_px': axes[1].tolist(), 'costs': costs,
            'failures': failures, 'sampled_connectivity': components(costs, levels)}
