# -*- coding: utf-8 -*-
"""
pshg_core
=========
Instrument-agnostic per-field-of-view pSHG computation, factored out of the v6
driver so it can be reused (e.g. per tile by a future 111 stitch driver) and
tested without any GUI or plotting.

analyse_fov() takes the loaded per-orientation frames plus an instrument profile
and returns the projector maps and the intermediate stacks the mask/plot stages
need. It does NO plotting and NO file I/O.
"""

import numpy as np

from instruments import angles_base, angles_for


def analyse_fov(imgs, profile, data_path):
    """Analyse one field of view.

    Parameters
    ----------
    imgs : list of per-orientation frames, channels-last, in 123D channel order
           (both loaders produce this). Length = number of orientations acquired.
    profile : instrument profile dict (see instruments.py).
    data_path : passed through to pshgProjector for signature compatibility.

    Returns
    -------
    dict with:
        pshg, ptpf, pshg_raw : (n_used, Y, X) float stacks (SHG clipped,
            TPF clipped, and SHG BEFORE clipping for the GoF noise model).
        allSum, allSumTPF    : (Y, X) summed intensity images.
        angles_proj          : angles fed to the projector (delta + flip).
        angles_gof           : delta-only, UN-flipped angles for the GoF mask
            (matches v6; the trust mask's pooled coherence depends on this).
        I2, Phi2, I4, Phi4, I4a, I4s : projector maps.
    """
    from pshgProjector import pshgProjector

    n_used = len(imgs) - profile["n_drop"]
    if n_used < 3:
        raise ValueError(f"Only {n_used} orientations after n_drop="
                         f"{profile['n_drop']}; need >= 3 to fit.")

    si, ti = profile["shg_index"], profile["tpf_index"]
    pshg, ptpf, pshg_raw = [], [], []
    for idx in range(n_used):
        im = imgs[idx]
        if min(im.shape) > 2:                      # channels-last -> first
            im = np.transpose(im, axes=(2, 0, 1))
        if im.ndim > 2:
            shg = im[si, :, :].astype(float)
            shg_raw = shg.copy()                   # keep negatives for GoF
            shg[shg < 0] = 0
            tpf = im[ti, :, :].astype(float)
            tpf[tpf < 0] = 0
        else:                                      # single-channel acquisition
            shg = im.astype(float)
            shg_raw = shg.copy()
            shg[shg < 0] = 0
            tpf = np.zeros_like(shg)
        pshg.append(shg)
        pshg_raw.append(shg_raw)
        ptpf.append(tpf)

    pshg = np.asarray(pshg)
    ptpf = np.asarray(ptpf)
    pshg_raw = np.asarray(pshg_raw)

    ang_proj = angles_for(profile, n_used)         # delta + flip
    ang_gof = angles_base(profile, n_used)         # delta only, un-flipped

    I2, Phi2, I4, Phi4, I4a, I4s = pshgProjector(data_path, pshg, ang_proj)

    return dict(pshg=pshg, ptpf=ptpf, pshg_raw=pshg_raw,
                allSum=pshg.sum(0), allSumTPF=ptpf.sum(0),
                angles_proj=ang_proj, angles_gof=ang_gof,
                I2=I2, Phi2=Phi2, I4=I4, Phi4=Phi4, I4a=I4a, I4s=I4s)
