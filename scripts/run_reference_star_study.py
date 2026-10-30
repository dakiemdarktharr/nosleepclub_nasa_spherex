"""Native reference-star comparison, all 840 attempts with durable records.

Three disjoint CLI shards share an immutable journal. No source is selected
from these new fit results. This is an opened, image-selected development
cohort, not an independent instrumental or scientific accuracy validation.
"""
import argparse
from numbers import Integral
import os
import time

THREAD_ENV = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
              'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')
if __name__ == '__main__':
    for _name in THREAD_ENV:
        os.environ[_name] = '1'

import astropy.units as u
from astropy.coordinates import SkyCoord
import numpy as np

from . import frozen_experiment as frozen
from . import reference_star_inputs as inputs
from . import neighbor_intervention_inputs as semantic
from . import neighbor_epoch_model as model
from . import run_neighbor_intervention as previous
from . import run_wise_linked_study as legacy
from .experiment_journal import Journal
from .science_jobs import locked


ROOT = frozen.ROOT
DESIGN = ROOT / 'web/data/reference-stars/design.json'
OUTPUT = ROOT / 'data/raw/benchmark/reference-stars'
RULES = {**inputs.RULES, 'version': '0.10.0-reference-stars.1',
         'planned_attempts': 840, 'shards': 3,
         'time': 'actual IMAGE MJD-AVG UTC; first-order Gaia PM and Earth parallax',
         'target_flux': 'signed, independent Jy per native exposure',
         'point_model': 'unchanged neighbor_epoch_model, nine starts, bounded 2.5 sky pixels',
         'max_irls_iterations': 20,
         'start_offsets': list(model.START_OFFSETS),
         'numerical_screening': 'reported alongside all fits, never used to drop a planned attempt',
         'registration_covariance': 'legacy nominal conditional matrix only; not total error',
         'catalog_cross_time': 'full shared five-parameter Gaia covariance component retained separately',
         'reporting': 'paired all-completed and common-numerical subsets; source-level and frame-level summaries',
         'uncertainty': 'no calibrated centroid covariance or detection probability',
         'promotion': False}
SOURCES = ('scripts/frozen_experiment.py', 'scripts/experiment_journal.py',
           'scripts/reference_star_inputs.py', 'scripts/run_reference_star_study.py',
           'scripts/astrometric_time_model.py', 'tests/test_reference_star_inputs.py',
           'tests/test_frozen_experiment.py',
           'tests/test_experiment_journal.py', 'tests/test_reference_star_study.py',
           'docs/REFERENCE_STAR_PROTOCOL.md')


def expected_keys(context):
    keys = [(r['catalog']['source_id'], f['record']['obs_id'], variant)
            for r in context.references for f in context.frames for variant in RULES['epsf_variants']]
    if len(keys) != RULES['planned_attempts'] or len(set(keys)) != len(keys):
        raise RuntimeError('planned reference denominator changed')
    return keys


def create_design():
    context = inputs.read_context()  # geometry/catalog metadata only; no point fit
    metadata = {'sources': [{'source_id': r['catalog']['source_id'], 'legacy_split': r['split']}
                            for r in context.references],
                'obs_ids': [f['record']['obs_id'] for f in context.frames],
                'time_metadata': [f['exposure_time'] for f in context.frames],
                'expected_keys': expected_keys(context),
                'qualification': 'all previously image-selected stars in one opened field; no new fit outcomes'}
    return frozen.create(DESIGN, RULES, SOURCES, metadata=metadata)


def sky_residual_arcsec(position, anchor):
    """Exact tangent east/north offsets in the common sky WCS, not a fit error."""
    wcs = inputs.gaia.motion.WCS
    predicted = SkyCoord(*wcs.pixel_to_world_values(*anchor), unit=u.deg)
    measured = SkyCoord(*wcs.pixel_to_world_values(*position), unit=u.deg)
    east, north = predicted.spherical_offsets_to(measured)
    return [float(east.to_value(u.arcsec)), float(north.to_value(u.arcsec))]


def attempt(prepared, metadata, variant):
    started = time.monotonic();stage = 'preparation'
    row = {'status': 'preparation_failed', 'variant': variant, 'metadata': metadata,
           'data_role': 'measured IMAGE minus ZODI minus legacy scalar; native pixels'}
    try:
        anchor = np.asarray(metadata['anchor_sky_px'])
        item = inputs.prepare_variant(prepared, anchor, variant)
        row['samples'] = previous.descriptors([item]);stage = 'fit'
        result = model.fit_epoch(semantic.model_samples([item]), anchor, data_unit='MJy/sr',
                                 nonnegative_neighbors=False, max_irls_iterations=RULES['max_irls_iterations'])
        if [f['obs_id'] for f in result['frames']] != [prepared['obs_id']]:
            raise RuntimeError('fit exposure differs from planned identity')
        row.update(status='fit_completed', fit=legacy.jsonable(result),
                   residual_east_north_arcsec=sky_residual_arcsec(result['position'], anchor))
    except Exception as exc:
        row.update(status='fit_failed' if stage == 'fit' else 'preparation_failed',
                   failure_stage=stage, error=type(exc).__name__ + ': ' + str(exc),
                   start_reports=legacy.jsonable(getattr(exc, 'start_reports', [])))
    row['elapsed_seconds'] = time.monotonic() - started
    return legacy.jsonable(row)


def run(commit, shard):
    if isinstance(shard, bool) or not isinstance(shard, Integral) or shard not in range(RULES['shards']):
        raise ValueError('shard must be 0, 1 or 2')
    design = frozen.verify(DESIGN, RULES, SOURCES, commit)
    context = inputs.read_context();keys = expected_keys(context)
    if design['metadata']['expected_keys'] != legacy.jsonable(keys):
        raise RuntimeError('planned source/frame/variant identities changed')
    journal = Journal(OUTPUT, frozen.identity(DESIGN, commit, frozen.runtime(), 'real-reference-stars'),
                      keys, ('fit_completed', 'fit_failed', 'preparation_failed'))
    worker_locks = OUTPUT.parent / (OUTPUT.name + '-workers')
    worker_locks.mkdir(parents=True, exist_ok=True)
    with locked(worker_locks, 'shard-' + str(shard) + '.lock'):
        for index, reference in enumerate(context.references):
            if index % RULES['shards'] != shard:
                continue
            sid = reference['catalog']['source_id']
            for frame in context.frames:
                obs = frame['record']['obs_id']
                pending = [v for v in RULES['epsf_variants'] if journal.read((sid, obs, v)) is None]
                if not pending:
                    continue
                try:
                    prepared, metadata = inputs.prepare_cell(context, reference, frame)
                    error = None
                except Exception as exc:
                    prepared = None;metadata = {'source_id': sid, 'obs_id': obs, 'legacy_split': reference['split']}
                    error = type(exc).__name__ + ': ' + str(exc)
                for variant in pending:
                    row = (attempt(prepared, metadata, variant) if error is None else
                           {'status': 'preparation_failed', 'variant': variant, 'metadata': metadata,
                            'failure_stage': 'common_preparation', 'error': error})
                    journal.write((sid, obs, variant), row)
                    print('CHECKPOINT', sid, obs, variant, row['status'],
                          round(row.get('elapsed_seconds', 0.), 2), flush=True)
    print('SHARD_COMPLETE', shard, 'inspect full journal after all writers stop', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--design', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--protocol-commit')
    parser.add_argument('--shard', type=int, choices=range(3))
    args = parser.parse_args()
    if args.design == args.run:
        parser.error('choose exactly one of --design or --run')
    if args.design:
        create_design();print('DESIGN_WRITTEN', legacy.relative(DESIGN))
    elif args.protocol_commit is None or args.shard is None:
        parser.error('--run requires --protocol-commit and --shard')
    else:
        run(args.protocol_commit, args.shard)


if __name__ == '__main__':
    main()
