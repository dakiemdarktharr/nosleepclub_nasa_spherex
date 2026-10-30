"""Narrow R7 D6 map binding with per-HDU coordinate declarations.

The channel map is SKY; band center/width maps are DEVICE. These are
laboratory diagnostics, not a replacement for a QR2 calibration product.
"""
from dataclasses import dataclass
from io import BytesIO

from astropy.io import fits
import numpy as np

from . import lab_spectral_response as lab


def unique(header, key):
    values = [c.value for c in header.cards if c.keyword == key]
    if len(values) != 1:
        raise ValueError('missing or duplicate header '+key)
    return values[0]


def active_to_map_indices(x, y, shape, orientation, *, detector=6):
    """Convert zero-based sky-oriented active integer pixels for D6 only."""
    x, y = np.asarray(x), np.asarray(y)
    if (type(detector) is not int or detector != 6 or len(shape) != 2 or
            any(type(v) is not int or v <= 0 for v in shape) or
            x.shape != y.shape or x.dtype.kind not in 'iuf' or y.dtype.kind not in 'iuf'):
        raise ValueError('unsupported map geometry')
    if (not np.isfinite(x).all() or not np.isfinite(y).all() or
            np.any(x != np.rint(x)) or np.any(y != np.rint(y)) or
            np.any(x < 0) or np.any(y < 0) or
            np.any(x >= shape[1]) or np.any(y >= shape[0])):
        raise ValueError('active pixels must be exact integers inside the map')
    if orientation not in ('sky', 'DEVICE'):
        raise ValueError('unknown map coordinate system')
    ix = x.astype(np.int64)
    iy = y.astype(np.int64)
    return (shape[1]-1-ix if orientation == 'DEVICE' else ix), iy


@dataclass(frozen=True)
class CalibrationMap:
    array: np.ndarray
    orientation: str
    member: str
    headers: tuple
    unit: str | None
    unit_source: str | None

    def values(self, x, y):
        ix, iy = active_to_map_indices(x, y, self.array.shape, self.orientation)
        return np.asarray(self.array[iy, ix]).copy()


def _read_map(archive, name, extension, *, orientation, detector, unit=None):
    raw = archive.read(name, maximum_bytes=34000000)
    with fits.open(BytesIO(raw), memmap=False) as h:
        found = [x for x in h if x.name == extension]
        if len(found) != 1 or found[0].data is None:
            raise ValueError('missing or ambiguous calibration extension')
        image = found[0]
        if image.data.shape != (2040,2040) or image.data.dtype.kind not in 'iuf':
            raise ValueError('unsupported calibration shape/type')
        if (unique(image.header,'DETCOORD') != orientation or
                unique(image.header,'DETECTOR') != detector or
                unique(image.header,'TELESCOP') != 'SPHEREx'):
            raise ValueError('calibration coordinate/detector metadata mismatch')
        if unit is not None and 'BUNIT' in image.header and unique(image.header,'BUNIT') != 'um':
            raise ValueError('calibration unit contradicts delivery documentation')
        array = np.asarray(image.data).copy()
        headers = tuple((c.keyword,c.value,c.comment) for c in image.header.cards)
    return CalibrationMap(array, orientation, name, headers, unit,
                          lab.DOCUMENTATION_URL if unit is not None else None)


def read_maps(archive, *, channels=68):
    if type(channels) is not int or channels not in (17,34,51,68):
        raise ValueError('unsupported channel granularity')
    channel = _read_map(archive,
        f'ChannelMaps/spectral_channels_{channels}ch_2040.fits',
        f'CHANNEL_MAP_{channels}', orientation='sky', detector='ALL')
    center = _read_map(archive, 'ParameterFiles/20260604_SSDC_BC_Band6.fits',
                       'BAND_CENTER', orientation='DEVICE', detector='6', unit='um')
    width = _read_map(archive, 'ParameterFiles/20260604_SSDC_BW_Band6.fits',
                      'BAND_WIDTH', orientation='DEVICE', detector='6', unit='um')
    if (channel.array.dtype.kind not in 'iu' or np.any(channel.array < 0) or
            np.any(channel.array > channels+1)):
        raise ValueError('invalid channel map encoding')
    return {'channel': channel, 'center': center, 'width': width}


def bind_pixel(maps, x, y, *, channels=68):
    """Return channel and local map parameters; no spectral curve is altered."""
    if type(x) is not int or type(y) is not int or type(channels) is not int:
        raise ValueError('one exact integer source pixel required')
    channel = int(maps['channel'].values(x,y))
    center = float(maps['center'].values(x,y))
    width = float(maps['width'].values(x,y))
    if not 1 <= channel <= channels:
        raise ValueError('source pixel in unsupported excess channel')
    if not np.isfinite([center,width]).all() or center <= 0 or width <= 0:
        raise ValueError('source pixel lacks positive finite band parameters')
    return {'sky_active_xy':[x,y], 'channel':channel, 'channels':channels,
            'center_um':center, 'width_um':width,
            'channel_map_xy':[x,y], 'parameter_map_xy':[maps['center'].array.shape[1]-1-x,y],
            'unit_source':lab.DOCUMENTATION_URL,
            'qualification':'R7 laboratory geometry only; no QR2 calibration replacement, curve shift or fit'}
