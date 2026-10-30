"""Locked laboratory-response/JWST diagnostic on existing development inputs."""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import astropy.units as u
import numpy as np

from . import lab_spectral_response as lab
from . import parse_wise0855_x1d as jwst
from .spectral_bandpass_v2 import photon_weighted_bandpass


ROOT = lab.ROOT
DESIGN = ROOT / 'web/data/spectral-response/v2-design.json'
OUTPUT = ROOT / 'web/data/spectral-response/v2-development-audit.json'
SOURCE_PATHS = (
    'scripts/lab_spectral_response.py', 'scripts/parse_wise0855_x1d.py',
    'scripts/spectral_bandpass.py', 'scripts/audit_spectral_reference.py',
    'scripts/spectral_bandpass_v2.py', 'scripts/audit_spectral_reference_v2.py',
    'tests/test_lab_spectral_response.py', 'tests/test_wise0855_x1d.py',
    'tests/test_spectral_bandpass.py', 'tests/test_spectral_bandpass_v2.py',
    'docs/SPECTRAL_REFERENCE_PROTOCOL.md', 'docs/SPECTRAL_REFERENCE_V2.md',
    'web/data/spectral-response/design.json',
    'web/data/external/wise0855-sed-reference.json', 'requirements.txt')
RAW_PATHS = (lab.ARCHIVE, jwst.PATH)
RULES = {
    'version': '0.10.0-spectral-reference-development.2',
    'scope': '17 nominal D6 laboratory channels and one existing MAST WISE 0855 spectrum; no new sky fields or fits',
    'channels': 17, 'detector': 6, 'response_kinds': ['Cent','Allpix'],
    'wavelength_shifts_um': [-.0064,0.,.0064],
    'shift_interpretation': 'sensitivity only; not a QR2/QR3 release mapping or correction',
    'maximum_spectral_gap_um': .01,
    'spectrum_mask': 'DQ==0, flux/error finite, error>0; negative flux retained',
    'response_interpretation': 'signed_laboratory_measurement',
    'weighting': 'photon convention: F_nu*R/lambda, normalized by R/lambda; diagnostic, pipeline calibration convention not verified',
    'missing_support': 'no extrapolation, no bridging invalid samples; full-band mean null if any nonzero absolute response weight unsupported',
    'uncertainty': 'no diagonal independent-sample error or confidence interval; full spectral covariance/calibration/variability unknown',
    'numerical_failure': 'retain every attempt; numerical integration failures are separate from partial spectral support, never zero flux',
    'qualifications': [
        'R7 laboratory response is not the exact per-pixel QR2 response; no detector-coordinate binding is performed.',
        'Signed response samples cannot serve as nonnegative physical photon truth without a separately validated model.',
        'No centroid, motion, astrometric truth, injection, detection or scientific promotion is produced.',
        'Cent and Allpix share laboratory measurements; they are sensitivity variants, not independent validation sources.'
    ]}


def relative(path):
    return Path(path).relative_to(ROOT).as_posix()


def inputs():
    return {'sources': {name: lab.digest(ROOT/name) for name in SOURCE_PATHS},
            'raw': {relative(path): {'sha256': lab.digest(path), 'bytes': path.stat().st_size} for path in RAW_PATHS}}


def encode(document):
    return (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')


def create_design():
    if DESIGN.exists():
        raise RuntimeError('design exists; refusing overwrite')
    document = {'rules': RULES, **inputs(), 'status': 'development diagnostic, not validation or calibration'}
    DESIGN.parent.mkdir(parents=True, exist_ok=True)
    with DESIGN.open('xb') as stream:
        stream.write(encode(document))
    return document


def verify_design():
    document = json.loads(DESIGN.read_text(encoding='utf-8'))
    actual = inputs()
    if document.get('rules') != RULES or any(document.get(k) != actual[k] for k in ('sources','raw')):
        raise RuntimeError('protocol/input mismatch')
    for name in (*SOURCE_PATHS, relative(DESIGN)):
        try:
            committed = subprocess.check_output(['git','show','HEAD:'+name], cwd=ROOT, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError('required source/design not committed: '+name) from exc
        if sha256(committed).hexdigest() != lab.digest(ROOT/name):
            raise RuntimeError('source/design differs from committed bytes: '+name)
    return document


def monochromatic(spectrum, wavelength):
    wave = spectrum.wavelength_um
    i = int(np.searchsorted(wave, wavelength, side='right') - 1)
    if i < 0 or i >= len(wave)-1 or not spectrum.usable[i:i+2].all() or wave[i+1]-wave[i] > RULES['maximum_spectral_gap_um']:
        return None
    return float(np.interp(wavelength, wave[i:i+2], spectrum.flux_jy[i:i+2]))


def build():
    design = verify_design()
    spectrum = jwst.read_spectrum()
    records = []
    with lab.LabArchive() as archive:
        summary_name, summary = archive.summary()
        for kind in RULES['response_kinds']:
            for channel in range(1,18):
                member, wavelength, response = archive.curve(channel, kind=kind)
                center_column = 1 if kind == 'Cent' else 3
                center = float(summary[channel-1,center_column])
                width = float(summary[channel-1,center_column+1])
                for shift in RULES['wavelength_shifts_um']:
                    try:
                        result = photon_weighted_bandpass(
                            spectrum.wavelength_um*u.um, spectrum.flux_jy*u.Jy, spectrum.usable,
                            (wavelength+shift)*u.um, response*u.one,
                            maximum_gap=RULES['maximum_spectral_gap_um']*u.um,
                            response_kind=RULES['response_interpretation'])
                        row = asdict(result)
                        row['status'] = 'full_support' if result.support_complete else 'partial_only'
                        weights = row.pop('supported_part_weights')
                        nonzero = np.flatnonzero(weights)
                        row['supported_weights_sha256'] = sha256(np.asarray(weights,dtype='<f8').tobytes()).hexdigest()
                        row['contributing_source_samples'] = int(len(nonzero))
                        row['contributing_wavelength_range_um'] = [float(spectrum.wavelength_um[nonzero[0]]),float(spectrum.wavelength_um[nonzero[-1]])] if len(nonzero) else None
                    except (ValueError, FloatingPointError) as exc:
                        row = {'status':'numerical_failure', 'error':str(exc), 'full_band_mean_jy':None,
                               'supported_part_mean_jy':None, 'support_complete':False}
                    mono = monochromatic(spectrum, center+shift)
                    mean = row['full_band_mean_jy']
                    row.update({'kind':kind, 'channel':channel, 'member':member,
                        'shift_um':shift, 'summary_center_um':center, 'summary_width_um':width,
                        'response_range_um':[float(wavelength[0]+shift),float(wavelength[-1]+shift)],
                        'response_rows':len(wavelength), 'negative_response_rows':int(np.sum(response<0)),
                        'monochromatic_jy':mono,
                        'full_mean_to_monochromatic_ratio':mean/mono if mean is not None and mono is not None and mono>0 else None})
                    records.append(row)
        members = archive.used
    for row in records:
        base = next(x for x in records if x['kind']==row['kind'] and x['channel']==row['channel'] and x['shift_um']==0.)
        current, original = row['full_band_mean_jy'], base['full_band_mean_jy']
        row['full_mean_relative_to_zero_shift_percent'] = 100*(current/original-1) if current is not None and original is not None and original>0 else None
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    return {'stage':'spectral_reference_development_diagnostic_only', 'protocol_commit':commit,
        'protocol_path':relative(DESIGN), 'protocol_sha256':lab.digest(DESIGN), 'rules':RULES,
        'inputs':design['raw'], 'source_hashes':design['sources'],
        'laboratory':{'url':lab.ARCHIVE_URL,'documentation_url':lab.DOCUMENTATION_URL,
            'release':'R7 / July 22 2026 documentation; tar last modified August 26 2026',
            'summary_member':summary_name,'selected_member_hashes':members},
        'spectrum':{'path':relative(jwst.PATH),'sha256':jwst.FILE_SHA256, 'summary':spectrum.summary(),
            'reference_metadata':'web/data/external/wise0855-sed-reference.json'},
        'counts':{'attempted':len(records),'full_support':sum(x['status']=='full_support' for x in records),
            'partial_only':sum(x['status']=='partial_only' for x in records),
            'numerical_failure':sum(x['status']=='numerical_failure' for x in records)}, 'records':records}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--design',action='store_true')
    parser.add_argument('--run',action='store_true')
    args = parser.parse_args()
    if args.design == args.run:
        parser.error('choose exactly --design or --run')
    if args.design:
        create_design()
        print('DESIGN', relative(DESIGN), lab.digest(DESIGN))
    else:
        if OUTPUT.exists():
            raise RuntimeError('output exists; refusing overwrite')
        document = build()
        with OUTPUT.open('xb') as stream:
            stream.write(encode(document))
        print('AUDIT',relative(OUTPUT),lab.digest(OUTPUT),document['counts'])


if __name__ == '__main__':
    main()
