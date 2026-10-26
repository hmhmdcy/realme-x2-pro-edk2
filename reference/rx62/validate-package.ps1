$ErrorActionPreference='Stop'
$rxIso='E:\edk2-samurai-out\rx61\EWDK_ge_release_svc_prod1_26100_250904-1728.iso'
$rxBase='E:\edk2-samurai-out\rx62'
$rxOriginal=Join-Path $rxBase 'build-output\attempt-03\qceudexp'
$rxPackage=Join-Path $rxBase 'package-unsigned'
if(Test-Path -LiteralPath $rxPackage){throw 'Package copy already exists; preserve prior output.'}
New-Item -ItemType Directory -Path $rxPackage | Out-Null
foreach($rxName in @('qceudexp.inf','qcwdfserial.sys','qceudexp.cat')){
  Copy-Item -LiteralPath (Join-Path $rxOriginal $rxName) -Destination (Join-Path $rxPackage $rxName)
  if((Get-FileHash -LiteralPath (Join-Path $rxOriginal $rxName)).Hash -ne (Get-FileHash -LiteralPath (Join-Path $rxPackage $rxName)).Hash){throw 'Package copy differs from successful build.'}
}
$rxInf=Join-Path $rxPackage 'qceudexp.inf'
$rxText=[IO.File]::ReadAllText($rxInf)
if($rxText -match '\$KMDFVERSION\$' -or $rxText -notmatch 'KmdfLibraryVersion=1\.15' -or $rxText -notmatch 'NTamd64\.10\.0\.\.\.26100'){throw 'Stamped package input is unexpected.'}
$rxMounted=$false
try {
  $rxImage=Get-DiskImage -ImagePath $rxIso
  if($rxImage.Attached){throw 'Kit already mounted unexpectedly.'}
  $rxImage=Mount-DiskImage -ImagePath $rxIso -StorageType ISO -Access ReadOnly -PassThru
  $rxMounted=$true
  $rxVolume=@($rxImage | Get-Volume)
  if($rxVolume.Count -ne 1 -or $rxVolume[0].DriveType -ne 'CD-ROM'){throw 'Unexpected kit volume.'}
  $rxRoot=$rxVolume[0].DriveLetter.ToString()+':\'
  $rxInfVerif=Join-Path $rxRoot 'Program Files\Windows Kits\10\Tools\10.0.26100.0\x64\infverif.exe'
  $rxInf2Cat=Join-Path $rxRoot 'Program Files\Windows Kits\10\bin\10.0.26100.0\x86\Inf2Cat.exe'
  if((Get-AuthenticodeSignature -LiteralPath $rxInfVerif).Status -ne 'Valid'){throw 'InfVerif signature not verified.'}
  $rxInfLog=@(& $rxInfVerif /w /v /info $rxInf 2>&1)
  $rxInfExit=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $rxBase 'infverif-w.log'),($rxInfLog | Out-String).Replace("`r`n","`n"),[Text.UTF8Encoding]::new($false))
  $rxInfLog | ForEach-Object {Write-Output $_}
  if($rxInfExit -ne 0){throw 'Standalone InfVerif /w failed; no installation is permitted by this validation.'}
  $rxCatLog=@(& $rxInf2Cat ('/driver:'+$rxPackage) /os:10_GE_X64,10_25H2_X64 /uselocaltime /nocat /verbose 2>&1)
  $rxCatExit=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $rxBase 'inf2cat-windows11.log'),($rxCatLog | Out-String).Replace("`r`n","`n"),[Text.UTF8Encoding]::new($false))
  $rxCatLog | ForEach-Object {Write-Output $_}
  if($rxCatExit -ne 0){throw 'Explicit Windows 11 package signability check failed.'}
  $rxFiles=@(Get-ChildItem -LiteralPath $rxPackage -File | ForEach-Object {[ordered]@{name=$_.Name;bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName).Hash.ToLower()}})
  $rxReport=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');package=$rxPackage;infverif_mode='/w /v /info';infverif_exit=$rxInfExit;inf2cat_explicit_targets='10_GE_X64,10_25H2_X64';inf2cat_exit=$rxCatExit;local_time=$true;catalog_generated_by_full_build=$true;standalone_nocat_preserves_original_catalog=$true;files=$rxFiles;binary_signature=(Get-AuthenticodeSignature -LiteralPath (Join-Path $rxPackage 'qcwdfserial.sys')).Status.ToString();signed=$false;installed=$false;hardware_validated=$false}
  [IO.File]::WriteAllText((Join-Path $rxBase 'package-validation.json'),($rxReport | ConvertTo-Json -Depth 5).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
  $rxReport | ConvertTo-Json -Depth 5
} finally {
  if($rxMounted){Dismount-DiskImage -ImagePath $rxIso | Out-Null}
}
