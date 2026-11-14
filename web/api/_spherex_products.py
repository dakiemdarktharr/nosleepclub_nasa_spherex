"""Canonical identifiers and URL policy for IRSA spectral image products."""
import re
from urllib.parse import urlsplit


HOST = 'irsa.ipac.caltech.edu'
PATH = re.compile(
    r'^/ibe/data/spherex/(?P<release>dr1|qr[23])/level2/'
    r'(?P<period>\d{4}W\d{2}_[0-9][A-Z])/'
    r'(?P<version>l2b(?:_retry)?-v\d+-\d{4}-\d{3})/(?P<detector>[1-6])/'
    r'level2_(?P=period)_(?P<exposure>\d{4}_[0-9])D(?P=detector)_spx_(?P=version)\.fits$'
)


def image_identity(url):
    """Return a matched product identity for a canonical, unmodified data URL."""
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if parsed.scheme != 'https' or parsed.netloc != HOST or parsed.query or parsed.fragment:
        return None
    return PATH.fullmatch(parsed.path)
