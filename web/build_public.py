"""Build a small static shell; public science products are served from MongoDB."""
from pathlib import Path
import shutil


def build(root=None, output=None):
    root = Path(__file__).resolve().parent if root is None else Path(root)
    output = root / 'public' if output is None else Path(output)
    output.mkdir(parents=True, exist_ok=True)
    # Explicit allowlist: no datasets, API source, credentials or offline files.
    for path in root.iterdir():
        if path.is_file() and path.suffix in ('.html', '.css', '.js', '.svg', '.ico'):
            shutil.copy2(path, output / path.name)
    shutil.copytree(root / 'assets', output / 'assets', dirs_exist_ok=True)
    files = list(output.rglob('*'))
    if (output / 'data').exists() or (output / 'api').exists():
        raise RuntimeError('Unexpected data or API in static output')
    print(f'Static shell: {sum(p.is_file() for p in files)} files; '
          f'{sum(p.stat().st_size for p in files if p.is_file())} bytes; no data/')


if __name__ == '__main__':
    build()
