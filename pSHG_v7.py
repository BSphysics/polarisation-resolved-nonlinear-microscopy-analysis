# -*- coding: utf-8 -*-
"""
pSHG_v7.py
==========
Unified polarisation-resolved SHG analysis driver.

Handles forward OR epi SHG on either microscope, chosen in the GUI dropdown
via an instrument profile (instruments.py):

    123D : ScanImage multiphoton, ONE .tif per polarisation orientation.
    111  : Olympus FV3000, ALL channels + orientations in ONE multipage .tif.

Everything instrument-specific — which channel is the SHG image (epi vs
forward), pixel-size calibration, polarisation zero/rotation, orientations to
drop — lives in the profile. The projection / masking / plotting core is the
same as v6, so any 123D profile should reproduce v6 output exactly.


@author: BES
"""
import os
scriptDir = os.getcwd()
import sys
sys.path.append(os.path.join(scriptDir, "new pSHG functions"))
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import copy
plt.close('all')

# ============================================================ GUI + instrument
from pSHG_GUI import pSHGGUI
from instruments import get_profile, load_for_instrument
from pshg_core import analyse_fov

defaultDir = scriptDir + '\\Test data'
initialDir = r'C:\Users\bs426\OneDrive - University of Exeter\!Work\Work.2024\Lab 2024\123D'
defaultThreshold = 1e2

(data_path, plotHistograms, pSHGFitViewer, plotPolarHistogram, arrowPlot,
 usepolygonalROI, useSlider, thresh, polygonal_roi_image,
 maskMode, sigmaPhi2Max, poolSigma, minFeature, closeRadius,
 instrument) = pSHGGUI(initialDir, defaultDir, defaultThreshold, 'transmission')

profile = get_profile(instrument)
print('\n Instrument profile: ' + instrument)

# ============================================================ load (dispatched)
filenames, imgs, meta = load_for_instrument(data_path, profile)

if os.path.isfile(data_path):
    base_dir = os.path.dirname(data_path)
    stem = os.path.splitext(os.path.basename(data_path))[0]
    results_folder = os.path.join(base_dir, stem, instrument + " pSHG results")
else:
    results_folder = os.path.join(data_path, instrument + " pSHG results")
os.makedirs(results_folder, exist_ok=True)
folderName = results_folder

res = analyse_fov(imgs, profile, data_path)

pshg      = res['pshg']
ptpf      = res['ptpf']
pshg_raw  = res['pshg_raw']
allSum    = res['allSum']
allSumTPF = res['allSumTPF']
I2, Phi2, I4, I4a, I4s = res['I2'], res['Phi2'], res['I4'], res['I4a'], res['I4s']
angles    = res['angles_gof']        

# ============================================================ mask
if maskMode == 'trust':
    from pSHG_gof import pshg_gof
    from pSHG_SNR_mask import snr_trust_mask

    # GoF gets the raw (un-clipped) SHG and the UN-flipped angles, as in v6.
    gof = pshg_gof(np.asarray(pshg_raw), res['angles_gof'])
    SNR_mask = snr_trust_mask(gof, sigmaPhi2Max, poolSigma,
                              min_feature=minFeature, close_radius=closeRadius)['mask']

    # --- bail out cleanly if too few pixels survive the SNR filter ---
    n_pass = int(np.count_nonzero(SNR_mask))
    frac_pass = n_pass / SNR_mask.size
    if frac_pass < 1e-3:                       # < 0.1 % of pixels (covers zero)
        print(f"\nSNR filter left {n_pass} pixels "
              f"({frac_pass:.3%} of {SNR_mask.size}) — too sparse for a meaningful mask.")
        print("Loosen the filter and re-run: raise sigmaPhi2Max, drop minFeature/"
              "closeRadius, or lower the intensity threshold.")
        sys.exit()
    # -----------------------------------------------------------------

    gray_red = copy.copy(plt.cm.gray)
    gray_red.set_bad('red')
    vmin, vmax = np.percentile(allSum, [1, 99.5])

    fig, ax = plt.subplots(1, 2, figsize=(13, 6), constrained_layout=True)
    ax[0].imshow(allSum, cmap='gray', vmin=vmin, vmax=vmax)
    ax[0].set_title('Summed SHG intensity')
    ax[1].imshow(np.ma.masked_where(~SNR_mask, allSum), cmap=gray_red, vmin=vmin, vmax=vmax)
    ax[1].set_title('SNR-masked (rejected pixels = red)')
    for a in ax:
        a.axis('off')
    plt.show()
    plt.pause(0.1)
    while True:
        if plt.waitforbuttonpress():
            break
    plt.close(fig=1)

else:
    SNR_mask = None
    from slider_thresh import sliderThresh
    plt.ion()
    slide = sliderThresh(allSum)
    plt.show()
    plt.pause(0.1)
    while True:
        if plt.waitforbuttonpress():
            break
    print('\n Threshold = ' + str(np.round(slide.val)))
    plt.close(fig=1)
    thresh = slide.val

# ============================================================ scale bar (mpp)
# mpp now comes from the instrument profile (123D: zoom calibration; 111: the
# um/pixel stated in the FV3000 metadata), NOT a hard-coded formula.
scaleBarinMicrons = float(50)
mpp = profile['mpp'](meta)
scaleBarLength = scaleBarinMicrons / mpp
scaleBarWidth = 15
print('\n Pixel size = %.4f um/px  (scale bar %d um = %.1f px)'
      % (mpp, scaleBarinMicrons, scaleBarLength))

# ============================================================ multipanel + mask
threshHigh = 1e9
from pSHGmultiPanel import pSHGmultiPanel
mask = pSHGmultiPanel(allSum, Phi2, I2, I4, I4a, I4s, thresh, threshHigh,
                      folderName, SNR_mask, maskMode)

# ============================================================ summed SHG image
scaleBar = patches.Rectangle((400, 475), scaleBarLength, scaleBarWidth,
                             linewidth=1, edgecolor='m', facecolor='w')
fig, ax = plt.subplots(figsize=(12, 10))
im = (allSum ** mask) / np.max(allSum)
plt.imshow(np.power(im, .7), cmap='gray')
plt.axis('off')
ax.add_patch(scaleBar)
plt.title(os.path.basename(data_path) + ',  scale bar = ' + str(scaleBarinMicrons)
          + r' $\mu$m', fontsize=6, loc="right")
plt.savefig(folderName + '\\' + 'all sum SHG.png', dpi=400, bbox_inches='tight', pad_inches=0)
plt.close('all')

# ============================================================ merge image
allSum = np.sum(pshg, 0)
allSumTPF = np.sum(ptpf, 0)

color_image = np.zeros((allSum.shape[0], allSum.shape[1], 3), dtype=float)
color_image[:, :, 1] = allSum / (np.mean(allSum) * 2.5)          # Green: SHG
color_image[:, :, 0] = allSumTPF / (np.mean(allSumTPF) * 4)      # Red: TPF
color_image = np.clip(color_image, 0, 1)
fig, ax1 = plt.subplots()
plt.imshow(color_image[:, :, :])
plt.axis('off')
scaleBar1 = patches.Rectangle((400, 475), scaleBarLength, scaleBarWidth,
                              linewidth=1, edgecolor='m', facecolor='w')
ax1.add_patch(scaleBar1)
plt.title(os.path.basename(data_path) + ',  scale bar = ' + str(scaleBarinMicrons)
          + r' $\mu$m', fontsize=6, loc="right")
plt.savefig(folderName + '\\' + 'merge_Image.png', dpi=400, bbox_inches='tight', pad_inches=0)
plt.close('all')

# ============================================================ arrow plot
if arrowPlot == True:
    from pSHG_arrows import pSHGArrows
    arrowColourMax = 0.5
    pSHGArrows(I2, Phi2, allSum, mask, folderName, arrowColourMax)

# ============================================================ single-pixel fits
if pSHGFitViewer == True:
    from pSHGfitviewer import pSHGFitViewer
    points = pSHGFitViewer(pshg, I2, Phi2, mask, angles, folderName)

# ============================================================ histograms
from pSHG_histograms_NEW import pSHGhistogramsNEW
if plotHistograms == True:
    [bins, binCounts, data] = pSHGhistogramsNEW(Phi2, mask, 'Phi2', folderName)
    [bins, binCounts, data] = pSHGhistogramsNEW(I2, mask, 'I2', folderName)
    [bins, binCounts, data] = pSHGhistogramsNEW(I4a, mask, 'I4a', folderName)
    [bins, binCounts, data] = pSHGhistogramsNEW(I4s, mask, 'I4s', folderName)

# ============================================================ polar histogram
if plotPolarHistogram == True:
    from pSHGpolar import pSHGpolar
    pSHGpolar(binCounts, folderName)

# ============================================================ polygonal ROI
plt.close('all')
from pSHG_histograms_NEW import pSHGhistogramsNEW
if usepolygonalROI:
    from polygonal_roi import polygonalROI

    if polygonal_roi_image == 'Phi2':
        roi_image = Phi2
    elif polygonal_roi_image == 'I2':
        roi_image = I2
    elif polygonal_roi_image == 'All SHG':
        roi_image = allSum

    [ROI, polygonalSavePath] = polygonalROI(roi_image, Phi2, I2, mask, folderName,
                                            plot_mode=polygonal_roi_image)
    [bins, binCounts, roi_data] = pSHGhistogramsNEW(Phi2 * ROI, mask, 'Phi2', polygonalSavePath)
    [bins, binCounts, roi_data] = pSHGhistogramsNEW(I2 * ROI, mask, 'I2', polygonalSavePath)
    [bins, binCounts, roi_data] = pSHGhistogramsNEW(I4a * ROI, mask, 'I4a', polygonalSavePath)
    [bins, binCounts, roi_data] = pSHGhistogramsNEW(I4s * ROI, mask, 'I4s', polygonalSavePath)

plt.close('all')
path = os.path.realpath(folderName)
os.startfile(path)

# ============================================================ save masked maps
for name, arr in [('I2_masked', I2 * mask), ('Phi2_masked', Phi2 * mask),
                  ('I4a_masked', I4a * mask), ('I4s_masked', I4s * mask)]:
    np.save(os.path.join(folderName, name), arr)

# ============================================================ density plot
from densityPlot import density_plot
fullFileName = os.path.join(folderName, 'I4s_vs_I4a.png')
density_plot(I4a, I4s, I2=I2, draw_arc=True, out_path=fullFileName)
plt.close('all')
