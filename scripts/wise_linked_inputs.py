"""Existing WISE development inputs for a conditional linked-flux comparison.

No data are loaded at import. This adapter does not establish a source-color
calibration or replace any published measurement.
"""
import json
from contextlib import contextmanager
from numbers import Real

import astropy.units as u
from astropy.io import fits
import numpy as np

from . import gaia_motion as gaia
from . import lab_pixel_binding as binding
from . import lab_spectral_response as lab
from . import native_gain_binding as active_geometry
from . import parse_wise0855_prism as prism
from . import quality_model as quality
from . import science_mask_policy as masking
from .native_flux_template import native_flux_template
from .sed_flux_coefficient import sed_flux_coefficient
from .wcs_pixel_area import wcs_pixel_area


ROOT = lab.ROOT
GAIA_RESULTS = ROOT/'web/data/gaia/results.json'
CATALOG = ROOT/'web/data/release/protocol.json'


@contextmanager
def exposure_context(obs_id):
    try:
        yield
    except Exception as exc:
        raise ValueError(str(obs_id)+': spectral_prediction: '+type(exc).__name__+': '+str(exc)) from exc


def checked_unit(header, expected):
    text = binding.unique(header,'BUNIT')
    if not isinstance(text,str):
        raise ValueError('explicit FITS unit string required')
    try:
        actual = u.Unit(text,parse_strict='raise')
    except (TypeError,ValueError) as exc:
        raise ValueError('invalid FITS physical unit') from exc
    # Equivalent units with a different numerical scale are not interchangeable
    # here: the adapter does not rescale the stored array.
    if actual != expected:
        raise ValueError('FITS unit differs from the numerical-array contract')
    return str(actual)


def validate_spectral_calibration(hdul):
    for name in ('CWAVE','CBAND'):
        matches = [h for h in hdul if h.name == name]
        if len(matches)!=1 or matches[0].data is None or matches[0].data.shape!=(2040,2040):
            raise ValueError('ambiguous or unsupported spectral calibration')
        image = matches[0]
        checked_unit(image.header,u.um)
        if binding.unique(image.header,'DETCOORD')!='sky' or binding.unique(image.header,'DETECTOR')!=6:
            raise ValueError('unsupported QR2 spectral coordinate convention')


def read_verified_frames():
    manifest = json.loads(gaia.INPUT.read_text(encoding='utf-8'))
    for item in (*manifest['records'], *manifest['calibrations'].values()):
        path = ROOT/item['path']
        if lab.digest(path) != item['sha256']:
            raise ValueError('WISE input hash mismatch: '+item['path'])
    with fits.open(ROOT/manifest['calibrations']['spectral_wcs']['path'],memmap=False) as h:
        validate_spectral_calibration(h)
    with fits.open(ROOT/manifest['calibrations']['epsf']['path'],memmap=False) as h:
        header = h['EPSF'].header
        if (binding.unique(header,'DETECTOR')!='6' or binding.unique(header,'DETCOORD')!='sky' or
                binding.unique(header,'OVSMPX')!=5 or binding.unique(header,'OVSMPY')!=5):
            raise ValueError('unsupported ePSF coordinate/oversampling convention')
    frames, _ = gaia.load_frames()
    for frame in frames:
        with fits.open(ROOT/frame['record']['path'],memmap=False) as h:
            checked_unit(h['IMAGE'].header,u.MJy/u.sr)
            checked_unit(h['ZODI'].header,u.MJy/u.sr)
            checked_unit(h['VARIANCE'].header,(u.MJy/u.sr)**2)
            if binding.unique(h['IMAGE'].header,'DETCOORD')!='sky' or binding.unique(h['IMAGE'].header,'DETECTOR')!=6:
                raise ValueError('unsupported native image coordinate convention')
            valid, _ = masking.science_masks(h['FLAGS'].data,h['IMAGE'].data,
                h['VARIANCE'].data,h['FLAGS'].header,frame['record']['collection'])
            frame['valid'] = valid & np.isfinite(frame['data'])
            frame['image_header'] = h['IMAGE'].header.copy()
            frame['primary_header'] = h[0].header.copy()
            frame['data_unit'] = 'MJy/sr'
        frame['epsf_provenance'] = json.dumps(manifest['calibrations']['epsf'],sort_keys=True)
    return frames, manifest


def configuration(frames, label):
    report = json.loads(GAIA_RESULTS.read_text(encoding='utf-8'))
    selected = [x for x in report['configurations'] if x['spectral_configuration']==label]
    if len(selected) != 1:
        raise ValueError('missing or ambiguous frozen WISE configuration')
    previous = selected[0]
    registration = {x['obs_id']:x for x in previous['frame_registration']}
    if len(registration) != len(previous['frame_registration']):
        raise ValueError('duplicate registration ID')
    by_id = {f['record']['obs_id']:f for f in frames}
    if len(by_id)!=len(frames):
        raise ValueError('duplicate native exposure ID')
    groups = []
    for side in ('before','after'):
        group = []
        for pair in previous['spectral_pairs']:
            obs = pair[side]['obs_id']
            reg = registration[obs]
            group.append({**by_id[obs], 'offset':np.asarray(reg['offset_px'],float),
                          'offset_cov':np.asarray(reg['covariance_px2'],float)})
        if len(group) != len({f['record']['obs_id'] for f in group}):
            raise ValueError('duplicate exposure in epoch')
        groups.append(group)
    if {f['record']['obs_id'] for f in groups[0]} & {f['record']['obs_id'] for f in groups[1]}:
        raise ValueError('one exposure cannot occur in both epochs')
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))['catalog']
    xy = quality.positions(catalog, groups[0]+groups[1])
    return groups, catalog, xy, previous


def native_position(frame, position):
    sky = gaia.motion.WCS.pixel_to_world_values(*(np.asarray(position,float)+frame['offset']))
    native = np.asarray(frame['wcs'].world_to_pixel_values(*sky),float)
    if native.shape != (2,) or not np.isfinite(native).all():
        raise ValueError('invalid exact target WCS position')
    return native


def spectral_predictions(frames, *, normalization_jy, channels=68, center_model='r7', reference_alpha=0.):
    """Compute proposed ratios only when called under the new study protocol.

    Channel assignment and center are evaluated at the nearest active source
    pixel at the fixed search anchor. The shifted nominal response remains an
    approximation; this is not an exact response at every fitted pixel.
    """
    if center_model not in ('r7','qr2'):
        raise ValueError('unknown wavelength-center hypothesis')
    if isinstance(normalization_jy,(bool,np.bool_)) or not isinstance(normalization_jy,Real) or not np.isfinite(normalization_jy) or normalization_jy<=0:
        raise ValueError('explicit positive fixed spectral normalization required')
    spectrum = prism.read_spectrum()
    manifest = json.loads(gaia.INPUT.read_text(encoding='utf-8'))
    with fits.open(ROOT/manifest['calibrations']['spectral_wcs']['path'],memmap=False) as h:
        validate_spectral_calibration(h)
        qr2_center = np.array(h['CWAVE'].data,float)
    output = []
    with lab.LabArchive() as archive:
        maps = binding.read_maps(archive,channels=channels)
        _, summary = archive.summary(channels=channels)
        for frame in frames:
            with exposure_context(frame['record']['obs_id']):
                native = native_position(frame, gaia.motion.TARGET_ANCHOR)
                px, py = map(int,np.floor(native+.5))
                ax, ay = active_geometry.detector_indices(
                    frame['image_header'],frame['primary_header'],frame['record']['collection'],
                    np.array([px]),np.array([py]),frame['data'].shape)
                x, y = int(ax[0]), int(ay[0])
                pixel = binding.bind_pixel(maps,x,y,channels=channels)
                channel = pixel['channel']
                member, wave, response = archive.curve(channel,channels=channels,kind='Cent')
                center = pixel['center_um'] if center_model=='r7' else float(qr2_center[y,x])
                coefficient = sed_flux_coefficient(
                    spectrum.wavelength_um*u.um,spectrum.flux_jy*u.Jy,spectrum.usable,
                    wave*u.um,response*u.one,local_center=center*u.um,
                    fiducial_center=float(summary[channel-1,1])*u.um,
                    reference_alpha=reference_alpha,maximum_gap=.01*u.um,
                    spectrum_provenance=prism.FILE_SHA256,
                    response_provenance=lab.ARCHIVE_SHA256+'|'+member,
                    reference_provenance='declared diagnostic Fnu(lambda)/Fnu(local)=(lambda/local)^alpha; not verified official convention')
                output.append({'obs_id':frame['record']['obs_id'], 'native_anchor_xy':native.tolist(),
                    'nearest_native_xy':[px,py], 'r7_binding':pixel,
                    'qr2_center_um':float(qr2_center[y,x]), 'chosen_center_um':center,
                    'center_model':center_model,'reference_alpha':float(reference_alpha),
                    'curve_member':member,'curve_sha256':archive.used[member]['sha256'],
                    'sed_coefficient_jy':float(coefficient.coefficient.to_value(u.Jy)),
                    'reference_mean':coefficient.reference_mean,
                    'response_shift_um':float(coefficient.shift.to_value(u.um)),
                    'negative_response_absolute_fraction':coefficient.response_negative_absolute_fraction,
                    'reference_quadrature_difference':coefficient.reference_quadrature_relative_difference})
        members = archive.used
    common = float(normalization_jy)
    for item in output:
        item['relative_coefficient'] = item['sed_coefficient_jy']/common
        item['common_normalization_jy'] = common
    return output, members


def prepared_samples(frames,catalog,xy,anchor):
    """Recover the frozen nuisance span; its basis has no source-level meaning."""
    originals = quality.samples_for(frames,catalog,xy,anchor)
    output = []
    for sample in originals:
        frame = sample['frame']
        if frame.get('data_unit') != 'MJy/sr':
            raise ValueError('prepared frame requires validated MJy/sr array units')
        sx,sy=np.asarray(sample['x']),np.asarray(sample['y'])
        if (sx.ndim!=1 or sy.shape!=sx.shape or sx.dtype.kind not in 'iuf' or sy.dtype.kind not in 'iuf' or
                not np.isfinite(sx).all() or not np.isfinite(sy).all() or
                np.any(sx!=np.rint(sx)) or np.any(sy!=np.rint(sy)) or
                np.any(sx<0) or np.any(sy<0) or np.any(sx>=frame['data'].shape[1]) or np.any(sy>=frame['data'].shape[0])):
            raise ValueError('sample coordinates must be exact in-image integers')
        mask = np.zeros(frame['data'].shape,dtype=bool)
        mask[sy.astype(int),sx.astype(int)] = True
        my,mx=np.nonzero(mask)
        if not np.array_equal(mx,sx) or not np.array_equal(my,sy):
            raise ValueError('sample pixels must be unique and in row-major order')
        raw = np.asarray(frame['epsf_table']['EPSF'][sample['zone']],float)
        over = frame['epsf_oversampling']
        if not np.isfinite(over) or over != int(over):
            raise ValueError('unsupported ePSF oversampling')
        error = np.asarray(sample['error'],float)
        nuisance = sample['q']*(error/np.median(error))[:,None]
        provenance = frame['record']['path']+'|'+frame['record']['sha256']

        def rendering(position, *, frame=frame,mask=mask,raw=raw,over=int(over),provenance=provenance):
            native = native_position(frame,position)
            area = wcs_pixel_area(frame['wcs'],native,provenance=provenance)
            if not area.supported:
                raise ValueError('WCS pixel area fails declared refinement diagnostic')
            rendered = native_flux_template(raw,oversampling_x=over,oversampling_y=over,
                source_xy=native,selection_mask=mask,source_omega=area.solid_angle,
                source_omega_provenance=provenance+'|instantaneous celestial-WCS area, not exact SAPM',
                epsf_provenance=frame['epsf_provenance'])
            return rendered,area,native

        def renderer(position, *, rendering=rendering):
            return rendering(position)[0].template_per_jy

        def describe_renderer(position, *, rendering=rendering):
            rendered,area,native=rendering(position)
            return {'native_position_xy':native.tolist(),'source_omega_sr':rendered.source_omega_sr,
                'area_refinement_difference':area.relative_difference,
                'area_provenance':area.provenance,
                'native_sum_before_normalization':rendered.native_sum_before_normalization,
                'signed_selected_psf_fraction':rendered.signed_selected_sum,
                'support_truncated_by_image':rendered.support_truncated_by_image}

        output.append({'obs_id':frame['record']['obs_id'], 'data':sample['data'].copy(),
            'error':error.copy(),'nuisance':nuisance,'renderer':renderer,'describe_renderer':describe_renderer,
            'sample':sample,'selection_mask':mask,'data_unit':'MJy/sr',
            'nuisance_provenance':'fixed frozen neighbor/background span; rescaled from initial whitened SVD basis',
            'subtraction_provenance':'legacy IMAGE minus ZODI minus scalar background; fitted constant absorbs the scalar; structured ZODI subtraction is shared by all compared modes',
            'renderer_provenance':provenance+'|phase-normalized padded ePSF and exact source WCS; Omega is geometric approximation'})
    return output
