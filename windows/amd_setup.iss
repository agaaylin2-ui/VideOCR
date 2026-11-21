; Compile with the x64 edition of Inno Setup 7.
#ifndef Bundle
  #error "Define Bundle as the absolute path to the prepared Windows desktop bundle."
#endif
#ifndef AppVersion
  #error "Define AppVersion, for example 1.6.0-amd-preview.4."
#endif
#define Launcher "VideOCR-AMD.exe"
#if !FileExists(Bundle + "\" + Launcher) || !FileExists(Bundle + "\runtime\pythonw.exe") || !FileExists(Bundle + "\app\desktop.pyw") || !FileExists(Bundle + "\app\models\det\inference.onnx") || !FileExists(Bundle + "\app\models\rec\inference.onnx")
  #error "Incomplete Windows desktop bundle."
#endif

[Setup]
AppId={{3F76B8ED-A880-454A-9897-EEC40E06F710}
AppName=VideoOCR-AMD
AppVersion={#AppVersion}
AppPublisher=aylinlabs
AppPublisherURL=https://github.com/aylinlabs/VideoOCR-AMD
DefaultDirName={localappdata}\Programs\VideoOCR-AMD
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=no
UninstallDisplayIcon={app}\{#Launcher}
SetupIconFile={#Bundle}\app\VideOCR.ico
OutputBaseFilename=VideoOCR-AMD-Windows-x64-{#AppVersion}-Setup
Compression=lzma2/fast
SolidCompression=yes

[Files]
Source: "{#Bundle}\{#Launcher}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Bundle}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Bundle}\AMD_DESKTOP.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Bundle}\app\*"; DestDir: "{app}\app"; Excludes: "__pycache__,*.pyc"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#Bundle}\runtime\*"; DestDir: "{app}\runtime"; Excludes: "__pycache__,*.pyc"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\VideoOCR-AMD"; Filename: "{app}\{#Launcher}"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#Launcher}"; Description: "Open VideoOCR-AMD"; Flags: postinstall nowait skipifsilent
