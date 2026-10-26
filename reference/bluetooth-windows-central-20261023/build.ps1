param([switch]$Probe)
$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'windows-gatt-central.cs'
$outputRoot = 'E:\edk2-samurai-out\bluetooth-windows-central-20261023'
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
$compilerRoot = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319'
$compiler = Join-Path $compilerRoot 'csc.exe'
$exe = Join-Path $outputRoot 'windows-gatt-central.exe'
$winmd = 'C:\Program Files (x86)\Windows Kits\10\UnionMetadata\10.0.26100.0\Windows.winmd'
$compilerArgs = @('/nologo','/noconfig','/target:exe','/optimize+','/warn:4','/warnaserror+',"/out:$exe",
          "/r:$winmd", "/r:$compilerRoot\System.Runtime.dll",
          "/r:$compilerRoot\System.Runtime.WindowsRuntime.dll",
          "/r:$compilerRoot\System.Runtime.InteropServices.WindowsRuntime.dll",
          '/r:System.dll','/r:System.Core.dll','/r:System.Web.Extensions.dll', $source)
& $compiler @compilerArgs 2>&1 | Tee-Object -FilePath (Join-Path $outputRoot 'compile-private.log')
if ($LASTEXITCODE -ne 0) { throw "C# compiler exit $LASTEXITCODE" }
if ($Probe) {
    $probePath = Join-Path $outputRoot 'watcher-probe-private.json'
    & $exe --probe $probePath
    if ($LASTEXITCODE -ne 0) { throw "Windows watcher probe exit $LASTEXITCODE" }
}
