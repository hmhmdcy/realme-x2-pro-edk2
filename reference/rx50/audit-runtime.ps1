$ErrorActionPreference = 'Stop'
Add-Type -Path (Join-Path $PSScriptRoot 'EudRxAudit.cs')
$assembly = [IO.Ports.SerialPort].Assembly
$stream = $assembly.GetType('System.IO.Ports.SerialStream')
$flags = [Reflection.BindingFlags]'Instance,Static,Public,NonPublic'
$methods = @(
    $stream.GetProperty('BytesToRead',$flags).GetGetMethod($true),
    [IO.Ports.SerialPort].GetProperty('BytesToRead',$flags).GetGetMethod(),
    [IO.Ports.SerialPort].GetMethod('Read',$flags,$null,[type[]]@([byte[]],[int],[int]),$null),
    $stream.GetNestedType('EventLoopRunner',$flags).GetMethod('CallEvents',$flags)
)
$result = [ordered]@{
    captured_at = (Get-Date).ToString('o')
    ps_version = $PSVersionTable.PSVersion.ToString()
    runtime = [Environment]::Version.ToString()
    assembly = $assembly.FullName
    assembly_path = $assembly.Location
    assembly_sha256 = (Get-FileHash -LiteralPath $assembly.Location).Hash.ToLower()
    methods = @()
}
foreach ($method in $methods) {
    $result.methods += [ordered]@{
        type = $method.DeclaringType.FullName
        name = $method.Name
        calls = @([EudRxAudit]::Calls($method))
    }
}
$result | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'installed-managed-runtime.json') -Encoding UTF8
$result | ConvertTo-Json -Depth 7
$tokens = $null
$errors = $null
[void][Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'eud-terminal-rx-audit.ps1'),[ref]$tokens,[ref]$errors)
if ($errors.Count) { $errors | Format-List; throw 'Terminal parser errors.' }
'Parser clean; no serial port opened.'
