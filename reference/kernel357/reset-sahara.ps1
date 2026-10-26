# A single Sahara RESET_REQ (7,length8), expecting RESET_RSP (8).
# bkerler/edl edlclient/Library/sahara.py cmd_reset(), constants in sahara_defs.py.
$ErrorActionPreference='Stop'
$taskOut='E:/edk2-samurai-out/kernel357'
$taskMarker="$taskOut/sahara-reset-r1-private.json"
if (Test-Path -LiteralPath $taskMarker) {throw 'Inspect the existing Sahara reset result instead of repeating it'}
$taskHello=[IO.File]::ReadAllBytes("$taskOut/sahara-first-read-private.bin")
if ($taskHello.Length -ne 48 -or [BitConverter]::ToUInt32($taskHello,0) -ne 1 -or [BitConverter]::ToUInt32($taskHello,4) -ne 48) {throw 'Observed Sahara HELLO required'}
$taskDevice=@(Get-PnpDevice -PresentOnly -Class Ports | Where-Object {$_.FriendlyName -eq 'Qualcomm HS-USB QDLoader 9008 (COM16)'})
if ($taskDevice.Count -ne 1) {throw 'The observed 9008 endpoint is no longer present'}
$taskState=@{utc=(Get-Date).ToUniversalTime().ToString('o');request_attempted=$false;request_write_returned=$false;response_command=$null;response_length=$null;reset_acknowledged=$false;partition_commands_sent=0;programmer_uploaded=$false}
$taskSerial=[IO.Ports.SerialPort]::new('COM16',115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$taskSerial.ReadTimeout=1000;$taskSerial.WriteTimeout=1000
$taskBuffer=[byte[]]::new(1024);$taskReceived=0
try {
    $taskSerial.Open()
    $taskState.request_attempted=$true;$taskState | ConvertTo-Json | Set-Content $taskMarker -Encoding utf8NoBOM
    $taskSerial.Write([byte[]]@(7,0,0,0,8,0,0,0),0,8)
    $taskState.request_write_returned=$true
    for($taskTry=0;$taskTry -lt 3 -and $taskReceived -lt 8;$taskTry++) {
        try {$taskReceived+=$taskSerial.Read($taskBuffer,$taskReceived,$taskBuffer.Length-$taskReceived)} catch [TimeoutException] {}
    }
    if ($taskReceived -gt 0) {[IO.File]::WriteAllBytes("$taskOut/sahara-reset-response-private.bin",[byte[]]$taskBuffer[0..($taskReceived-1)])}
    if ($taskReceived -ge 8) {
        $taskState.response_command=[BitConverter]::ToUInt32($taskBuffer,0)
        $taskState.response_length=[BitConverter]::ToUInt32($taskBuffer,4)
        $taskState.reset_acknowledged=$taskState.response_command -eq 8 -and $taskState.response_length -eq 8
    }
} catch { $taskState.error=$_.Exception.Message;throw } finally {
    if ($taskSerial.IsOpen) {$taskSerial.Close()};$taskSerial.Dispose()
    $taskState | ConvertTo-Json | Set-Content $taskMarker -Encoding utf8NoBOM
}
$taskState | ConvertTo-Json
