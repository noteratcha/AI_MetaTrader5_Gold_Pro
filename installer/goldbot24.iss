; ==============================================================================
; AI Gold Commander Pro (GoldBot24) — ตัวติดตั้ง Windows (Inno Setup 6)
; สร้างโดย build_dist.py: ISCC /DAppVersion=<เวอร์ชัน> installer\goldbot24.iss
;   - ติดตั้งแบบผู้ใช้ปัจจุบัน ไม่ต้องใช้สิทธิ์ Admin (%LOCALAPPDATA%\Programs\GoldBot24)
;   - สร้าง Icon บน Desktop + Start Menu และถอนการติดตั้งได้จาก Settings → Apps
;   - อัปเดตทับเวอร์ชันเดิมได้ (AppId เดิม) และปิดโปรแกรมที่เปิดอยู่ให้อัตโนมัติ
;   - ข้อมูลผู้ใช้ใน %APPDATA%\GoldBot24 (ล็อกอิน/สถิติ) ไม่ถูกลบตอนถอนการติดตั้ง
; ==============================================================================
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "AI Gold Commander Pro"
#define AppExe "AI_Gold_Commander_Pro.exe"
#define SourceDir "..\dist\AI_Gold_Commander_Pro"

[Setup]
AppId={{7C1E2B54-9E3A-4F0B-A6D2-6B9F24C0D724}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
AppPublisher=GoldBot24
AppPublisherURL=https://goldbot24.vercel.app
AppSupportURL=https://goldbot24.vercel.app
AppUpdatesURL=https://goldbot24.vercel.app/download
DefaultDirName={localappdata}\Programs\GoldBot24
DefaultGroupName=GoldBot24
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=GoldBot24_Setup_v{#AppVersion}
SetupIconFile=..\assets\app_icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force
RestartApplications=no
VersionInfoVersion={#AppVersion}
VersionInfoCompany=GoldBot24
VersionInfoDescription={#AppName} Setup

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut (สร้างไอคอนบนหน้าจอ)"; GroupDescription: "Shortcuts:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; ล้างไฟล์โปรแกรมเวอร์ชันเก่าก่อนติดตั้งทับ (ไม่แตะข้อมูลผู้ใช้ใน %APPDATA%)
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autoprograms}\Uninstall {#AppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName} (เปิดโปรแกรม)"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
