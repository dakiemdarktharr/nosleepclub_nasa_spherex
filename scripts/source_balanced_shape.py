"""Calibration-information-only source weights for one composite shape model.

Weights equalize mean trace information per available source exposure, using
the declared physical parameter scales. Neither residuals nor holdout results
enter the weights. The original dominance/precision guards still apply.
"""
from dataclasses import dataclass

import numpy as np

from .shared_pixel_covariance import finite


POLICY = 'median positive source mean information trace / source mean information trace'


@dataclass(frozen=True)
class SourceBalance:
    cells: tuple
    source_weights: dict
    source_counts: dict
    reference_mean_trace: float
    policy: str = POLICY


def balance_sources(cells, *, include_scores=True):
    if not isinstance(include_scores, bool) or not cells:
        raise ValueError('nonempty cells and explicit score mode required')
    grouped = {};counts = {};keys = set()
    for cell in cells:
        source = cell.get('source_id');obs = cell.get('obs_id')
        if (not isinstance(source, str) or not source or not isinstance(obs, str) or not obs
                or not isinstance(cell.get('key'), (tuple, list))
                or tuple(cell['key']) != (source, obs) or (source, obs) in keys):
            raise ValueError('unique matching calibration source/exposure identity required')
        keys.add((source, obs))
        F = finite(cell['shape_information_scaled'], (3, 3), 'source information')
        scale = float(np.max(np.abs(F)))
        if (not np.allclose(F, F.T, rtol=0., atol=1e-12*scale)
                or np.linalg.eigvalsh(F/2+F.T/2)[0] < -1e-12*scale):
            raise ValueError('source information must be symmetric PSD')
        with np.errstate(over='ignore', invalid='ignore'):
            grouped[source] = grouped.get(source, np.zeros((3, 3)))+F
        if not np.isfinite(grouped[source]).all():
            raise ValueError('summed source information is nonfinite')
        counts[source] = counts.get(source, 0)+1
    with np.errstate(over='ignore', invalid='ignore'):
        means = {source: float(np.trace(F))/counts[source] for source, F in grouped.items()}
    if any(not np.isfinite(v) or v <= 0 for v in means.values()):
        raise ValueError('each represented calibration source requires positive finite mean information')
    ordered = sorted(means.values());middle = len(ordered)//2
    reference = (ordered[middle] if len(ordered) % 2 else
                 ordered[middle-1]+(ordered[middle]-ordered[middle-1])/2)
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        weights = {source: reference/value for source, value in means.items()}
    if any(not np.isfinite(v) or v <= 0 for v in weights.values()):
        raise ValueError('source balance is numerically unrepresentable')
    output = []
    for cell in cells:
        weight = weights[cell['source_id']]
        with np.errstate(over='ignore', invalid='ignore'):
            copy = {**cell, 'source_balance_weight': weight,
                    'shape_information_scaled': finite(cell['shape_information_scaled'], (3, 3), 'information')*weight}
            if include_scores:
                n = len(cell['error'])
                copy['shape_score_scaled'] = finite(cell['shape_score_scaled'], (3,), 'shape score')*weight
                copy['shape_score_pixel_response'] = finite(cell['shape_score_pixel_response'], (3, n), 'shape score pixel response')*weight
            else:
                # The feasibility API cannot accidentally expose a residual score.
                copy.pop('shape_score_scaled', None);copy.pop('shape_score_pixel_response', None)
        fields = ('shape_information_scaled', 'shape_score_scaled', 'shape_score_pixel_response') if include_scores else ('shape_information_scaled',)
        if any(not np.isfinite(copy[field]).all() for field in fields):
            raise ValueError('weighted information or score is nonfinite')
        output.append(copy)
    return SourceBalance(tuple(output), weights, counts, reference)
