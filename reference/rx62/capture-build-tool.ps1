$ErrorActionPreference='Stop'
$rxDest='E:\edk2-samurai-out\rx62\amd64-msbuild-provenance.json'
if(Test-Path -LiteralPath $rxDest){throw 'Snapshot exists.'}
$rxIso='E:\edk2-samurai-out\rx61\EWDK_ge_release_svc_prod1_26100_250904-1728.iso'
if((Get-DiskImage -ImagePath $rxIso).Attached){throw 'Unexpected mount.'}
$rxMounted=$false
try {
  $rxImage=Mount-DiskImage -ImagePath $rxIso -StorageType ISO -Access ReadOnly -PassThru
  $rxMounted=$true
  $rxVolumes=@($rxImage | Get-Volume)
  if($rxVolumes.Count -ne 1 -or $rxVolumes[0].DriveType -ne 'CD-ROM'){throw 'Unexpected volume.'}
  $rxRoot=$rxVolumes[0].DriveLetter.ToString()+':\'
  $rxFile=Join-Path $rxRoot 'Program Files\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\amd64\MSBuild.exe'
  $rxSig=Get-AuthenticodeSignature -LiteralPath $rxFile
  if($rxSig.Status -ne 'Valid' -or $rxSig.SignerCertificate.Subject -notmatch 'Microsoft'){throw 'MSBuild trust check failed.'}
  $rxRecord=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');path=$rxFile;sha256=(Get-FileHash -LiteralPath $rxFile).Hash.ToLower();signature_status=$rxSig.Status.ToString();signer_subject=$rxSig.SignerCertificate.Subject;file_version=(Get-Item -LiteralPath $rxFile).VersionInfo.FileVersion;purpose='Record exact amd64 MSBuild used in successful full build; no rebuild or install'}
  [IO.File]::WriteAllText($rxDest,($rxRecord | ConvertTo-Json).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
  $rxRecord | ConvertTo-Json
} finally {if($rxMounted){Dismount-DiskImage -ImagePath $rxIso | Out-Null}}
