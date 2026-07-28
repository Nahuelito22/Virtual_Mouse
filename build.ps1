# Build AI Virtual Mouse .exe (Windows / PowerShell)
# Uso: .\build.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = Join-Path $Root "venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
    Write-Host "Usando Python del sistema: $Python"
} else {
    Write-Host "Usando venv: $Python"
}

Write-Host "Instalando dependencias de build..."
& $Python -m pip install -q -r requirements.txt pyinstaller

$OutDir = Join-Path $Root "Release"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "Compilando con PyInstaller (puede tardar varios minutos)..."
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "AI_Virtual_Mouse" `
    --distpath $OutDir `
    --workpath (Join-Path $Root "build") `
    --specpath $Root `
    --collect-all mediapipe `
    --hidden-import=pyautogui `
    --hidden-import=mouseinfo `
    --hidden-import=pygetwindow `
    --hidden-import=pymsgbox `
    --hidden-import=pyperclip `
    --hidden-import=pyrect `
    --hidden-import=pyscreeze `
    --hidden-import=pytweening `
    virtual_mouse.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller fallo con codigo $LASTEXITCODE"
    exit $LASTEXITCODE
}

$Exe = Join-Path $OutDir "AI_Virtual_Mouse.exe"
if (Test-Path $Exe) {
    $SizeMb = [math]::Round((Get-Item $Exe).Length / 1MB, 1)
    Write-Host ""
    Write-Host "OK -> $Exe ($SizeMb MB)"
    Write-Host "Ejecuta el .exe o: python virtual_mouse.py"
} else {
    Write-Error "No se genero el ejecutable."
    exit 1
}
