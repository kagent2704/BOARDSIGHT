param()

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$srcRoot = Join-Path $projectRoot "java-app\src\main\java"
$resourcesRoot = Join-Path $projectRoot "java-app\src\main\resources"
$buildRoot = Join-Path $projectRoot "java-app\build"
$classesRoot = Join-Path $buildRoot "classes"
$jarPath = Join-Path $buildRoot "boardsight.jar"
$jarExe = Get-ChildItem "C:\Program Files\Java\*\bin\jar.exe" | Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
if (-not $jarExe) {
    throw "Unable to locate jar.exe under C:\Program Files\Java"
}

if (Test-Path $buildRoot) {
    Remove-Item -Recurse -Force $buildRoot
}

New-Item -ItemType Directory -Path $classesRoot | Out-Null

$javaFiles = Get-ChildItem -Path $srcRoot -Recurse -Filter *.java | ForEach-Object { $_.FullName }
if (-not $javaFiles) {
    throw "No Java source files found under $srcRoot"
}

javac -d $classesRoot $javaFiles

if (Test-Path $resourcesRoot) {
    Copy-Item -Path (Join-Path $resourcesRoot "*") -Destination $classesRoot -Recurse -Force
}

$manifestPath = Join-Path $buildRoot "manifest.mf"
@(
    "Manifest-Version: 1.0"
    "Main-Class: com.boardsight.web.BoardSightWebApp"
) | Set-Content -Path $manifestPath

& $jarExe --create --file $jarPath --manifest $manifestPath -C $classesRoot .

Write-Host "Built $jarPath"
