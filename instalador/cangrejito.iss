; Instalador del Cangrejito (Inno Setup 6).
;   1) python -m PyInstaller cangrejito.spec --noconfirm        (arma dist\Cangrejito)
;   2) ISCC instalador\cangrejito.iss [/DDist=<carpeta de dist\Cangrejito>]
; Sale en instalador\salida\CangrejitoSetup.exe

; Cangrejito — Copyright (c) 2026 MaxCurat — SPDX-License-Identifier: MIT
#define Version "1.3.0"
#ifndef Dist
  #define Dist "..\dist\Cangrejito"
#endif

[Setup]
AppId={{7C1E2B4A-5D3F-4A8E-9B61-CA2B0D3E5F17}
AppName=Cangrejito
AppVersion={#Version}
AppVerName=Cangrejito {#Version}
AppPublisher=MaxCurat
AppCopyright=Copyright (c) 2026 MaxCurat
VersionInfoVersion={#Version}
VersionInfoCompany=MaxCurat
VersionInfoCopyright=Copyright (c) 2026 MaxCurat
VersionInfoDescription=Instalador del Cangrejito
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
WizardImageFile=asistente-grande.bmp
WizardSmallImageFile=asistente-chico.bmp
DisableWelcomePage=no
LicenseFile=..\LICENSE

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Messages]
; en castellano rioplatense (el Spanish.isl de Inno Setup está en castellano de España)
WelcomeLabel1=¡Hola! Te damos la bienvenida al Cangrejito
WelcomeLabel2=Esto instala [name/ver] en tu computadora.%n%nEl cangrejito es una mascota que vive sobre la barra de tareas y te cuenta en voz alta lo que hace Claude Code mientras vos hacés otra cosa. Todo corre en tu PC.%n%nNo hace falta ser administrador.
ClickNext=Tocá «Siguiente» para seguir o «Cancelar» para salir.
WizardLicense=Licencia
LicenseLabel=Leé esto antes de seguir.
LicenseLabel3=El Cangrejito es libre (licencia MIT). Para seguir, tenés que aceptar la licencia.
LicenseAccepted=&Acepto la licencia
LicenseNotAccepted=&No la acepto
WizardSelectTasks=Opciones
SelectTasksDesc=¿Cómo querés que funcione el cangrejito?
SelectTasksLabel2=Elegí las opciones y tocá «Siguiente».
WizardReady=Todo listo
ReadyLabel1=Ya está todo para instalar el Cangrejito.
ReadyLabel2a=Tocá «Instalar» para empezar, o «Atrás» si querés cambiar algo.
ReadyLabel2b=Tocá «Instalar» para empezar.
WizardInstalling=Instalando
InstallingLabel=Esperá un momento mientras se instala el Cangrejito...
FinishedHeadingLabel=¡Listo!
FinishedLabelNoIcons=El Cangrejito quedó instalado. Aparece cuando abrís Claude y se despide cuando la cerrás.%n%nLa primera vez te pregunta cómo llamarte y baja su voz (unos 110 MB).
FinishedLabel=El Cangrejito quedó instalado. Aparece cuando abrís Claude y se despide cuando la cerrás.%n%nLa primera vez te pregunta cómo llamarte y baja su voz (unos 110 MB).
ClickFinish=Tocá «Terminar» para cerrar.
ExitSetupMessage=La instalación no terminó: si salís ahora, el Cangrejito no queda instalado.%n%n¿Querés salir igual?
ButtonNext=&Siguiente >
ButtonBack=< &Atrás
ButtonInstall=&Instalar
ButtonFinish=&Terminar
ButtonCancel=Cancelar
ConfirmUninstall=¿Querés desinstalar el Cangrejito? Se van a sacar los hooks de Claude Code y las reglas de narración. Tus ajustes quedan guardados por si lo volvés a instalar.
UninstalledAll=El Cangrejito se desinstaló. ¡Chau!

[Tasks]
Name: "narracion"; Description: "Narración en castellano: pedirle a Claude Code que explique cada paso en castellano (agrega unas reglas a tu CLAUDE.md global)"

[Files]
Source: "{#Dist}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userstartup}\Cangrejito"; Filename: "{app}\Cangrejito.exe"; Parameters: "--lanzador"; Comment: "Abre el cangrejito cuando abrís Claude"
Name: "{userprograms}\Cangrejito"; Filename: "{app}\Cangrejito.exe"; Parameters: "--lanzador"; Comment: "Cangrejito: tu mascota que narra lo que hace Claude Code"

[Run]
; conecta Claude Code con el cangrejito (hooks en %USERPROFILE%\.claude\settings.json, con copia de seguridad)
Filename: "{app}\Cangrejito.exe"; Parameters: "--instalar-hooks"; Flags: runhidden waituntilterminated; Tasks: not narracion
Filename: "{app}\Cangrejito.exe"; Parameters: "--instalar-hooks --narracion"; Flags: runhidden waituntilterminated; Tasks: narracion
Filename: "{app}\Cangrejito.exe"; Parameters: "--lanzador"; Description: "Arrancar el cangrejito ahora"; Flags: nowait postinstall

[UninstallRun]
Filename: "{app}\Cangrejito.exe"; Parameters: "--quitar-hooks"; Flags: runhidden waituntilterminated; RunOnceId: "QuitarHooks"
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM Cangrejito.exe"; Flags: runhidden waituntilterminated; RunOnceId: "Cerrar"

[Code]
// «Hecho por MaxCurat» abajo a la izquierda, en todos los pasos
procedure InitializeWizard();
var
  Firma: TNewStaticText;
begin
  Firma := TNewStaticText.Create(WizardForm);
  Firma.Parent := WizardForm;
  Firma.Caption := 'Hecho por MaxCurat · Cangrejito {#Version}';
  Firma.Font.Color := clGray;
  Firma.Left := ScaleX(16);
  Firma.Top := WizardForm.CancelButton.Top + (WizardForm.CancelButton.Height - Firma.Height) div 2;
end;

// si ya estaba andando (reinstalación o actualización), lo cierra antes de copiar los archivos
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  R: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM Cangrejito.exe', '', SW_HIDE, ewWaitUntilTerminated, R);
  Result := '';
end;
