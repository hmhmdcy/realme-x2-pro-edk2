from pathlib import Path
import hashlib

root = Path(__file__).resolve().parent
source = root.parent / 'rx50'
root.mkdir(exist_ok=True)
probe = (source / 'EudRxAudit.cs').read_bytes()
assert hashlib.sha256(probe).hexdigest() == '123034acbff502cb567cceff1eb09df19afaa28f24fa6aa3e06efe7004f12969'
(root / 'EudRxAudit.cs').write_bytes(probe.replace(b'Calls(MethodInfo method)', b'Calls(MethodBase method)'))
original = (source / 'eud-terminal-rx-audit.ps1').read_bytes()
assert hashlib.sha256(original).hexdigest() == 'f337b789c0a7cf69ce8d0d83d4dc64ef8106002a29f836290204b7690f7d46b6'
text = original.decode('utf-8').replace('\r\n', '\n')

def replace(old, new):
    global text
    assert text.count(old) == 1, (old, text.count(old))
    text = text.replace(old, new)

replace('$rxProbe = $null', '$rxProbe = $null\n$perfProbe = $null')
replace("if ($RxAudit) { Add-Type -Path (Join-Path $PSScriptRoot 'EudRxAudit.cs') }", """if (!$RxAudit) { throw 'RX55 diagnostic requires -RxAudit.' }
Add-Type -Path (Join-Path $PSScriptRoot 'EudRxAudit.cs')
Add-Type -Path (Join-Path $PSScriptRoot 'EudSerialPerf.cs')""")
replace('function Show-EudText', """function Write-PerfAudit([string]$reason) {
    $begin = $clock.ElapsedMilliseconds
    try {
        $perf = $perfProbe.Sample()
        $queueSample = $rxProbe.Sample()
        Write-RxAudit @{ event='perf'; reason=$reason; ms_begin=$begin; ms=$clock.ElapsedMilliseconds;
            perf=$perf; raw_position=$raw.Position; queued_input=$queue.Count;
            pending_input=($null -ne $state.Pending); buffered_wire=$wire.Count; queue=$queueSample }
        if ($queueSample.errors) {
            $auditState.error_samples++
            $auditState.error_mask = $auditState.error_mask -bor [int]$queueSample.errors
        }
        Drain-RxErrors
    } catch {
        Write-RxAudit @{ event='perf_error'; reason=$reason; ms_begin=$begin;
            ms=$clock.ElapsedMilliseconds; message=$_.Exception.Message;
            stalled=$perfProbe.HasStalledQuery; raw_position=$raw.Position }
        throw
    }
}

function Show-EudText""")
replace('$rxProbe = [EudRxAudit]::new($sp,$clock)', '$rxProbe = [EudRxAudit]::new($sp,$clock)\n        $perfProbe = [EudSerialPerf]::new($sp)')
replace('parity=$sp.Parity.ToString(); audit_max_seconds=$AuditMaxSeconds }', """parity=$sp.Parity.ToString(); audit_max_seconds=$AuditMaxSeconds;
            perf_probe_sha256=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'EudSerialPerf.cs')).Hash.ToLower();
            perf_ioctl=[EudSerialPerf]::GetStatsCode; overlap_size=[EudSerialPerf]::OverlapSize;
            overlap_event_offset=[EudSerialPerf]::EventOffset; perf_own_event_low_bit=$true }
        Write-PerfAudit 'opened-before-sync'""")
replace('if ($code -eq 29) { $running = $false; break }', """if ($code -eq 29) { $running = $false; break }
                if ($code -eq 16) {
                    if ($queue.Count -or $null -ne $state.Pending -or $state.Synchronizing) {
                        Write-RxAudit @{ event='perf_manual_rejected'; ms=$clock.ElapsedMilliseconds;
                            queued_input=$queue.Count; pending_input=($null -ne $state.Pending) }
                        [Console]::Error.WriteLine('[host] Ctrl-P snapshot requires idle input and completed sync.')
                    } else {
                        Receive-Eud
                        Write-PerfAudit 'manual-idle'
                        [Console]::Error.WriteLine('[host] Read-only GET_STATS snapshot saved.')
                    }
                    continue
                }""")
replace('} finally {\n    try { if ($sp.IsOpen) { $sp.Close() } } finally {', """} finally {
    try { try {
        if ($sp.IsOpen -and $perfProbe -and !$perfProbe.HasStalledQuery) {
            try { Receive-Eud; Write-PerfAudit 'before-close' }
            catch { [Console]::Error.WriteLine('[host] Final perf query failed; closing serial owner.') }
        }
    } finally { if ($sp.IsOpen) { $sp.Close() } }
    } finally {
        if ($perfProbe) { $perfProbe.Dispose() }""")
replace('serial_is_open=$sp.IsOpen; probe_detached=($null -ne $rxProbe);', 'serial_is_open=$sp.IsOpen; probe_detached=($null -ne $rxProbe);\n                perf_probe_disposed=($null -ne $perfProbe); retained_pending_perf=[EudSerialPerf]::RetainedCount;')
replace('[host] $Port opened; Ctrl-] exits, Ctrl-C interrupts phone, Ctrl-U clears line.', '[host] $Port opened; Ctrl-] exits, Ctrl-P snapshots GET_STATS, Ctrl-C interrupts phone, Ctrl-U clears line.')
(root / 'eud-terminal-rx-perf.ps1').write_bytes(text.encode('utf-8'))
for name in ('EudRxAudit.cs', 'EudSerialPerf.cs', 'eud-terminal-rx-perf.ps1'):
    print(name, hashlib.sha256((root / name).read_bytes()).hexdigest())
