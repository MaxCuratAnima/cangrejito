; Instalador del Cangrejito (Inno Setup 6).
;   1) python -m PyInstaller cangrejito.spec --noconfirm        (arma dist\Cangrejito)
;   2) ISCC instalador\cangrejito.iss [/DDist=<carpeta de dist\Cangrejito>]
; Sale en instalador\salida\CangrejitoSetup.exe

#define Version "1.0.0"
#ifndef Dist
  #define Dist "..\dist\Cangrejito"
#endif

[Setup]
AppId={{7C1E2B4A-5D3F-4A8E-9B61-CA2B0D3E5F17}
AppName=Cangrejito
AppVersion={#Version}
AppVerName=Cangrejito {#Version}
AppPublisher=MaxCuratAnima
AppPublisherURL=https://github.com/MaxCuratAnima/cangrejito
AppSupportURL=https://github.com/MaxCuratAnima/cangrejito/issues
DefaultDirName={localappdata}\Programs\Cangrejito
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=salida
OutputBaseFilename=CangrejitoSetup
SetupIconFile=..\cangrejito.ico
UninstallDisplayIcon={app}\Cangrejito.exe
UninstallDisplayName=Cangrejito
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "narracion"; Description: "Narración en castellano: pedirle a Claude Code que explique cada paso en castellano (agrega unas reglas a tu CLAUDE.md global)"
Name: "siempre"; Description: "Mostrarlo aunque la app de Claude esté cerrada (si usás Claude Code en la terminal)"; Flags: unchecked

[Files]
Source: "{#Dist}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userstartup}\Cangrejito"; Filename: "{app}\Cangrejito.exe"; Parameters: "--lanzador"; Comment: "Abre el cangrejito cuando abrís Claude"
Name: "{userprograms}\Cangrejito"; Filename: "{app}\Cangrejito.exe"; Parameters: "--lanzador"; Comment: "Cangrejito: tu mascota que narra lo que hace Claude Code"

[Run]
; conecta Claude Code con el cangrejito (hooks en %USERPROFILE%\.claude\settings.json, con copia de seguridad)
Filename: "{app}\Cangrejito.exe"; Parameters: "--instalar-hooks"; Flags: runhidden waituntilterminated; Tasks: not narracion and not siempre
Filename: "{app}\Cangrejito.exe"; Parameters: "--instalar-hooks --narracion"; Flags: runhidden waituntilterminated; Tasks: narracion and not siempre
Filename: "{app}\Cangrejito.exe"; Parameters: "--instalar-hooks --siempre-visible"; Flags: runhidden waituntilterminated; Tasks: not narracion and siempre
Filename: "{app}\Cangrejito.exe"; Parameters: "--instalar-hooks --narracion --siempre-visible"; Flags: runhidden waituntilterminated; Tasks: narracion and siempre
Filename: "{app}\Cangrejito.exe"; Parameters: "--lanzador"; Description: "Arrancar el cangrejito ahora"; Flags: nowait postinstall

[UninstallRun]
Filename: "{app}\Cangrejito.exe"; Parameters: "--quitar-hooks"; Flags: runhidden waituntilterminated; RunOnceId: "QuitarHooks"
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM Cangrejito.exe"; Flags: runhidden waituntilterminated; RunOnceId: "Cerrar"

[Code]
// si ya estaba andando (reinstalación o actualización), lo cierra antes de copiar los archivos
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  R: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM Cangrejito.exe', '', SW_HIDE, ewWaitUntilTerminated, R);
  Result := '';
end;
