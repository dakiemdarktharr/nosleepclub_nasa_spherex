"""Opened, previously image-selected Gaia stars for native ePSF diagnostics.

The cohort is deliberately retained in full, including future preparation/fit
failures. It is development data, not an unseen catalogue sample. Nothing is
loaded at import and no position fit or source-presence score is evaluated here.
"""
from dataclasses import dataclass
import json

import astropy.units as u
import numpy as np

from . import astrometric_time_model as timing
from . import gaia_motion as gaia
from . import neighbor_intervention_inputs as semantic
from . import quality_model as quality
from . import wise_linked_inputs as original


ROOT = original.ROOT
RESULTS = ROOT / 'web/data/gaia/results.json'
CATALOG = ROOT / 'web/data/release/protocol.json'
INTENSITY = u.MJy / u.sr
RULES = {
    'expected_sources': 21, 'expected_training_sources': 14,
    'expected_exposures': 20, 'epsf_variants': ['nearest', 'bilinear'],
    'stamp_radius_native_px': 6, 'minimum_pixels': 35,
    'edge_margin_native_px': 12., 'core_radius_native_px': 2.5,
    'core_valid_fraction_minimum': .75, 'neighbor_radius_sky_px': 8.,
    'maximum_neighbors': 24, 'counterpart_max_separation_sky_px': .35,
    'background_degree': 1, 'nonnegative_neighbors': False,
    'registration': 'legacy translation; leave evaluated training source out',
    'selection': 'all 21 previously image-selected sources, no new fit cuts',
}


@dataclass
class ReferenceContext:
    frames: list
    input_manifest: dict
    report: dict
    references: list
    training_ids: tuple
    catalog: list
    catalog_positions: dict


def cohort(report):
    references = report['references']
    ids = [r['catalog']['source_id'] for r in references]
    if (len(ids) != RULES['expected_sources'] or len(set(ids)) != len(ids)
            or any(not isinstance(sid, str) or not sid for sid in ids)):
        raise ValueError('legacy reference cohort changed or has duplicate IDs')
    rows = report['configurations']
    configurations = {r['spectral_configuration']: r for r in rows}
    if len(rows) != 2 or set(configurations) != {'broad', 'strict'}:
        raise ValueError('both frozen configurations are required')
    first = configurations['broad']
    training = tuple(first['training_source_ids'])
    heldout = tuple(first['heldout_source_ids'])
    if (len(training) != RULES['expected_training_sources'] or len(set(training)) != len(training)
            or len(set(heldout)) != len(heldout) or set(training) & set(heldout)
            or set(training) | set(heldout) != set(ids)):
        raise ValueError('invalid old reference allocation')
    for item in configurations.values():
        if tuple(item['training_source_ids']) != training or tuple(item['heldout_source_ids']) != heldout:
            raise ValueError('inconsistent old reference allocations')
    for reference in references:
        expected = 'training' if reference['catalog']['source_id'] in training else 'heldout'
        if reference['split'] != expected:
            raise ValueError('old reference label disagrees with its allocation')
    return sorted(references, key=lambda r: r['catalog']['source_id']), training


def read_context():
    frames, manifest = original.read_verified_frames()
    if len(frames) != RULES['expected_exposures']:
        raise ValueError('opened exposure denominator changed')
    report = json.loads(RESULTS.read_text(encoding='utf-8'))
    references, training = cohort(report)
    gaia_entry = manifest['gaia']
    if original.lab.digest(ROOT / gaia_entry['path']) != gaia_entry['sha256']:
        raise ValueError('raw Gaia catalogue hash mismatch')
    raw_rows = gaia.catalog_rows(manifest)
    raw_sources = {row['source_id']: row for row in raw_rows}
    if len(raw_rows) != len(raw_sources):
        raise ValueError('duplicate raw Gaia source IDs')
    for reference in references:
        source = reference['catalog']; raw = raw_sources.get(source['source_id'])
        if raw is None or any(key not in raw or raw[key] != value for key, value in source.items()):
            raise ValueError('legacy Gaia snapshot differs from pinned raw catalogue')
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))['catalog']
    if len(catalog) != len({c['id'] for c in catalog}):
        raise ValueError('duplicate infrared catalogue IDs')
    for frame in frames:
        time = timing.parse_image_header(frame['image_header'])
        frame['legacy_mjd'] = frame['mjd']
        frame['mjd'] = float(time.midpoint.utc.mjd)
        frame['exposure_time'] = time.metadata()
    frames.sort(key=lambda f: (f['mjd'], f['record']['obs_id']))
    if len({f['record']['obs_id'] for f in frames}) != len(frames):
        raise ValueError('duplicate opened exposure')
    positions = quality.positions(catalog, frames)
    return ReferenceContext(frames, manifest, report, references, training, catalog, positions)


def prediction(source, frame):
    errors = np.asarray([source[key + '_error'] for key in gaia.PARAMETERS])
    if errors.dtype.kind not in 'iuf' or not np.isfinite(errors).all() or np.any(errors <= 0):
        raise ValueError('Gaia standard errors must be finite and positive')
    covariance = np.asarray(gaia.gaia_covariance(source), float)
    std = np.sqrt(np.diag(covariance))
    if (covariance.shape != (5, 5) or not np.isfinite(covariance).all()
            or not np.isfinite(std).all() or np.any(std <= 0)):
        raise ValueError('invalid Gaia covariance')
    np.linalg.cholesky(covariance / std[:, None] / std[None, :])
    anchor = np.asarray(gaia.gaia_xy(source, frame['mjd']), float)
    jacobian = np.asarray(gaia.gaia_jacobian(source, frame['mjd']), float)
    if (anchor.shape != (2,) or jacobian.shape != (2, 5)
            or not np.isfinite(anchor).all() or not np.isfinite(jacobian).all()):
        raise ValueError('invalid propagated Gaia position/Jacobian')
    return anchor, jacobian, covariance


def source_registration(context, reference, frame):
    sid = reference['catalog']['source_id']
    training = [r for r in context.references
                if r['catalog']['source_id'] in context.training_ids
                and r['catalog']['source_id'] != sid]
    result = gaia.fit_registration(frame, training, model='translation')
    if sid in result['source_ids']:
        raise ValueError('evaluated source leaked into its registration')
    return result


def counterpart_and_neighbors(catalog, positions, source_id, anchor):
    xy = np.asarray(positions, float)
    if xy.shape != (len(catalog), 2) or not np.isfinite(xy).all():
        raise ValueError('invalid propagated infrared positions')
    distance = np.linalg.norm(xy - anchor, axis=1)
    exact = [i for i, c in enumerate(catalog)
             if c.get('gaia') and str(c['gaia']['source_id']) == source_id]
    close = np.flatnonzero(distance <= RULES['counterpart_max_separation_sky_px']).tolist()
    if len(exact) != 1 or len(close) != 1 or close[0] != exact[0]:
        raise ValueError('infrared target counterpart is missing, duplicated or ambiguous')
    target = exact[0]
    keep = [i for i in np.flatnonzero(distance <= RULES['neighbor_radius_sky_px']) if i != target]
    if len(keep) > RULES['maximum_neighbors']:
        raise ValueError('too many neighbors; no brightness-based truncation is allowed')
    keep.sort(key=lambda i: catalog[i]['id'])
    return catalog[target]['id'], [(catalog[i]['id'], xy[i].copy()) for i in keep]


def prepare_cell(context, reference, frame):
    """Common fixed pixels/IDs for both arms; errors remain original VARIANCE."""
    source = reference['catalog'];sid = source['source_id']
    anchor, jacobian, covariance = prediction(source, frame)
    registration = source_registration(context, reference, frame)
    adjusted = {**frame, 'offset': np.asarray(registration['offset'], float).copy(),
                'offset_cov': np.asarray(registration['offset_covariance'], float).copy()}
    native = original.native_position(adjusted, anchor)
    margin = min(native[0], native[1], frame['data'].shape[1] - 1 - native[0],
                 frame['data'].shape[0] - 1 - native[1])
    if margin < RULES['edge_margin_native_px']:
        raise ValueError('insufficient native edge margin for full search/PSF support')
    counterpart, neighbors = counterpart_and_neighbors(
        context.catalog, context.catalog_positions[frame['record']['obs_id']], sid, anchor)
    sample = gaia.motion.native_stamp(adjusted, anchor, radius=RULES['stamp_radius_native_px'])
    sx, sy = sample['x'].astype(int), sample['y'].astype(int)
    if len(sx) < RULES['minimum_pixels']:
        raise ValueError('too few selected source-only native pixels')
    mask = np.zeros(frame['data'].shape, bool);mask[sy, sx] = True
    yy, xx = np.indices(mask.shape)
    core = (xx-native[0])**2 + (yy-native[1])**2 <= RULES['core_radius_native_px']**2
    possible = int(core.sum())
    coverage = float((mask & core).sum() / possible) if possible else 0.
    if coverage < RULES['core_valid_fraction_minimum']:
        raise ValueError('insufficient fixed-anchor core mask coverage')
    sample = {**sample, 'neighbour_ids': [sid for sid, _ in neighbors], 'neighbours': neighbors}
    provenance = frame['record']['path'] + '|' + frame['record']['sha256']
    prepared = {'obs_id': frame['record']['obs_id'], 'data': sample['data'], 'error': sample['error'],
                'data_unit': 'MJy/sr', 'selection_mask': mask, 'sample': sample,
                'renderer_provenance': provenance + '|reference native template',
                'subtraction_provenance': 'IMAGE minus ZODI minus original scalar; plane fitted separately'}
    metadata = {'source_id': sid, 'legacy_split': reference['split'], 'anchor_sky_px': anchor.tolist(),
                'native_anchor_xy': native.tolist(), 'native_edge_margin_px': float(margin),
                'core_possible_pixels': possible, 'core_valid_fraction': coverage,
                'counterpart_excluded': counterpart, 'neighbor_ids': [sid for sid, _ in neighbors],
                'registration_source_ids': registration['source_ids'],
                'registration_offset_px': adjusted['offset'].tolist(),
                'registration_covariance_px2_nominal_only': adjusted['offset_cov'].tolist(),
                'gaia_jacobian_px_per_catalog_unit': jacobian.tolist(),
                'gaia_covariance_catalog_units': covariance.tolist(),
                'gaia_covariance_px2': (jacobian @ covariance @ jacobian.T).tolist(),
                'exposure_time': frame['exposure_time'], 'mjd_midpoint_utc': frame['mjd'],
                'epoch': frame['record']['epoch'], 'raw_sha256': frame['record']['sha256'],
                'cutout_url': frame['record']['cutout_url'], 'bp_rp': source.get('bp_rp'),
                'phot_g_mean_mag': source.get('phot_g_mean_mag'),
                'selection_qualification': 'legacy image-selected development cohort; upstream PSF/WCS training membership unknown'}
    return prepared, metadata


def prepare_variant(prepared, anchor, kind):
    if kind not in RULES['epsf_variants']:
        raise ValueError('unsupported reference ePSF variant')
    return semantic.prepare_semantic([prepared], anchor, background_order=1, epsf_kind=kind)[0]


def source_catalog_cross_time(context, reference):
    matrices = [];times = [];covariance = None
    for frame in context.frames:
        anchor, jacobian, covariance = prediction(reference['catalog'], frame)
        matrices.append(jacobian);times.append({'obs_id': frame['record']['obs_id'],
                                              'mjd_midpoint_utc': frame['mjd'], 'anchor_sky_px': anchor.tolist()})
    stacked = np.vstack(matrices)
    return {'source_id': reference['catalog']['source_id'], 'rows': 'x,y per listed exposure',
            'times': times, 'covariance_px2': (stacked @ covariance @ stacked.T).tolist(),
            'parameter_units': ['mas', 'mas', 'mas', 'mas/yr', 'mas/yr'],
            'qualification': 'same Gaia five-parameter error shared across exposures; not centroid or shared registration covariance'}
