$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx61'
$rxDownload=Join-Path $rxRoot 'ewdk-download'
if(Test-Path -LiteralPath $rxDownload){throw 'Download already prepared; inspect and reuse its live handles, do not restart.'}
$rxHead=Get-Content -Raw -LiteralPath (Join-Path $rxRoot 'ewdk-head.json')|ConvertFrom-Json
$rxUrl='https://download.microsoft.com/download/be985897-caaa-4497-9ea4-17fa7065cd8a/EWDK_ge_release_svc_prod1_26100_250904-1728.iso'
$rxLength=20002537472L
if($rxHead.uri -ne $rxUrl -or [long]$rxHead.headers.'Content-Length'[0] -ne $rxLength){throw 'Official ISO identity/size changed.'}
$rxDisk=Get-PSDrive -Name E
if($rxDisk.Free -lt 65000000000L){throw 'Insufficient headroom for parts, ISO and offline build.'}
[IO.Directory]::CreateDirectory($rxDownload)|Out-Null
$rxParts=@()
$rxPartSize=[long][Math]::Ceiling($rxLength/8.0)
foreach($rxIndex in 0..7){
    $rxStart=$rxIndex*$rxPartSize
    $rxEnd=[Math]::Min($rxLength-1,$rxStart+$rxPartSize-1)
    $rxStem='part-{0:d2}' -f $rxIndex
    $rxPart=Join-Path $rxDownload ($rxStem+'.bin')
    $rxConfig=Join-Path $rxDownload ($rxStem+'.curl.cfg')
    $rxHeaders=Join-Path $rxDownload ($rxStem+'.headers.txt')
    # curl config paths use escaped Windows backslashes. All inputs are fixed
    # task paths/official URL, never untrusted shell text.
    $rxPartEsc=$rxPart.Replace('\','\\')
    $rxHeaderEsc=$rxHeaders.Replace('\','\\')
    $rxText=@"
url = "$rxUrl"
output = "$rxPartEsc"
dump-header = "$rxHeaderEsc"
range = "$rxStart-$rxEnd"
fail
location
silent
show-error
connect-timeout = 20
max-time = 7200
write-out = "http_code=%{http_code}\nsize_download=%{size_download}\nexitcode=%{exitcode}\nspeed_download=%{speed_download}\ntime_total=%{time_total}\n"
"@
    [IO.File]::WriteAllText($rxConfig,$rxText,[Text.UTF8Encoding]::new($false))
    $rxProc=Start-Process -FilePath 'C:\Windows\System32\curl.exe' -ArgumentList @('--config',$rxConfig) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $rxDownload ($rxStem+'.result.txt')) -RedirectStandardError (Join-Path $rxDownload ($rxStem+'.error.txt')) -PassThru
    $rxParts+= [ordered]@{index=$rxIndex;start=$rxStart;end=$rxEnd;expected_bytes=$rxEnd-$rxStart+1;path=$rxPart;pid=$rxProc.Id;process_start_utc=$rxProc.StartTime.ToUniversalTime().ToString('o')}
}
$rxPlan=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');source=$rxUrl;expected_iso_bytes=$rxLength;head_etag=$rxHead.headers.ETag[0];parts=$rxParts;purpose='Self-contained offline Windows driver build; no installation, device/registry/PnP or boot-setting changes.'}
[IO.File]::WriteAllText((Join-Path $rxRoot 'ewdk-download-plan.json'),($rxPlan|ConvertTo-Json -Depth 5)+"`n",[Text.UTF8Encoding]::new($false))
$rxPlan|ConvertTo-Json -Depth 5
