"""Private worker: one process, one cached-field audit; never fetch data."""
from contextlib import contextmanager
import os
import sys
import threading
import time


def start_parent_watchdog():
    # The supervisor never writes. EOF means its only write handle has closed.
    # Install this before loading scientific libraries or opening any input.
    ready = threading.Event()
    def watch():
        try:
            if os.name == 'nt':
                # A blocking CRT read holds a Windows descriptor lock that can
                # deadlock native-library initialization. Poll the pipe handle.
                import ctypes
                import msvcrt
                from ctypes import wintypes
                kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                kernel.PeekNamedPipe.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                                                wintypes.LPVOID, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
                kernel.PeekNamedPipe.restype = wintypes.BOOL
                handle = msvcrt.get_osfhandle(0)
                while True:
                    available = wintypes.DWORD()
                    if not kernel.PeekNamedPipe(handle, None, 0, None, ctypes.byref(available), None) or available.value:
                        break
                    ready.set()
                    time.sleep(.1)
            else:
                import select
                if select.select([0], [], [], 0)[0]: return
                ready.set()
                select.select([0], [], [])
        finally:
            os._exit(70)
    threading.Thread(target=watch, name='supervisor-watchdog', daemon=True).start()
    ready.wait()


@contextmanager
def hold_worker_lock(path):
    # Recovery must not start science until the previous worker has exited.
    from . import science_jobs as jobs
    deadline = time.monotonic() + 3.0
    while True:
        lock = jobs.locked(path, name='worker.lock')
        try:
            lock.__enter__()
            break
        except RuntimeError:
            if time.monotonic() >= deadline: raise RuntimeError('previous worker still active')
            time.sleep(.05)
    try:
        yield
    finally:
        lock.__exit__(None, None, None)


def main(job_id, output_name):
    start_parent_watchdog()
    from . import science_jobs as jobs
    with hold_worker_lock(jobs.job_path(job_id)):
        return execute(job_id, output_name)


def execute(job_id, output_name):
    import json
    import re
    import numpy as np
    from astropy.io import fits
    from astropy.wcs import WCS
    from scipy.ndimage import map_coordinates
    from . import science_jobs as jobs
    from . import benchmark_accuracy as bench
    if not re.fullmatch(r'attempt-[0-9]+-[0-9a-f]{32}\.json', output_name):
        raise ValueError('invalid attempt output')
    path = jobs.job_path(job_id)
    spec = json.loads((path / 'manifest.json').read_text(encoding='utf-8'))
    if jobs.sha256(jobs.encode(spec)).hexdigest() != job_id: raise ValueError('identity mismatch')
    jobs.verify_identity(spec)
    manifest = json.loads((jobs.ROOT / spec['manifest_path']).read_text(encoding='utf-8'))
    bench.context(manifest['field'])  # Globals remain private to this process.
    rows = bench.gaia.catalog_rows(manifest)
    center = manifest['field']; dec0 = np.deg2rad(center['dec'])
    candidates = []
    for r in rows:
        if r.get('ra') is None or r.get('dec') is None: continue
        # Great-circle separation for declared geometric selection.
        d = np.deg2rad(float(r['dec'])); dra = np.deg2rad(float(r['ra'])-center['ra'])
        sep = np.rad2deg(np.arccos(np.clip(np.sin(d)*np.sin(dec0)+np.cos(d)*np.cos(dec0)*np.cos(dra), -1, 1)))
        if sep <= .05: candidates.append(r)
    candidates.sort(key=lambda r: int(r['source_id']))
    controls = candidates[:5]
    if len(controls) < 5: raise ValueError('fewer than five cached Gaia controls')
    cal = manifest['calibrations']['spectral_wcs']
    with fits.open(jobs.safe_input(cal['path']), memmap=False) as h:
        cw = np.array(h['CWAVE'].data, dtype=float); cb = np.array(h['CBAND'].data, dtype=float)
        units = {'cwave': str(h['CWAVE'].header.get('BUNIT', 'unspecified')), 'cband': str(h['CBAND'].header.get('BUNIT', 'unspecified'))}
    output = {'job_id': job_id, 'identity': spec, 'field': center, 'gaia': manifest['gaia'], 'spectral_calibration': cal,
              'units_from_calibration_header': units,
              'interpretation': 'Gaia reference-epoch fixed catalog coordinates; not measured or crossmatched at SPHEREx epoch; no proper-motion/parallax propagation or astrometric fit. Opened-field diagnostic, not validation.',
              'mask': {'bad_bits': list(bench.base.BAD_BITS), 'valid_rule': 'FLAGS & BAD_MASK == 0 and finite IMAGE/VARIANCE and VARIANCE > 0', 'support': 'valid pixels in clipped 11x11 native-pixel stamp; not an acceptance of a source detection'}, 'frames': []}
    selected = {r['obs_id']:r for r in manifest['records']}
    for obs in spec['selected_obs_ids']:
        record = selected[obs]
        with fits.open(jobs.safe_input(record['path']), memmap=False) as h:
            header = h['IMAGE'].header; spatial = WCS(header); parent = bench.base.alternate_wcs(header, h, 'A')
            flags = np.asarray(h['FLAGS'].data, dtype=np.int64); raw = np.asarray(h['IMAGE'].data, dtype=float); var = np.asarray(h['VARIANCE'].data, dtype=float)
            valid = ((flags & bench.base.BAD_MASK) == 0) & np.isfinite(raw) & np.isfinite(var) & (var > 0)
            frame = {'record': record, 'mjd_obs_header': float(header['MJD-OBS']), 'timesys_header': str(header.get('TIMESYS', 'unspecified')),
                     'pipeline_version': str(h[0].header.get('VERSION', '')), 'controls': []}
            for r in controls:
                x,y = (float(v) for v in spatial.world_to_pixel_values(float(r['ra']), float(r['dec'])))
                in_image = np.isfinite(x+y) and 0 <= x < raw.shape[1] and 0 <= y < raw.shape[0]
                entry = {'source_id': str(r['source_id']), 'catalog_ra_deg': float(r['ra']), 'catalog_dec_deg': float(r['dec']),
                         'ref_epoch_jyear': float(r['ref_epoch']), 'native_xy_px': [x,y] if np.isfinite(x+y) else None,
                         'position_offset_native_px': None, 'stamp_valid_pixels': 0, 'stamp_total_pixels': 0,
                         'center_valid': False, 'stamp_bounds_xy_exclusive': None, 'stamp_valid_mask_rows': None, 'cwave': None, 'cband': None, 'spectral_calibration_support': False}
                if in_image:
                    xi,yi = int(round(x)), int(round(y)); x0=max(0,xi-5); x1=min(raw.shape[1],xi+6); y0=max(0,yi-5); y1=min(raw.shape[0],yi+6)
                    entry['position_offset_native_px'] = [x-xi,y-yi]
                    entry['stamp_valid_pixels'] = int(valid[y0:y1,x0:x1].sum()); entry['stamp_total_pixels'] = int((x1-x0)*(y1-y0))
                    entry['stamp_bounds_xy_exclusive'] = [x0,y0,x1,y1]
                    entry['stamp_valid_mask_rows'] = valid[y0:y1,x0:x1].astype(int).tolist()
                    entry['center_valid'] = bool(valid[min(yi,raw.shape[0]-1),min(xi,raw.shape[1]-1)])
                    gx,gy = parent.pixel_to_world_values(x,y)
                    if np.isfinite(gx+gy):
                        wave=float(map_coordinates(cw, [[gy],[gx]], order=1, mode='constant', cval=np.nan)[0])
                        band=float(map_coordinates(cb, [[gy],[gx]], order=1, mode='constant', cval=np.nan)[0])
                        if np.isfinite(wave) and np.isfinite(band) and band > 0:
                            entry.update(cwave=wave,cband=band,spectral_calibration_support=True)
                frame['controls'].append(entry)
            output['frames'].append(frame)
    jobs.verify_identity(spec)
    with (path / output_name).open('xb') as f:
        f.write(jobs.encode(output)); f.flush()
    return 0

if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
