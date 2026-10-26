# File-only signing preparation. No certificate import, driver install or boot change.
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$false
$rxBase='E:\edk2-samurai-out\rx62'
$rxPackage=Join-Path $rxBase 'package-test-signed'
$rxPrivate=Join-Path $rxBase 'private-signing'
$rxPfx=Join-Path $rxPrivate 'one-use.pfx'
$rxIso='E:\edk2-samurai-out\rx61\EWDK_ge_release_svc_prod1_26100_250904-1728.iso'
foreach($rxPath in @($rxPackage,$rxPrivate,(Join-Path $rxBase 'offline-signing.json'))){if(Test-Path -LiteralPath $rxPath){throw 'Single-use output exists; preserve it.'}}
$rxUnsigned=Join-Path $rxBase 'package-windows11'
if((Get-FileHash -LiteralPath (Join-Path $rxUnsigned 'qcwdfserial.sys')).Hash.ToLower() -ne '3cceeafcb3c5656e87de130d938f748cdc3875e826c63f9826440b56674b4a2a'){throw 'Unsigned source differs.'}
if((Get-DiskImage -ImagePath $rxIso).Attached){throw 'Unexpected pre-existing kit mount.'}
$rxMounted=$false
$rxRsa=$null
$rxCert=$null
$rxPassword=$null
$rxStatus='started'
try {
  New-Item -ItemType Directory -Path $rxPrivate | Out-Null
  $rxAcl=[Security.AccessControl.DirectorySecurity]::new()
  $rxAcl.SetAccessRuleProtection($true,$false)
  $rxIdentity=[Security.Principal.WindowsIdentity]::GetCurrent().User
  $rxAcl.SetOwner($rxIdentity)
  foreach($rxSid in @($rxIdentity,[Security.Principal.SecurityIdentifier]::new('S-1-5-18'),[Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))){
    $rxRule=[Security.AccessControl.FileSystemAccessRule]::new($rxSid,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
    $rxAcl.AddAccessRule($rxRule)
  }
  Set-Acl -LiteralPath $rxPrivate -AclObject $rxAcl
  $rxFinalAcl=Get-Acl -LiteralPath $rxPrivate
  if(!$rxFinalAcl.AreAccessRulesProtected -or @($rxFinalAcl.Access | Where-Object IsInherited).Count){throw 'Private directory permissions did not apply.'}
  New-Item -ItemType Directory -Path $rxPackage | Out-Null
  foreach($rxName in @('qceudexp.inf','qcwdfserial.sys','QUALCOMM-LICENSE.txt')){Copy-Item -LiteralPath (Join-Path $rxUnsigned $rxName) -Destination (Join-Path $rxPackage $rxName)}

  $rxRsa=[Security.Cryptography.RSA]::Create(3072)
  $rxRequest=[Security.Cryptography.X509Certificates.CertificateRequest]::new('CN=EUD RX62 offline experiment only',$rxRsa,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)
  $rxRequest.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($false,$false,0,$true))
  $rxRequest.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new([Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature,$true))
  $rxEku=[Security.Cryptography.OidCollection]::new()
  [void]$rxEku.Add([Security.Cryptography.Oid]::new('1.3.6.1.5.5.7.3.3'))
  $rxRequest.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]::new($rxEku,$false))
  $rxCert=$rxRequest.CreateSelfSigned([DateTimeOffset]::UtcNow.AddMinutes(-5),[DateTimeOffset]::UtcNow.AddDays(14))
  $rxRandom=[byte[]]::new(32)
  [Security.Cryptography.RandomNumberGenerator]::Fill($rxRandom)
  $rxPassword=[Convert]::ToBase64String($rxRandom)
  [IO.File]::WriteAllBytes($rxPfx,$rxCert.Export([Security.Cryptography.X509Certificates.X509ContentType]::Pfx,$rxPassword))
  [IO.File]::WriteAllBytes((Join-Path $rxPackage 'eud-rx62-test.cer'),$rxCert.Export([Security.Cryptography.X509Certificates.X509ContentType]::Cert))

  $rxImage=Mount-DiskImage -ImagePath $rxIso -StorageType ISO -Access ReadOnly -PassThru
  $rxMounted=$true
  $rxVolumes=@($rxImage | Get-Volume)
  if($rxVolumes.Count -ne 1 -or $rxVolumes[0].DriveType -ne 'CD-ROM'){throw 'Unexpected kit volume.'}
  $rxRoot=$rxVolumes[0].DriveLetter.ToString()+':\'
  $rxSignTool=Join-Path $rxRoot 'Program Files\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe'
  $rxInf2Cat=Join-Path $rxRoot 'Program Files\Windows Kits\10\bin\10.0.26100.0\x86\Inf2Cat.exe'
  $rxSig=Get-AuthenticodeSignature -LiteralPath $rxSignTool
  if($rxSig.Status -ne 'Valid' -or $rxSig.SignerCertificate.Subject -notmatch 'Microsoft'){throw 'Signing tool trust check failed.'}
  $rxTool=[ordered]@{path=$rxSignTool;sha256=(Get-FileHash -LiteralPath $rxSignTool).Hash.ToLower();signature_status=$rxSig.Status.ToString();version=(Get-Item -LiteralPath $rxSignTool).VersionInfo.FileVersion}
  $rxLines=@(& $rxSignTool sign /f $rxPfx /p $rxPassword /fd SHA256 /ph (Join-Path $rxPackage 'qcwdfserial.sys') 2>&1)
  $rxSysExit=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $rxBase 'test-sign-sys.log'),($rxLines | Out-String).Replace("`r`n","`n"),[Text.UTF8Encoding]::new($false))
  if($rxSysExit -ne 0){throw 'File-only SYS signing failed.'}
  $rxLines=@(& $rxInf2Cat ('/driver:'+$rxPackage) /os:10_GE_X64,10_25H2_X64 /uselocaltime /verbose 2>&1)
  $rxCatExit=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $rxBase 'test-signed-inf2cat.log'),($rxLines | Out-String).Replace("`r`n","`n"),[Text.UTF8Encoding]::new($false))
  if($rxCatExit -ne 0){throw 'Signed SYS catalog generation failed.'}
  $rxLines=@(& $rxSignTool sign /f $rxPfx /p $rxPassword /fd SHA256 (Join-Path $rxPackage 'qceudexp.cat') 2>&1)
  $rxSignCatExit=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $rxBase 'test-sign-cat.log'),($rxLines | Out-String).Replace("`r`n","`n"),[Text.UTF8Encoding]::new($false))
  if($rxSignCatExit -ne 0){throw 'File-only catalog signing failed.'}

  Add-Type -AssemblyName System.Security.Cryptography.Pkcs
  $rxCmsChecks=@()
  foreach($rxName in @('qcwdfserial.sys','qceudexp.cat')){
    $rxBytes=[IO.File]::ReadAllBytes((Join-Path $rxPackage $rxName))
    if($rxName -eq 'qcwdfserial.sys'){
      $rxPe=[BitConverter]::ToInt32($rxBytes,0x3c)
      $rxSecurity=$rxPe+24+112+32
      $rxCertOffset=[BitConverter]::ToInt32($rxBytes,$rxSecurity)
      $rxCertLength=[BitConverter]::ToInt32($rxBytes,$rxCertOffset)
      if($rxCertOffset -lt 102912 -or $rxCertLength -lt 8 -or $rxCertOffset+$rxCertLength -gt $rxBytes.Length){throw 'Unexpected PE certificate record.'}
      $rxCmsBytes=[byte[]]::new($rxCertLength-8)
      [Array]::Copy($rxBytes,$rxCertOffset+8,$rxCmsBytes,0,$rxCmsBytes.Length)
    } else {$rxCmsBytes=$rxBytes}
    $rxCms=[Security.Cryptography.Pkcs.SignedCms]::new()
    $rxCms.Decode($rxCmsBytes)
    $rxCms.CheckSignature($true)
    if($rxCms.SignerInfos.Count -ne 1 -or $rxCms.SignerInfos[0].Certificate.Thumbprint -ne $rxCert.Thumbprint){throw 'Unexpected CMS signer.'}
    [IO.File]::WriteAllBytes((Join-Path $rxBase ($rxName+'.cms-content.bin')),$rxCms.ContentInfo.Content)
    $rxCmsChecks += [ordered]@{file=$rxName;signature_only_valid=$true;content_oid=$rxCms.ContentInfo.ContentType.Value;digest_oid=$rxCms.SignerInfos[0].DigestAlgorithm.Value;signer_thumbprint=$rxCert.Thumbprint}
  }
  $rxStoreChecks=@()
  foreach($rxLocation in @('CurrentUser','LocalMachine')){foreach($rxStoreName in @('My','Root','TrustedPublisher')){
    $rxStore=[Security.Cryptography.X509Certificates.X509Store]::new($rxStoreName,[Security.Cryptography.X509Certificates.StoreLocation]$rxLocation)
    try {
      $rxStore.Open([Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly)
      $rxMatches=@($rxStore.Certificates | Where-Object Thumbprint -eq $rxCert.Thumbprint).Count
      if($rxMatches -ne 0){throw 'File-only test certificate unexpectedly exists in a system certificate store.'}
      $rxStoreChecks += [ordered]@{location=$rxLocation;store=$rxStoreName;test_certificate_matches=$rxMatches}
    } finally {$rxStore.Close();$rxStore.Dispose()}
  }}
  $rxFiles=@(Get-ChildItem -LiteralPath $rxPackage -File | ForEach-Object {[ordered]@{name=$_.Name;bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName).Hash.ToLower()}})
  $rxReport=[ordered]@{
    utc=[DateTime]::UtcNow.ToString('o');package=$rxPackage;signtool=$rxTool
    sys_sign_exit=$rxSysExit;inf2cat_exit=$rxCatExit;catalog_sign_exit=$rxSignCatExit
    certificate=[ordered]@{subject=$rxCert.Subject;thumbprint=$rxCert.Thumbprint;not_before_utc=$rxCert.NotBefore.ToUniversalTime().ToString('o');not_after_utc=$rxCert.NotAfter.ToUniversalTime().ToString('o');rsa_bits=3072;certificate_store_imported=$false;timestamped=$false}
    cms_signature_checks=$rxCmsChecks;certificate_store_checks=$rxStoreChecks;files=$rxFiles
    microsoft_release_signed=$false;trusted_by_current_host=$false;installed=$false;hardware_validated=$false
    private_key_policy='Ephemeral RSA and password protected one-use PFX in owner/Admin/SYSTEM-only directory; PFX removed in finally. No private signing material published.'
    limits='CMS signature-only validation; independent PE file digest comparison required. File signing does not grant Windows kernel loading trust. No root import, BCD/security/driver-store changes or phone I/O.'
  }
  [IO.File]::WriteAllText((Join-Path $rxBase 'offline-signing.json'),($rxReport | ConvertTo-Json -Depth 8).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
  $rxStatus='file-only test signing complete; loading not authorized or attempted'
} finally {
  if($rxMounted){Dismount-DiskImage -ImagePath $rxIso | Out-Null}
  if($rxCert){$rxCert.Dispose()}
  if($rxRsa){$rxRsa.Dispose()}
  $rxPassword=$null
  if(Test-Path -LiteralPath $rxPfx){Remove-Item -LiteralPath $rxPfx -Force}
  [IO.File]::WriteAllText((Join-Path $rxBase 'offline-signing-cleanup.json'),([ordered]@{utc=[DateTime]::UtcNow.ToString('o');status=$rxStatus;temporary_pfx_absent=(!(Test-Path -LiteralPath $rxPfx));iso_attached=(Get-DiskImage -ImagePath $rxIso).Attached;private_directory_acl_protected=($(if(Test-Path -LiteralPath $rxPrivate){(Get-Acl -LiteralPath $rxPrivate).AreAccessRulesProtected}else{$false}))} | ConvertTo-Json -Depth 4).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
}
Write-Output $rxStatus
