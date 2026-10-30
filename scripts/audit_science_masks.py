"""Audit only cached WISE coadd L2 flags; does not estimate source positions."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

from astropy.io import fits
from astropy.wcs import WCS
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_demo, science_mask_policy as policy

MANIFEST = ROOT / 'data/raw/wise0855/coadd/manifest.json'
OUTPUT = ROOT / 'web/data/mask-audit/development-audit.json'
LEGACY_WEB_COMMIT = '77ad00f75796d9fc0c54a0e9c7b446eaaf35e2eb'


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def count_region(flags, image, variance, target, background, region):
    """Count native pixels; web counts describe its native-nearest flag rule."""
    f = np.asarray(flags).astype(np.uint64)
    numeric = np.isfinite(image) & np.isfinite(variance) & (variance > 0)
    legacy_science = ((f & np.uint64(build_demo.BAD_MASK)) == 0) & numeric
    legacy_web = ((f & np.uint64(((1 << 64)-1) ^ ((1 << 12) | (1 << 21)))) == 0) & np.isfinite(image)
    full = (f & np.uint64(1 << 12)) != 0
    masks = {'pixels': region, 'numeric_science': region & numeric,
             'fullsample_any': region & full,
             'legacy_science_good': region & legacy_science,
             'legacy_science_good_fullsample': region & legacy_science & full,
             'legacy_web_good': region & legacy_web,
             'legacy_web_good_fullsample': region & legacy_web & full,
             'strict_target_good': region & target,
             'strict_background_good': region & background}
    return {name: int(np.count_nonzero(mask)) for name, mask in masks.items()}


def build():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    records = []
    for r in manifest['records']:
        path = ROOT / r['path']
        raw_hash = digest(path)
        if raw_hash != r['sha256']:
            raise ValueError('FITS hash mismatch: ' + r['path'])
        with fits.open(path, memmap=False) as h:
            hdr = h['IMAGE'].header
            flags = np.asarray(h['FLAGS'].data)
            image = np.asarray(h['IMAGE'].data)
            var = np.asarray(h['VARIANCE'].data)
            layout = policy.validate_layout(h['FLAGS'].header, r['collection'])
            target, background = policy.science_masks(flags, image, var, h['FLAGS'].header, r['collection'])
            wcs = WCS(hdr)
            mjd = float(hdr['MJD-OBS'])
            prior = build_demo.expected_position(mjd)
            x, y = [float(v) for v in wcs.world_to_pixel_values(*prior)]
            if not np.isfinite([x, y]).all():
                raise ValueError('nonfinite prior WCS')
            yy, xx = np.indices(flags.shape, dtype=float)
            regions = {'full_cutout': np.ones(flags.shape, dtype=bool),
                       'prior_radius_2_5_native_px': (xx-x)**2 + (yy-y)**2 <= 2.5**2,
                       'prior_box_halfwidth_5_native_px': (np.abs(xx-x) <= 5) & (np.abs(yy-y) <= 5)}
            records.append({'obs_id': r['obs_id'], 'epoch': r['epoch'], 'collection': r['collection'],
                'path': r['path'], 'sha256': raw_hash, 'access_url': r['access_url'],
                'cutout_url': r['cutout_url'], 'pipeline_version': str(h[0].header.get('VERSION', '')),
                'mjd_obs': mjd, 'image_bunit': hdr.get('BUNIT'), 'shape': list(flags.shape),
                'headers': {name: [[c.keyword, c.value, c.comment] for c in h[name].header.cards]
                            for name in ('IMAGE', 'FLAGS')},
                'flag_definitions': layout, 'prior_icrs_deg': list(prior), 'prior_native_xy': [x,y],
                'regions': {k: count_region(flags, image, var, target, background, v) for k,v in regions.items()}})
    totals = {region: {k: sum(r['regions'][region][k] for r in records)
                       for k in records[0]['regions'][region]} for region in records[0]['regions']}
    return {'stage':'development_mask_audit_only', 'records_count':len(records),
        'manifest':{'path':str(MANIFEST.relative_to(ROOT)).replace('\\','/'),'sha256':digest(MANIFEST)},
        'source_sha256':{p:digest(ROOT / p) for p in ('scripts/audit_science_masks.py',
            'scripts/science_mask_policy.py','scripts/build_demo.py')},
        'legacy_web_source': {'path':'web/api/frame.py', 'commit':LEGACY_WEB_COMMIT,
            'sha256':sha256(subprocess.check_output(['git','show',LEGACY_WEB_COMMIT + ':web/api/frame.py'], cwd=ROOT)).hexdigest()},
        'primary_sources': {'supplement':'https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf',
          'pipeline_flags':'https://github.com/Caltech-IPAC/spherex-pipelines/blob/aa0ba446ee12971024fe13dc1c47387615bbe85e/py_src/spx_data/spx_flags.py',
          'tutorial':'https://caltech-ipac.github.io/irsa-tutorials/spherex-source-discovery-tool-demo/',
          'qr2_qr3_flag_help':'https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html'},
        'region_note':'Native pixels relative to frozen Luhman 2014 linear prior at IMAGE MJD-OBS, without registration or parallax; not a fitted position or certified actual footprint. Box follows fixed-position fit footprint.',
        'web_note':'Native-equivalent flag and finite-image rule; actual renderer resamples onto user grid and applies inside test, with no variance test.',
        'totals':totals, 'records':records}


if __name__ == '__main__':
    out = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(out, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(out['totals'], indent=2))
