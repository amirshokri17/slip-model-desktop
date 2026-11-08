SLIP Model Desktop v0.7 — Windows 10/11 (64-bit)
================================================

This is a research/teaching implementation of the original SLIP shallow
landslide stability model. The sprinkler-geometry extension is NOT included.

INSTALLING
1. Download SLIP_Model_Setup_v0_7.exe from a trusted colleague.
2. Right-click -> Properties to inspect the file and publisher details.
3. Run the setup wizard, choose installation location and optional shortcut.
4. Open "SLIP Model Desktop" from the Start menu.
5. Uninstall via Windows Settings -> Installed apps.

No Python, PySide6 or other Python packages are required on the install PC.
No command prompt is needed to use the installed application.

The setup is not digitally signed. Windows SmartScreen/Defender may warn about
an unknown publisher. Such warnings are expected for some newly shared unsigned
applications, but are not proof of safety. Only install after verifying the file
came from a trusted project member; do not disable system security tools.

FEATURES
- Original Montrasio-Valentino (2008) SLIP stability formulation.
- Rectangular/trapezoidal soil profile; representative thickness H.
- Direct rainfall, original sprinkler-pressure calculation and CSV rainfall.
- FS chart, numerical output, sensitivity analysis, CSV/PNG export.

IMPORTANT MODEL LIMITATIONS
This is a research model, not a certified safety engineering tool.
Its predictions depend on parameter quality, model assumptions and experimental
calibration. A warning that m exceeds its physical limit means the model is
outside its valid hydrologic range for those conditions.

CSV FORMAT
Imported rainfall requires headers: time_s,depth_mm
Each row is an incremental rainfall depth at the stated time in seconds.
An example file is installed in the Examples folder.

CREDITS AND THIRD-PARTY LICENSES
See THIRD_PARTY_NOTICES.txt in the installation directory.
