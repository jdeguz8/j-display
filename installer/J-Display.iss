; J-Display Inno Setup

[Setup]
AppName=J-Display
AppVersion=1.0.0
DefaultDirName={pf}\J-Display
DefaultGroupName=J-Display
OutputDir=installer\output
OutputBaseFilename=J-Display-Setup
Compression=lzma
SolidCompression=yes
SetupIconFile=assets\jdisplay.ico
LicenseFile=assets\LICENSE.txt
WizardStyle=modern

[Files]
; Install your packaged EXE into the app directory
Source: "dist\J-Display.exe"; DestDir: "{app}"; Flags: ignoreversion

; (Optional) If you ever need to include a default config, you can add it here too:
; Source: "config\config.toml"; DestDir: "{localappdata}\J-Display"; Flags: onlyifdoesntexist

[Icons]
; Start menu shortcut
Name: "{group}\J-Display"; Filename: "{app}\J-Display.exe"

; Desktop shortcut
Name: "{commondesktop}\J-Display"; Filename: "{app}\J-Display.exe"

[Run]
; Optionally launch app after install
Filename: "{app}\J-Display.exe"; Description: "Run J-Display"; Flags: nowait postinstall skipifsilent
