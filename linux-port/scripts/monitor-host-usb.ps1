param(
    [int]$DurationSeconds = 900,
    [int]$IntervalMilliseconds = 5000,
    [string]$LogPath = "host-usb-heartbeat.txt",
    [string]$NcmAddress = "10.42.0.1",
    [string]$WifiAddress = "192.168.0.114"
)

$ErrorActionPreference = "Continue"
$deadline = (Get-Date).AddSeconds($DurationSeconds)
$sample = 0
$lastArrival = ""
$arrivalChanges = 0
$ncmFailures = 0
$wifiFailures = 0
$pnpFailures = 0

if ($IntervalMilliseconds -lt 200) {
    throw "IntervalMilliseconds must be at least 200"
}

"schema=samurai-host-usb-heartbeat-v1" | Out-File -Encoding utf8 $LogPath
"start=$(Get-Date -Format o) duration=$DurationSeconds interval_ms=$IntervalMilliseconds ncm=$NcmAddress wifi=$WifiAddress" |
    Out-File -Encoding utf8 -Append $LogPath

while ((Get-Date) -lt $deadline) {
    $sample++
    $ncm = Test-Connection -Count 1 -Quiet -ComputerName $NcmAddress
    $wifi = Test-Connection -Count 1 -Quiet -ComputerName $WifiAddress
    $phone = Get-PnpDevice -PresentOnly |
        Where-Object { $_.InstanceId -like "USB\VID_0525&PID_A4A1*" } |
        Select-Object -First 1
    $pnpOk = $phone -and $phone.Status -eq "OK" -and $phone.Problem -eq "CM_PROB_NONE"
    $arrival = ""
    if ($phone) {
        $arrival = (Get-PnpDeviceProperty -InstanceId $phone.InstanceId `
            -KeyName "DEVPKEY_Device_LastArrivalDate" -ErrorAction SilentlyContinue).Data
    }
    if ($lastArrival -and $arrival -and $arrival -ne $lastArrival) {
        $arrivalChanges++
    }
    if ($arrival) { $lastArrival = $arrival }
    if (-not $ncm) { $ncmFailures++ }
    if (-not $wifi) { $wifiFailures++ }
    if (-not $pnpOk) { $pnpFailures++ }

    ("{0} sample={1} ncm={2} wifi={3} pnp={4} problem={5} arrival={6}" -f `
        (Get-Date -Format o), $sample, $ncm, $wifi, $pnpOk, $phone.Problem, $arrival) |
        Out-File -Encoding utf8 -Append $LogPath

    Start-Sleep -Milliseconds $IntervalMilliseconds
}

("end={0} samples={1} ncm_failures={2} wifi_failures={3} pnp_failures={4} arrival_changes={5}" -f `
    (Get-Date -Format o), $sample, $ncmFailures, $wifiFailures, $pnpFailures, $arrivalChanges) |
    Out-File -Encoding utf8 -Append $LogPath
