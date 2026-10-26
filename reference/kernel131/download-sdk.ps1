$ErrorActionPreference='Stop'
$dir='E:/edk2-samurai-out/kernel131/native-sdk'
$index=Get-Content -LiteralPath "$dir/sdk-index-selected-private.json" -Raw | ConvertFrom-Json -AsHashtable
$wanted=@('gcc','g++','binutils','musl','musl-dev','libgcc-static','linux-headers','libstdc++-dev','mpc1','isl26','libpng-dev','libjpeg-turbo-dev','wayland-dev','wayland-protocols','mesa-dev')
$results=$wanted | ForEach-Object -Parallel {
    $entry=($using:index)[$_]
    if (-not $entry) {throw "Missing package $_"}
    $name=$entry.P+'-'+$entry.V+'.apk'
    $path=Join-Path $using:dir $name
    if (-not (Test-Path -LiteralPath $path) -or (Get-Item -LiteralPath $path).Length -ne [long]$entry.S) {
        & curl.exe --silent --show-error --fail --location --retry 2 --retry-all-errors --max-time 75 --output ($path+'.download') ('https://dl-cdn.alpinelinux.org/alpine/edge/main/aarch64/'+$name)
        if ($LASTEXITCODE -ne 0) { throw "curl failed for $name" }
        if ((Get-Item -LiteralPath ($path+'.download')).Length -ne [long]$entry.S) {throw "Package size mismatch $name"}
        Move-Item -LiteralPath ($path+'.download') -Destination $path -Force
    }
    [pscustomobject]@{Package=$name; Bytes=(Get-Item -LiteralPath $path).Length; SHA256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower()}
} -ThrottleLimit 3
if (@($results).Count -ne $wanted.Count) {throw 'Incomplete SDK downloads'}
$results | ConvertTo-Json | Set-Content -LiteralPath "$dir/sdk-download-receipts.json" -Encoding utf8
Write-Output 'SDK_DOWNLOADS_TERMINAL'
