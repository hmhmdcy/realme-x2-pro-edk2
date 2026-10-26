param([switch]$ProbeOnly, [int]$DurationSeconds = 120)
$ErrorActionPreference = 'Stop'
$outputRoot = 'E:\edk2-samurai-out\bluetooth-20261023'
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Devices.Bluetooth.BluetoothAdapter,Windows.Devices.Bluetooth,ContentType=WindowsRuntime] | Out-Null
[Windows.Devices.Bluetooth.GenericAttributeProfile.GattServiceProvider,Windows.Devices.Bluetooth,ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.Streams.DataWriter,Windows.Storage.Streams,ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.Streams.IBuffer,Windows.Storage.Streams,ContentType=WindowsRuntime] | Out-Null
[Windows.Devices.Radios.Radio,Windows.Devices.Radios,ContentType=WindowsRuntime] | Out-Null
$script:asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
} | Select-Object -First 1
function Await-Operation($Operation, [Type]$ResultType) {
    $task = $script:asTask.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    if (-not $task.Wait(15000)) { throw 'WinRT operation timed out' }
    return $task.Result
}
$adapter = Await-Operation ([Windows.Devices.Bluetooth.BluetoothAdapter]::GetDefaultAsync()) ([Windows.Devices.Bluetooth.BluetoothAdapter])
$result = [ordered]@{ adapter_available = $null -ne $adapter; probe_only = [bool]$ProbeOnly }
if ($null -ne $adapter) {
    $result.peripheral_supported = $adapter.IsPeripheralRoleSupported
    $result.central_supported = $adapter.IsCentralRoleSupported
    $result.low_energy_supported = $adapter.IsLowEnergySupported
    $result.classic_supported = $adapter.IsClassicSupported
    $radio = Await-Operation ($adapter.GetRadioAsync()) ([Windows.Devices.Radios.Radio])
    $result.radio_state = $radio.State.ToString()
}
if ($ProbeOnly) {
    $result | ConvertTo-Json | Set-Content -LiteralPath "$outputRoot\windows-adapter-probe-private.json" -Encoding UTF8
    $result | ConvertTo-Json
    exit 0
}
throw 'Use the compiled windows-gatt-peer.cs for a test service. This host currently reports Aborted when advertising; peripheral capability alone is not a working peer.'
