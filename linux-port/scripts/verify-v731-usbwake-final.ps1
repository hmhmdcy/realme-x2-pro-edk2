[CmdletBinding()]
param(
    [string]$HostAddress = "10.42.0.1",
    [string]$KeyPath = (Join-Path $HOME ".ssh\samurai_id_ed25519"),
    [string]$KnownHostsPath = (Join-Path $HOME ".ssh\samurai_usb_known_hosts"),
    [string]$ExpectedRelease = "7.3.1-rmx1931-samurai-v731-usbwake",
    [string]$PreviousBootId = "9b3f38f2-8233-4425-a20a-d921edc8381b",
    [string]$ExpectedBootSha256 = "b9e9e53129d7d82401385a6f096af8a260a3b3d9e63d5940f7516424f4e6a438",
    [string]$ExpectedLogdumpSha256 = "2d91d2eae5a65e0f38509d02e2fcdb89954063fcdbe372e10424f0a54041db94",
    [string]$ExpectedImageSha256 = "fe9e623a1276a25fe03fa73c55f7cbe345c03b4150f28da730ded29304772ecf",
    [string]$ExpectedDtbSha256 = "9648ca7f8dbba077c7474b2687ccdbf54b6f9c26fd196e50acf007f7d7e9cb52",
    [string]$ExpectedModulesTarSha256 = "32ac83ef4b082eb99c7efc9167a0dd01b695053a53707cf00a7133ce90a16aaf",
    [string]$ImagePath = "E:\edk2-samurai-out\standard-arm64-v731\usbwake-final-20261110\Image",
    [string]$DtbPath = "E:\edk2-samurai-out\standard-arm64-v731\usbwake-final-20261110\sm8150-samurai.dtb",
    [string]$ModulesTarPath = "E:\edk2-samurai-out\standard-arm64-v731\usbwake-final-20261110\modules-7.3.1-rmx1931-samurai-v731-usbwake.tar.gz",
    [string]$FlashScriptPath = "E:\RealmeX2Pro edk2\linux-port\scripts\flash-v731-usbwake-final.ps1",
    [string]$SourceHead = "604f840ec52b24142aff59b5d1a77b6cecb58397",
    [string]$PatchDir = "E:\RealmeX2Pro edk2\linux-port\patches\v7.3.1",
    [string]$ActiveLinkExperimentPatch = "E:\RealmeX2Pro edk2\linux-port\patches\experiments\0009-usb-dwc3-gadget-keep-connect-active-link.patch",
    [string]$ExpectedSleepInhibitorConfSha256 = "9c6ca8ecb04ca042abab57d0f1b44ac2dbcfbc5d9f1962185a1bcfe3b51cab99",
    [int]$ExpectedModuleCount = 773,
    [int]$ExpectedTaint = 512,
    [string]$OutputPath = "E:\edk2-samurai-out\standard-arm64-v731\usbwake-final-20261110\manifest.json"
)

$ErrorActionPreference = "Stop"

function Get-RequiredFileHash {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "required file not found: $Path"
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

$imageHash = Get-RequiredFileHash -Path $ImagePath
$dtbHash = Get-RequiredFileHash -Path $DtbPath
$modulesTarHash = Get-RequiredFileHash -Path $ModulesTarPath
$flashScriptHash = Get-RequiredFileHash -Path $FlashScriptPath
$verifyScriptHash = Get-RequiredFileHash -Path $PSCommandPath

$patchNames = @(
    "0006-usb-dwc3-gadget-keep-connect-sys-sleep.patch",
    "0007-usb-dwc3-qcom-peripheral-wake.patch",
    "0008-arm64-dts-samurai-usb-host-resume.patch"
)
$patches = foreach ($name in $patchNames) {
    [ordered]@{
        name = $name
        sha256 = Get-RequiredFileHash -Path (Join-Path $PatchDir $name)
    }
}
$activeLinkExperimentHash = Get-RequiredFileHash -Path $ActiveLinkExperimentPatch

if ($imageHash -ne $ExpectedImageSha256) {
    throw "Image hash mismatch: expected $ExpectedImageSha256, got $imageHash"
}
if ($dtbHash -ne $ExpectedDtbSha256) {
    throw "DTB hash mismatch: expected $ExpectedDtbSha256, got $dtbHash"
}
if ($modulesTarHash -ne $ExpectedModulesTarSha256) {
    throw "modules archive hash mismatch: expected $ExpectedModulesTarSha256, got $modulesTarHash"
}

$remoteScript = @'
set -eu
release=$(uname -r)
boot_id=$(cat /proc/sys/kernel/random/boot_id)
taint=$(cat /proc/sys/kernel/tainted)
udc_state=$(cat /sys/class/udc/a600000.usb/state)
udc_speed=$(cat /sys/class/udc/a600000.usb/current_speed)
usb0_carrier=$(cat /sys/class/net/usb0/carrier)
usb0_ip=$(ip -4 -o addr show usb0 | awk '{printf "%s ", $4}' | sed 's/ $//')
wlan0_state=$(nmcli -g GENERAL.STATE device show wlan0 2>/dev/null || true)
wlan0_ip=$(ip -4 -br addr show wlan0 | awk '{print $3}')
rc-service usbwake-debug status >/dev/null 2>&1
usbwake_service_rc=$?
usbwake_locks=$(elogind-inhibit --list 2>/dev/null | grep -ci 'USBwake power/NCM guard' || true)
guard_power_rc=0
USBWAKE_GUARD_MODE=power sh /usr/libexec/usbwake-guard || guard_power_rc=$?
guard_ncm_rc=0
USBWAKE_GUARD_MODE=ncm sh /usr/libexec/usbwake-guard || guard_ncm_rc=$?
guard_either_rc=0
USBWAKE_GUARD_MODE=either sh /usr/libexec/usbwake-guard || guard_either_rc=$?
sleep_inhibitor_conf=$(sha256sum /etc/sleep-inhibitor.conf | awk '{print $1}')
boot_hash=$(dd if=/dev/disk/by-partlabel/boot bs=4M status=none | sha256sum | awk '{print $1}')
logdump_hash=$(dd if=/dev/disk/by-partlabel/logdump bs=4M status=none | sha256sum | awk '{print $1}')
module_count=$(find "/lib/modules/$release" -name '*.ko' | wc -l)
modprobe nbd
sleep 2
modprobe -r nbd 2>/dev/null || rmmod nbd
module_probe=ok
printf 'release=%s\n' "$release"
printf 'boot_id=%s\n' "$boot_id"
printf 'taint=%s\n' "$taint"
printf 'udc_state=%s\n' "$udc_state"
printf 'udc_speed=%s\n' "$udc_speed"
printf 'usb0_carrier=%s\n' "$usb0_carrier"
printf 'usb0_ip=%s\n' "$usb0_ip"
printf 'wlan0_state=%s\n' "$wlan0_state"
printf 'wlan0_ip=%s\n' "$wlan0_ip"
printf 'usbwake_service_rc=%s\n' "$usbwake_service_rc"
printf 'usbwake_locks=%s\n' "$usbwake_locks"
printf 'guard_power_rc=%s\n' "$guard_power_rc"
printf 'guard_ncm_rc=%s\n' "$guard_ncm_rc"
printf 'guard_either_rc=%s\n' "$guard_either_rc"
printf 'sleep_inhibitor_conf=%s\n' "$sleep_inhibitor_conf"
printf 'boot_hash=%s\n' "$boot_hash"
printf 'logdump_hash=%s\n' "$logdump_hash"
printf 'module_count=%s\n' "$module_count"
printf 'module_probe=%s\n' "$module_probe"
'@

$capture = $remoteScript | ssh -T -i $KeyPath `
    -o UserKnownHostsFile=$KnownHostsPath `
    -o ConnectTimeout=8 `
    "root@$HostAddress" "sh -s"
if ($LASTEXITCODE -ne 0) {
    throw "remote evidence collection failed with exit code $LASTEXITCODE"
}

$evidence = @{}
foreach ($line in ($capture -split "`r?`n")) {
    if ($line -match "^([^=]+)=(.*)$") {
        $evidence[$Matches[1]] = $Matches[2]
    }
}

$failures = [System.Collections.Generic.List[string]]::new()
function Check-Equal {
    param([string]$Name, $Actual, $Expected)
    if ($Actual -ne $Expected) {
        $failures.Add("$Name expected '$Expected', got '$Actual'")
    }
}

Check-Equal "release" $evidence.release $ExpectedRelease
Check-Equal "udc_state" $evidence.udc_state "configured"
Check-Equal "udc_speed" $evidence.udc_speed "high-speed"
Check-Equal "usb0_carrier" $evidence.usb0_carrier "1"
Check-Equal "usbwake_service_rc" $evidence.usbwake_service_rc "0"
Check-Equal "usbwake_locks" $evidence.usbwake_locks "1"
Check-Equal "guard_power_rc" $evidence.guard_power_rc "254"
Check-Equal "guard_ncm_rc" $evidence.guard_ncm_rc "254"
Check-Equal "guard_either_rc" $evidence.guard_either_rc "254"
Check-Equal "sleep_inhibitor_conf" $evidence.sleep_inhibitor_conf $ExpectedSleepInhibitorConfSha256
Check-Equal "boot_hash" $evidence.boot_hash $ExpectedBootSha256
Check-Equal "logdump_hash" $evidence.logdump_hash $ExpectedLogdumpSha256
Check-Equal "module_count" $evidence.module_count "$ExpectedModuleCount"
Check-Equal "module_probe" $evidence.module_probe "ok"
Check-Equal "taint" $evidence.taint "$ExpectedTaint"

if ([string]::IsNullOrWhiteSpace($evidence.boot_id) -or $evidence.boot_id -eq $PreviousBootId) {
    $failures.Add("boot_id did not change from $PreviousBootId")
}
if ([string]::IsNullOrWhiteSpace($evidence.usb0_ip)) {
    $failures.Add("usb0 has no IPv4 address")
}

$manifest = [ordered]@{
    schema = "samurai-usbwake-final-v1"
    verified_at = (Get-Date).ToString("o")
    device = "realme X2 Pro (RMX1931), SM8150"
    release = $evidence.release
    boot_id_before = $PreviousBootId
    boot_id_after = $evidence.boot_id
    udc_state = $evidence.udc_state
    udc_speed = $evidence.udc_speed
    usb0_carrier = $evidence.usb0_carrier
    usb0_ip = $evidence.usb0_ip
    wlan0_state = $evidence.wlan0_state
    wlan0_ip = $evidence.wlan0_ip
    taint = $evidence.taint
    taint_note = "512 is the pre-existing TAINT_WARN bit from boot-time clk warnings; it was also 512 before this deployment"
    boot_sha256 = $evidence.boot_hash
    logdump_sha256 = $evidence.logdump_hash
    image_sha256 = $imageHash
    dtb_sha256 = $dtbHash
    modules_archive_sha256 = $modulesTarHash
    flash_script_sha256 = $flashScriptHash
    verify_script_sha256 = $verifyScriptHash
    source_head = $SourceHead
    build_command = "make -j12 O=/home/cy122/samurai-v731-usbwake-final-build-20261110 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- LOCALVERSION=-usbwake Image modules dtbs"
    patches = @($patches)
    experimental_active_link_patch_sha256 = $activeLinkExperimentHash
    experimental_active_link_deployed = $false
    module_count = [int]$evidence.module_count
    module_probe = $evidence.module_probe
    usbwake_debug_service_started = ($evidence.usbwake_service_rc -eq "0")
    usbwake_sleep_locks = [int]$evidence.usbwake_locks
    guard_power_rc = [int]$evidence.guard_power_rc
    guard_ncm_rc = [int]$evidence.guard_ncm_rc
    guard_either_rc = [int]$evidence.guard_either_rc
    official_sleep_inhibitor_conf_sha256 = $evidence.sleep_inhibitor_conf
    host_resume_verified = $false
    u0_usb_wake_verified = $false
    deployed_mode = "U3-only keep-connect plus debug-only USBwake sleep inhibitor"
    policy_scope = "Debug helper; not installed by samurai-platform"
    failures = @($failures)
}

if ($failures.Count -ne 0) {
    $manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $OutputPath -Encoding utf8
    throw ($failures -join "; ")
}

$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $OutputPath -Encoding utf8
$manifest | ConvertTo-Json -Depth 5
