"""Read the pinned R7 laboratory response delivery without extracting its tar."""
import csv
from hashlib import sha256
from io import StringIO
from pathlib import Path, PurePosixPath
import tarfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'data/raw/external/spherex-spectral-calibration/SPHERExSpectralFiles_202607.tar'
ARCHIVE_BYTES = 436705280
ARCHIVE_SHA256 = '45ff6c57ca68da00a595a4e8a5c2f875cc98b094fde143d9ce109e69df252f09'
ARCHIVE_URL = 'https://irsa.ipac.caltech.edu/data/SPHEREx/docs/spectral_files_20260812/SPHERExSpectralFiles_202607.tar'
DOCUMENTATION_URL = 'https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHERExSpectralFiles_202607.pdf'


def digest(path):
    h = sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _table(raw, columns):
    if not isinstance(raw, bytes) or len(raw) > 100000:
        raise ValueError('bounded CSV bytes required')
    rows = [row for row in csv.reader(StringIO(raw.decode('utf-8'), newline=None)) if row]
    if not rows or rows[0] != list(columns) or any(len(row) != len(columns) for row in rows[1:]):
        raise ValueError('unexpected CSV columns or row width')
    try:
        array = np.array(rows[1:], dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError('invalid CSV numeric values') from exc
    if array.ndim != 2 or not len(array) or not np.isfinite(array).all():
        raise ValueError('CSV must have finite numeric rows')
    return array


def parse_curve(raw):
    array = _table(raw, ('Wavelength_um', 'NormTransmission'))
    if len(array) < 2 or np.any(array[:, 0] <= 0) or np.any(np.diff(array[:, 0]) <= 0):
        raise ValueError('invalid response wavelength sequence')
    if array[:, 1].max() <= 0:
        raise ValueError('response has no positive samples')
    # Negative lab measurements are retained, not converted to photon truth.
    return array[:, 0], array[:, 1]


def parse_summary(raw, channels):
    array = _table(raw, ('SpecCh', 'BandCenter_um', 'BandWidth_um',
                         'BandCenter_Allpix_um', 'BandWidth_Allpix_um'))
    if array.shape != (channels, 5) or not np.array_equal(array[:, 0], np.arange(1, channels + 1)) or np.any(array[:, 1:] <= 0):
        raise ValueError('unexpected channel summary')
    return array


class LabArchive:
    """Only the exact recorded archive is supported; no filesystem extraction."""
    def __init__(self, path=ARCHIVE):
        self.path = Path(path)
        if self.path.stat().st_size != ARCHIVE_BYTES or digest(self.path) != ARCHIVE_SHA256:
            raise ValueError('laboratory archive size or hash mismatch')
        self.tar = tarfile.open(self.path, mode='r:')
        try:
            items = self.tar.getmembers()
            if len(items) != 2169:
                raise ValueError('unexpected archive member count')
            self.members = {}
            for item in items:
                name = PurePosixPath(item.name)
                if (name.is_absolute() or '..' in name.parts or '\\' in item.name or
                        not (item.isfile() or item.isdir()) or item.name in self.members):
                    raise ValueError('unsafe or ambiguous archive member')
                self.members[item.name] = item
        except Exception:
            self.tar.close()
            raise
        self.used = {}

    def close(self):
        self.tar.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def read(self, name, maximum_bytes=100000):
        item = self.members.get(name)
        if item is None or not item.isfile() or not 0 < item.size <= maximum_bytes:
            raise ValueError('missing or oversized selected member')
        with self.tar.extractfile(item) as stream:
            raw = stream.read(item.size + 1)
        if len(raw) != item.size:
            raise ValueError('truncated selected member')
        self.used[name] = {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
        return raw

    def curve(self, channel, *, channels=17, kind='Cent', detector=6):
        if type(channel) is not int or type(channels) is not int or channels not in (17,34,51,68) or not 1 <= channel <= channels or type(detector) is not int or detector not in range(1,7) or kind not in ('Cent','Allpix'):
            raise ValueError('unsupported response selection')
        folder = 'MiddlePixel' if kind == 'Cent' else 'MeanAllPixel'
        name = f'{folder}/SubChannel{channels}/Band{detector}/FiducialSpec_Band{detector}_SubCh{channel:02d}_{channels}_{kind}.csv'
        return name, *parse_curve(self.read(name))

    def summary(self, *, channels=17, detector=6):
        if type(channels) is not int or channels not in (17,34,51,68) or type(detector) is not int or detector not in range(1,7):
            raise ValueError('unsupported summary selection')
        name = f'FidSpecSummary/SubChannel{channels}/Band{detector}/FidSpecSummary_Band{detector}_SpecCh{channels}.csv'
        return name, parse_summary(self.read(name), channels)
