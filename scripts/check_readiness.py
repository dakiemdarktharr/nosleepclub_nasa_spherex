"""Report repository evidence without certifying scientific or operational readiness."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys

try:
    from scripts.build_review_contract import render_contract
except ModuleNotFoundError as exc:
    if exc.name != 'scripts':
        raise
    from build_review_contract import render_contract

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def git_identity(root):
    try:
        def git(*args):
            return subprocess.run(['git', '-C', str(root), *args], check=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=10).stdout.strip()
        commit = git('rev-parse', 'HEAD')
        dirty = bool(git('status', '--porcelain', '--untracked-files=normal'))
        return {'commit': commit, 'dirty': dirty}
    except (OSError, subprocess.SubprocessError):
        return {'commit': None, 'dirty': None}


def pinned_dependencies(path):
    result = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)', line)
        if not match:
            raise ValueError('non-pinned dependency')
        name = match[1].lower().replace('_', '-')
        if name in result:
            raise ValueError('duplicate dependency')
        result[name] = match[2]
    return result


def collect(root=ROOT):
    root = Path(root)
    checks, evidence = [], {}
    def check(name, operation):
        try:
            value = operation()
            checks.append({'name': name, 'passed': bool(value)})
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            checks.append({'name': name, 'passed': False})
    def read_json(path):
        return json.loads((root / path).read_text(encoding='utf-8'))
    def config():
        data = read_json('web/vercel.json')
        funcs = data['functions']
        return (funcs['api/reviews.py']['maxDuration'] >= 15 and
                funcs['api/observations.py']['maxDuration'] >= 30 and
                funcs['api/frame.py']['maxDuration'] >= 60 and
                funcs['api/reviews.py']['includeFiles'] == 'api/_review_manifest.json' and
                all(funcs[name]['excludeFiles'] == '{data/**,assets/**,*.html,*.css,*.js,*.svg}'
                    for name in ('api/reviews.py', 'api/observations.py', 'api/frame.py')) and
                all((root / 'web' / name).is_file() for name in ('api/reviews.py', 'api/observations.py', 'api/frame.py')))
    def review_contract():
        return ((root / 'web/api/_review_manifest.json').read_bytes() ==
                render_contract((root / 'web/data/manifest.json').read_bytes()))
    def dependencies():
        science = pinned_dependencies(root / 'requirements.txt')
        web = pinned_dependencies(root / 'web/requirements.txt')
        ops = pinned_dependencies(root / 'requirements-ops.txt')
        required = {'pymongo', 'dnspython', 'numpy', 'astropy', 'pillow'}
        return (required <= web.keys() and all(science.get(k, v) == v for k, v in web.items())
                and {'cryptography', 'cffi', 'pycparser'} <= ops.keys() and not (ops.keys() & web.keys()))
    def provenance():
        manifest = read_json('web/data/manifest.json')
        result = read_json('web/data/gaia/results.json')
        source = result['source_sha256']
        calculated = sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
        evidence['manifest_analysis_sha256'] = manifest['analysis_sha256']
        return (manifest['analysis_sha256'] == result['analysis_sha256'] == calculated and
                all(digest(root / 'scripts' / name) == value for name, value in source.items()))
    def protocol():
        result = read_json('web/data/ablation/validation-summary.json')
        proto = read_json('web/data/ablation/validation-protocol.json')
        path = root / 'web/data/ablation/validation-protocol.json'
        baseline = proto['rules']['selection']['baseline']
        evidence['science_0_9'] = {
            'version': result['version'], 'selected_model': result['selected_model'], 'baseline': baseline,
            'point_passed': result['point_passed'], 'coverage_passed': result['coverage_gate']['passed'],
            'overall_passed': result['passed'], 'comparison_is_self': result['selected_model'] == baseline,
            'protocol_sha256': digest(path), 'summary_sha256': digest(root / 'web/data/ablation/validation-summary.json'),
            'protocol_path': 'web/data/ablation/validation-protocol.json',
            'summary_path': 'web/data/ablation/validation-summary.json'}
        return (result['version'] == '0.9.0' and digest(path) == result['validation_protocol_sha256'] and
                result['design_sha256'] == proto['design_sha256'] and
                result['selected_model'] == proto['selected_model'] and
                all(type(result[k]) is bool for k in ('point_passed', 'passed')) and
                type(result['coverage_gate']['passed']) is bool)
    def ledger():
        text = (root / 'docs/PRODUCTION_READINESS.md').read_text(encoding='utf-8')
        rows = re.findall(r'^\|\s*(\d{2})\s*\|[^\n]*\|\s*([^|]+?)\s*\|\s*$', text, re.M)
        states = {int(number): state.strip() for number, state in rows}
        evidence['ledger'] = {'path': 'docs/PRODUCTION_READINESS.md', 'sha256': digest(root / 'docs/PRODUCTION_READINESS.md'),
                              'items': [{'id': f'{k:02}', 'state': v} for k, v in sorted(states.items())]}
        return len(rows) == 20 and set(states) == set(range(1, 21))
    def contract_docs():
        return all((root / 'docs' / name).is_file() for name in ('REVIEW_API_CONTRACT.md', 'OBSERVATION_API_CONTRACT.md', 'FRAME_API_CONTRACT.md'))
    for name, fn in [('serverless_config', config), ('review_contract', review_contract), ('pinned_dependencies', dependencies),
                     ('manifest_provenance', provenance), ('validation_protocol', protocol),
                     ('acceptance_ledger', ledger), ('api_contracts', contract_docs)]:
        check(name, fn)
    return {'schema_version': '1.0', 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'source': git_identity(root), 'repository_checks': checks,
            'repository_checks_passed': all(c['passed'] for c in checks), 'evidence': evidence,
            'software_test_status': 'not_executed_by_this_report',
            'operational_readiness': 'unverified', 'scientific_readiness': 'unverified',
            'scientific_ready': False,
            'limitations': ['CI results do not establish scientific validity or operational readiness',
                            'A self-comparison cannot promote a baseline',
                            'Independent scientific review and acceptance evidence are required']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-science', action='store_true', help='Fail unless scientific readiness is independently verified')
    args = parser.parse_args(argv)
    report = collect()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(not report['repository_checks_passed'] or (args.require_science and not report['scientific_ready']))


if __name__ == '__main__':
    sys.exit(main())
