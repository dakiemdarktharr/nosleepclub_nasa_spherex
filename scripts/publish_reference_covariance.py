"""Publish the complete conditional covariance audit without new inference."""
from collections import Counter
from hashlib import sha256
import gzip
import json
import os

if __name__ == '__main__':
    for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                  'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[_name] = '1'

from . import run_reference_covariance_study as study
from .experiment_journal import Journal
from .science_jobs import atomic


COMMIT = 'b42515e3a4ac95df5e786d47f5ff18ad706b937b'
AUDIT = study.ROOT/'data/raw/benchmark/reference-covariance-audit.json'
OUT = study.ROOT/'web/data/reference-covariance'


def checked_document(path, checksum_key):
    value = json.loads(path.read_text(encoding='utf-8'))
    body = {k: v for k, v in value.items() if k != checksum_key}
    if value.get(checksum_key) != sha256(study.legacy.encoded(body)).hexdigest():
        raise ValueError('document checksum differs: '+path.name)
    return value


def build():
    study.frozen.verify(study.DESIGN, study.RULES, study.SOURCES, COMMIT)
    context, _, baseline_digest = study.shape.open_baseline()
    identity = study.frozen.identity(study.DESIGN, COMMIT, study.frozen.runtime(), 'baseline-reference-covariance')
    keys, _ = study.planned_cells(context)
    journal = Journal(study.OUTPUT/'cells', identity, keys, study.STATUSES)
    records = journal.records(require_complete=True)
    result = checked_document(study.RESULT, 'result_sha256')
    audit = checked_document(AUDIT, 'receipt_sha256')
    digest = study.shape.record_digest(journal, records)
    if (result['identity'] != identity or result['cell_digest'] != digest
            or audit['frozen_protocol_commit'] != COMMIT or audit['cell_digest'] != digest
            or audit['baseline_journal_digest'] != baseline_digest
            or audit['result_file_sha256'] != study.legacy.lab.digest(study.RESULT)
            or audit['result_sha256'] != result['result_sha256']):
        raise ValueError('covariance/audit input bindings differ')
    for path, expected in audit['audit_source_sha256'].items():
        if study.legacy.lab.digest(study.ROOT/path) != expected:
            raise ValueError('independent audit source changed')
    counts = dict(Counter(r['payload']['status'] for r in records))
    if counts != result['counts'] or counts != audit['counts'] or len(records) != 420:
        raise ValueError('covariance denominator differs')
    if audit['native_audited'] != audit['native_available'] or audit['native_available'] != counts['influence_available']:
        raise ValueError('native audit is incomplete')
    if result['status'] != 'descriptive_complete' or result['promotion'] is not False:
        raise ValueError('no complete unpromoted diagnostic')
    d = result['diagnostic'];heldout = set(d['heldout_by_source'])
    if len(heldout) != 7 or len(result['source_counts']) != 21:
        raise ValueError('source denominator differs')
    overview = {'schema': 'reference-covariance-overview-1', 'protocol_commit': COMMIT,
        'design_sha256': study.legacy.lab.digest(study.DESIGN), 'cell_digest': digest,
        'result_sha256': result['result_sha256'], 'result_file_sha256': audit['result_file_sha256'],
        'status': result['status'], 'planned': 420, 'counts': counts,
        'source_counts': result['source_counts'], 'unique_original_pixels': d['unique_original_pixels'],
        'heldout_joint': d['heldout_joint'],
        'heldout_sources': [{'source_id': sid, **d['heldout_by_source'][sid]} for sid in sorted(heldout)],
        'training': {'chi2': d['frame']['training_chi2'], 'dof': d['frame']['training_dof'],
                     'per_exposure_counts': d['frame']['training_counts']},
        'independent_audit': {'receipt_sha256': audit['receipt_sha256'],
            'native_audited': audit['native_audited'], 'max_absolute_differences': audit['max_absolute_differences'],
            'native_max_absolute_differences': audit['native_max_absolute_differences'],
            'audit_source_sha256': audit['audit_source_sha256']},
        'publisher_sha256': study.legacy.lab.digest(study.ROOT/'scripts/publish_reference_covariance.py'),
        'new_point_fits': 0, 'random_draws': 0, 'prospective_fields': 0, 'learned_shape_used': False,
        'promotion': False, 'qualification': study.QUALIFICATION}
    return overview, {'result': result, 'journal_records': records, 'independent_audit': audit}, audit


def main():
    for name in ('overview.json', 'records.json.gz', 'independent-audit.json'):
        if (OUT/name).exists():
            raise ValueError('covariance publication already exists; refusing overwrite')
    overview, full, audit = build()
    raw = study.legacy.encoded(full);packed = gzip.compress(raw, compresslevel=9, mtime=0)
    (OUT/'records.json.gz').write_bytes(packed)
    overview['download'] = {'path': 'data/reference-covariance/records.json.gz',
        'bytes': len(packed), 'sha256': sha256(packed).hexdigest(),
        'uncompressed_bytes': len(raw), 'uncompressed_sha256': sha256(raw).hexdigest()}
    atomic(OUT/'independent-audit.json', audit);atomic(OUT/'overview.json', overview)
    print(json.dumps({'counts': overview['counts'], 'heldout': overview['heldout_joint'], 'download': overview['download']}, indent=2))


if __name__ == '__main__':
    main()
