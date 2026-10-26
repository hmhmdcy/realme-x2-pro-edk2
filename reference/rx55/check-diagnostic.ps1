$ErrorActionPreference='Stop'
Add-Type -Path (Join-Path $PSScriptRoot 'EudRxAudit.cs')
Add-Type -Path (Join-Path $PSScriptRoot 'EudSerialPerf.cs')
$tokens=$null; $parseErrors=$null
[void][Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'eud-terminal-rx-perf.ps1'),[ref]$tokens,[ref]$parseErrors)
if ($parseErrors.Count) { $parseErrors | Format-List; throw 'Diagnostic parser errors' }
$assembly=[IO.Ports.SerialPort].Assembly
$stream=$assembly.GetType('System.IO.Ports.SerialStream')
$flags=[Reflection.BindingFlags]'Instance,Static,Public,NonPublic'
$constructor=@($stream.GetConstructors($flags) | Where-Object { $_.GetParameters().Count -gt 5 })
$calls=@([EudRxAudit]::Calls($constructor[0]))
if (!($calls -match 'ThreadPool.BindHandle')) { throw 'Installed SerialStream bind path not identified' }
if ([EudSerialPerf]::GetStatsCode -ne 0x1b008c -or [EudSerialPerf]::OverlapSize -ne 32 -or [EudSerialPerf]::EventOffset -ne 24) { throw 'Unexpected x64 IOCTL/OVERLAPPED ABI' }
$result=[ordered]@{utc=(Get-Date).ToUniversalTime().ToString('o'); ps_version=$PSVersionTable.PSVersion.ToString(); runtime=[Environment]::Version.ToString(); assembly_sha256=(Get-FileHash -LiteralPath $assembly.Location).Hash.ToLower(); ctor_calls=$calls; ioctl=[EudSerialPerf]::GetStatsCode; overlap_size=[EudSerialPerf]::OverlapSize; event_offset=[EudSerialPerf]::EventOffset; parser_clean=$true; no_port_opened=$true; retained_pending_perf=[EudSerialPerf]::RetainedCount; sdk_ntddser_sha256=(Get-FileHash -LiteralPath 'C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\shared\ntddser.h').Hash.ToLower()}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'diagnostic-abi.json'),($result | ConvertTo-Json -Depth 5).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
'C# compiled; PowerShell syntax and x64 ABI clean; installed constructor binds handle; no port opened.'
