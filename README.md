# SLIP Model Desktop v0.7

Independent Python desktop implementation of the SLIP model for rainfall-induced shallow-landslide stability analysis. This release excludes the experimental sprinkler-geometry extension. The existing conversion from sprinkler flow to uniform rainfall intensity remains part of the original application.

## Scientific attribution

The underlying model is credited to Montrasio, L. and Valentino, R. (2008), A model for triggering mechanisms of shallow landslides, Natural Hazards and Earth System Sciences, 8, 1149–1159. https://doi.org/10.5194/nhess-8-1149-2008

This repository provides an independent software implementation and does not claim authorship of the underlying mathematical model or endorsement by the paper's authors or a university.

## Run from source

Use Python 3.12 on Windows. Create a virtual environment, install requirements.txt, then run main.py:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m unittest -v
```

The interface supports rectangular/trapezoidal geometry, rainfall inputs, FS plots, sensitivity analysis, and CSV/PNG export. Rainfall CSV uses time_s,depth_mm; depths are increments at their timestamps.

## Reproducible reference

The regression suite specifies the full baseline inputs. At 57.5 mm/h with 2-minute rainfall increments, it checks FS(0) = 5.925859189117114 and FS(40 min) = 1.6417795775649306. All 10 existing tests passed during staging on 8 November 2026, including offscreen GUI, sensitivity and export tests. This does not establish scientific validation.

## Scientific limitations and implementation choices

The model uses a homogeneous representative layer and infinite-slope limit equilibrium. Rectangular/trapezoidal geometry supplies volume and rainfall area; it does not produce a spatially resolved stress or infiltration calculation. H is normal to the platform. The optional KT = K/L relation is an implementation approximation, not a universal calibration law. Empirical apparent cohesion and drainage parameters require justified selection. The program does not resolve full infiltration, preferential flow, spatial rainfall variation, runoff, erosion or progressive local collapse.

Rainfall increments are applied at their event times. The engine caps m at 1 and returns m_raw and a saturation-limit flag. A later FS plateau in this capped regime is not evidence of a validated physical response. The displayed FS = 1 crossing is linear interpolation between samples, not an exact physical failure time. Numerical regression tests and successful installation on another device do not establish predictive accuracy.

For educational and research use. Site-specific engineering decisions require independent assessment and appropriately validated inputs.

## Experimental context

No raw laboratory sensor recordings are included. The numerical example and separate laboratory observations discussed during development do not constitute a matched, calibrated validation. Experimental timing comparisons are omitted because a matched calibration has not been established.

## Windows distribution

The existing Windows installer is intended as a separate v0.7.0 release asset, with SHA256SUMS.txt. The user reports successful operation on a second device. The installer was preserved unchanged from the tested local build; it was not rebuilt or independently reinstalled during publication preparation. Build instructions and third-party notices are included.

## License status

No license for the application source has been selected. The GNU license texts here accompany third-party notices; they do not establish a license for the original application code. Public availability of the source does not grant an open-source license. Third-party components retain their applicable licenses.
