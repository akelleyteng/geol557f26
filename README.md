# GEOL 557A Group Project: Climate Forcing Data Wrangling

**Team:** Brock Drengenberg, Hsu Kyi, Amanda Kelley-Teng

**Question:** How do external forcing (CO2 and volcanic aerosols) and internal variability (ENSO) shape global temperature, and are today's CO2 level and rate of change outside the natural range of the last 800,000 years?

The notebook loads the raw ice-core, instrumental, ENSO and volcanic records, cleans them, and puts them on shared units and time axes. It produces two clean tables, then runs descriptive statistics and plots on them.

## Repository layout

```
notebook/GEOL557_wrangling.ipynb   the full workflow: raw data → cleaning → transformations → clean tables → plots
data/raw/                          source files, as downloaded
data/clean/                        tables written by the notebook
GEOL557_wrangling.pdf              PDF export from Nov 10 (may lag behind the notebook)
```

## Getting the project

You need [Git installed and set up](https://docs.github.com/en/get-started/git-basics/set-up-git). To push changes, you also need collaborator access to this repo (ask Amanda).

### Option A: start fresh (simplest)

If you don't have a copy of the project yet, [clone the repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository):

```bash
git clone https://github.com/akelleyteng/geol557f26.git GEOL557_group_project
cd GEOL557_group_project
```

### Option B: connect a folder you already have

If you already have a copy of the project folder, for example from a shared drive, you can connect it to the repo without losing your local edits. Run these commands from inside the project folder:

```bash
git init -b main
git remote add origin https://github.com/akelleyteng/geol557f26.git
git fetch origin
git reset origin/main                            # point at the repo's history; your files are not touched
git branch --set-upstream-to=origin/main
git ls-files --deleted -z | xargs -0 git restore --   # bring in any repo files your folder is missing
git status
```

`git status` then shows how your folder differs from the repo:

- `M`: a file you changed locally
- `??`: a file that exists only in your folder

Review those changes, then commit the ones you want to share and push them, or discard the rest with `git restore <file>`.

### Day to day

```bash
git pull                                  # get teammates' changes
git add <files>
git commit -m "short description of the change"
git push
```

New to Git or GitHub? Start with [About Git](https://docs.github.com/en/get-started/using-git/about-git) and the [Start your journey](https://docs.github.com/en/get-started/start-your-journey) tutorials.

## Setup

Requires Python 3 and Jupyter. Tested with Python 3.14.7, pandas 2.3.3, numpy 2.5.3, matplotlib 3.11.2 and xlrd 2.0.2.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pandas numpy matplotlib xlrd jupyter
```

`xlrd` is needed to read the `.xls` ice-core workbooks. Google Colab already has it.

## Running

Open `notebook/GEOL557_wrangling.ipynb` and run all cells. Start Jupyter from the `notebook/` folder (or open the notebook there in VS Code) so the `../data` paths resolve.

Running the notebook overwrites these two files in `data/clean/`:

| Clean table | Contents |
|---|---|
| `deep_time_co2_temp.csv` | One row per ice-core CO2 sample (~801,000 yr BP to 1911 CE), with EPICA Dome C temperature interpolated onto each sample's age, plus glacial/interglacial and pre-industrial flags |
| `modern_climate_1850_2025.csv` | One row per year, 1850–2025: temperature anomaly (rebased to 1850–1900), spliced CO2 and its radiative forcing, DJF Niño 3.4, volcanic aerosol optical depth, and catalog eruptions |

## Data sources

| File in `data/raw/` | Source |
|---|---|
| `antarctica2015co2.xls` | NOAA paleo study 17975: Antarctic ice-core CO2 composite, 0–806 kyr |
| `edc3deuttemp2007.txt` | NOAA paleo study 6080: EPICA Dome C temperature reconstruction |
| `HadCRUT.5.2.0.0.analysis.summary_series.global.annual.csv` | Met Office HadCRUT5: global annual temperature anomaly, 1850 on |
| `law2006.csv` | Law Dome ice core: annual CO2, through 2004 |
| `co2_annmean_mlo.csv` | NOAA GML, Mauna Loa: annual mean CO2, 1959 on |
| `nino34.long.anom .csv` | NOAA PSL: Niño 3.4 long anomaly series, monthly, 1870 on (the space before `.csv` is part of the file name) |
| `tau.line_2012.12.txt` | NASA GISS: stratospheric aerosol optical depth at 550 nm, monthly, 1850 to Sep 2012 |
| `GEOL557_Volcano_Catalog.csv` | Smithsonian Global Volcanism Program: 17 selected eruptions, VEI 3–6, 1854–1991 |

The current notebook does not read these files: `data/raw/antarctica2015co2composite.txt`, `data/raw/co2-long-term-concentration.csv`, `data/raw/df2012isotope-temperature.xls`, `data/raw/global_temp_annual.csv`, `data/clean/deep_time_co2_1kyr.csv` and `data/clean/instrumental_co2_temp.csv`.

## Working together

- Run `git pull` before you start editing (see Day to day above).
- Notebooks are JSON, so two people editing the same notebook at once will produce merge conflicts that are hard to resolve. Agree who is editing before you start, or work in a separate notebook and merge the cells in afterwards.
- Before committing, restart the kernel and run all cells so the saved outputs match the code.
