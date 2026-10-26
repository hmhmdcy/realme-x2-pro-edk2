$ErrorActionPreference='Stop'
$rxIso='E:\edk2-samurai-out\rx61\EWDK_ge_release_svc_prod1_26100_250904-1728.iso'
$rxBase='E:\edk2-samurai-out\rx62'
$rxPackage=Join-Path $rxBase 'package-windows11'
$rxOriginal=Join-Path $rxBase 'build-output\attempt-03\qceudexp'
if(Test-Path -LiteralPath $rxPackage){throw 'Windows 11 package already exists; preserve previous result.'}
New-Item -ItemType Directory -Path $rxPackage | Out-Null
foreach($rxName in @('qceudexp.inf','qcwdfserial.sys')){Copy-Item -LiteralPath (Join-Path $rxOriginal $rxName) -Destination (Join-Path $rxPackage $rxName)}
$rxMounted=$false
try {
  $rxImage=Get-DiskImage -ImagePath $rxIso
  if($rxImage.Attached){throw 'Kit mount already exists unexpectedly.'}
  $rxImage=Mount-DiskImage -ImagePath $rxIso -StorageType ISO -Access ReadOnly -PassThru
  $rxMounted=$true
  $rxVolume=@($rxImage | Get-Volume)
  if($rxVolume.Count -ne 1 -or $rxVolume[0].DriveType -ne 'CD-ROM'){throw 'Unexpected kit volume.'}
  $rxRoot=$rxVolume[0].DriveLetter.ToString()+':\'
  $rxKit=Join-Path $rxRoot 'Program Files\Windows Kits\10'
  $rxInfVerif=Join-Path $rxKit 'Tools\10.0.26100.0\x64\infverif.exe'
  $rxInf2Cat=Join-Path $rxKit 'bin\10.0.26100.0\x86\Inf2Cat.exe'
  $rxDumpbin=Join-Path $rxRoot 'Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\dumpbin.exe'
  $rxInf=Join-Path $rxPackage 'qceudexp.inf'
  $rxSteps=@()
  foreach($rxRun in @(
    @{name='infverif-w-verbose';exe=$rxInfVerif;args=@('/w','/v',$rxInf)},
    @{name='infverif-info';exe=$rxInfVerif;args=@('/info',$rxInf)},
    @{name='inf2cat-win11-generation';exe=$rxInf2Cat;args=@('/driver:'+$rxPackage,'/os:10_GE_X64,10_25H2_X64','/uselocaltime','/verbose')},
    @{name='dumpbin-headers-imports';exe=$rxDumpbin;args=@('/headers','/imports',(Join-Path $rxPackage 'qcwdfserial.sys'))}
  )){
    $rxArgs=$rxRun.args
    $rxLines=@(& $rxRun.exe @rxArgs 2>&1)
    $rxExit=$LASTEXITCODE
    [IO.File]::WriteAllText((Join-Path $rxBase ($rxRun.name+'.log')),($rxLines | Out-String).Replace("`r`n","`n"),[Text.UTF8Encoding]::new($false))
    $rxSteps+=[ordered]@{name=$rxRun.name;exit=$rxExit}
    [ordered]@{name=$rxRun.name;exit=$rxExit;tail=@($rxLines | Select-Object -Last 12)} | ConvertTo-Json -Depth 4
    if($rxExit -ne 0){throw ('Required package check failed: '+$rxRun.name)}
  }
  Copy-Item -LiteralPath 'E:\edk2-samurai-out\rx61\source-pinned\qcom-usb-kernel-drivers-14b6fe1ee69cdd9182502629da9192156b9d206a\LICENSE.txt' -Destination (Join-Path $rxPackage 'QUALCOMM-LICENSE.txt')
  $rxFiles=@(Get-ChildItem -LiteralPath $rxPackage -File | ForEach-Object {[ordered]@{name=$_.Name;bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName).Hash.ToLower()}})
  $rxReport=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');package=$rxPackage;steps=$rxSteps;minimum_os='10.0.26100';architecture='amd64';kmdf='1.15';catalog_targets='10_GE_X64,10_25H2_X64';files=$rxFiles;signed=$false;installed=$false;hardware_validated=$false;notes=@('Separate /w /v and /info avoid incompatible display flags in first standalone run.','New catalog explicitly covers Windows 11 24H2/25H2; original full-build package is preserved.','Microsoft Inf2Cat comes from the official HTTPS kit; its internal code-sign certificate chains to a root not trusted by this host. No root or certificate was installed.')}
  [IO.File]::WriteAllText((Join-Path $rxBase 'windows11-package.json'),($rxReport | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
  $rxReport | ConvertTo-Json -Depth 6
} finally {
  if($rxMounted){Dismount-DiskImage -ImagePath $rxIso | Out-Null}
}
