# -*- coding: utf-8 -*-
"""
single_tiff_loader
==================
Loader for lab 111 (the single-file microscope) polarisation-resolved data, where EVERY channel and
EVERY polarisation orientation is written to ONE multi-page .tif file, as
opposed to microscope 1 (one .tif per orientation, handled by tiff_loader).

The verified layout of the example file (Olympus FV3000 export) is:

    56 pages = 4 channels * 14 orientations, stored CHANNEL-MAJOR (axes 'CTYX')
    => skimage/tifffile read it as shape (C, T, Y, X) = (4, 14, 512, 512)

This function slices that into the SAME kind of array the rest of the pSHG GUI
already consumes: a list `imgs`, one entry per polarisation orientation, each
entry channels-LAST (Y, X, nCh) with channels ordered to match microscope 1
so the existing main loop works unchanged:

    microscope 1 per-orientation channel order (after its transpose):
        index 0 = epi SHG,  index 1 = TPEF,  index 2 = forward SHG
    the main loop reads  shg = im[2]  (forward SHG)  and  tpf = im[1]  (TPEF)

So we emit each orientation as  [epi SHG, TPEF, forward SHG, SRS]  (channels
last). SRS is carried along at index 3 for future use; the current pipeline
ignores it.

@author: (loader written to spec for Ben Sherlock's pSHG GUI)
"""

import os
import numpy as np
import tifffile


# ---------------------------------------------------------------------------
# EDIT THIS to match microscope 2's acquisition order.
# Keys are physical detectors; values are the channel INDEX in the .tif
# (i.e. C in the (C, T, Y, X) array).  From the example file, C1 is a large
# flat channel (SRS) and C0 modulates strongly with polarisation (forward SHG).
# CONFIRM the epi-SHG vs forward-SHG assignment against a known sample before
# trusting results, since both SHG channels can look similar in a pixel sum.
# ---------------------------------------------------------------------------
M2_CHANNEL_INDEX = {
    'forward_shg': 0,   # C0  -> becomes downstream `shg`   (im[2])
    'srs':         1,   # C1
    'tpef':        2,   # C2  -> becomes downstream `tpf`   (im[1])
    'epi_shg':     3,   # C3
}

# Order in which channels are written into each per-orientation frame.
# Positions 1 and 2 MUST be TPEF and forward SHG respectively to match the
# main loop's im[1]/im[2] indexing. Do not reorder those two without also
# editing the main loop.
M2_EMIT_ORDER = ['epi_shg', 'tpef', 'forward_shg', 'srs']


def _find_single_tiff(data_path):
    """Return the path to the single multi-page .tif in data_path.

    Accepts either a direct path to a .tif file or a folder containing exactly
    one .tif. Raises a clear error otherwise."""
    if os.path.isfile(data_path) and data_path.lower().endswith(('.tif', '.tiff')):
        return data_path
    tifs = [f for f in os.listdir(data_path)
            if f.lower().endswith(('.tif', '.tiff'))]
    if len(tifs) == 0:
        raise FileNotFoundError(f"No .tif found in {data_path}")
    if len(tifs) > 1:
        raise ValueError(
            f"Expected ONE multi-page .tif for microscope 2, found {len(tifs)}: "
            f"{tifs}. Point data_path at the specific file, or use the "
            f"microscope-1 loader for per-orientation files.")
    return os.path.join(data_path, tifs[0])


def _to_CTYX(path, n_channels, channel_major):
    """Read the file and return a (C, T, Y, X) uint array, using the TIFF's own
    axis labels when available and falling back to a manual reshape."""
    with tifffile.TiffFile(path) as tf:
        series = tf.series[0]
        arr = series.asarray()
        axes = series.axes  # e.g. 'CTYX', 'TCYX', 'IYX', 'QYX'

    # Case 1: the writer labelled both channel and time/orientation axes.
    if 'C' in axes and 'T' in axes and arr.ndim == len(axes):
        order = [axes.index('C'), axes.index('T'),
                 axes.index('Y'), axes.index('X')]
        return np.transpose(arr, order)

    # Case 2: already 4-D but unlabelled -> assume (C, T, Y, X) unless
    # channel_major is False, in which case treat the first two as (T, C).
    if arr.ndim == 4:
        return arr if channel_major else np.swapaxes(arr, 0, 1)

    # Case 3: flat stack (n, Y, X). Split by n_channels.
    if arr.ndim == 3:
        n = arr.shape[0]
        if n % n_channels != 0:
            raise ValueError(
                f"Flat stack has {n} pages, not divisible by n_channels="
                f"{n_channels}. Set n_channels correctly.")
        n_orient = n // n_channels
        if channel_major:
            # pages: C0T0 C0T1 ... C0T{k-1} C1T0 ...  -> (C, T, Y, X)
            return arr.reshape(n_channels, n_orient, *arr.shape[1:])
        else:
            # pages: T0C0 T0C1 ... T0C{c-1} T1C0 ... -> (T, C, Y, X) -> swap
            return np.swapaxes(
                arr.reshape(n_orient, n_channels, *arr.shape[1:]), 0, 1)

    raise ValueError(f"Unexpected TIFF shape {arr.shape} (axes '{axes}').")


def single_tiff_loader(data_path,
                       n_channels=4,
                       channel_major=True,
                       channel_index=None,
                       emit_order=None,
                       return_stack=False):
    """Load microscope-2 single-file pSHG data.

    Parameters
    ----------
    data_path : str
        Path to the multi-page .tif, or to a folder containing exactly one.
    n_channels : int
        Number of detector channels multiplexed into the file (4 for micro 2).
        Only used as a fallback when the TIFF doesn't label its axes.
    channel_major : bool
        True  -> pages ordered all-orientations-of-C0, then C1, ... (verified
                 for the example file, axes 'CTYX').
        False -> pages ordered all-channels-of-orientation-0, then orient 1, ...
    channel_index : dict or None
        Physical-detector -> channel-index map. Defaults to M2_CHANNEL_INDEX.
    emit_order : list or None
        Order channels are packed into each returned frame. Defaults to
        M2_EMIT_ORDER; positions 1 and 2 must be tpef and forward_shg.
    return_stack : bool
        If True, also return the raw (C, T, Y, X) array as a third value
        (handy for debugging / building a microscope-2 metadata parser).

    Returns
    -------
    filenames : list[str]
        Synthetic per-orientation names ('orientation_00', ...) so downstream
        code that expects one name per image still works.
    imgs : list[np.ndarray]
        One (Y, X, nEmit) int64 array per orientation, channels last, ordered
        to match microscope 1 (index1=TPEF, index2=forward SHG).
    stack : np.ndarray, optional
        (C, T, Y, X) raw array, only if return_stack=True.
    """
    channel_index = channel_index or M2_CHANNEL_INDEX
    emit_order = emit_order or M2_EMIT_ORDER

    path = _find_single_tiff(data_path)
    stack = _to_CTYX(path, n_channels, channel_major)   # (C, T, Y, X)
    C, T, Y, X = stack.shape

    # sanity: every emitted channel must exist in the file
    for name in emit_order:
        ci = channel_index[name]
        if ci >= C:
            raise IndexError(
                f"Channel '{name}' wants index {ci} but file only has {C} "
                f"channels. Fix M2_CHANNEL_INDEX / n_channels.")

    order_idx = [channel_index[name] for name in emit_order]  # e.g. [3,2,0,1]

    imgs = []
    filenames = []
    for t in range(T):
        # (nEmit, Y, X) -> channels last (Y, X, nEmit) to match microscope 1's
        # channels-last frames (its loop transposes (2,0,1) back to first).
        frame = stack[order_idx, t, :, :]           # (nEmit, Y, X)
        frame = np.moveaxis(frame, 0, -1)           # (Y, X, nEmit)
        imgs.append(frame.astype('int64'))          # match tiff_loader dtype
        filenames.append(f"orientation_{t:02d}")

    if return_stack:
        return filenames, imgs, stack
    return filenames, imgs
