"""Local celestial WCS pixel solid angle; no photometric calibration implied."""
from dataclasses import dataclass
from numbers import Integral, Real

import numpy as np
from astropy import units as u
from astropy.wcs import WCS


@dataclass(frozen=True)
class PixelArea:
    solid_angle: u.Quantity
    coarse_solid_angle: u.Quantity
    relative_difference: float
    supported: bool
    orientation: int
    coarse_subdivisions: int
    fine_subdivisions: int
    relative_tolerance: float
    provenance: str


def _triangles(a, b, c):
    # The difference form avoids cancellation in the triple product at small
    # pixel scales. All coordinates are unit vectors in the same sky frame.
    numerator = np.einsum('...i,...i->...', a, np.cross(b-a, c-a))
    scale = np.linalg.norm(b-a, axis=-1)*np.linalg.norm(c-a, axis=-1)
    denominator = 1 + np.einsum('...i,...i->...', a, b) + np.einsum('...i,...i->...', b, c) + np.einsum('...i,...i->...', c, a)
    if (not np.isfinite(numerator).all() or not np.isfinite(denominator).all()
            or not np.isfinite(scale).all() or np.any(scale == 0)
            or np.any(np.abs(numerator) <= 64*np.finfo(float).eps*scale)
            or np.any(denominator <= 0)):
        raise ValueError('degenerate or nonlocal spherical triangle')
    return 2*np.arctan2(numerator, denominator)


def _area(wcs, x, y, n, lon_axis, lat_axis):
    offsets = np.linspace(-.5, .5, n+1)
    xx, yy = np.meshgrid(x+offsets, y+offsets)
    try:
        world = np.asarray(wcs.all_pix2world(np.column_stack((xx.ravel(), yy.ravel())), 0), dtype=float)
    except Exception as exc:
        raise ValueError('celestial WCS transformation failed') from exc
    if world.shape != ((n+1)**2, 2) or not np.isfinite(world).all():
        raise ValueError('celestial WCS returned invalid coordinates')
    lon, lat = world[:, lon_axis], world[:, lat_axis]
    if np.any(np.abs(lat) > 90):
        raise ValueError('invalid celestial latitude')
    lon, lat = np.deg2rad(lon), np.deg2rad(lat)
    coslat = np.cos(lat)
    v = np.column_stack((coslat*np.cos(lon), coslat*np.sin(lon), np.sin(lat))).reshape(n+1, n+1, 3)
    a, b, c, d = v[:-1, :-1], v[:-1, 1:], v[1:, 1:], v[1:, :-1]
    # Four triangles check both diagonals: a concave or folded quad has a
    # sign reversal even if a single chosen diagonal appears nonzero.
    triangles = np.stack((_triangles(a,b,c), _triangles(a,c,d),
                          _triangles(a,b,d), _triangles(b,c,d)))
    sign = np.sign(triangles.flat[0])
    if np.any(np.sign(triangles) != sign):
        raise ValueError('folded, nonconvex, or mixed-orientation pixel')
    area = float(np.sum(np.abs(triangles[0]) + np.abs(triangles[1])))
    if not np.isfinite(area) or area <= 0:
        raise ValueError('invalid pixel solid angle')
    return area, int(sign)


def wcs_pixel_area(wcs, pixel_xy, *, provenance, relative_tolerance=1e-4,
                   coarse_subdivisions=2, fine_subdivisions=4):
    """Approximate one unit-square pixel area in sr with a refinement check.

    pixel_xy is a zero-based (x,y) center; integer coordinates denote actual
    native pixel centers. Celestial longitude/latitude WCS must have two pixel
    and two world axes in degrees. The refinement difference is a diagnostic,
    not a rigorous error bound; unsupported means it exceeded the tolerance.
    Caller supplies a traceable WCS provenance string, and must separately
    establish image association, solid-angle calibration and flux convention.
    """
    if not isinstance(wcs, WCS) or wcs.pixel_n_dim != 2 or wcs.world_n_dim != 2 or not wcs.has_celestial:
        raise ValueError('a two-dimensional celestial WCS is required')
    types = list(wcs.world_axis_physical_types)
    lon_axis, lat_axis = wcs.wcs.lng, wcs.wcs.lat
    if (sorted((lon_axis, lat_axis)) != [0, 1] or
            any(not isinstance(kind, str) or not kind.startswith('pos.') for kind in types) or
            any(unit != 'deg' for unit in wcs.world_axis_units)):
        raise ValueError('celestial longitude and latitude axes in degrees are required')
    if not isinstance(provenance, str) or not provenance.strip():
        raise ValueError('WCS provenance is required')
    position = np.asarray(pixel_xy)
    if position.shape != (2,) or position.dtype.kind not in 'iuf' or not np.isfinite(position).all():
        raise ValueError('pixel center must be finite real (x,y)')
    x, y = map(float, position)
    if not isinstance(relative_tolerance, Real) or isinstance(relative_tolerance, (bool, np.bool_)) or not np.isfinite(relative_tolerance) or relative_tolerance < 0:
        raise ValueError('relative tolerance must be finite and nonnegative')
    for n in (coarse_subdivisions, fine_subdivisions):
        if isinstance(n, (bool, np.bool_)) or not isinstance(n, Integral) or not 1 <= n <= 64:
            raise ValueError('subdivision count must be an integer in [1,64]')
    if fine_subdivisions <= coarse_subdivisions or fine_subdivisions % coarse_subdivisions:
        raise ValueError('fine subdivisions must be a larger integer multiple of coarse subdivisions')
    coarse, coarse_sign = _area(wcs, x, y, coarse_subdivisions, lon_axis, lat_axis)
    fine, fine_sign = _area(wcs, x, y, fine_subdivisions, lon_axis, lat_axis)
    if coarse_sign != fine_sign:
        raise ValueError('orientation changes with subdivision')
    difference = abs(fine-coarse)/fine
    return PixelArea(fine*u.sr, coarse*u.sr, difference, difference <= relative_tolerance,
                     fine_sign, int(coarse_subdivisions), int(fine_subdivisions),
                     float(relative_tolerance), provenance)
