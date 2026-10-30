"""Build a small UI product from sealed, immutable 0.8 experiment results."""
from pathlib import Path
from . import covariance_study as study


def main():
    out=study.OUT;names=['design.json','calibrator.json','validation-protocol.json',
        'development-summary.json','calibration-summary.json','validation-summary.json','failure-audit.json']
    data={n:study.read(out/n) for n in names};s=data['validation-summary.json']
    payload={'version':'0.8.0','passed':s['passed'],'point_passed':s['point_passed'],'coverage_gate':s['coverage_gate'],
        'design_sha256':s['design_sha256'],'validation_protocol_sha256':s['validation_protocol_sha256'],
        'lock_commit':s['lock_commit'],'calibrator':data['calibrator.json'],'fields':s['fields'],
        'injection_summary':s['injection_summary'],'real_summary':s['real_summary'],
        'development':data['development-summary.json'],'calibration':data['calibration-summary.json'],
        'failure_audit':{'checked':len(data['failure-audit.json']['corrections']),
            'recovered_baseline':data['failure-audit.json']['recovered_baseline']},
        'current_measurement_changed':False,'input_sha256':{n:study.bench.digest(out/n) for n in names},
        'source_sha256':study.bench.digest(Path(__file__))}
    study.bench.save(out/'overview.json',payload)


if __name__=='__main__':main()
