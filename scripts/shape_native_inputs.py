"""Native star samples for a fixed, globally shared three-shape correction."""
import astropy.units as u
import numpy as np

from . import neighbor_intervention_inputs as semantic
from . import native_gain_binding as geometry
from . import wise_linked_inputs as original
from .moment_preserving_epsf import MomentPreservingEPSF, numeric_parameters, physical_parameters
from .wcs_pixel_area import wcs_pixel_area


I = u.MJy/u.sr


def prepare_shape_sample(prepared, anchor, parameters, *, kind='nearest'):
    """Preserve the old native pixels/plane/IDs; correct target AND neighbors.

    Nearest is the single primary control family. Bilinear remains available
    for explicit software tests, never as an automatic fallback or selector.
    """
    values = numeric_parameters(parameters)
    baseline = semantic.prepare_semantic([prepared], anchor, background_order=1, epsf_kind=kind)[0]
    sample = prepared['sample'];frame = sample['frame'];mask = prepared['selection_mask']
    active = geometry.validate_image(frame['image_header'], frame['primary_header'], frame['record']['collection'])

    def make_kernel(position, label):
        native = original.native_position(frame, position)
        raw, description = semantic.select_epsf(frame['epsf_table'], active.pixel_to_world_values(*native), kind)
        return MomentPreservingEPSF(raw, provenance=frame['epsf_provenance']+'|'+label), description

    target_kernel, target_shape = make_kernel(anchor, 'target fixed shape anchor')

    def render_details(position, coefficients):
        native = original.native_position(frame, position)
        area = wcs_pixel_area(frame['wcs'], native, provenance=prepared['renderer_provenance'])
        if not area.supported:
            raise ValueError('target solid-angle refinement unsupported')
        return target_kernel.render(native, mask, source_omega=area.solid_angle, parameters=coefficients,
            source_omega_provenance=prepared['renderer_provenance']+'|same geometric center Omega')

    def renderer(position):
        return render_details(position, parameters).template_per_jy

    def shape_renderer(position):
        rendered = render_details(position, physical_parameters([0., 0., 0.]))
        return rendered.selected_shape_directions/(1e6*rendered.metadata['source_omega_sr'])

    columns = [];directions = [];descriptions = []
    positions = dict(sample['neighbours'])
    for sid in baseline['neighbor_ids']:
        position = positions[sid];kernel, description = make_kernel(position, sid)
        native = original.native_position(frame, position)
        area = wcs_pixel_area(frame['wcs'], native, provenance=prepared['renderer_provenance']+'|'+sid)
        if not area.supported:
            raise ValueError('neighbor solid-angle refinement unsupported')
        result = kernel.render(native, mask, source_omega=area.solid_angle, parameters=parameters,
            source_omega_provenance=prepared['renderer_provenance']+'|'+sid+'|same geometric center Omega')
        column = result.template_per_jy.to_value(I/u.Jy)
        if not np.any(column != 0):
            raise ValueError('zero corrected neighbor template')
        columns.append(column)
        directions.append(result.selected_shape_directions/(1e6*result.metadata['source_omega_sr']))
        descriptions.append({'id': sid, 'spatial_epsf': description, 'correction': result.metadata})
    n = len(baseline['data'])
    output = {**baseline, 'renderer': renderer, 'shape_renderer': shape_renderer,
              'neighbor_design': np.column_stack(columns) if columns else np.empty((n, 0)),
              'neighbor_shape_design': np.stack(directions, axis=1) if directions else np.empty((n, 0, 3)),
              'render_details': render_details,
              'metadata': {**baseline['metadata'], 'shape_coefficients': values.tolist(),
                           'shape_parameter_units': ['pix2', 'pix3', 'pix3'],
                           'shape_family': 'global width/odd-x/odd-y; full-native-lattice three-moment gauge',
                           'target_spatial_epsf': target_shape, 'corrected_neighbors': descriptions}}
    # A new family at theta=0 must reproduce the frozen physical templates.
    if np.all(values == 0):
        control = baseline['renderer'](anchor).to_value(I/u.Jy)
        candidate = renderer(anchor).to_value(I/u.Jy)
        tolerance = 1e-11*max(1., float(np.max(np.abs(control))))
        if (not np.allclose(control, candidate, rtol=1e-11, atol=tolerance)
                or not np.allclose(baseline['neighbor_design'], output['neighbor_design'], rtol=1e-11, atol=tolerance)):
            raise ValueError('zero-correction control differs from frozen renderer')
    return output
