"""Publish audited synthetic controls, retaining all trials and missing outcomes."""
import argparse
from collections import Counter, defaultdict
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path

if __name__ == '__main__':
    for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                  'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[_name] = '1'

import numpy as np

from . import run_signal_control_study as study
from .experiment_journal import Journal


COMMIT = '9894074fdacbba908b8816d3dbcac1df901731f1'
PUBLIC = study.ROOT/'web/data/signal-controls'
AUDIT_DIR = study.ROOT/'data/raw/benchmark/signal-controls-audit'
AUDIT_SOURCES = ('scripts/audit_signal_controls.py', 'tests/test_signal_control_audit.py', 'docs/SIGNAL_CONTROL_AUDIT.md')
PUBLISHER_SOURCES = ('scripts/publish_signal_controls.py', 'tests/test_signal_control_publication.py')
FIGURE_REQUIREMENTS_SHA256 = '6e73d507401a635ca162ca32987d949faf197fec2c6d23e849f46cea8b15c7d3'


def digest(path): return sha256(path.read_bytes()).hexdigest()


def keep(path, content):
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
            raise ValueError('refusing to overwrite different published bytes: '+path.name)
    else:
        with path.open('xb') as stream: stream.write(content)


def verify_receipt(receipt, cell_digest, summary_hash, sources, design_hash, metadata):
    body = {k:v for k,v in receipt.items() if k != 'receipt_sha256'}
    if sha256(study.parent.calibration.legacy.encoded(body)).hexdigest() != receipt.get('receipt_sha256'):
        raise ValueError('audit receipt checksum differs')
    identity = receipt.get('identity', {})
    if (receipt.get('schema') != 'signal-control-independent-audit-1' or receipt.get('status') != 'passed'
            or receipt.get('planned') != 640 or receipt.get('failures') != []
            or receipt.get('assessment_opened') is not False or receipt.get('promotion') is not False
            or identity.get('protocol_commit') != COMMIT or identity.get('study_cell_digest') != cell_digest
            or identity.get('summary_sha256') != summary_hash or identity.get('source_sha256') != sources
            or identity.get('design_sha256') != design_hash or identity.get('upstream') != metadata
            or receipt.get('metric_checks') != {'strata':216, 'null_strata':8, 'pairs':320,
                                               'noiseless_clean':128, 'noisy_gates':16, 'preservation':64}):
        raise ValueError('audit does not bind these exact source/study/summary bytes')
    counts = receipt.get('counts', {})
    if (not isinstance(counts, dict) or set(counts)-{'verified', 'input_checked_unavailable'}
            or any(type(n) is not int or n < 0 for n in counts.values()) or sum(counts.values()) != 640):
        raise ValueError('audit does not account for every planned record')


def verify_checkpoints(receipt, records, audit):
    checked = audit.records(require_complete=True)
    if (study.parent.calibration.record_digest(audit, checked) != receipt.get('audit_checkpoint_digest')
            or [r['key'] for r in checked] != [r['key'] for r in records]):
        raise ValueError('audit checkpoint keys/digest differ')
    if dict(Counter(r['payload']['status'] for r in checked)) != receipt['counts']:
        raise ValueError('audit checkpoint counts differ')
    objective_count = 0; start_count = 0
    for row, verified in zip(records, checked):
        v = verified['payload']; original = row['payload']; status = original['status']
        if (v.get('study_checksum') != row['checksum'] or v.get('study_status') != status
                or v.get('study_error') != original.get('error')):
            raise ValueError('audit checkpoint study binding differs')
        completed = status == 'fit_completed'
        if (status not in study.STATUSES or v.get('status') != ('verified' if completed else 'input_checked_unavailable')
                or v.get('objective_available') is not completed):
            raise ValueError('audit checkpoint objective status differs')
        starts = v.get('successful_final_starts')
        if type(starts) is not int or not 0 <= starts <= 9: raise ValueError('audit start count invalid')
        if completed:
            reports = original['fit']['final_mode_audit']['starts']
            if (len(reports) != 9 or any(type(r.get('success')) is not bool for r in reports)
                    or starts != sum(r['success'] for r in reports)):
                raise ValueError('audit saved final-start count differs')
        elif starts != 0:
            raise ValueError('unavailable objective has start count')
        if status == 'preparation_failed' and (v.get('replayed_preparation_error') != original.get('error')
                or v.get('replayed_failure_stage') != original.get('failure_stage')):
            raise ValueError('preparation failure replay differs')
        objective_count += int(completed); start_count += starts
    if (type(receipt.get('objective_checked')) is not int or receipt['objective_checked'] != objective_count
            or type(receipt.get('successful_final_starts_checked')) is not int
            or receipt['successful_final_starts_checked'] != start_count):
        raise ValueError('audit objective or final-start aggregate differs')
    return checked


def validate_metrics(metrics, records):
    """Keep the declared population, failures and null semantics in products."""
    expected = [list(k) for k in study.expected_keys()]
    rows = metrics.get('records', [])
    if (metrics.get('schema') != 'signal-control-metrics-1' or metrics.get('planned') != 640
            or [r.get('key') for r in rows] != expected or [r.get('key') for r in records] != expected
            or metrics.get('section_counts') != {'noiseless':192, 'noisy':384, 'null':64}
            or metrics.get('status_counts') != dict(Counter(r['payload']['status'] for r in records))
            or metrics.get('old_assessment_blocked') is not True or metrics.get('promotion') is not False):
        raise ValueError('metrics planned keys, status counts or isolation differ')
    for row, record in zip(rows, records):
        if row.get('status') != record['payload']['status']: raise ValueError('metrics record status differs')
        values = row.get('values')
        if (values is None) != (row['status'] != 'fit_completed'): raise ValueError('metrics completion differs')
        if row['key'][0] == 'null' and values is not None:
            if (values.get('true_flux_jy') != 0 or values.get('position_native_error') is not None
                    or values.get('radial_error_native_px') is not None or values.get('flux_ratio') is not None
                    or values.get('distance_to_companion_native') is not None or values.get('identity') is not None):
                raise ValueError('null must not contain position or source truth')
    if (metrics['noiseless_clean_gate']['planned'] != 128
            or len(metrics['noiseless_clean_gate']['rows']) != 128
            or metrics['noiseless_preservation_guard']['planned_pairs'] != 64
            or len(metrics['noiseless_preservation_guard']['rows']) != 64
            or len(metrics['noisy_clean_gates']) != 16 or any(r['planned'] != 16 for r in metrics['noisy_clean_gates'])
            or len(metrics['null_strata']) != 8 or any(r['planned'] != 8 for r in metrics['null_strata'])
            or metrics['paired']['planned'] != 320):
        raise ValueError('metrics gate denominators differ')
    fidelity = fidelity_components(metrics)
    if len(fidelity) != 8 or any(group['planned'] != 16 for group in fidelity):
        raise ValueError('fidelity component denominator differs')
    return fidelity


def pack_archive(archive):
    raw = study.parent.calibration.legacy.encoded(archive)
    packed = gzip.compress(raw, mtime=0)
    return packed, {'path':'data/signal-controls/records.json.gz', 'bytes':len(packed),
        'sha256':sha256(packed).hexdigest(), 'uncompressed_bytes':len(raw), 'uncompressed_sha256':sha256(raw).hexdigest()}


def fidelity_components(metrics):
    groups = defaultdict(list)
    for row in metrics['records']:
        key = row['key']
        if key[0] == 'noiseless' and key[4] in ('isolated', 'modeled'):
            groups[(key[2], key[4], key[-1])].append(row['values'])
    output = []
    for (truth, scene, arm), rows in sorted(groups.items()):
        complete = [r for r in rows if r is not None]
        position = lambda r: r['radial_error_native_px'] <= .1
        flux = lambda r: .9 <= r['flux_ratio'] <= 1.1
        output.append({'truth': truth, 'scene': scene, 'arm': arm, 'planned': len(rows), 'completed': len(complete),
            'supported': sum(r['numerical_support'] for r in complete),
            'position_within_budget': sum(position(r) for r in complete),
            'flux_within_budget': sum(flux(r) for r in complete),
            'position_and_flux_within_budget': sum(position(r) and flux(r) for r in complete),
            'joint_passed': sum(r['numerical_support'] and position(r) and flux(r) for r in complete)})
    return output


def null_flux_summaries(metrics):
    output = []
    for row in metrics['null_strata']:
        values = [r['values']['target_flux_jy'] for r in metrics['records']
            if r['key'][0] == 'null' and r['key'][1] == row['geometry'] and r['key'][3] == row['phase']
            and r['key'][-1] == row['arm'] and r['values'] is not None]
        output.append({**row, 'signed_flux_jy': {'completed': len(values),
            'mean': float(np.mean(values)) if values else None, 'median': float(np.median(values)) if values else None,
            'min': float(np.min(values)) if values else None, 'max': float(np.max(values)) if values else None}})
    return output


def example(records, path):
    """Fixed first geometry/phase/draw: modeled versus omitted, corrected arm."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from io import BytesIO
    rows = []
    for scene in ('modeled', 'omitted'):
        key = ('noisy', study.GEOMETRIES[0], 'gaussian', '0', scene, '1200', '0', 'corrected')
        rows.append(next(r for r in records if tuple(r['key']) == key))
    fig, axes = plt.subplots(2, 3, figsize=(12, 7.8), layout='constrained')
    display = []
    for row in rows:
        payload = row['payload']
        if payload['status'] == 'fit_completed':
            sample = payload['samples'][0];frame = payload['fit']['frames'][0]
            display.extend([np.asarray(sample['data_mjysr']), np.asarray(frame['model'])])
    lo = float(min(np.min(a) for a in display)) if display else 0.
    hi = float(max(np.max(a) for a in display)) if display else 1.
    resmax = max((float(np.max(np.abs(r['payload']['fit']['frames'][0]['residual'])))
        for r in rows if r['payload']['status'] == 'fit_completed'), default=1.)
    if resmax == 0: resmax = 1e-12
    for axes_row, record, scene in zip(axes, rows, ('known companion', 'omitted companion')):
        row = record['payload']
        if row['status'] != 'fit_completed':
            for axis in axes_row: axis.text(.5, .5, row['status'], ha='center', va='center', transform=axis.transAxes);axis.set_axis_off()
            continue
        sample = row['samples'][0];frame = row['fit']['frames'][0]
        x, y = np.asarray(sample['x'], int), np.asarray(sample['y'], int)
        xmin, xmax, ymin, ymax = int(x.min()), int(x.max()), int(y.min()), int(y.max())
        for axis, title, values in zip(axes_row, ('Synthetic input', 'Fitted model', 'Residual'),
                (sample['data_mjysr'], frame['model'], frame['residual'])):
            image = np.full((ymax-ymin+1, xmax-xmin+1), np.nan);image[y-ymin, x-xmin] = values
            artist = axis.imshow(image, origin='lower', extent=(xmin-.5, xmax+.5, ymin-.5, ymax+.5), interpolation='nearest',
                cmap='coolwarm' if title == 'Residual' else 'gray', vmin=-resmax if title == 'Residual' else lo,
                vmax=resmax if title == 'Residual' else hi)
            for position, marker, color in ((row['realization']['target_native_xy'], '+', '#e69f00'),
                    (row['realization']['companion_native_xy'], 'x', '#00a6c7'),
                    (row['position_native'], 'o', '#ff3b8d')):
                axis.plot(*position, marker=marker, color=color, fillstyle='none', linestyle='none', markersize=10, markeredgewidth=1.7)
            axis.set(title=title+' | '+scene, xlabel='native x [pixel]', ylabel='native y [pixel]')
            fig.colorbar(artist, ax=axis, label='MJy/sr', shrink=.75)
    fig.suptitle('SYNTHETIC control, not a new WISE 0855 measurement\nCorrected candidate: same injected data, known vs omitted neighbor', fontsize=12)
    stream = BytesIO();fig.savefig(stream, format='png', dpi=130, metadata={'Software': 'NoSleepClub synthetic signal control'})
    plt.close(fig);keep(path, stream.getvalue())
    from matplotlib.font_manager import findfont
    from importlib.metadata import version
    font = Path(findfont('DejaVu Sans'))
    return {'path': 'data/signal-controls/scene-example.png', 'sha256': digest(path),
        'selection': [r['key'] for r in rows], 'record_checksums': [r['checksum'] for r in rows],
        'selection_rule': 'first fixed geometry, Gaussian, noisy phase0/1200uJy/draw0/corrected; show both modeled and omitted even if unavailable',
        'render_environment': {'matplotlib': version('matplotlib'), 'font_family': 'DejaVu Sans', 'font_sha256': digest(font),
            'figure_requirements_sha256': digest(study.ROOT/'requirements-figures.txt')},
        'display': 'same intensity limits for input and model in both rows; common symmetric residual limits; original masks remain missing'}


def run():
    design = study.parent.frozen.verify(study.DESIGN, study.RULES, study.SOURCES, COMMIT)
    _, _, metadata = study.open_inputs()
    if design['metadata'] != study.parent.calibration.legacy.jsonable(metadata): raise ValueError('study input identity changed')
    journal = study.open_journal(COMMIT);records = journal.records(require_complete=True)
    cell_digest = study.parent.calibration.record_digest(journal, records)
    summary_path = study.OUTPUT/'summary.json'; summary = json.loads(summary_path.read_text(encoding='utf-8'))
    if (summary['cell_digest'] != cell_digest or summary['protocol_commit'] != COMMIT
            or summary.get('design_sha256') != digest(study.DESIGN) or summary.get('assessment_opened') is not False
            or summary.get('promotion') is not False): raise ValueError('summary journal differs')
    metrics = summary['metrics']; fidelity = validate_metrics(metrics, records)
    receipt = json.loads((AUDIT_DIR/'audit-receipt.json').read_text(encoding='utf-8'))
    verify_receipt(receipt, cell_digest, digest(summary_path), {p:digest(study.ROOT/p) for p in AUDIT_SOURCES},
                   digest(study.DESIGN), study.parent.calibration.legacy.jsonable(metadata))
    audit = Journal(AUDIT_DIR/'cells', receipt['identity'], study.expected_keys(),
        ('verified', 'input_checked_unavailable', 'unverified_failure', 'audit_mismatch'))
    checked = verify_checkpoints(receipt, records, audit)
    archive = {'schema': 'signal-control-records-1', 'protocol_commit': COMMIT, 'design_sha256': digest(study.DESIGN),
        'journal_header': json.loads((journal.directory/'header.json').read_text(encoding='utf-8')), 'records': records,
        'audit_journal_header': json.loads((audit.directory/'header.json').read_text(encoding='utf-8')), 'audit_records': checked,
        'cell_digest': cell_digest, 'audit_checkpoint_digest': receipt['audit_checkpoint_digest']}
    packed, download = pack_archive(archive)
    if digest(study.ROOT/'requirements-figures.txt') != FIGURE_REQUIREMENTS_SHA256:
        raise ValueError('figure requirements bytes differ')
    PUBLIC.mkdir(parents=True, exist_ok=True)
    figure = example(records, PUBLIC/'scene-example.png')
    overview = {'schema': 'signal-control-overview-1', 'protocol_commit': COMMIT, 'design_sha256': digest(study.DESIGN),
        'cell_digest': cell_digest, 'is_synthetic': True, 'original_image_added': False,
        'source_ids': list(study.GEOMETRIES), 'obs_id': study.OBS_ID, 'planned': 640,
        'section_counts': metrics['section_counts'], 'status_counts': metrics['status_counts'],
        'strata': metrics['strata'], 'null_strata': null_flux_summaries(metrics),
        'noiseless_clean_gate': {k:v for k,v in metrics['noiseless_clean_gate'].items() if k != 'rows'},
        'noisy_clean_gates': metrics['noisy_clean_gates'], 'noisy_clean_all_gates_passed': metrics['noisy_clean_all_gates_passed'],
        'noiseless_preservation_guard': {k:v for k,v in metrics['noiseless_preservation_guard'].items() if k != 'rows'},
        'fidelity_components': fidelity,
        'paired': {k:v for k,v in metrics['paired'].items() if k != 'rows'},
        'audit': {'receipt_sha256': receipt['receipt_sha256'], 'counts': receipt['counts'],
                  'audit_checkpoint_digest': receipt['audit_checkpoint_digest']},
        'audit_source_sha256': receipt['identity']['source_sha256'],
        'publisher_source_sha256': {p:digest(study.ROOT/p) for p in PUBLISHER_SOURCES},
        'figure': figure, 'download': download,
        'old_assessment_blocked': True, 'assessment_opened': False, 'prospective_fields_opened': 0, 'promotion': False,
        'qualification': metrics['qualification']}
    keep(PUBLIC/'records.json.gz', packed);keep(PUBLIC/'independent-audit.json', study.parent.calibration.legacy.encoded(receipt))
    keep(PUBLIC/'overview.json', study.parent.calibration.legacy.encoded(overview))
    study.parent.assert_assessment_unopened()
    print(json.dumps({'planned': 640, 'status_counts': metrics['status_counts'], 'download': overview['download']}, indent=2))
    return overview


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();run()
