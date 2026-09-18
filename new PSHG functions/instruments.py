# -*- coding: utf-8 -*-
"""
instruments
===========
One profile per acquisition configuration. Everything that differs between epi
SHG, forward SHG, and the two microscopes lives HERE as data; the projection /
mask / plotting core stays single-sourced and instrument-agnostic.

Microscopes are named by their lab:
    123D : ScanImage multiphoton, ONE .tif per polarisation orientation.
    111  : Olympus FV3000, ALL channels + orientations in ONE multipage .tif.

A profile is a dict:
    loader     : 'per_orientation' (123D) or 'single_tiff' (111).
    shg_index  : channel index used as the SHG image, in the per-orientation
                 channels-first frame AFTER the loader's transpose. Both loaders
                 present channels in 123D order [epi, TPEF, forward, (SRS)]:
                     epi SHG = 0,  forward SHG = 2.
    tpf_index  : channel index used as the two-photon-fluorescence image (=1).
    delta      : polarisation zero offset (deg) in the angle vector.
    flip       : whether angles are reversed (np.flip) before projection —
                 encodes the half-wave-plate rotation sense.
    n_drop     : orientations discarded from the end before fitting.
    mpp        : callable(meta_dict) -> microns per pixel.

delta / flip are physical to each rig's polarisation optics. They are known for
123D (epi and forward share its optics). They are NOT known for 111 and are left
as None on purpose: the angle builders below refuse to run until they are
calibrated, rather than silently borrowing 123D's values.
"""

import numpy as np


def micronsPerPixel(zoom):
    """123D calibration (ScanImage scanZoomFactor -> um/pixel)."""
    return 1.9634 * zoom ** (-0.987)


def _mpp_123D(meta):
    return micronsPerPixel(meta["zoom"])


def _mpp_111(meta):
    return meta["um_per_px"]          # stated directly in the FV3000 metadata


INSTRUMENTS = {
    "123D - forward SHG": dict(
        loader="per_orientation", shg_index=2, tpf_index=1,
        delta=-30, flip=True, n_drop=2, mpp=_mpp_123D),

    "123D - epi SHG": dict(
        loader="per_orientation", shg_index=0, tpf_index=1,
        delta=-30, flip=True, n_drop=2, mpp=_mpp_123D),

    "111 - forward SHG": dict(
        loader="single_tiff", shg_index=2, tpf_index=1,
        delta=0, flip = True, n_drop=2, mpp=_mpp_111),   # delta/flip: CALIBRATE

    "111 - epi SHG": dict(
        loader="single_tiff", shg_index=0, tpf_index=1,
        delta=0, flip=True, n_drop=2, mpp=_mpp_111),    # delta/flip: CALIBRATE
}

# Order shown in the GUI dropdown; first entry is the default.
INSTRUMENT_NAMES = list(INSTRUMENTS.keys())
DEFAULT_INSTRUMENT = INSTRUMENT_NAMES[0]


def get_profile(name):
    if name not in INSTRUMENTS:
        raise KeyError(f"Unknown instrument '{name}'. Known: {INSTRUMENT_NAMES}")
    return INSTRUMENTS[name]


def load_for_instrument(data_path, profile):
    """Dispatch to the right loader and return (filenames, imgs, meta).

    imgs is identical in structure for both loaders (list of per-orientation,
    channels-last frames in 123D channel order), so everything downstream is
    instrument-agnostic. meta carries what mpp() needs.
    """
    if profile["loader"] == "single_tiff":
        from single_tiff_loader import single_tiff_loader, _find_single_tiff
        from lab111_metadata import lab111_metadata
        tif_path = _find_single_tiff(data_path)        # resolve the one .tif first
        filenames, imgs = single_tiff_loader(tif_path)
        meta = lab111_metadata(tif_path)               # match sidecar by .tif name
    elif profile["loader"] == "per_orientation":
        from tiff_loader import tiff_loader
        filenames, imgs = tiff_loader(data_path)
        # Guard BEFORE importing/running imageMetaData (which writes a .txt):
        # a 123D profile needs one .tif per orientation (~14). Finding ~1 means
        # this is really a 111 single-file dataset selected under a 123D profile.
        if len(imgs) < 3:
            raise ValueError(
                f"A 123D (per-orientation) profile found only {len(imgs)} TIFF "
                f"file(s) in {data_path}. 123D data is one TIFF per polarisation "
                f"orientation (~14 files); a single multi-page TIFF is a 111 "
                f"dataset — select a '111 - ...' profile for it.")
        from imageMetaData import imageMetaData
        zoomFactor, frames, zStackStep, allMetaData = imageMetaData(
            data_path, filenames)
        meta = {"zoom": zoomFactor, "frames": frames,
                "zStackStep": zStackStep, "allMetaData": allMetaData}
    else:
        raise ValueError(f"Unknown loader '{profile['loader']}'")
    return filenames, imgs, meta


def _require_cal(profile):
    if profile["delta"] is None or profile["flip"] is None:
        raise ValueError(
            "This instrument profile has no polarisation calibration set "
            "(delta / flip are None). Determine the half-wave-plate zero and "
            "rotation sense for this microscope, set them in instruments.py, "
            "then re-run. Refusing to borrow another instrument's values.")


def angles_base(profile, n):
    """Delta-applied, UN-flipped angle vector (radians). This is what v6 fed to
    pshg_gof, and what the trust mask must see so its pooled orientation
    coherence matches v6."""
    _require_cal(profile)
    return (np.arange(n) * 15 - profile["delta"]) * np.pi / 180


def angles_for(profile, n):
    """Projection angle vector: angles_base, reversed if the profile's flip is
    set. This is what v6 fed to pshgProjector (np.flip(angles))."""
    base = angles_base(profile, n)
    return np.flip(base) if profile["flip"] else base
