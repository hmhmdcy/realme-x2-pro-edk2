$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel147'
$ssh='E:/RealmeX2Pro edk2/reference/kernel109/usb-ssh-pmos.ps1'
$scp='E:/RealmeX2Pro edk2/reference/kernel109/scp-pmos.ps1'
$bootId=(Get-Content -LiteralPath "$out/embedded-boot-id-private.txt" -Raw).Trim()
if($bootId -notmatch '^[a-f0-9-]{36}$') {throw 'Missing current boot identity'}
& $ssh -Command "test `"`$(uname -v | cut -d' ' -f1)`" = '#147' && test `"`$(cat /proc/sys/kernel/random/boot_id)`" = '$bootId' && test `"`$(cat /proc/sys/kernel/tainted)`" = 0"
$jobs=@(
    @{name='control147'; scene='build:use-vbo=true'; repeat=4; delay=35; bench=$false},
    @{name='novbo147'; scene='build:use-vbo=false'; repeat=2; delay=35; bench=$false},
    @{name='nearest147'; scene='texture:texture-filter=nearest'; repeat=3; delay=35; bench=$false},
    @{name='linear147'; scene='texture:texture-filter=linear'; repeat=3; delay=35; bench=$false},
    @{name='stressbuild147'; scene='build:use-vbo=true:duration=2.0'; repeat=2; delay=35; bench=$true},
    @{name='stresstexture147'; scene='texture:texture-filter=linear:duration=2.0'; repeat=2; delay=35; bench=$true},
    @{name='stressphong147'; scene='shading:shading=phong:duration=2.0'; repeat=2; delay=90; bench=$true}
)
$reports=@()
foreach($job in $jobs) {
    $log="$out/$($job.name)-host-private.log"
    $command="python3 /tmp/k147-run-gpu-probe-next.py $($job.name) --scene '$($job.scene)' --repeat $($job.repeat) --delay $($job.delay)"
    if($job.bench) {$command+=' --benchmark-only'}
    if(!(Test-Path -LiteralPath $log)) {& $ssh -Command $command *> $log}
    $lines=Get-Content -LiteralPath $log
    $result=$lines | Where-Object {$_ -match '^\{"label"'} | Select-Object -Last 1
    if(!$result) {throw "No result receipt for $($job.name); inspect current state"}
    $r=$result | ConvertFrom-Json
    $archive="$out/$($job.name)-private.tar.gz"
    if(!(Test-Path -LiteralPath $archive)) {& $scp -Source "root@169.254.42.1:/tmp/k147-$($job.name)-private.tar.gz" -Destination $archive}
    $receipt='ARCHIVE_SHA256 '+(Get-FileHash -LiteralPath $archive).Hash.ToLowerInvariant()
    if($lines -notcontains $receipt) {throw "$($job.name) archived evidence hash mismatch"}
    if($r.error -or $r.kernel -ne '#147' -or $r.taint -ne '0' -or !$r.desktop_preserved -or !$r.packages_preserved -or !$r.trace_removed) {throw "$($job.name) state check failed"}
    if($r.results.Count -ne $job.repeat -or $r.before.gpu_faults -ne 0 -or $r.after.gpu_faults -ne 0 -or $r.after.warnings -ne 0 -or $r.after.dpu_timeouts -ne 0 -or $r.after.dsi_errors -ne 0) {throw "$($job.name) fault or completion check failed"}
    foreach($case in $r.results) {
        if($case.exit -ne 0 -or !$case.renderer_fd640) {throw "$($job.name) renderer check failed"}
        if(!$job.bench -and !$case.fixed_fbo) {throw "$($job.name) pixel-validation FBO size check failed"}
        if($job.bench) {if(!$case.benchmark_completed) {throw "$($job.name) sustained draw did not complete"}}
        elseif(!$case.pixel_success) {throw "$($job.name) pixel validation failed"}
    }
    $reports+=$r
    $reports | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath "$out/regression-progress-private.json" -Encoding utf8NoBOM
    Write-Output "K147_$($job.name.ToUpperInvariant())_PASS_$($r.results.Count)"
}
Write-Output 'K147_FULL_REGRESSION_BATCH_PASSED'
