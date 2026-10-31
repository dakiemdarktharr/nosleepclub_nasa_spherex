"""Known-pixel and shared-shape linear covariance, with overlap cross terms.

Rows describe common-grid position coordinates. Intensities/errors use MJy/sr;
shape responses use the ordered native pixel²/pixel³ parameter convention.
The construction is conditional, not an empirical coverage calibration.
"""
from dataclasses import dataclass
from numbers import Integral

import astropy.units as u
import numpy as np
from scipy import sparse


def finite(value, shape, name):
    if isinstance(value, u.Quantity) or any(isinstance(v, (bool, np.bool_))
                                           for v in np.asarray(value, dtype=object).ravel()):
        raise ValueError(name + ' must use declared numeric units without booleans')
    a = np.asarray(value)
    if a.shape != shape or a.dtype.kind not in 'iuf' or not np.isfinite(a).all():
        raise ValueError('invalid ' + name)
    return a.astype(float)


def pixel_keys(record):
    obs = record['obs_id'];x = np.asarray(record['x']);y = np.asarray(record['y'])
    if any(isinstance(v, (bool, np.bool_)) for a in (record['x'], record['y']) for v in np.asarray(a, dtype=object).ravel()):
        raise ValueError('native pixel coordinates cannot be booleans')
    if (not isinstance(obs, str) or not obs or x.ndim != 1 or not len(x) or y.shape != x.shape
            or x.dtype.kind not in 'iu' or y.dtype.kind not in 'iu'
            or np.any(x < 0) or np.any(y < 0)):
        raise ValueError('exact nonnegative native pixel coordinates and exposure ID required')
    keys = tuple((obs, int(xx), int(yy)) for xx, yy in zip(x, y))
    if len(set(keys)) != len(keys):
        raise ValueError('duplicate pixel within one sample')
    return keys


@dataclass(frozen=True)
class PixelRegistry:
    keys: tuple
    variance: np.ndarray
    index: dict


def make_registry(records):
    values = {}
    for record in records:
        keys = pixel_keys(record);error = finite(record['error'], (len(keys),), 'original errors')
        if np.any(error <= 0):
            raise ValueError('original pixel errors must be positive')
        for key, sigma in zip(keys, error):
            variance = float(sigma*sigma)
            if not np.isfinite(variance) or variance <= 0:
                raise ValueError('unrepresentable pixel variance')
            if key in values and not np.isclose(values[key], variance, rtol=1e-12, atol=0.):
                raise ValueError('one physical pixel has contradictory original variances')
            values[key] = variance
    if not values:
        raise ValueError('no original pixels')
    keys = tuple(sorted(values));variance = np.asarray([values[k] for k in keys])
    return PixelRegistry(keys, variance, {key: i for i, key in enumerate(keys)})


def add_pixel_response(registry, records, *, response_key, output_rows):
    """Sum contributions to the SAME image pixel; do not duplicate its noise."""
    if isinstance(output_rows, (bool, np.bool_)) or not isinstance(output_rows, Integral) or output_rows <= 0:
        raise ValueError('positive integer output row count required')
    result = np.zeros((output_rows, len(registry.keys)))
    for record in records:
        keys = pixel_keys(record)
        response = finite(record[response_key], (output_rows, len(keys)), response_key)
        error = finite(record['error'], (len(keys),), 'original errors')
        if np.any(error <= 0):
            raise ValueError('original errors must be positive')
        for j, key in enumerate(keys):
            if key not in registry.index or not np.isclose(registry.variance[registry.index[key]], error[j]**2, rtol=1e-12, atol=0.):
                raise ValueError('pixel response disagrees with registry')
            result[:, registry.index[key]] += response[:, j]
    return result


def position_covariance(registry, records, *, shape_pixel_influence=None):
    """Covariance of A*noise + R*theta_hat, including BOTH cross terms.

    Each row-record has ``position_pixel_influence`` (2 x N) and optional
    ``position_shape_response`` (2 x 3). ``shape_pixel_influence`` maps the
    registry's unique image intensities to the three physical shape parameters.
    """
    if not records:
        raise ValueError('at least one measured position required')
    rows = [];cols = [];values = [];responses = []
    for i, record in enumerate(records):
        keys = pixel_keys(record);error = finite(record['error'], (len(keys),), 'original errors')
        if np.any(error <= 0):
            raise ValueError('original errors must be positive')
        influence = finite(record['position_pixel_influence'], (2, len(keys)), 'position influence')
        response = finite(record.get('position_shape_response', np.zeros((2, 3))), (2, 3), 'shape response')
        responses.append(response)
        for j, key in enumerate(keys):
            if key not in registry.index or not np.isclose(registry.variance[registry.index[key]], error[j]**2, rtol=1e-12, atol=0.):
                raise ValueError('position pixel disagrees with registry')
            for axis in range(2):
                rows.append(2*i+axis);cols.append(registry.index[key]);values.append(influence[axis, j])
    A = sparse.csr_matrix((values, (rows, cols)), shape=(2*len(records), len(registry.keys)))
    R = np.vstack(responses)
    if shape_pixel_influence is None:
        G = np.zeros((3, len(registry.keys)));R = np.zeros_like(R)
    else:
        G = finite(shape_pixel_influence, (3, len(registry.keys)), 'shared shape pixel influence')
    weighted = A.multiply(registry.variance[None, :])
    base = (weighted@A.T).toarray()
    shape_cov = (G*registry.variance[None, :])@G.T
    position_shape_cov = np.asarray(weighted@G.T)
    covariance = base + R@shape_cov@R.T + position_shape_cov@R.T + R@position_shape_cov.T
    covariance = (covariance+covariance.T)/2
    if not np.isfinite(covariance).all() or np.any(np.diag(covariance) <= 0):
        raise ValueError('invalid propagated position covariance')
    return {'covariance_px2': covariance, 'pixel_only_covariance_px2': base,
            'shape_covariance_physical_units': shape_cov,
            'position_shape_covariance': position_shape_cov,
            'position_pixel_influence': A, 'position_shape_response': R,
            'qualification': 'original diagonal image variance, fixed profile weights/tangents and estimated shape response; excludes unknown detector/model/selection covariance'}


def catalogue_covariance(source_ids, jacobians, source_covariances):
    """Shared five-parameter catalogue error for every observation of a source.

    Numeric Jacobians are common-grid pixels per source's declared native
    parameter units. Different catalogue source errors are assumed independent.
    Neighbour-coordinate and catalogue--shape dependence are not added here.
    """
    if (isinstance(source_ids, (str, bytes)) or len(source_ids) != len(jacobians) or not source_ids
            or any(not isinstance(s, str) or not s for s in source_ids)):
        raise ValueError('matching nonempty source IDs and catalogue Jacobians required')
    n = len(source_ids);result = np.zeros((2*n, 2*n))
    for source in sorted(set(source_ids)):
        if source not in source_covariances:
            raise ValueError('missing declared source covariance')
        C = finite(source_covariances[source], (5, 5), 'five-parameter covariance')
        if np.any(np.diag(C) <= 0):
            raise ValueError('invalid catalogue diagonal')
        std = np.sqrt(np.diag(C))
        normalized = C/std[:, None]/std[None, :]
        if not np.isfinite(normalized).all() or not np.allclose(normalized, normalized.T, rtol=0., atol=1e-12):
            raise ValueError('asymmetric catalogue covariance')
        try:
            np.linalg.cholesky((normalized+normalized.T)/2)
        except np.linalg.LinAlgError as exc:
            raise ValueError('catalogue covariance is not positive definite') from exc
        indices = [i for i, sid in enumerate(source_ids) if sid == source]
        J = np.vstack([finite(jacobians[i], (2, 5), 'catalogue Jacobian') for i in indices])
        rows = np.asarray([axis for i in indices for axis in (2*i, 2*i+1)])
        result[np.ix_(rows, rows)] = J@C@J.T
    if not np.isfinite(result).all():
        raise ValueError('unrepresentable catalogue position covariance')
    return (result+result.T)/2
