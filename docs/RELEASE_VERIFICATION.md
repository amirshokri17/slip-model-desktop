# v0.7.0 release verification

This record is specific to the **published GitHub release asset**, not a similarly named local Windows executable.

- Release: https://github.com/amirshokri17/slip-model-desktop/releases/tag/v0.7.0
- Filename: `SLIP_Model_Setup_v0_7.exe`
- Asset size: 36,684,187 bytes
- SHA-256 (obtained from the GitHub Releases asset `digest` field):
  `f5be2b71b619ae8fe397e58b4dcdd103eeee0f496f2806747e3f680eefe41e09`
- Published release tag: `v0.7.0`

## Verify the downloaded installer

In the Windows folder containing the **downloaded file from GitHub**, open Command Prompt and run:

```bat
certutil -hashfile "SLIP_Model_Setup_v0_7.exe" SHA256
```

Compare the 64-digit hexadecimal result to [SHA256SUMS.txt](../SHA256SUMS.txt) or the digest shown on the GitHub release asset. An incorrect value means the binary does not match the published artifact; do not install it.

## Verify the installed MIT license

The tagged v0.7.0 source contains `LICENSE`, and the tagged Inno Setup installer configuration includes:

```ini
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
```

This **verifies the build instructions**, not the contents of the already uploaded `.exe`. To establish whether that uploaded installer actually contains the license, run the **downloaded** installer on Windows and inspect its installation directory. It should contain `LICENSE` with `MIT License` and `Copyright (c) 2026 Amir Shokri`.

The public GitHub connector could inspect the release metadata and tagged source but could not unpack or execute the hosted Windows installer; installed-file verification is therefore **not independently confirmed**.

## Scientific scope

A matching download hash verifies integrity relative to GitHub's uploaded asset. It does not certify the software's scientific validity, absence of malware, or code-signing authenticity. The original SLIP mathematical formulation remains attributed to Montrasio and Valentino (2008). Third-party Qt/PySide6 redistribution terms remain separate from the project's MIT license.
