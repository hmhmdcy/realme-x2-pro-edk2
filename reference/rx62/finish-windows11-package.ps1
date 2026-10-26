$ErrorActionPreference='Stop'
$rxIso='E:\edk2-samurai-out\rx61\EWDK_ge_release_svc_prod1_26100_250904-1728.iso'
$rxBase='E:\edk2-samurai-out\rx62'
$rxPackage=Join-Path $rxBase 'package-windows11'
if(Test-Path -LiteralPath (Join-Path $rxPackage 'qceudexp.cat')){throw 'Catalog exists; do not overwrite an already generated artifact.'}
if([IO.File]::ReadAllText((Join-Path $rxBase 'infverif-w-verbose.log')) -notmatch 'INF is VALID'){throw 'Prior Windows-driver INF validation did not pass.'}
if((Get-FileHash -LiteralPath (Join-Path $rxPackage 'qcwdfserial.sys')).Hash.ToLower() -ne '3cceeafcb3c5656e87de130d938f748cdc3875e826c63f9826440b56674b4a2a'){throw 'Compiled driver differs.'}
$rxMounted=$false
try {
  $rxImage=Get-DiskImage -ImagePath $rxIso
  if($rxImage.Attached){throw 'Kit mount exists unexpectedly.'}
  $rxImage=Mount-DiskImage -ImagePath $rxIso -StorageType ISO -Access ReadOnly -PassThru
  $rxMounted=$true
  $rxVolume=@($rxImage | Get-Volume)
  if($rxVolume.Count -ne 1 -or $rxVolume[0].DriveType -ne 'CD-ROM'){throw 'Unexpected kit volume.'}
  $rxRoot=$rxVolume[0].DriveLetter.ToString()+':\'
  $rxInf2Cat=Join-Path $rxRoot 'Program Files\Windows Kits\10\bin\10.0.26100.0\x86\Inf2Cat.exe'
  $rxDumpbin=Join-Path $rxRoot 'Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\dumpbin.exe'
  $rxCatLines=@(& $rxInf2Cat ('/driver:'+$rxPackage) /os:10_GE_X64,10_25H2_X64 /uselocaltime /verbose 2>&1)
  $rxCatExit=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $rxBase 'inf2cat-win11-generation-retry.log'),($rxCatLines | Out-String).Replace("`r`n","`n"),[Text.UTF8Encoding]::new($false))
  $rxCatLines | Select-Object -Last 12
  if($rxCatExit -ne 0){throw 'Corrected explicit Inf2Cat invocation failed.'}
  $rxHeaders=@(& $rxDumpbin /headers /imports (Join-Path $rxPackage 'qcwdfserial.sys') 2>&1)
  $rxDumpExit=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $rxBase 'dumpbin-headers-imports.log'),($rxHeaders | Out-String).Replace("`r`n","`n"),[Text.UTF8Encoding]::new($false))
  if($rxDumpExit -ne 0){throw 'PE inspection failed.'}
  Copy-Item -LiteralPath 'E:\edk2-samurai-out\rx61\source-pinned\qcom-usb-kernel-drivers-14b6fe1ee69cdd9182502629da9192156b9d206a\LICENSE.txt' -Destination (Join-Path $rxPackage 'QUALCOMM-LICENSE.txt')
  $rxFiles=@(Get-ChildItem -LiteralPath $rxPackage -File | ForEach-Object {[ordered]@{name=$_.Name;bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName).Hash.ToLower()}})
  $rxReport=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');package=$rxPackage;minimum_os='10.0.26100';architecture='amd64';kmdf='1.15';catalog_targets='10_GE_X64,10_25H2_X64';infverif_windows_driver_exit=0;infverif_info_exit=0;inf2cat_exit=$rxCatExit;dumpbin_exit=$rxDumpExit;files=$rxFiles;signed=$false;installed=$false;hardware_validated=$false;notes=@('Standalone InfVerif /w /v reports INF is VALID.','New catalog explicitly generated for Windows 11 24H2/25H2; original build package remains unchanged.','First catalog-generation script combined array arguments incorrectly; corrected direct invocation preserved its failed log. No phone action occurred.','Internal Microsoft Inf2Cat signing root remains untrusted by this host; tool is from official HTTPS EWDK. No trust root was installed.')}
  [IO.File]::WriteAllText((Join-Path $rxBase 'windows11-package.json'),($rxReport | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
  $rxReport | ConvertTo-Json -Depth 6
} finally {
  if($rxMounted){Dismount-DiskImage -ImagePath $rxIso | Out-Null}
}
