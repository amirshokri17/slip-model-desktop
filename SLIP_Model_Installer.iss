; SLIP Model Desktop v0.7: installable Windows distribution.
; Built from the original homogeneous SLIP app supplied by the user.
; No sprinkler-geometry extension is included.
; Compile AFTER running PyInstaller on Windows using BUILD_WINDOWS_INSTALLER.bat.

#define AppName "SLIP Model Desktop"
#define AppVersion "0.7.0"
#define AppExe "SLIP_Model.exe"

[Setup]
AppId={{B00EFB1D-8892-4B78-9F69-D9FAFFFD8C48}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
AppPublisher=SLIP Model Research Project
DefaultDirName={localappdata}\Programs\SLIP Model Desktop
DefaultGroupName=SLIP Model Desktop
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=installer
OutputBaseFilename=SLIP_Model_Setup_v0_7
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; PyInstaller one-dir output includes the executable and all its _internal files.
Source: "dist\SLIP_Model\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "reference_rainfall.csv"; DestDir: "{app}\Examples"; Flags: ignoreversion
Source: "COLLEAGUE_INSTALL_README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE_LGPL_3_0.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE_GPL_3_0.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\SLIP Model Desktop"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{autodesktop}\SLIP Model Desktop"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch SLIP Model Desktop"; Flags: nowait postinstall skipifsilent
