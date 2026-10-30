"""Calibrate, commit a threshold, then validate a conditional presence rule."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
import subprocess

THREAD_ENV = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
              'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')
if __name__ == '__main__':
    for _name in THREAD_ENV:
        os.environ[_name] = '1'

from . import frozen_experiment as frozen
from . import presence_experiment_inputs as inputs
from . import run_wise_linked_study as legacy
from .experiment_journal import Journal
from .science_jobs import atomic, encode as atomic_encode, locked


ROOT = frozen.ROOT
DESIGN = ROOT / 'web/data/source-presence/design.json'
THRESHOLD = ROOT / 'web/data/source-presence/threshold.json'
OUTPUT = ROOT / 'data/raw/benchmark/source-presence'
GEOMETRY = OUTPUT / 'geometry.json'
RULES = inputs.RULES
SOURCES = ('scripts/frozen_experiment.py', 'scripts/experiment_journal.py',
           'scripts/source_presence_score.py', 'scripts/presence_experiment_inputs.py',
           'scripts/run_presence_study.py', 'tests/test_source_presence_score.py',
           'tests/test_presence_experiment_inputs.py', 'tests/test_presence_study.py',
           'tests/test_experiment_journal.py', 'tests/test_frozen_experiment.py',
           'docs/SOURCE_PRESENCE_PROTOCOL.md')


def expected_keys(stage):
    if stage not in ('calibration', 'validation'):
        raise ValueError('unknown experiment stage')
    scenarios = inputs.SCENARIOS[:2] if stage == 'calibration' else inputs.SCENARIOS
    return [(stage, s['id'], str(draw)) for s in scenarios for draw in range(RULES['draws_per_case'])]


def create_design():
    return frozen.create(DESIGN, RULES, SOURCES,
        metadata={'calibration_attempts': len(expected_keys('calibration')),
                  'validation_attempts': len(expected_keys('validation')),
                  'geometry': 'same opened four strict frames used by neighbor-intervention design',
                  'validation_unopened': True})


def save_geometry(context):
    document = context['snapshot']
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with locked(OUTPUT, 'snapshot.lock'):
        if GEOMETRY.exists():
            if GEOMETRY.read_bytes() != atomic_encode(document):
                raise RuntimeError('fixed operator/geometry snapshot changed')
        else:
            atomic(GEOMETRY, document)
    return legacy.lab.digest(GEOMETRY)


def journal_identity(commit, runtime, stage, geometry_sha256, threshold=None, threshold_commit=None):
    result = {**frozen.identity(DESIGN, commit, runtime, stage), 'geometry_sha256': geometry_sha256}
    if stage == 'validation':
        if threshold is None or threshold_commit is None:
            raise RuntimeError('validation requires a committed threshold')
        result.update(threshold_sha256=legacy.lab.digest(THRESHOLD), threshold_commit=threshold_commit)
    return result


def open_journal(commit, runtime, stage, geometry_sha256, threshold=None, threshold_commit=None):
    return Journal(OUTPUT / stage, journal_identity(commit, runtime, stage, geometry_sha256,
                   threshold, threshold_commit), expected_keys(stage), ('score_completed', 'score_failed'))


def calibration_digest(journal):
    records = journal.records(require_complete=True)
    return sha256(legacy.encoded({'header_sha256': legacy.lab.digest(journal.directory / 'header.json'),
                                 'records': [{'key': r['key'], 'checksum': r['checksum']} for r in records]})).hexdigest()


def threshold_from_records(records):
    if len(records) != len(expected_keys('calibration')):
        raise RuntimeError('calibration incomplete')
    expected = set(expected_keys('calibration'))
    if {tuple(r['key']) for r in records} != expected:
        raise RuntimeError('calibration keys changed')
    if any(r['payload']['status'] != 'score_completed' for r in records):
        raise RuntimeError('calibration has failures; threshold abstains')
    maxima = {scenario['id']: max(r['payload']['score']['combined'] for r in records
                                  if r['key'][1] == scenario['id']) for scenario in inputs.SCENARIOS[:2]}
    return {'threshold': float(max(maxima.values())), 'case_maxima': maxima,
            'calibration_counts': {s['id']: RULES['draws_per_case'] for s in inputs.SCENARIOS[:2]},
            'acceptance_comparison': 'strictly greater than threshold',
            'max_order_statistic_qualification': 'per-background 1/(999+1) exchangeable predictive tail under the declared model; not a confidence bound or real-sky FPR'}


def seal(commit):
    frozen.verify(DESIGN, RULES, SOURCES, commit)
    if THRESHOLD.exists():
        raise RuntimeError('threshold already sealed; refusing overwrite')
    if not GEOMETRY.is_file():
        raise RuntimeError('calibration geometry missing')
    journal = open_journal(commit, frozen.runtime(), 'calibration', legacy.lab.digest(GEOMETRY))
    records = journal.records(require_complete=True)
    document = {'version': 'source-presence-threshold.1', 'protocol_commit': commit,
                'design_sha256': legacy.lab.digest(DESIGN), 'geometry_sha256': legacy.lab.digest(GEOMETRY),
                'calibration_digest': calibration_digest(journal), **threshold_from_records(records),
                'sealed_at_utc': datetime.now(timezone.utc).isoformat(),
                'validation_generated': False, 'qualification': RULES['qualifications']}
    THRESHOLD.parent.mkdir(parents=True, exist_ok=True)
    with locked(OUTPUT, 'execute.lock'):
        if THRESHOLD.exists():
            raise RuntimeError('threshold already sealed; refusing overwrite')
        atomic(THRESHOLD, document)
    return document


def verify_threshold(commit, threshold_commit):
    if (not isinstance(threshold_commit, str) or len(threshold_commit) != 40
            or any(c not in '0123456789abcdef' for c in threshold_commit)):
        raise RuntimeError('explicit frozen threshold commit required')
    blob = subprocess.check_output(['git', 'show', threshold_commit + ':' + legacy.relative(THRESHOLD)],
                                   cwd=ROOT, stderr=subprocess.DEVNULL)
    if blob != THRESHOLD.read_bytes():
        raise RuntimeError('threshold bytes differ from committed seal')
    document = json.loads(blob)
    if (document['protocol_commit'] != commit or document['design_sha256'] != legacy.lab.digest(DESIGN)
            or document['geometry_sha256'] != legacy.lab.digest(GEOMETRY)
            or document['validation_generated'] is not False):
        raise RuntimeError('threshold identity changed')
    journal = open_journal(commit, frozen.runtime(), 'calibration', document['geometry_sha256'])
    if calibration_digest(journal) != document['calibration_digest']:
        raise RuntimeError('sealed calibration records changed')
    if any(document.get(k) != v for k, v in threshold_from_records(journal.records(require_complete=True)).items()):
        raise RuntimeError('threshold rule differs from complete calibration')
    return document


def run(commit, stage, threshold_commit=None):
    frozen.verify(DESIGN, RULES, SOURCES, commit)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    # A single stage owns generation. Validation cannot run beside calibration.
    with locked(OUTPUT, 'execute.lock'):
        if stage == 'validation':
            threshold = verify_threshold(commit, threshold_commit)
        elif stage == 'calibration':
            if THRESHOLD.exists():
                raise RuntimeError('calibration sealed; refusing further generation')
            threshold = None
        else:
            raise ValueError('unknown experiment stage')
        context = inputs.build_geometry()
        geometry_sha = save_geometry(context)
        journal = open_journal(commit, frozen.runtime(), stage, geometry_sha, threshold, threshold_commit)
        cases = inputs.SCENARIOS[:2] if stage == 'calibration' else inputs.SCENARIOS
        for scenario_index, scenario in enumerate(cases):
            for draw in range(RULES['draws_per_case']):
                key = (stage, scenario['id'], str(draw))
                if journal.read(key) is not None:
                    continue
                row = {'scenario': scenario, 'scenario_index': scenario_index, 'draw': draw,
                       'data_role': 'synthetic independent Gaussian-family scene, observed error weights'}
                try:
                    data, realization = inputs.realize(context, stage, scenario_index, draw)
                    row['realization'] = realization
                    row.update(score=inputs.score_data(context, data), status='score_completed')
                    if threshold is not None:
                        row['accepted'] = row['score']['combined'] > threshold['threshold']
                except Exception as exc:
                    row.update(status='score_failed', error=type(exc).__name__ + ': ' + str(exc))
                journal.write(key, legacy.jsonable(row))
                if draw % 50 == 0 or draw == RULES['draws_per_case'] - 1:
                    print('CHECKPOINT', stage, scenario['id'], draw, row['status'], flush=True)
        journal.records(require_complete=True)
        print('STAGE_COMPLETE', stage, journal.counts(), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--design', action='store_true')
    action.add_argument('--calibration', action='store_true')
    action.add_argument('--seal-calibration', action='store_true')
    action.add_argument('--validation', action='store_true')
    parser.add_argument('--protocol-commit');parser.add_argument('--threshold-commit')
    args = parser.parse_args()
    if args.design:
        create_design();print('DESIGN_WRITTEN', legacy.relative(DESIGN));return
    if args.protocol_commit is None:
        parser.error('--protocol-commit is required')
    if args.seal_calibration:
        print(json.dumps(seal(args.protocol_commit), ensure_ascii=False, indent=2));return
    run(args.protocol_commit, 'calibration' if args.calibration else 'validation', args.threshold_commit)


if __name__ == '__main__':
    main()
