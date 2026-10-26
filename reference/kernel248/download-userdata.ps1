$ErrorActionPreference='Stop'
$taskPrivate='E:/edk2-samurai-out/kernel248'
$taskConfig=Get-Content -LiteralPath "$taskPrivate/userdata-server-config-private.json" -Raw | ConvertFrom-Json
$taskDest="$taskPrivate/"+$taskConfig.output_filename
if (Test-Path -LiteralPath $taskDest) {throw 'Userdata backup output already exists; inspect before selecting a new attempt'}
if ((Get-PSDrive E).Free -lt 40GB) {throw 'Insufficient backup and validation reserve'}
$taskUrl='http://'+$taskConfig.bind_address+':'+$taskConfig.port+'/'+$taskConfig.token+'/userdata.pcl.zst'
& C:/Windows/System32/curl.exe --disable --noproxy '*' --fail --silent --show-error --connect-timeout 10 --max-time 7200 --speed-time 120 --speed-limit 1024 --output $taskDest $taskUrl 2> "$taskPrivate/userdata-download-private.log"
$taskResult=$LASTEXITCODE
$taskBytes=0
if (Test-Path -LiteralPath $taskDest) {$taskBytes=(Get-Item -LiteralPath $taskDest).Length}
[pscustomobject]@{curl_exit_code=$taskResult;received_bytes=$taskBytes;not_yet_verified=$true} | ConvertTo-Json | Set-Content -LiteralPath "$taskPrivate/userdata-download-result-private.json"
'Userdata stream ended; source completion and hash verification are still required'
