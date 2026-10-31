"""Prefreeze information-only feasibility on previously published star fits.

No new position fit, shape estimate, random realization or prospective field
is evaluated. Residual shape scores are deliberately not saved or reported.
"""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
import subprocess

if __name__ == '__main__':
    for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                  'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[_name] = '1'

import numpy as np

from . import run_reference_star_study as old
from . import run_wise_linked_study as legacy
from .shape_native_inputs import prepare_shape_sample
from .moment_preserving_epsf import physical_parameters, DEFAULT_BOUNDS
from .profile_image_influence import centroid_and_shape_influence
from .shared_pixel_covariance import make_registry, add_pixel_response
from .composite_shape_update import information
from .experiment_journal import Journal
from .science_jobs import atomic


COMMIT = '71f63ca4bab85e9ee51c539cd46ae5bfd50c8bc2'
OUTPUT = old.ROOT / 'data/raw/benchmark/shape-information-prefreeze.json'
SOURCES = ('scripts/moment_preserving_epsf.py', 'scripts/profile_image_influence.py',
           'scripts/shape_native_inputs.py', 'scripts/shared_pixel_covariance.py',
           'scripts/composite_shape_update.py', 'scripts/joint_reference_frame.py',
           'scripts/inspect_shape_information.py')


def exposure_split(context):
    learning = [];reserved = []
    for epoch in ('2025-11', '2026-04'):
        frames = [f for f in context.frames if f['record']['epoch'] == epoch]
        if len(frames) != 10:
            raise ValueError('expected ten opened frames per season')
        learning.extend(f['record']['obs_id'] for f in frames[:6])
        reserved.extend(f['record']['obs_id'] for f in frames[6:])
    return learning, reserved


def build():
    old.frozen.verify(old.DESIGN, old.RULES, old.SOURCES, COMMIT)
    context = old.inputs.read_context();learning, reserved = exposure_split(context)
    expected_identity = old.frozen.identity(old.DESIGN, COMMIT, old.frozen.runtime(), 'real-reference-stars')
    journal = Journal(old.OUTPUT, expected_identity, old.expected_keys(context),
                      ('fit_completed', 'fit_failed', 'preparation_failed'))
    journal.records(require_complete=True)
    rows = [];cells = []
    for reference in context.references:
        sid = reference['catalog']['source_id']
        if sid not in context.training_ids:
            continue
        for frame in context.frames:
            obs = frame['record']['obs_id']
            if obs not in learning:
                continue
            saved = journal.read((sid, obs, 'nearest'))['payload']
            row = {'key': [sid, obs], 'source_id': sid, 'obs_id': obs, 'epoch': frame['record']['epoch'],
                   'old_status': saved['status'], 'status': 'upstream_unavailable'}
            if saved['status'] != 'fit_completed':
                row['reason'] = saved['error'];rows.append(row);continue
            if not saved['fit']['numerical_support']:
                row.update(status='old_numerical_refusal', reason=saved['fit']['numerical_reasons'])
                rows.append(row);continue
            try:
                prepared, metadata = old.inputs.prepare_cell(context, reference, frame)
                item = prepare_shape_sample(prepared, metadata['anchor_sky_px'], physical_parameters([0., 0., 0.]))
                response = centroid_and_shape_influence(item, saved['fit'], metadata['anchor_sky_px'])
                cell = {'key': (sid, obs), 'source_id': sid, 'obs_id': obs,
                        'x': item['metadata']['x'], 'y': item['metadata']['y'], 'error': item['error'],
                        'shape_information_scaled': response['shape_information_scaled'],
                        'shape_score_pixel_response': response['shape_score_pixel_response']}
                cells.append(cell)
                # No shape residual score or estimated parameter is published.
                row.update(status='information_available', local_condition=response['condition'],
                           information_scaled=response['shape_information_scaled'].tolist(),
                           native_phase=(np.asarray(metadata['native_anchor_xy']) % 1).tolist(),
                           pixel_count=len(item['data']))
            except Exception as exc:
                row.update(status='information_failed', reason=type(exc).__name__+': '+str(exc))
            rows.append(row)
    planned = len(context.training_ids)*len(learning)
    if len(rows) != planned or planned != 168:
        raise ValueError('calibration-only feasibility denominator changed')
    summary = {}
    try:
        info = information(cells)
        registry = make_registry(cells)
        score_response = add_pixel_response(registry, cells, response_key='shape_score_pixel_response', output_rows=3)
        G = np.linalg.solve(info['matrix'], score_response)
        covariance = (G*registry.variance[None, :])@G.T
        summary = {'sources': info['sources'], 'information_scaled': info['matrix'],
                   'condition': info['condition'], 'source_information_fractions': info['source_fractions'],
                   'maximum_source_fraction': info['max_source_fraction'],
                   'nominal_scaled_standard_errors': np.sqrt(np.diag(covariance)),
                   'physical_parameter_scales': DEFAULT_BOUNDS,
                   'unique_original_pixels': len(registry.keys),
                   'qualification': 'conditional known-noise linear information, not measured shape precision or source accuracy'}
    except Exception as exc:
        summary = {'unavailable': type(exc).__name__+': '+str(exc)}
    return legacy.jsonable({'scope': 'prefreeze descriptive feasibility on opened old calibration fits only',
        'at_utc': datetime.now(timezone.utc).isoformat(), 'baseline_protocol_commit': COMMIT,
        'baseline_design_sha256': legacy.lab.digest(old.DESIGN),
        'source_hashes': {path: legacy.lab.digest(old.ROOT/path) for path in SOURCES},
        'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=old.ROOT, text=True).strip(),
        'new_code_not_yet_frozen': True, 'shape_estimate_evaluated': False,
        'learning_sources': list(context.training_ids), 'learning_exposures': learning,
        'reserved_exposures': reserved, 'planned': planned,
        'counts': dict(Counter(r['status'] for r in rows)), 'summary': summary, 'records': rows,
        'qualifications': ['no new point fit, corrected heldout result, noise draw or new field',
            '21-source cohort previously image selected and already opened',
            'exclusions and all planned 168 calibration cells retained',
            'rank and conditional precision do not prove improvement or scientific calibration']})


def main():
    if OUTPUT.exists():
        raise RuntimeError('prefreeze receipt exists; do not overwrite a viewed diagnostic')
    result = build();atomic(OUTPUT, result)
    print(json.dumps({'planned': result['planned'], 'counts': result['counts'], 'summary': result['summary'],
                      'output': legacy.relative(OUTPUT)}, indent=2))


if __name__ == '__main__':
    main()
