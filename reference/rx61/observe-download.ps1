param([string]$OutputPath)
$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx61'
$rxPlan=Get-Content -Raw -LiteralPath (Join-Path $rxRoot 'ewdk-download-plan.json')|ConvertFrom-Json
$rxRows=@();$rxTotal=0L
foreach($rxPart in $rxPlan.parts){
    $rxProcess=Get-Process -Id $rxPart.pid -ErrorAction SilentlyContinue
    # ConvertFrom-Json in PS7 may create a UTC DateTime; DateTime.Parse would
    # coerce it through local culture and lose its UTC marker. Preserve the kind.
    $rxExpectedStart=([DateTimeOffset]$rxPart.process_start_utc).UtcDateTime
    $rxLive=[bool]$rxProcess -and $rxProcess.ProcessName -eq 'curl' -and [Math]::Abs(($rxProcess.StartTime.ToUniversalTime()-$rxExpectedStart).TotalSeconds) -lt 1
    $rxBytes=if(Test-Path -LiteralPath $rxPart.path){(Get-Item -LiteralPath $rxPart.path).Length}else{0L}
    $rxTotal+=$rxBytes
    $rxStem='part-{0:d2}' -f $rxPart.index
    $rxHeaderPath=Join-Path $rxRoot ('ewdk-download\'+$rxStem+'.headers.txt')
    $rxHeader=if(Test-Path -LiteralPath $rxHeaderPath){Get-Content -Raw -LiteralPath $rxHeaderPath}else{''}
    $rxResult=Get-Content -Raw -LiteralPath (Join-Path $rxRoot ('ewdk-download\'+$rxStem+'.result.txt')) -ErrorAction SilentlyContinue
    $rxRows+=[pscustomobject][ordered]@{index=$rxPart.index;pid=$rxPart.pid;live=$rxLive;bytes=$rxBytes;expected=$rxPart.expected_bytes;range_ok=($rxHeader -match ('(?im)^Content-Range:\s*bytes\s+'+$rxPart.start+'-'+$rxPart.end+'/20002537472\s*$'));http206=($rxHeader -match '(?m)^HTTP/[^ ]+ 206');etag_matches=$rxHeader.Contains($rxPlan.head_etag);result=$rxResult}
}
$rxState=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');total_bytes=$rxTotal;expected_iso_bytes=$rxPlan.expected_iso_bytes;percent=[Math]::Round(100.0*$rxTotal/$rxPlan.expected_iso_bytes,2);live_count=@($rxRows|Where-Object live).Count;parts=$rxRows}
$rxJson=$rxState|ConvertTo-Json -Depth 5
if($OutputPath){if(Test-Path -LiteralPath $OutputPath){throw 'Preserve previous snapshot.'};[IO.File]::WriteAllText($OutputPath,$rxJson+"`n",[Text.UTF8Encoding]::new($false))}
$rxJson
