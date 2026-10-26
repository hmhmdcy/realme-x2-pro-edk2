param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$')][string]$BootId,
    [Parameter(Mandatory=$true)][ValidateSet('initial','initial-retry1','five-ghz')][string]$Phase,
    [Parameter(Mandatory=$true)][ValidateSet(2462,5180)][int]$Frequency
)
$ErrorActionPreference='Stop'
$k98Out='E:\edk2-samurai-out\kernel98'
$k98Ssh=Join-Path $PSScriptRoot '..\kernel72\usb-ssh.ps1'
$k98Scp=Join-Path $PSScriptRoot 'scp-private.ps1'
$k98Directory=Join-Path $k98Out ('traffic-'+$Phase)
if (Test-Path -LiteralPath $k98Directory) {throw 'Use a fresh traffic phase'}
New-Item -ItemType Directory -Path $k98Directory | Out-Null
& $k98Ssh "sh /tmp/k98-start-traffic.sh $BootId $Phase $Frequency" > (Join-Path $k98Out ($Phase+'-traffic-start.log')) 2>&1
if ($LASTEXITCODE -ne 0) {throw 'Listener launch failed'}
if ((Get-Content (Join-Path $k98Out ($Phase+'-traffic-start.log')) -Raw) -notmatch 'TRAFFIC_SERVER_READY') {throw 'Listener completion missing'}
& $k98Scp "root@169.254.42.1:/tmp/k98-$Phase-traffic-dhcp.txt" (Join-Path $k98Directory 'dhcp-lease.txt')
if ($LASTEXITCODE -ne 0) {throw 'Lease download failed'}
$k98Remote=(Get-Content (Join-Path $k98Directory 'dhcp-lease.txt') | Where-Object {$_ -match '^ip='}) -replace '^ip=',''
$k98Prefix=($k98Remote -split '\.')[0..2] -join '.'
$k98Hosts=@(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress.StartsWith($k98Prefix+'.') -and $_.IPAddress -ne $k98Remote})
if ($k98Hosts.Count -ne 1) {throw 'Wi-Fi host address ambiguous'}
& (Join-Path $PSScriptRoot 'wifi-traffic-client.ps1') -PrivateDirectory $k98Directory -LocalAddress $k98Hosts[0].IPAddress > (Join-Path $k98Out ($Phase+'-traffic-client.log')) 2>&1
& $k98Ssh "sha256sum /tmp/k98-$Phase-traffic.bin /tmp/k98-$Phase-traffic-upload.bin > /tmp/k98-$Phase-traffic-sha.txt" > (Join-Path $k98Out ($Phase+'-traffic-check.log')) 2>&1
if ($LASTEXITCODE -ne 0) {throw 'Phone traffic hashing failed'}
& $k98Scp "root@169.254.42.1:/tmp/k98-$Phase-traffic-sha.txt" (Join-Path $k98Out ($Phase+'-traffic-sha.txt'))
if ($LASTEXITCODE -ne 0) {throw 'Phone hashes download failed'}
$k98PhoneSums=Get-Content (Join-Path $k98Out ($Phase+'-traffic-sha.txt'))
$k98Names=@('traffic-download.bin','traffic-upload-source.bin')
for ($k98Index=0;$k98Index -lt 2;$k98Index++) {
    $k98Path=Join-Path $k98Directory $k98Names[$k98Index]
    if ((Get-Item $k98Path).Length -ne 4194304 -or (Get-FileHash $k98Path).Hash.ToLowerInvariant() -ne ($k98PhoneSums[$k98Index] -split ' ')[0]) {throw 'Traffic content verification failed'}
}
'WIFI_BIDIRECTIONAL_4MIB_HASH_PASS'
