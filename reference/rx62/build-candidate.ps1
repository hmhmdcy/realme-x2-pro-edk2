param([ValidateRange(1,3)][int]$Attempt=1)
$ErrorActionPreference='Stop'
$rxIso='E:\edk2-samurai-out\rx61\EWDK_ge_release_svc_prod1_26100_250904-1728.iso'
$rxSource='E:\edk2-samurai-out\rx61\source-pinned\qcom-usb-kernel-drivers-14b6fe1ee69cdd9182502629da9192156b9d206a\src\windows\wdfserial'
$rxTag=('attempt-{0:d2}' -f $Attempt)
$rxBase='E:\edk2-samurai-out\rx62'
$rxOut=Join-Path $rxBase ('build-output\'+$rxTag)
$rxInt=Join-Path $rxBase ('build-intermediate\'+$rxTag)
$rxCmd=Join-Path $rxBase ('build-'+$rxTag+'.cmd')
$rxLog=Join-Path $rxBase ('build-'+$rxTag+'.log')
$rxResult=Join-Path $rxBase ('build-'+$rxTag+'.json')
foreach($rxTarget in @($rxOut,$rxInt,$rxCmd,$rxLog,$rxResult)){if(Test-Path -LiteralPath $rxTarget){throw 'Build attempt outputs already exist; inspect them instead of rerunning.'}}
if((Get-FileHash -LiteralPath (Join-Path $rxSource 'QCPNP.c')).Hash.ToLower() -ne '7cf3f3db7878d4a1a037da075e4dfda6985851b7805a42434cf3ae2202c014fd'){throw 'Frozen toggle candidate source changed.'}
$rxMounted=$false
$rxStarted=[DateTime]::UtcNow
$rxExit=$null
try {
  $rxImage=Get-DiskImage -ImagePath $rxIso
  if(!$rxImage.Attached){$rxImage=Mount-DiskImage -ImagePath $rxIso -StorageType ISO -Access ReadOnly -PassThru}
  $rxMounted=$true
  $rxVolume=@($rxImage | Get-Volume)
  if($rxVolume.Count -ne 1 -or $rxVolume[0].DriveType -ne 'CD-ROM' -or !$rxVolume[0].DriveLetter){throw 'Unexpected build kit volume.'}
  $rxRoot=$rxVolume[0].DriveLetter.ToString()+':\'
  $rxBuild=Join-Path $rxRoot 'Program Files\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\amd64\MSBuild.exe'
  if((Get-AuthenticodeSignature -LiteralPath $rxBuild).Status -ne 'Valid'){throw 'MSBuild signature is not verified.'}
  New-Item -ItemType Directory -Path $rxOut,$rxInt | Out-Null
  $rxLines=@(
    '@echo off',
    ('call "{0}BuildEnv\SetupBuildEnv.cmd" amd64' -f $rxRoot),
    'if errorlevel 1 exit /b %errorlevel%',
    '@echo off',
    ('"{0}" "{1}\qceudexp.vcxproj" /t:Build /nologo /m:1 /nr:false /v:minimal /p:Configuration=Release /p:Platform=x64 /p:WindowsTargetPlatformVersion=10.0.26100.0 /p:SignMode=Off /p:EnableTestSign=false /p:Inf2CatUseLocalTime=true /p:OutDir={2}\ /p:IntDir={3}\ "/flp:LogFile={4};Verbosity=normal;Encoding=UTF-8"' -f $rxBuild,$rxSource,$rxOut,$rxInt,$rxLog),
    'exit /b %errorlevel%'
  )
  [IO.File]::WriteAllLines($rxCmd,$rxLines,[Text.ASCIIEncoding]::new())
  & $env:ComSpec /d /c $rxCmd
  $rxExit=$LASTEXITCODE
  $rxFiles=@(Get-ChildItem -LiteralPath $rxOut -File -Recurse | Select-Object FullName,Length)
  $rxReport=[ordered]@{
    started_utc=$rxStarted.ToString('o');ended_utc=[DateTime]::UtcNow.ToString('o');exit_code=$rxExit;
    attempt=$Attempt;kit_root=$rxRoot;source=$rxSource;configuration='Release|x64';sign_mode='Off';enable_test_sign=$false;
    project_sha256=(Get-FileHash -LiteralPath (Join-Path $rxSource 'qceudexp.vcxproj')).Hash.ToLower();
    input_inf_sha256=(Get-FileHash -LiteralPath (Join-Path $rxSource 'qceudexp.inf')).Hash.ToLower();
    qcpnp_sha256=(Get-FileHash -LiteralPath (Join-Path $rxSource 'QCPNP.c')).Hash.ToLower();
    command_file=$rxCmd;log=$rxLog;output=$rxOut;files=$rxFiles;installed=$false;hardware_validated=$false;
    changes='Offline compilation only; no signing/deployment, registry, boot/security setting or phone I/O'
  }
  [IO.File]::WriteAllText($rxResult,($rxReport | ConvertTo-Json -Depth 5).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
  $rxReport | ConvertTo-Json -Depth 5
  if($rxExit -ne 0){throw ('WDK build failed with exit '+$rxExit+'; preserve diagnostics and repair before a fresh attempt.')}
} finally {
  if($rxMounted){Dismount-DiskImage -ImagePath $rxIso | Out-Null}
}
