"""Audit the already cached WISE cutouts against one QR2 D6 calibration."""
from hashlib import sha256
import json
from pathlib import Path
import sys

from astropy.io import fits
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import native_gain_binding as binding, science_mask_policy as mask_policy, source_ramp_noise as ramp

MANIFEST = ROOT / 'data/raw/wise0855/coadd/manifest.json'
LOOKUP = ROOT / 'data/raw/benchmark/calibration-uuid-lookup.xml'
GAIN = ROOT / 'data/raw/wise0855/calibration/abs_gain_matrix_D6_spx_cal-agm-v7-2025-218.fits'
OUT = ROOT / 'web/data/native-gain/development-audit.json'
URL = 'https://irsa.ipac.caltech.edu/' + binding.URI


def digest(path):
    h=sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def stats(x):
    if len(x)==0: return None
    q=np.quantile(x,[0,.01,.05,.5,.95,.99,1])
    return dict(zip(('min','p01','p05','median','p95','p99','max'),map(float,q)))


def build():
    xml=LOOKUP.read_bytes()
    row=binding.validate_lookup(xml)
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    records=[]
    with fits.open(GAIN, memmap=False) as g:
        gain=binding.validate_calibration(g,digest(GAIN),GAIN.stat().st_size,xml)
        gain_headers={h.name:[[c.keyword,c.value,c.comment] for c in h.header.cards] for h in g}
        for rec in manifest['records']:
            path=ROOT/rec['path']
            actual_hash=digest(path)
            if actual_hash!=rec['sha256']:
                raise ValueError('raw FITS hash mismatch: '+rec['path'])
            with fits.open(path,memmap=False) as h:
                header=h['IMAGE'].header
                y,x=np.indices(h['IMAGE'].data.shape)
                eligible,_=mask_policy.science_masks(h['FLAGS'].data,h['IMAGE'].data,h['VARIANCE'].data,h['FLAGS'].header,rec['collection'])
                selected_x,selected_y=x[eligible],y[eligible]
                dx,dy=binding.detector_indices(header,h[0].header,rec['collection'],selected_x,selected_y,eligible.shape)
                raw=np.asarray(gain[dy,dx],float)
                good=np.isfinite(raw)&(raw>0)
                # Check the same strict selection used by the proposed binding API.
                positive=binding.bind_values(gain,dx[good],dy[good]).value
                timing=ramp._header_values(header)
                factor=ramp.poisson_factor(timing['n'])/timing['nominal_pipeline_integration_seconds']
                invalid=[{'native_xy':[int(a),int(b)],'active_xy':[int(c),int(d)],
                          'gain':float(v) if np.isfinite(v) else None,
                          'image':float(h['IMAGE'].data[b,a]) if np.isfinite(h['IMAGE'].data[b,a]) else None,
                          'variance':float(h['VARIANCE'].data[b,a]) if np.isfinite(h['VARIANCE'].data[b,a]) else None,
                          'flags':int(h['FLAGS'].data[b,a]),
                          'neighbor_gain_3x3':np.asarray(gain[max(0,d-1):d+2,max(0,c-1):c+2],float).tolist()}
                         for a,b,c,d,v in zip(selected_x[~good],selected_y[~good],dx[~good],dy[~good],raw[~good])]
                records.append({'obs_id':rec['obs_id'],'epoch':rec['epoch'],'path':rec['path'],
                    'raw_sha256':actual_hash,'access_url':rec['access_url'],'cutout_url':rec['cutout_url'],
                    'image_version':str(h[0].header['VERSION']), 'mjd_obs':float(header['MJD-OBS']),
                    'image_shape':list(eligible.shape), 'detector':int(header['DETECTOR']),
                    'detcoord':str(header['DETCOORD']), 'gain_history':'[CALIB] abs_gain_matrix '+binding.UUID,
                    'active_origin_xy':[int(dx[0]-selected_x[0]),int(dy[0]-selected_y[0])] if len(dx) else None,
                    'strict_target_count':int(eligible.sum()), 'positive_finite_gain_count':int(good.sum()),
                    'invalid_gain_count':int((~good).sum()),'invalid_gain_pixels':invalid,
                    'status':'conditional_all_selected' if good.all() and len(good)>0 else 'conditional_partial_or_no_usable_gain',
                    'gain_positive_finite_stats':stats(positive), 'timing':timing,
                    'source_variance_coefficient_positive_finite_stats':stats(positive*factor)})
    return {'stage':'native_gain_development_audit_only',
      'scope':'31 previously cached WISE QR2 D6 cutouts; no fitting or photon injection',
      'orientation_evidence':'Public R6.4 and R6.5.4/6.5.5 module v1.5 multiplies gain array directly after MWIR X flip; WCS A reports sky-oriented active coordinates. Gain file does not itself contain DETCOORD; exact private patch builds are not public.',
      'calibration':{'uuid':binding.UUID,'uri':binding.URI,'url':URL,'path':str(GAIN.relative_to(ROOT)).replace('\\','/'),
         'sha256':digest(GAIN),'bytes':GAIN.stat().st_size,'unit':'MJy s / (electron sr)',
         'software_version':binding.GAIN_VERSION,'shape':[2040,2040],'headers':gain_headers},
      'lookup':{'path':str(LOOKUP.relative_to(ROOT)).replace('\\','/'),'sha256':digest(LOOKUP),'row':row,
                'service':'https://irsa.ipac.caltech.edu/TAP/sync',
                'request':{'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable',
                  'QUERY':"SELECT a.planeid,a.uri,a.producttype,p.productid,p.provenance_version FROM spherex.artifact AS a JOIN spherex.plane AS p ON a.planeid=p.planeid WHERE p.planeid IN ('0b762d1b-bec8-473f-9e6e-436fff6c631f','2dc965d6-bad3-4916-83ca-54e9e9cfcbd3')"}},
      'manifest':{'path':str(MANIFEST.relative_to(ROOT)).replace('\\','/'),'sha256':digest(MANIFEST)},
      'source_sha256':{p:digest(ROOT/p) for p in ('scripts/native_gain_binding.py','scripts/audit_native_gain.py','scripts/science_mask_policy.py','scripts/source_ramp_noise.py')},
      'primary_sources':{
        'pipeline_r64_calibration':'https://github.com/Caltech-IPAC/spherex-pipelines/blob/d31bc5a6666b4530c6e233c2484c586b4a598b24/py_src/spx_tasks/apply_dark_flat_field_and_photo_calib.py',
        'pipeline_r64_flip':'https://github.com/Caltech-IPAC/spherex-pipelines/blob/d31bc5a6666b4530c6e233c2484c586b4a598b24/py_src/spx_tasks/remove_reference_pixels.py',
        'pipeline_r64_active_wcs':'https://github.com/Caltech-IPAC/spherex-pipelines/blob/d31bc5a6666b4530c6e233c2484c586b4a598b24/py_src/spx_utils/alt_wcs.py',
        'pipeline_r655_calibration':'https://github.com/Caltech-IPAC/spherex-pipelines/blob/aa0ba446ee12971024fe13dc1c47387615bbe85e/py_src/spx_tasks/apply_dark_flat_field_and_photo_calib.py',
        'archive_docs':'https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/'},
      'unit_note':'gain = (MJy/sr)/(electron/s); source variance coefficient = P(n)*gain/(n*TSAMP) in gain/s, multiplied by source brightness for added ideal source-only variance.',
      'record_count':len(records),'records':records}


if __name__=='__main__':
    product=build()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(product,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print('audited',len(product['records']),'conditional-all-selected',sum(x['status']=='conditional_all_selected' for x in product['records']))
