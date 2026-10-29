"""Build a reproducible, explicitly exploratory comparison from real SPHEREx FITS."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from astropy import log
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.time import Time
from astropy.wcs import WCS
import astropy.units as u
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates, maximum_filter, binary_erosion
from scipy.signal import convolve2d

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/wise0855"
OUT = ROOT / "web/data"
SHAPE = (64, 64)
SCALE = 6.15
CENTER = (133.76037473328523, -7.242149767967145)
BAD_BITS = (0, 1, 2, 6, 7, 9, 10, 11, 14, 15, 17, 19, 20, 22, 24, 25, 26, 27, 28, 29)
BAD_MASK = sum(1 << bit for bit in BAD_BITS)
PAIRS = [
    ("matched-4853", "4.853 µm · khớp phổ tốt nhất", "2025W19_1B_0138_1", "2026W19_2A_0651_1"),
    ("matched-4961", "4.961 µm · đối chiếu độc lập", "2025W19_1B_0116_1", "2026W20_1A_0033_1"),
    ("matched-4609", "4.609 µm · baseline ngắn hơn", "2025W46_1A_0090_3", "2026W17_1B_0634_1"),
]


def expected_position(mjd: float) -> tuple[float, float]:
    """Linear search prior from Luhman 2014 Tables 1/2; no parallax fit."""
    dt = (mjd - 56677.3) / 365.25
    return (133.787085 - 8.06 * dt / (3600 * np.cos(np.deg2rad(-7.244451))),
            -7.244451 + 0.70 * dt / 3600)


def grid_wcs(shape=SHAPE, center=CENTER) -> WCS:
    w = WCS(naxis=2)
    w.wcs.crpix = [(shape[1] + 1) / 2, (shape[0] + 1) / 2]
    w.wcs.cdelt = [-SCALE / 3600, SCALE / 3600]
    w.wcs.crval = center
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    return w


def alternate_wcs(header, hdul, key):
    # The official tutorial disables SIP on the spectral and detector WCS.
    clean = header.copy()
    for name in list(clean):
        if name in ("A_ORDER", "B_ORDER", "AP_ORDER", "BP_ORDER") or name.startswith(("A_", "B_", "AP_", "BP_")):
            del clean[name]
    w = WCS(clean, fobj=hdul, key=key)
    w.sip = None
    return w


def bilinear(data, variance, valid, x, y):
    """Masked bilinear sampling with squared-weight variance propagation.

    Neighbouring output pixels remain correlated; empirical residual scores below
    are deliberately not described as calibrated Gaussian significance.
    """
    finite = np.isfinite(x) & np.isfinite(y)
    x0 = np.floor(np.where(finite, x, 0)).astype(int)
    y0 = np.floor(np.where(finite, y, 0)).astype(int)
    dx, dy = x - x0, y - y0
    numerator, varnum, support = (np.zeros_like(x, dtype=float) for _ in range(3))
    for ox, oy, weight in ((0, 0, (1-dx)*(1-dy)), (1, 0, dx*(1-dy)),
                           (0, 1, (1-dx)*dy), (1, 1, dx*dy)):
        xx, yy = x0 + ox, y0 + oy
        inside = finite & (xx >= 0) & (yy >= 0) & (xx < data.shape[1]) & (yy < data.shape[0])
        xx = np.clip(xx, 0, data.shape[1]-1)
        yy = np.clip(yy, 0, data.shape[0]-1)
        ww = np.where(inside & valid[yy, xx], weight, 0)
        numerator += ww * np.nan_to_num(data[yy, xx])
        varnum += ww**2 * np.nan_to_num(variance[yy, xx])
        support += ww
    safe = np.maximum(support, 1e-12)
    image, var = numerator / safe, varnum / safe**2
    image[support < .75] = np.nan
    var[support < .75] = np.nan
    return image, var, support


def read_frame(record):
    path = ROOT / record["path"]
    with fits.open(path) as h:
        header = h["IMAGE"].header
        spatial = WCS(header)
        spectral = alternate_wcs(header, h, "W")
        parent = alternate_wcs(header, h, "A")
        mjd = float(header["MJD-OBS"])
        position = expected_position(mjd)
        px, py = spatial.world_to_pixel_values(*position)
        wavelength, bandwidth = spectral.pixel_to_world(float(px), float(py))
        flags = h["FLAGS"].data.astype(np.int64)
        raw = np.array(h["IMAGE"].data, dtype=float)
        variance = np.array(h["VARIANCE"].data, dtype=float)
        zodi = np.array(h["ZODI"].data, dtype=float)
        valid = ((flags & BAD_MASK) == 0) & np.isfinite(raw) & np.isfinite(variance) & (variance > 0)
        corrected = raw - zodi
        _, background, _ = sigma_clipped_stats(corrected, mask=~valid)
        corrected -= background
        gx, gy = parent.pixel_to_world_values(float(px), float(py))
        ph = h["PSF"].header
        zones = range(1, h["PSF"].data.shape[0]+1)
        zone = min(zones, key=lambda i: (ph[f"XCTR_{i}"]-gx)**2 + (ph[f"YCTR_{i}"]-gy)**2)
        high_psf = np.asarray(h["PSF"].data[zone-1], dtype=float)
        oversampling = float(ph["OVERSAMP"])
        # Rotate and resample the measured local PSF onto the north-up grid.
        psf_w = grid_wcs((11, 11), position)
        ky, kx = np.indices((11, 11), dtype=float)
        kr, kd = psf_w.pixel_to_world_values(kx, ky)
        nx, ny = spatial.world_to_pixel_values(kr, kd)
        kernel = map_coordinates(high_psf,
            [(ny-py)*oversampling+(high_psf.shape[0]-1)/2,
             (nx-px)*oversampling+(high_psf.shape[1]-1)/2], order=1, mode="constant", cval=0)
        kernel = np.maximum(kernel, 0)
        kernel /= kernel.sum()
        return {"record": record, "wcs": spatial, "spectral": spectral, "data": corrected,
                "variance": variance, "valid": valid, "flags": flags, "psf": kernel,
                "mjd": mjd, "position": position, "wavelength": float(wavelength.to_value(u.um)),
                "bandwidth": float(bandwidth.to_value(u.um)), "background": float(background),
                "pipeline_version": str(h[0].header.get("VERSION", "")), "psf_zone": zone,
                "native_shape": list(raw.shape), "native_psf": high_psf, "oversampling": oversampling}


def native_target_fit(frame):
    """Fixed-position PSF amplitude fit; this does not measure proper motion."""
    px, py = frame["wcs"].world_to_pixel_values(*frame["position"])
    yy, xx = np.indices(frame["data"].shape, dtype=float)
    dx, dy = xx-px, yy-py
    keep = (np.abs(dx)<=5) & (np.abs(dy)<=5) & frame["valid"]
    psf = frame["native_psf"]
    over = frame["oversampling"]
    model = map_coordinates(psf, [dy*over+(psf.shape[0]-1)/2, dx*over+(psf.shape[1]-1)/2],
                            order=1, mode="constant", cval=0)
    model *= over**2/max(psf.sum(),1e-12)
    design = np.column_stack([model[keep], np.ones(keep.sum()), dx[keep], dy[keep]])
    errors = np.sqrt(frame["variance"][keep])
    weights = design/errors[:,None]
    coefficients, _, _, _ = np.linalg.lstsq(weights, frame["data"][keep]/errors, rcond=None)
    covariance = np.linalg.pinv(weights.T@weights)
    amplitude_error = np.sqrt(covariance[0,0])
    reduced_chi2 = np.sum(((design@coefficients-frame["data"][keep])/errors)**2)/max(1,keep.sum()-4)
    # Conservatively inflate the formal error for residual model mismatch.
    amplitude_error *= max(1.,np.sqrt(reduced_chi2))
    return {"fixed_prior_snr": float(coefficients[0]/amplitude_error),
            "reduced_chi2": float(reduced_chi2), "fit_pixels": int(keep.sum()),
            "position_fitted": False, "note": "PSF amplitude at an extrapolated position; no independent motion fit."}


def project(frame, output_wcs, shift=(0., 0.)):
    yy, xx = np.indices(SHAPE, dtype=float)
    ra, dec = output_wcs.pixel_to_world_values(xx+shift[0], yy+shift[1])
    x, y = frame["wcs"].world_to_pixel_values(ra, dec)
    image, variance, coverage = bilinear(frame["data"], frame["variance"], frame["valid"], x, y)
    wavelength, width = frame["spectral"].pixel_to_world(x, y)
    return image, variance, coverage, wavelength.to_value(u.um), width.to_value(u.um)


def star_centers(image):
    work = gaussian_filter(np.nan_to_num(image), .65)
    _, med, std = sigma_clipped_stats(work)
    peaks = (work == maximum_filter(work, size=5)) & (work > med+5*std)
    peaks[:5] = peaks[-5:] = False
    peaks[:, :5] = peaks[:, -5:] = False
    centers = []
    for y, x in zip(*np.where(peaks)):
        patch = np.maximum(np.nan_to_num(image[y-2:y+3, x-2:x+3])-med, 0)
        yy, xx = np.indices(patch.shape)
        total = patch.sum()
        if total > 0:
            centers.append([x-2+float((patch*xx).sum()/total), y-2+float((patch*yy).sum()/total)])
    return np.array(centers).reshape(-1, 2)


def registration(before, after, target_pixels):
    a, b = star_centers(before), star_centers(after)
    matches = []
    used = set()
    for p in a:
        if min(np.linalg.norm(p-t) for t in target_pixels) < 6 or not len(b):
            continue
        distances = np.linalg.norm(b-p, axis=1)
        j = int(np.argmin(distances))
        if distances[j] < 1.5 and j not in used:
            matches.append((p, b[j]))
            used.add(j)
    if len(matches) < 3:
        return np.zeros(2), {"matched_stars": len(matches), "applied": False,
                            "rms_before_px": None, "rms_after_px": None}
    offsets = np.array([q-p for p, q in matches])
    shift = np.median(offsets, axis=0)
    keep = np.linalg.norm(offsets-shift, axis=1) < .6
    offsets = offsets[keep]
    if len(offsets) < 3:
        return np.zeros(2), {"matched_stars": len(offsets), "applied": False,
                            "rms_before_px": None, "rms_after_px": None}
    shift = np.mean(offsets, axis=0)
    return shift, {"matched_stars": len(offsets), "applied": True,
                  "rms_before_px": float(np.sqrt(np.mean(np.sum(offsets**2, axis=1)))),
                  "rms_after_px": float(np.sqrt(np.mean(np.sum((offsets-shift)**2, axis=1))))}


def smooth_with_psf(image, variance, kernel):
    mask = np.isfinite(image) & np.isfinite(variance)
    support = convolve2d(mask.astype(float), kernel, mode="same", boundary="fill")
    value = convolve2d(np.nan_to_num(image), kernel, mode="same") / np.maximum(support, 1e-12)
    var = convolve2d(np.nan_to_num(variance), kernel**2, mode="same") / np.maximum(support, 1e-12)**2
    value[support < .85] = np.nan
    var[support < .85] = np.nan
    return value, var, support


def calibration_from_stars(a, b, valid, positions):
    """Aperture ratios avoid regression-dilution bias from noisy sky pixels."""
    yy, xx = np.indices(a.shape)
    ratios = []
    for x, y in star_centers(a):
        if min(np.linalg.norm(np.array([x,y])-p) for p in positions) < 7:
            continue
        r2 = (xx-x)**2+(yy-y)**2
        disk, ring = (r2 <= 3**2) & valid, (r2>4**2) & (r2<6**2) & valid
        if disk.sum() < 23 or ring.sum() < 20:
            continue
        fa = np.sum(a[disk]-np.median(a[ring]))
        fb = np.sum(b[disk]-np.median(b[ring]))
        if fa > .1 and fb > .1 and .5 < fb/fa < 1.5:
            ratios.append(float(fb/fa))
    gain = float(np.median(ratios)) if len(ratios)>=3 else 1.
    offset = float(np.nanmedian((b-gain*a)[valid]))
    return gain, offset, ratios


def residual_candidates(score, valid, wcs):
    masked = np.where(valid, np.abs(score), 0.)
    peaks = (masked == maximum_filter(masked, size=7)) & valid & (masked >= 3.5)
    safe = binary_erosion(valid, iterations=2)
    peaks &= safe
    rows = []
    for y, x in zip(*np.where(peaks)):
        ra, dec = wcs.pixel_to_world_values(float(x), float(y))
        rows.append({"x": int(x), "y": int(y), "ra_deg": float(ra), "dec_deg": float(dec),
                     "score": round(float(score[y,x]), 3), "kind": "positive" if score[y,x]>0 else "negative"})
    rows.sort(key=lambda row: -abs(row["score"]))
    return [{"id": f"R{i+1:02}", **row} for i, row in enumerate(rows[:12])]


def png_image(array, path, low, high, diverging=False):
    valid = np.isfinite(array)
    if diverging:
        t = np.clip(array/high, -1, 1)
        base = np.array([14, 26, 44], dtype=float)
        positive, negative = np.array([255, 192, 99]), np.array([107, 210, 244])
        rgb = base + np.abs(t)[...,None] * (np.where((t>=0)[...,None], positive, negative)-base)
    else:
        t = np.clip((array-low)/(high-low), 0, 1)
        t = np.arcsinh(t*8)/np.arcsinh(8)
        rgb = np.repeat((t*255)[...,None], 3, axis=2)
    rgb = np.clip(np.nan_to_num(rgb), 0, 255).astype(np.uint8)
    rgb[~valid] = [27, 40, 57]
    # FITS increases y toward north. Browser images increase y downwards.
    Image.fromarray(np.flipud(rgb)).save(path)


def json_array(array):
    clean = array.astype(float)
    return [[None if not np.isfinite(v) else round(float(v), 6) for v in row] for row in clean]


def make_scene(scene_id, label, before, after):
    wcs = grid_wcs()
    positions = [np.array(wcs.world_to_pixel_values(*frame["position"])) for frame in (before, after)]
    a0, av0, ac0, aw, ab = project(before, wcs)
    b0, _, _, _, _ = project(after, wcs)
    shift, alignment = registration(a0, b0, positions)
    b0, bv0, bc0, bw, bb = project(after, wcs, shift)
    a, av, ac = smooth_with_psf(a0, av0, after["psf"])
    b, bv, bc = smooth_with_psf(b0, bv0, before["psf"])
    valid = np.isfinite(a) & np.isfinite(b) & (ac>.9) & (bc>.9)
    yy, xx = np.indices(SHAPE)
    fitmask = valid.copy()
    for p in positions:
        fitmask &= (xx-p[0])**2+(yy-p[1])**2 > 6**2
    # This fit removes global calibration/background differences, never the target ROI.
    gain, offset, aperture_ratios = calibration_from_stars(a, b, fitmask, positions)
    delta = b-(gain*a+offset)
    nominal_noise = np.sqrt(bv+gain**2*av)
    ratio = np.divide(delta, nominal_noise, out=np.full_like(delta, np.nan), where=nominal_noise>0)
    _, center, scale = sigma_clipped_stats(ratio, mask=~fitmask, sigma=3)
    score = (ratio-center)/max(float(scale), 1.)
    mismatch = np.abs(aw-bw)/((ab+bb)/2)
    # This is an exploratory compatibility gate, not a spectral-response correction.
    spectral_ok = mismatch <= .5
    highlight_valid = valid & spectral_ok
    candidates = residual_candidates(np.nan_to_num(score), highlight_valid, wcs)
    scene_dir = OUT / scene_id
    scene_dir.mkdir(parents=True, exist_ok=True)
    values = np.concatenate((a[valid], b[valid]))
    _, med, std = sigma_clipped_stats(values)
    low, high = med-2*std, max(float(np.nanpercentile(values, 99.8)), med+10*std)
    png_image(a, scene_dir/"before.png", low, high)
    png_image(b, scene_dir/"after.png", low, high)
    png_image(np.where(highlight_valid, score, np.nan), scene_dir/"difference.png", -6, 6, True)
    Image.fromarray(np.flipud((highlight_valid*255).astype(np.uint8))).save(scene_dir/"valid.png")
    np.savez_compressed(scene_dir/"arrays.npz", before=a, after=b, variance_before=av, variance_after=bv, difference=delta, score=score,
                        valid=valid, spectral_ok=spectral_ok, wavelength_before=aw, wavelength_after=bw)
    primary = wcs.to_header()
    primary["OBJECT"] = "WISE 0855 region"
    primary["ANAVERS"] = "0.1.0"
    primary["ANASHA"] = sha256(Path(__file__).read_bytes()).hexdigest()
    primary["OBSIDA"] = before["record"]["obs_id"]
    primary["OBSIDB"] = after["record"]["obs_id"]
    primary["FLXGAIN"] = gain
    primary["BKGOFF"] = offset
    primary["HISTORY"] = "Exploratory PSF cross-convolution; no confirmed target motion."
    products = [fits.PrimaryHDU(header=primary)]
    for name, array in (("BEFORE", a), ("AFTER", b), ("VAR_BEFORE", av), ("VAR_AFTER", bv), ("DIFFERENCE", delta),
                        ("EMP_SCORE", score), ("VALID", highlight_valid.astype(np.uint8))):
        header = wcs.to_header()
        if name in ("BEFORE", "AFTER", "DIFFERENCE"):
            header["BUNIT"] = "MJy/sr"
        elif name.startswith("VAR_"):
            header["BUNIT"] = "(MJy/sr)^2"
        products.append(fits.ImageHDU(array, header=header, name=name))
    fits.HDUList(products).writeto(scene_dir/"comparison.fits", overwrite=True)
    target = []
    for name, frame, p, image in zip(("before", "after"), (before, after), positions, (a,b)):
        x, y = p
        disk = (xx-x)**2+(yy-y)**2 <= 2.5**2
        usable = disk & highlight_valid
        target.append({"epoch": name, "x": float(x), "y": float(y), "ra_deg": frame["position"][0],
                       "dec_deg": frame["position"][1], "valid_fraction": float(usable.sum()/disk.sum()),
                       "peak_empirical_score": float(np.nanmax(np.abs(score[usable]))) if usable.any() else None})
    def frame_info(frame, name):
        return {**frame["record"], "date": Time(frame["mjd"], format="mjd").isot[:10],
                "mjd": frame["mjd"], "wavelength_um": frame["wavelength"], "bandwidth_um": frame["bandwidth"],
                "pipeline_version": frame["pipeline_version"], "psf_zone": frame["psf_zone"],
                "target_fit": native_target_fit(frame),
                "image": f"data/{scene_id}/{name}.png", "native_shape": frame["native_shape"]}
    scene = {"id": scene_id, "label": label, "shape": list(SHAPE), "pixel_scale_arcsec": SCALE,
             "before": frame_info(before, "before"), "after": frame_info(after, "after"),
             "baseline_days": after["mjd"]-before["mjd"],
             "target_wavelength_delta_nm": abs(before["wavelength"]-after["wavelength"])*1000,
             "wavelength_mismatch_channels": abs(before["wavelength"]-after["wavelength"])/((before["bandwidth"]+after["bandwidth"])/2),
             "alignment": {**alignment, "shift_x_px": float(shift[0]), "shift_y_px": float(shift[1])},
             "photometric_gain": float(gain), "background_offset": float(offset),
             "calibration_star_ratios": aperture_ratios,
             "empirical_noise_scale": float(scale), "valid_fraction": float(highlight_valid.mean()),
             "candidates": candidates, "target_prior": target, "target_detection": "unconfirmed",
             "difference_image": f"data/{scene_id}/difference.png", "fits": f"data/{scene_id}/comparison.fits",
             "arrays": f"data/{scene_id}/arrays.npz", "array_json": f"data/{scene_id}/pixels.json",
             "display_stretch": {"low": float(low), "high": float(high), "function": "asinh; identical limits"},
             "wcs": {"center_ra_deg": CENTER[0], "center_dec_deg": CENTER[1], "orientation": "north up, east left"}}
    (scene_dir/"pixels.json").write_text(json.dumps({"before": json_array(a), "after": json_array(b),
        "score": json_array(np.where(highlight_valid, score, np.nan)), "valid": highlight_valid.astype(int).tolist()}), encoding="utf-8")
    return scene


def main():
    log.setLevel("WARNING")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((RAW/"target-centered/manifest.json").read_text(encoding="utf-8"))
    frames = {row["obs_id"]: read_frame(row) for row in manifest["records"] if row["status"] == "downloaded"}
    scenes = [make_scene(sid, label, frames[a], frames[b]) for sid, label, a, b in PAIRS]
    report = {"target": "WISE 0855−0714", "title": "WISE 0855 · Change Explorer", "data_real": True,
        "analysis_version": "0.1.0", "analysis_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "collection": "SPHEREx QR2 / IRSA", "downloaded_scan_count": 43, "selected_cutout_count": len(frames),
        "method": "WCS reprojection, reference-star translation, local measured-PSF cross-convolution, median static-star aperture gain and sky offset, exploratory empirical residuals",
        "bad_flag_bits": list(BAD_BITS), "model": "Classical baseline; no trained vision model yet",
        "target_prior_source": "https://arxiv.org/pdf/1404.6501",
        "target_prior_note": "Linear extrapolation from Luhman 2014 Tables 1/2. Parallax is omitted. Search guide, not a measured SPHEREx detection.",
        "limitations": ["Highlight is an exploratory residual, not confirmation of WISE 0855 or a calibrated sigma probability.",
            "WCS-WAVE uses visualization precision; science-grade matching needs spectral calibration response.",
            "Interpolated and PSF-convolved pixels have correlated noise; score is empirically normalized.",
            "A half-bandwidth local wavelength gate does not remove all source-colour differences.",
            "Only local PSFs and a translation correction are used; targets require independent astrometric verification."],
        "sources": ["https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/",
            "https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts/",
            "https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/",
            "https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html"], "scenes": scenes}
    (OUT/"manifest.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps([{ "id": s["id"], "days": s["baseline_days"], "delta_nm": s["target_wavelength_delta_nm"],
        "alignment":s["alignment"], "gain":s["photometric_gain"], "valid_fraction":s["valid_fraction"],
        "residuals":len(s["candidates"]), "prior":s["target_prior"]} for s in scenes], indent=2))


if __name__ == "__main__":
    main()
