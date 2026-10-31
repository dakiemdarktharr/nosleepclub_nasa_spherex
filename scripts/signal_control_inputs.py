"""New synthetic controls on fixed, already opened native geometry.

Original IMAGE values are replaced, never added to synthetic means. Frozen
VARIANCE, mask, registration and ePSF source files remain conditioning inputs.
"""
from functools import lru_cache
from hashlib import sha256
from numbers import Integral

import astropy.units as u
import numpy as np

from . import run_reference_star_study as baseline
from . import wise_linked_inputs as original
from .shape_native_inputs import prepare_shape_sample
from .moment_preserving_epsf import physical_parameters
from .rotated_gaussian_control import integrated_source
from .profile_landscape import numeric
from .wcs_pixel_area import wcs_pixel_area


PHASES = ((.25, .25), (.25, .75), (.75, .25), (.75, .75))
NOISE_PREFIX = 2026103102
COMPANION_OFFSET = (1.5, 0.)
GAUSSIAN = {'sigma_xy': [.55, .70], 'angle_deg': 25.}
PLANE_COEFFICIENTS = (.04, .015, -.01)
COMPANION_ID = 'synthetic-companion'


def array_digest(value):
    a = np.ascontiguousarray(value, dtype='<f8')
    return sha256(str(a.shape).encode('ascii')+b'|'+a.tobytes()).hexdigest()


def common_from_native(frame, position):
    p = numeric(position, 'native position', 1)
    if p.shape != (2,): raise ValueError('native x,y required')
    sky = frame['wcs'].pixel_to_world_values(*p)
    common = np.asarray(original.gaia.motion.WCS.world_to_pixel_values(*sky))-np.asarray(frame['offset'])
    replay = original.native_position(frame, common)
    if not np.isfinite(common).all() or np.max(np.abs(replay-p)) > 1e-7:
        raise ValueError('exact native/common WCS roundtrip failed')
    return common


@lru_cache(maxsize=2)
def _noise_bank(shape, draw, prefix):
    result = np.random.Generator(np.random.PCG64(np.random.SeedSequence([prefix, draw]))).standard_normal(shape)
    result.flags.writeable = False
    return result


def standardized_noise(shape, draw, *, prefix=NOISE_PREFIX):
    if (not isinstance(shape, tuple) or len(shape) != 2
            or any(isinstance(v, (bool, np.bool_)) or not isinstance(v, Integral) or not 1 <= v <= 2048 for v in shape)
            or isinstance(draw, (bool, np.bool_)) or not isinstance(draw, Integral) or not 0 <= draw < 16
            or isinstance(prefix, (bool, np.bool_)) or not isinstance(prefix, Integral) or not 0 <= prefix < 2**32):
        raise ValueError('invalid bounded noise bank identity')
    return _noise_bank(tuple(map(int, shape)), int(draw), int(prefix))


def _cached_renderer(renderer):
    @lru_cache(maxsize=4096)
    def render(x, y): return renderer(np.asarray([x, y]))
    return lambda p: render(float(p[0]), float(p[1]))


def prepare_geometry(context, source_id, obs_id, phase, coefficients):
    if isinstance(phase, bool) or not isinstance(phase, Integral) or phase not in range(4):
        raise ValueError('one of four fixed native phases required')
    refs = {r['catalog']['source_id']: r for r in context.references}
    frames = {f['record']['obs_id']: f for f in context.frames}
    prepared, meta = baseline.inputs.prepare_cell(context, refs[source_id], frames[obs_id])
    anchor = np.asarray(meta['anchor_sky_px']); frame = prepared['sample']['frame']
    old_native = original.native_position(frame, anchor)
    target_native = np.floor(old_native)+np.asarray(PHASES[int(phase)])
    companion_native = target_native+COMPANION_OFFSET
    target_common = common_from_native(frame, target_native)
    if np.any(np.abs(target_common-anchor) >= 2.5): raise ValueError('planted phase outside unchanged common search square')
    sample = prepared['sample']; x = np.asarray(sample['x'], int); y = np.asarray(sample['y'], int)
    omega = []
    for xx, yy in zip(x, y):
        area = wcs_pixel_area(frame['wcs'], [xx, yy], provenance=prepared['renderer_provenance']+'|control pixel')
        if not area.supported: raise ValueError('pixel solid-angle refinement unsupported')
        omega.append(area.solid_angle.to_value(u.sr))
    zero = np.zeros_like(prepared['data'])
    synthetic = {**prepared, 'data': zero.copy(),
        'sample': {**sample, 'data': zero.copy(), 'neighbour_ids': [], 'neighbours': []},
        'subtraction_provenance': 'synthetic target/companion/plane; original IMAGE replaced, not added'}
    return {'source_id': source_id, 'obs_id': obs_id, 'phase': int(phase), 'anchor_common': anchor,
        'target_native': target_native, 'companion_native': companion_native, 'target_common': target_common,
        'frame': frame, 'x': x, 'y': y, 'omega': np.asarray(omega)*u.sr,
        'synthetic_prepared': synthetic, 'coefficients': np.asarray(coefficients).copy(),
        '_models': {}, '_center_areas': {}, 'original_metadata': meta,
        'background': baseline.semantic.background_design(sample['background'], 1)@np.asarray(PLANE_COEFFICIENTS),
        'error': np.asarray(prepared['error']).copy()}


def model_for(geometry, arm, needs_neighbor):
    """Prepare only the required arm/neighbor model; preserve local failures."""
    if arm not in ('baseline', 'corrected') or type(needs_neighbor) is not bool:
        raise ValueError('explicit arm and neighbor state required')
    key = (arm, needs_neighbor);cache = geometry['_models']
    if key not in cache:
        try:
            prepared = geometry['synthetic_prepared']; sample = prepared['sample']
            positions = [(COMPANION_ID, common_from_native(geometry['frame'], geometry['companion_native']))] if needs_neighbor else []
            selected = {**prepared, 'sample': {**sample, 'neighbour_ids': [p[0] for p in positions], 'neighbours': positions}}
            item = (baseline.inputs.prepare_variant(selected, geometry['anchor_common'], 'nearest') if arm == 'baseline'
                    else prepare_shape_sample(selected, geometry['anchor_common'], physical_parameters(geometry['coefficients'])))
            if (item['metadata']['x'] != geometry['x'].tolist() or item['metadata']['y'] != geometry['y'].tolist()
                    or not np.array_equal(item['error'], geometry['error'])):
                raise ValueError('fitter changed fixed native pixels or errors')
            item['renderer'] = _cached_renderer(item['renderer']);cache[key] = (item, None)
        except Exception as exc: cache[key] = (None, type(exc).__name__+': '+str(exc))
    item, error = cache[key]
    if error is not None: raise ValueError(error)
    return item


def solid_angle_metadata(geometry, needs_companion):
    labels = [('target', geometry['target_native'])]
    if needs_companion: labels.append(('companion', geometry['companion_native']))
    sources = {}
    for label, position in labels:
        if label not in geometry['_center_areas']:
            area = wcs_pixel_area(geometry['frame']['wcs'], position, provenance='synthetic control source center '+label)
            if not area.supported: raise ValueError('source-center solid-angle refinement unsupported')
            center = float(area.solid_angle.to_value(u.sr)); ratios = geometry['omega'].to_value(u.sr)/center
            geometry['_center_areas'][label] = {'center_omega_sr': center,
                'pixel_to_center_omega_ratio_range': [float(np.min(ratios)), float(np.max(ratios))]}
        value = geometry['_center_areas'][label]
        sources[label] = {**value, 'pixel_to_center_omega_ratio_range': list(value['pixel_to_center_omega_ratio_range'])}
    return {'sources': sources,
        'qualification': 'matched/fitter retain frozen source-center Omega; independent Gaussian uses per-pixel Omega. Cross-family differences include this convention, not PSF shape alone.'}


def realize(geometry, section, truth, scene, flux_ujy, draw):
    if isinstance(draw, (bool, np.bool_)) or not isinstance(draw, Integral):
        raise ValueError('draw must be an integer, not a boolean')
    if section not in ('noiseless', 'noisy', 'null') or scene not in ('isolated', 'modeled', 'omitted'):
        raise ValueError('invalid section or scene')
    if (isinstance(flux_ujy, bool) or not isinstance(flux_ujy, Integral) or
            (section == 'null' and (truth != 'none' or flux_ujy != 0 or scene != 'isolated')) or
            (section != 'null' and (truth not in ('matched', 'gaussian') or flux_ujy not in (600, 1200)))):
        raise ValueError('invalid planted truth/flux identity')
    flux = float(flux_ujy)*1e-6; count = len(geometry['x']); per_source = []
    target = np.zeros(count); companion = np.zeros(count)
    if truth == 'matched':
        base = model_for(geometry, 'baseline', False)
        target = flux*base['renderer'](geometry['target_common']).to_value(u.MJy/u.sr/u.Jy)
        if scene != 'isolated': companion = flux*np.asarray(model_for(geometry, 'baseline', True)['neighbor_design'][:, 0])
        for label, values in (('target', target), ('companion', companion)):
            per_source.append({'source': label, 'flux_jy': flux if label == 'target' or scene != 'isolated' else 0.,
                'selected_signed_flux_jy': float(np.sum(values*1e6*geometry['omega'].to_value(u.sr))),
                'qualification': 'matched signed mathematical template/center-Omega convention; not physical PSF truth or a nonnegative photon model'})
    elif truth == 'gaussian':
        for label, pos in (('target', geometry['target_native']), ('companion', geometry['companion_native'])):
            if label == 'companion' and scene == 'isolated':
                per_source.append({'source': label, 'flux_jy': 0., 'present': False}); continue
            amount = flux if label == 'target' or scene != 'isolated' else 0.
            result = integrated_source(geometry['x'], geometry['y'], source_xy=pos, **GAUSSIAN,
                flux=amount*u.Jy, pixel_omega=geometry['omega'])
            if label == 'target': target = result['surface'].value
            else: companion = result['surface'].value
            per_source.append({'source': label, **result['metadata']})
    mean = geometry['background']+target+companion
    if section == 'noiseless':
        if draw != 0: raise ValueError('noiseless control has exactly one deterministic record')
        z = np.zeros(count); seed = None; bank_hash = None
    else:
        if section == 'null' and not 0 <= draw < 8: raise ValueError('null uses first eight draws')
        bank = standardized_noise(tuple(geometry['frame']['data'].shape), draw)
        z = bank[geometry['y'], geometry['x']]
        seed = [NOISE_PREFIX, int(draw)]; bank_hash = array_digest(bank)
    data = mean+geometry['error']*z
    if not np.isfinite(data).all(): raise ValueError('nonfinite generated scene')
    return {'data': data, 'mean': mean, 'target': target, 'companion': companion,
        'metadata': {'per_source': per_source, 'seed': seed, 'whole_exposure_noise_bank_sha256': bank_hash,
            'noise_model': 'none' if section == 'noiseless' else 'diagonal Gaussian at original observed VARIANCE; not source Poisson or detector noise validation',
            'realization_sha256': array_digest(data), 'original_image_added': False,
            'target_flux_jy': flux, 'companion_flux_jy': flux if scene != 'isolated' else 0.,
            'target_native_xy': geometry['target_native'].tolist() if section != 'null' else None,
            'companion_native_xy': geometry['companion_native'].tolist() if scene != 'isolated' else None,
            'native_phase': list(PHASES[geometry['phase']]), 'background_coefficients_mjysr': list(PLANE_COEFFICIENTS),
            'solid_angle_conventions': solid_angle_metadata(geometry, scene != 'isolated'),
            'null_search_anchor_native_xy': geometry['target_native'].tolist() if section == 'null' else None}}


def fit_item(geometry, realization, scene, arm):
    if arm not in ('baseline', 'corrected') or scene not in ('isolated', 'modeled', 'omitted'):
        raise ValueError('invalid fitter arm/scene')
    present = scene == 'modeled'
    model = model_for(geometry, arm, present)
    result = {**model, 'data': realization['data'].copy(), 'error': geometry['error'].copy(),
        'neighbor_design': model['neighbor_design'].copy() if present else np.empty((len(geometry['x']), 0)),
        'neighbor_ids': [COMPANION_ID] if present else [],
        'metadata': {**model['metadata'], 'neighbors': model['metadata']['neighbors'] if present else [],
            'synthetic_scene': scene, 'original_catalog_neighbors_removed_for_control': True}}
    if not present:
        if 'corrected_neighbors' in result['metadata']: result['metadata']['corrected_neighbors'] = []
        if 'neighbor_shape_design' in result: result['neighbor_shape_design'] = np.empty((len(geometry['x']), 0, 3))
    return result
