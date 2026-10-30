"""Fail-closed SPHEREx L2 image mask proposal; no frozen pipeline changes."""

import numpy as np

# Caltech-IPAC/spherex-pipelines, spx_flags.py at aa0ba446ee12971024fe13dc1c47387615bbe85e.
VERIFIED_BITS = dict(TRANSIENT=0, OVERFLOW=1, SUR_ERROR=2, PHANTOM=4,
    REFERENCE=5, NONFUNC=6, DICHROIC=7, MISSING_DATA=9, HOT=10, COLD=11,
    FULLSAMPLE=12, SUR_MISMATCH=13, PHANMISS=14, NONLINEAR=15, VAR_UNDER=16,
    PERSIST=17, PERSIST_UNK=18, OUTLIER=19, CROSSTALK=20, SOURCE=21,
    GHOST=22, GHOST_FPA=23, GHOST_EXT=24, STREAK=25, BLOOM=26, SNOWBALL=27,
    HALO=28, SATELLITE_HALO=29)
REQUIRED = frozenset(('TRANSIENT', 'OVERFLOW', 'SUR_ERROR', 'PHANTOM',
    'REFERENCE', 'NONFUNC', 'DICHROIC', 'MISSING_DATA', 'HOT', 'COLD',
    'FULLSAMPLE', 'PHANMISS', 'NONLINEAR', 'PERSIST', 'OUTLIER', 'SOURCE'))


def validate_layout(header, collection):
    """Check all MP_ cards against the verified L2 image flag definitions.

    Optional documented flags are allowed only at their documented bits. Every
    set image bit must also be advertised by this particular header.
    """
    if collection not in ('spherex_qr2', 'spherex_qr3'):
        raise ValueError('unsupported data collection')
    pairs = [(str(c.keyword)[3:], c.value) for c in header.cards
             if str(c.keyword).startswith('MP_')]
    names = [name for name, _ in pairs]
    if len(set(names)) != len(names) or not REQUIRED.issubset(names):
        raise ValueError('missing or duplicate MP_ definitions')
    for name, bit in pairs:
        if name not in VERIFIED_BITS or isinstance(bit, (bool, np.bool_)) or not isinstance(bit, (int, np.integer)) or bit != VERIFIED_BITS[name]:
            raise ValueError(f'unknown or mismatched MP_ definition: {name}')
    return dict(pairs)


def science_masks(flags, image, variance, header, collection):
    """Return usable target/background masks, rejecting unknown layouts/bits."""
    layout = validate_layout(header, collection)
    flags = np.asarray(flags)
    image = np.asarray(image)
    variance = np.asarray(variance)
    if flags.shape != image.shape or flags.shape != variance.shape:
        raise ValueError('image, variance and flag shape mismatch')
    if flags.dtype.kind not in 'iu' or (flags.dtype.kind == 'i' and np.any(flags < 0)):
        raise ValueError('flags must be nonnegative integers')
    f = flags.astype(np.uint64)
    known = sum(1 << n for n in layout.values())
    if np.any(f & np.uint64(((1 << 64) - 1) ^ known)):
        raise ValueError('set flag bit not declared in image header')
    valid = np.isfinite(image) & np.isfinite(variance) & (variance > 0)
    return valid & ((f == 0) | (f == np.uint64(1 << 21))), valid & (f == 0)
