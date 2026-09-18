# -*- coding: utf-8 -*-
"""
lab111_metadata
===============
Parse the Olympus FV3000 text sidecar that the 111 microscope writes next to
its single multi-page .tif, returning the values the pSHG pipeline needs.

111 dumps many datasets into one folder, so the sidecar is matched to a
SELECTED .tif by exact basename. When a .tif is given, only that file's
same-name .txt is accepted — a missing sidecar is an error, never an excuse to
grab a neighbouring dataset's .txt. The lenient folder search is kept only for
the legacy one-dataset-per-folder case.

123D (ScanImage) gets pixel size from imageMetaData() -> scanZoomFactor -> the
micronsPerPixel() calibration. 111 states the pixel size directly in the
metadata ("0.259 [um/pixel]"), so we read it straight.
"""

import os
import re

# Files that are never the FV3000 sidecar, even if they sit in the folder.
_IGNORE_TXT = {"image meta data.txt"}


def _find_txt(data_path):
    """Return the FV3000 metadata .txt for data_path.

    - a .tif path  -> its exact same-name sidecar, or FileNotFoundError.
                      (No guessing among other datasets' .txt files.)
    - a folder     -> the lone non-dump .txt, else the one whose basename
                      matches a .tif in the folder (legacy single-dataset case).
    """
    if os.path.isfile(data_path):
        base, ext = os.path.splitext(data_path)
        if ext.lower() in (".tif", ".tiff"):
            cand = base + ".txt"
            if os.path.isfile(cand):
                return cand
            raise FileNotFoundError(
                f"No metadata sidecar '{os.path.basename(cand)}' beside the "
                f"selected TIFF '{os.path.basename(data_path)}'. 111 expects the "
                f".txt to share the .tif's name.")
        data_path = os.path.dirname(data_path)

    all_txt = [f for f in os.listdir(data_path) if f.lower().endswith(".txt")]
    txts = [f for f in all_txt if f.lower() not in _IGNORE_TXT]

    if len(txts) == 1:
        return os.path.join(data_path, txts[0])

    if len(txts) > 1:
        tifs = [f for f in os.listdir(data_path)
                if f.lower().endswith((".tif", ".tiff"))]
        lower = {f.lower(): f for f in txts}
        for t in tifs:
            key = os.path.splitext(t)[0].lower() + ".txt"
            if key in lower:
                return os.path.join(data_path, lower[key])
        raise ValueError(
            f"Multiple .txt files in {data_path}: {txts}; none matches a .tif "
            f"basename. Select the specific .tif file instead.")

    raise FileNotFoundError(f"No FV3000 metadata .txt found near {data_path}.")


def lab111_metadata(data_path):
    """Parse 111 (FV3000) metadata.

    Returns a dict with at least:
        um_per_px : float   pixel size in microns (from the X Dimension line)
        zoom      : float   optical zoom factor (e.g. 1.6)
        n_channels: int     channel count
        n_orient  : int     number of polarisation orientations (T dimension)
    Missing fields are omitted rather than guessed.
    """
    txt = _find_txt(data_path)
    with open(txt, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    meta = {}

    m = re.search(r'([0-9]*\.?[0-9]+)\s*\[um/pixel\]', text)
    if m:
        meta["um_per_px"] = float(m.group(1))

    m = re.search(r'"Zoom"\s*"\s*x?([0-9]*\.?[0-9]+)', text)
    if m:
        meta["zoom"] = float(m.group(1))

    m = re.search(r'"Channel Dimension"\s*"\s*([0-9]+)', text)
    if m:
        meta["n_channels"] = int(m.group(1))

    m = re.search(r'"T Dimension"\s*"\s*([0-9]+)', text)
    if m:
        meta["n_orient"] = int(m.group(1))

    if "um_per_px" not in meta:
        raise ValueError(f"Could not find '[um/pixel]' in {txt}; "
                         f"check the metadata format.")
    return meta
