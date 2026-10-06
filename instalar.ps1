# Cangrejito (desde el código, para desarrollo): hace que el lanzador arranque con Windows. El lanzador
# es liviano y abre el cangrejito cuando abris la app de Claude; al cerrarla, se despide y se cierra.
# Para usarlo normalmente, mejor el instalador (CangrejitoSetup.exe).
# Correrlo con INSTALAR.bat (si lo corre Claude desde su terminal, Windows lo guarda en otra carpeta y no anda).
#   -Python <ruta a pythonw.exe>   el Python base para el lanzador (por defecto, el pythonw.exe del PATH)
param([switch]$Quitar, [string]$Python)

$ErrorActionPreference = 'Stop'
$aqui     = Split-Path -Parent $MyInvocation.MyCommand.Path
$python   = if ($Python) { $Python } else { (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source }
$lanzador = Join-Path $aqui 'lanzador.pyw'
$icono    = Join-Path $aqui 'cangrejito.ico'
$inicio   = Join-Path ([Environment]::GetFolderPath('Startup')) 'Cangrejito de Claude.lnk'
$viejo    = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Cangrejito de Claude.lnk'

function Parar {
    Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe'" |
        Where-Object { $_.CommandLine -like '*lanzador.pyw*' -or $_.CommandLine -like '*cangrejito.pyw*' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

if ($Quitar) {
    Remove-Item $inicio, $viejo -ErrorAction SilentlyContinue
    Parar
    Write-Host 'Listo: el cangrejito ya no arranca con Windows.' -ForegroundColor Yellow
    return
}

if (-not $python -or -not (Test-Path $python)) { throw "No encuentro pythonw.exe: pasalo con -Python <ruta>." }
Remove-Item $viejo -ErrorAction SilentlyContinue

$shell = New-Object -ComObject WScript.Shell
$a = $shell.CreateShortcut($inicio)
$a.TargetPath = $python
$a.Arguments = "-S `"$lanzador`""
$a.WorkingDirectory = $aqui
$a.Description = 'Cangrejito de Claude (lanzador)'
if (Test-Path $icono) { $a.IconLocation = $icono }
$a.Save()
Write-Host "Arranca con Windows: $inicio" -ForegroundColor Green

$andando = Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe'" |
    Where-Object { $_.CommandLine -like '*lanzador.pyw*' }
if (-not $andando) {
    Start-Process -FilePath $python -ArgumentList '-S', "`"$lanzador`"" -WorkingDirectory $aqui
}
Write-Host 'Listo: el cangrejito aparece cuando abris Claude y se va cuando la cerras.' -ForegroundColor Green
