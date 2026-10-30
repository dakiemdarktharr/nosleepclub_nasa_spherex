"""Freeze new experiments without changing any earlier scientific protocol."""
from hashlib import sha256
import json
import os
import subprocess

from . import run_neighbor_intervention as inherited
from . import run_wise_linked_study as legacy


ROOT = legacy.ROOT
THREAD_ENV = inherited.THREAD_ENV


def inventory(extra_sources):
    document = inherited.inventory()
    for path in extra_sources:
        document['sources'][path] = legacy.lab.digest(ROOT / path)
    manifest = json.loads(legacy.inputs.gaia.INPUT.read_text(encoding='utf-8'))
    entry = manifest['gaia'];path = ROOT / entry['path']
    if legacy.lab.digest(path) != entry['sha256']:
        raise RuntimeError('raw Gaia catalogue hash mismatch')
    document['raw'][entry['path']] = {'sha256': entry['sha256'], 'bytes': path.stat().st_size}
    return document


def create(path, rules, extra_sources, *, metadata):
    if path.exists():
        raise RuntimeError('design exists; refusing overwrite')
    document = {'rules': rules, **inventory(extra_sources), 'metadata': metadata}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(legacy.encoded(document))
    return document


def verify(path, rules, extra_sources, commit):
    if not isinstance(commit, str) or len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise RuntimeError('explicit frozen 40-character protocol commit required')
    design = json.loads(path.read_text(encoding='utf-8'))
    if design['rules'] != legacy.jsonable(rules) or any(design.get(k) != v for k, v in inventory(extra_sources).items()):
        raise RuntimeError('design/source/input mismatch')
    paths = {**design['sources'], **design['opened_products'], legacy.relative(path): legacy.lab.digest(path)}
    for name, digest in paths.items():
        blob = subprocess.check_output(['git', 'show', commit + ':' + name], cwd=ROOT,
                                       stderr=subprocess.DEVNULL)
        if sha256(blob).hexdigest() != digest:
            raise RuntimeError('frozen Git bytes differ: ' + name)
    return design


def runtime():
    result = legacy.execution_runtime()
    result['thread_environment_request'] = {name: os.environ.get(name) for name in THREAD_ENV}
    if any(value != '1' for value in result['thread_environment_request'].values()):
        raise RuntimeError('run the fresh CLI with all declared thread requests equal to one')
    result['thread_qualification'] = 'environment requests only; backend thread count not independently measured'
    return result


def identity(path, commit, runtime_record, section):
    return {'protocol_commit': commit, 'design_sha256': legacy.lab.digest(path),
            'section': section, 'runtime': runtime_record}
