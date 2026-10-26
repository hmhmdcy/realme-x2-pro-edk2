$ErrorActionPreference='Stop'
$rxOriginalInf='C:\Windows\INF\oem102.inf'
$rxWantedInf=(Get-FileHash -LiteralPath $rxOriginalInf).Hash.ToLower()
$rxWantedSys=(Get-FileHash -LiteralPath 'C:\Windows\System32\drivers\qcusbser.sys').Hash.ToLower()
$rxMatches=@()
foreach($rxFolder in (Get-ChildItem -LiteralPath 'C:\Windows\System32\DriverStore\FileRepository' -Directory -Filter 'qcser.inf_*')){
  $rxInf=Join-Path $rxFolder.FullName 'qcser.inf'
  if((Test-Path -LiteralPath $rxInf) -and (Get-FileHash -LiteralPath $rxInf).Hash.ToLower() -eq $rxWantedInf){
    $rxSys=@(Get-ChildItem -LiteralPath $rxFolder.FullName -Recurse -File -Filter 'qcusbser.sys')
    if($rxSys.Count -eq 1 -and (Get-FileHash -LiteralPath $rxSys[0].FullName).Hash.ToLower() -eq $rxWantedSys){$rxMatches+= $rxFolder}
  }
}
if($rxMatches.Count -ne 1){throw 'Cannot identify exactly one installed package by both INF and SYS bytes.'}
$rxDest='E:\edk2-samurai-out\rx61\rollback-qcusbser-2.1.3.5'
if(Test-Path -LiteralPath $rxDest){throw 'Rollback copy already exists.'}
Copy-Item -LiteralPath $rxMatches[0].FullName -Destination $rxDest -Recurse
$rxManifest=@()
foreach($rxFile in (Get-ChildItem -LiteralPath $rxMatches[0].FullName -File -Recurse)){
  $rxRelative=$rxFile.FullName.Substring($rxMatches[0].FullName.Length+1)
  $rxCopy=Join-Path $rxDest $rxRelative
  $rxHash=(Get-FileHash -LiteralPath $rxFile.FullName).Hash.ToLower()
  if((Get-FileHash -LiteralPath $rxCopy).Hash.ToLower() -ne $rxHash){throw 'Rollback copy byte mismatch.'}
  $rxManifest+= [ordered]@{path=$rxRelative;bytes=$rxFile.Length;sha256=$rxHash}
}
$rxReport=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');source=$rxMatches[0].FullName;copy=$rxDest;installed_inf='oem102.inf';inf_sha256=$rxWantedInf;sys_sha256=$rxWantedSys;files=$rxManifest;action='Read existing driver package and copy byte-identical local rollback; no driver store or device changes'}
[IO.File]::WriteAllText('E:\edk2-samurai-out\rx61\rollback-package.json',($rxReport | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
$rxReport | ConvertTo-Json -Depth 6
