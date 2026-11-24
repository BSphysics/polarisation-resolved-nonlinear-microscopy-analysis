# pSHG analysis

Polarisation-resolved SHG (pSHG) analysis for forward or epi SHG data from:

- **123D**: ScanImage multiphoton (one `.tif` per polarisation orientation)
- **111**: Olympus FV3000 (all channels and orientations in one multipage `.tif`)

The main script is `pSHG_v7.py`. Helper functions are in the `new pSHG functions/` folder.

> **Platform:** currently Windows only. The script uses `os.startfile` and Windows-style paths.

---

## 1. Install Python

Install [Anaconda](https://www.anaconda.com/download) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html) if you don't already have it.

## 2. Get the code

Either clone the repository:

```
git clone <repo-url>
cd <repo-folder>
```

or download the ZIP from GitHub (**Code → Download ZIP**) and unzip it.
Keep the folder structure as it is: `pSHG_v7.py` must sit next to the `new pSHG functions/` folder.

## 3. Create an environment and install the requirements

Open the **Anaconda Prompt** (Start menu), `cd` into the repository folder, then run:

```
conda create -n pshg python=3.11 pip
conda activate pshg
pip install -r requirements.txt
```

This installs everything listed in `requirements.txt`: numpy, scipy, matplotlib, scikit-image, tifffile, Pillow, natsort, XlsxWriter and PyQt5.

> **Use a new environment; don't install into `base`.** Anaconda's base environment already has its own Qt libraries. Installing `PyQt5` over them with pip can break Spyder and other tools.

To check it worked:

```
python -c "import numpy, scipy, matplotlib, skimage, tifffile, PIL, natsort, xlsxwriter, PyQt5; print('OK')"
```

## 4. Run the analysis

### From the Anaconda Prompt

```
conda activate pshg
cd <repo-folder>
python pSHG_v7.py
```

### From Spyder

Spyder needs to use the `pshg` environment. The simplest way is to install Spyder into it:

```
conda activate pshg
conda install spyder
spyder
```

Open `pSHG_v7.py` and press **F5**.

> **The working directory must be the repository folder.** The script finds its helper functions relative to the current working directory. If you get `ModuleNotFoundError` for modules such as `pSHG_GUI` or `pshg_core`, the cause is almost always the working directory, not a missing package. In Spyder, check the path shown at the top right, or run `cd <repo-folder>` in the console.

A GUI opens. Choose your data file or folder, the instrument profile (123D or 111), and the analysis options. Results go into a `<instrument> pSHG results` folder next to your data.

---

## For developers: updating `requirements.txt`

`find_requirements.py` follows the imports in `pSHG_v7.py` and every local module it uses, then lists the third-party packages that are needed. It also picks up PyQt5, which the matplotlib Qt backend needs even though no file imports it by name. After adding a new dependency, run this from the repository folder:

```
python find_requirements.py pSHG_v7.py --write
```

This overwrites `requirements.txt`. Requires Python 3.10+.

To record the exact versions known to work:

```
pip freeze > requirements-locked.txt
```
