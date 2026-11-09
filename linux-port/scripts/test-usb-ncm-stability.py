#!/usr/bin/env python3
"""Run a bounded, debug-only USB NCM SSH/SCP stability matrix.

The harness holds a transient elogind sleep block for the test process and
releases it on exit. It is not installed and never writes a persistent
sleep-inhibitor or PowerDevil policy.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SIZES = "64K,256K,1M,4M"
DEFAULT_REMOTE_ROOT = "/tmp/samurai-ncm-stability"
REMOTE_INHIBIT_PID = "/tmp/samurai-ncm-inhibit.pid"
REMOTE_INHIBIT_LOG = "/tmp/samurai-ncm-inhibit.log"
REMOTE_HASH_RE = re.compile(r"sha=([0-9a-f]{64})")
REMOTE_SIZE_RE = re.compile(r"size=(\d+)")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_size(value: str) -> int:
    match = re.fullmatch(r"(\d+)([KMG]?)", value.strip(), re.IGNORECASE)
    if not match:
        raise argparse.ArgumentTypeError(f"invalid size: {value}")
    number = int(match.group(1))
    suffix = match.group(2).upper()
    multiplier = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}[suffix]
    result = number * multiplier
    if result <= 0:
        raise argparse.ArgumentTypeError("size must be positive")
    return result


def parse_sizes(value: str) -> tuple[int, ...]:
    sizes = tuple(parse_size(part) for part in value.split(",") if part.strip())
    if not sizes:
        raise argparse.ArgumentTypeError("at least one size is required")
    return sizes


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def tail_text(value: bytes | str | None, limit: int = 4000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    value = value.strip()
    return value[-limit:]


class CommandResult:
    def __init__(
        self,
        argv: list[str],
        returncode: int,
        stdout: bytes,
        stderr: bytes,
        duration_seconds: float,
        timed_out: bool,
    ) -> None:
        self.argv = argv
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.duration_seconds = duration_seconds
        self.timed_out = timed_out

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def record(self) -> dict[str, Any]:
        return {
            "argv": self.argv,
            "returncode": self.returncode,
            "timed_out": self.timed_out,
            "duration_seconds": round(self.duration_seconds, 3),
            "stdout": tail_text(self.stdout),
            "stderr": tail_text(self.stderr),
        }


def run_process(
    argv: list[str],
    timeout: float,
    cwd: Path | None = None,
) -> CommandResult:
    started = time.monotonic()
    try:
        with contextlib.ExitStack() as stack:
            process = stack.enter_context(
                subprocess.Popen(
                    argv,
                    cwd=str(cwd) if cwd else None,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            )
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                try:
                    stdout, stderr = process.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    stdout, stderr = b"", b"process did not exit after kill"
            returncode = process.returncode
            if returncode is None:
                returncode = -1
    except OSError as error:
        return CommandResult(
            argv=argv,
            returncode=127,
            stdout=b"",
            stderr=str(error).encode("utf-8", "replace"),
            duration_seconds=time.monotonic() - started,
            timed_out=False,
        )
    return CommandResult(
        argv=argv,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=time.monotonic() - started,
        timed_out=timed_out,
    )


class Link:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.destination = f"{args.user}@{args.host}"
        self.ssh_base = self._build_base(False)
        self.scp_base = self._build_base(True)

    def _build_base(self, scp: bool) -> list[str]:
        args = self.args
        program = args.scp if scp else args.ssh
        known_hosts = str(args.known_hosts).replace("\\", "/")
        base = [program, "-F", "none"]
        if scp:
            base += ["-O", "-P", str(args.port)]
        else:
            base += ["-p", str(args.port)]
        base += [
            "-o",
            f"UserKnownHostsFile={known_hosts}",
            "-o",
            "GlobalKnownHostsFile=none",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "BatchMode=yes",
            "-o",
            "Compression=no",
            "-o",
            "ConnectTimeout=5",
            "-o",
            "ServerAliveInterval=5",
            "-o",
            "ServerAliveCountMax=2",
            "-o",
            "TCPKeepAlive=yes",
            "-o",
            "LogLevel=ERROR",
        ]
        if args.identity:
            identity = str(args.identity).replace("\\", "/")
            base += ["-i", identity, "-o", "IdentitiesOnly=yes"]
            base += ["-o", "PasswordAuthentication=no"]
        return base

    def ssh(self, command: str, timeout: float) -> CommandResult:
        argv = [
            *self.ssh_base,
            self.destination,
            f"sh -lc {shlex.quote(command)}",
        ]
        return run_process(argv, timeout)

    def scp(
        self,
        source: str,
        destination: str,
        timeout: float,
        cwd: Path | None = None,
    ) -> CommandResult:
        argv = [*self.scp_base, source, destination]
        return run_process(argv, timeout, cwd=cwd)


def start_sleep_inhibitor(link: Link, seconds: int, timeout: float) -> CommandResult:
    """Hold a standard elogind block lock for the full unattended run."""
    script = f"""
set -eu
command -v elogind-inhibit >/dev/null 2>&1 || {{
	echo 'elogind-inhibit is not installed' >&2
	exit 127
}}
rm -f {REMOTE_INHIBIT_PID} {REMOTE_INHIBIT_LOG}
nohup elogind-inhibit --what=sleep --who=samurai-ncm-stability \
	--why='unattended USB NCM stability matrix' --mode=block sleep {seconds} \
	>{REMOTE_INHIBIT_LOG} 2>&1 </dev/null &
echo $! >{REMOTE_INHIBIT_PID}
sleep 1
pid=$(cat {REMOTE_INHIBIT_PID})
kill -0 "$pid"
elogind-inhibit --list 2>/dev/null | grep -q 'samurai-ncm-stability'
"""
    return link.ssh(script, timeout)


def stop_sleep_inhibitor(link: Link, timeout: float) -> CommandResult:
    """Release the inhibitor, including its detached process group."""
    script = f"""
if [ -r {REMOTE_INHIBIT_PID} ]; then
	pid=$(cat {REMOTE_INHIBIT_PID})
	pkill -TERM -P "$pid" 2>/dev/null || true
	kill -TERM "$pid" 2>/dev/null || true
	sleep 0.2
	kill -KILL "$pid" 2>/dev/null || true
fi
rm -f {REMOTE_INHIBIT_PID}
"""
    return link.ssh(script, timeout)


def remote_hash_command(path: str) -> str:
    quoted = shlex.quote(path)
    return (
        f"printf 'size='; stat -c %s {quoted}; "
        f"printf '\\nsha='; sha256sum {quoted} | cut -d' ' -f1; printf '\\n'"
    )


def parse_hash_and_size(output: bytes) -> tuple[str, int | None]:
    text = output.decode("utf-8", "replace")
    hash_match = REMOTE_HASH_RE.search(text)
    size_match = REMOTE_SIZE_RE.search(text)
    size = int(size_match.group(1)) if size_match else None
    return (hash_match.group(1) if hash_match else "", size)


def parse_snapshot(output: bytes) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in output.decode("utf-8", "replace").splitlines():
        if line.startswith("---") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def device_snapshot(link: Link, timeout: float) -> dict[str, Any]:
    script = (
        "printf 'release='; uname -r; "
        "printf 'boot_id='; cat /proc/sys/kernel/random/boot_id; "
        "printf 'taint='; cat /proc/sys/kernel/tainted; "
        "printf 'cmdline='; cat /proc/cmdline; "
        "for d in /sys/class/udc/*; do "
        "[ -e \"$d\" ] || continue; "
        "printf 'udc_%s=' \"${d##*/}\"; cat \"$d/state\"; done; "
        "ifname=$(cat /sys/kernel/config/usb_gadget/samurai/functions/"
        "ncm.usb0/ifname 2>/dev/null || echo usb0); "
        "printf 'carrier='; cat \"/sys/class/net/$ifname/carrier\" "
        "2>/dev/null || true; "
        "printf 'bound='; cat /sys/kernel/config/usb_gadget/samurai/UDC 2>/dev/null || true; "
        "printf 'interface=%s\\n' \"$ifname\"; "
        "printf '\\n--- ip link ---\\n'; ip -s link show \"$ifname\" 2>/dev/null || true; "
        "printf '\\n--- dmesg tail ---\\n'; dmesg 2>/dev/null | tail -n 160 || true"
    )
    result = link.ssh(script, timeout)
    record = result.record()
    record["parsed"] = parse_snapshot(result.stdout)
    return record


def host_snapshot(outdir: Path, phase: str) -> dict[str, Any]:
    if os.name != "nt":
        return {"supported": False, "reason": "Windows host snapshot only"}
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        return {"supported": False, "reason": "PowerShell not found"}
    script = r'''
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$ErrorActionPreference = 'SilentlyContinue'
$cutoff = (Get-Date).AddHours(-2)
$usbPnp = @(
    Get-PnpDevice -PresentOnly |
        Where-Object { $_.InstanceId -like 'USB\*' } |
        Select-Object Status,Class,FriendlyName,InstanceId,Problem,ProblemDescription,Service,Present
)
$problemPnp = @(
    Get-PnpDevice -PresentOnly |
        Where-Object { $_.Status -ne 'OK' -or $_.Problem -ne 'CM_PROB_NONE' } |
        Select-Object Status,Class,FriendlyName,InstanceId,Problem,ProblemDescription,Service,Present
)
$win32Pnp = @(
    Get-CimInstance Win32_PnPEntity |
        Where-Object { $_.PNPDeviceID -like 'USB\*' } |
        Select-Object Name,PNPDeviceID,Status,ConfigManagerErrorCode,Service
)
$adapters = @(
    Get-NetAdapter |
        Select-Object Name,InterfaceDescription,Status,LinkSpeed,MacAddress,ifIndex,PnPDeviceID
)
$adapterStats = @(
    Get-NetAdapter | ForEach-Object {
        $stats = $_ | Get-NetAdapterStatistics
        [pscustomobject]@{
            Name = $_.Name
            ifIndex = $_.ifIndex
            ReceivedBytes = $stats.ReceivedBytes
            ReceivedUnicastPackets = $stats.ReceivedUnicastPackets
            ReceivedDiscardedPackets = $stats.ReceivedDiscardedPackets
            ReceivedPacketErrors = $stats.ReceivedPacketErrors
            OutboundBytes = $stats.OutboundBytes
            OutboundUnicastPackets = $stats.OutboundUnicastPackets
            OutboundDiscardedPackets = $stats.OutboundDiscardedPackets
            OutboundPacketErrors = $stats.OutboundPacketErrors
        }
    }
)
$ipv4 = @(
    Get-NetIPAddress -AddressFamily IPv4 |
        Select-Object InterfaceAlias,IPAddress,PrefixLength,AddressState,ifIndex
)
$neighbors = @(
    Get-NetNeighbor -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -like '169.254.*' } |
        Select-Object InterfaceAlias,IPAddress,LinkLayerAddress,State,ifIndex
)
$events = @(
    Get-WinEvent -FilterHashtable @{ LogName = 'System'; StartTime = $cutoff } -MaxEvents 500 |
        Where-Object { $_.ProviderName -match 'USB|PnP|DriverFrameworks|Ncm|Cdc|Net' } |
        Select-Object -First 200 TimeCreated,ProviderName,Id,LevelDisplayName,
            @{ N = 'Message'; E = {
                if ($_.Message) {
                    $_.Message.Substring(0, [Math]::Min(2000, $_.Message.Length))
                } else {
                    ''
                }
            } }
)
[pscustomobject]@{
    captured_utc = (Get-Date).ToUniversalTime().ToString('o')
    usb_pnp = $usbPnp
    problem_pnp = $problemPnp
    win32_pnp = $win32Pnp
    net_adapters = $adapters
    net_statistics = $adapterStats
    ipv4 = $ipv4
    link_local_neighbors = $neighbors
    recent_events = $events
} | ConvertTo-Json -Depth 6
'''
    result = run_process(
        [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
        60,
    )
    path = outdir / f"host-snapshot-{phase}.json"
    path.write_bytes(result.stdout or b"null\n")
    return {
        "supported": True,
        "ok": result.ok,
        "path": str(path),
        **result.record(),
    }


def generate_host_file(path: Path, size: int) -> str:
    remaining = size
    with path.open("wb") as stream:
        while remaining:
            block = os.urandom(min(1024 * 1024, remaining))
            stream.write(block)
            remaining -= len(block)
    return sha256_file(path)


def prepare_remote_file(
    link: Link,
    remote_root: str,
    name: str,
    size: int,
    timeout: float,
) -> tuple[CommandResult, str, int | None]:
    path = f"{remote_root}/{name}"
    block_size = 1024 * 1024 if size % (1024 * 1024) == 0 else 1024
    block_count = size // block_size
    command = (
        f"mkdir -p {shlex.quote(remote_root)}; "
        f"dd if=/dev/urandom of={shlex.quote(path)} "
        f"bs={block_size} count={block_count}; "
        f"sync; {remote_hash_command(path)}"
    )
    result = link.ssh(command, timeout)
    if not result.ok:
        return result, "", None
    sha, actual_size = parse_hash_and_size(result.stdout)
    return result, sha, actual_size


def transfer_case(
    link: Link,
    args: argparse.Namespace,
    outdir: Path,
    run_root: str,
    direction: str,
    size: int,
    iteration: int,
    host_file: Path | None,
) -> dict[str, Any]:
    stem = f"{direction}-{size}-{iteration}"
    remote_path = f"{run_root}/{stem}.bin"
    record: dict[str, Any] = {
        "direction": direction,
        "size": size,
        "iteration": iteration,
        "remote_path": remote_path,
        "started_utc": utc_now(),
    }

    if direction == "upload":
        if host_file is None:
            raise ValueError("upload requires a host file")
        expected_sha = sha256_file(host_file)
        record["expected_sha256"] = expected_sha
        transfer = link.scp(
            host_file.name,
            f"{link.destination}:{remote_path}",
            args.timeout,
            cwd=outdir,
        )
        record["transfer"] = transfer.record()
        check = link.ssh(remote_hash_command(remote_path), args.probe_timeout)
        actual_sha, actual_size = parse_hash_and_size(check.stdout)
        record["verification"] = check.record()
        record["actual_sha256"] = actual_sha
        record["remote_bytes"] = actual_size
        record["bytes"] = host_file.stat().st_size
        passed = (
            transfer.ok
            and check.ok
            and actual_sha == expected_sha
            and actual_size == size
        )
    else:
        prepare, expected_sha, prepared_size = prepare_remote_file(
            link,
            run_root,
            stem + "-source.bin",
            size,
            args.timeout,
        )
        record["prepare"] = prepare.record()
        record["expected_sha256"] = expected_sha
        record["remote_bytes"] = prepared_size
        if not prepare.ok or not expected_sha:
            record["passed"] = False
            record["error"] = "remote file preparation failed"
            record["finished_utc"] = utc_now()
            return record
        local_path = outdir / f"{stem}.bin"
        local_path.unlink(missing_ok=True)
        transfer = link.scp(
            f"{link.destination}:{run_root}/{stem}-source.bin",
            local_path.name,
            args.timeout,
            cwd=outdir,
        )
        record["transfer"] = transfer.record()
        if local_path.is_file():
            actual_sha = sha256_file(local_path)
            actual_size = local_path.stat().st_size
        else:
            actual_sha = ""
            actual_size = 0
        record["actual_sha256"] = actual_sha
        record["bytes"] = actual_size
        passed = (
            transfer.ok
            and prepared_size == size
            and actual_size == size
            and actual_sha == expected_sha
        )

    record["passed"] = passed
    record["finished_utc"] = utc_now()
    return record


def run_heartbeat(
    link: Link,
    args: argparse.Namespace,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    started = time.monotonic()
    samples: list[dict[str, Any]] = []
    consecutive_failures = 0
    first_failure: dict[str, Any] | None = None
    while time.monotonic() - started < args.heartbeat_seconds:
        result = link.ssh("true", args.probe_timeout)
        sample = {
            "utc": utc_now(),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "passed": result.ok,
            "returncode": result.returncode,
            "timed_out": result.timed_out,
            "duration_seconds": round(result.duration_seconds, 3),
        }
        if not result.ok:
            sample["stderr"] = tail_text(result.stderr, 1000)
            consecutive_failures += 1
            if first_failure is None:
                first_failure = sample
        else:
            consecutive_failures = 0
        samples.append(sample)
        events.append({"kind": "heartbeat", **sample})
        if consecutive_failures >= args.heartbeat_stop_after:
            break
        time.sleep(max(0.0, args.heartbeat_interval))
    return {
        "requested_seconds": args.heartbeat_seconds,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "samples": samples,
        "passed": not first_failure,
        "first_failure": first_failure,
    }


def choose_default(path: str) -> Path | None:
    candidate = Path(path)
    return candidate if candidate.is_file() else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        default="10.42.0.1",
        help="USB NCM endpoint; use 169.254.42.1 only for a pre-DHCP image.",
    )
    parser.add_argument("--user", default="root")
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--ssh", default=shutil.which("ssh") or "ssh")
    parser.add_argument("--scp", default=shutil.which("scp") or "scp")
    parser.add_argument("--identity", type=Path)
    parser.add_argument("--known-hosts", type=Path)
    parser.add_argument("--sizes", type=parse_sizes, default=parse_sizes(DEFAULT_SIZES))
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument(
        "--directions",
        choices=("both", "upload", "download"),
        default="both",
    )
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--probe-timeout", type=float, default=15)
    parser.add_argument("--heartbeat-seconds", type=int, default=0)
    parser.add_argument("--heartbeat-interval", type=float, default=1.0)
    parser.add_argument("--heartbeat-stop-after", type=int, default=3)
    parser.add_argument(
        "--sleep-inhibit-seconds",
        type=int,
        default=7200,
        help="Hold a standard elogind sleep block for this many seconds.",
    )
    parser.add_argument(
        "--no-sleep-inhibit",
        action="store_true",
        help="Do not hold the standard elogind sleep lock.",
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--keep-remote", action="store_true")
    parser.add_argument("--host-snapshot", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.iterations <= 0:
        parser.error("--iterations must be positive")
    if args.timeout <= 0 or args.probe_timeout <= 0:
        parser.error("timeouts must be positive")
    if args.heartbeat_seconds < 0:
        parser.error("--heartbeat-seconds cannot be negative")
    if args.heartbeat_seconds and args.heartbeat_interval <= 0:
        parser.error("--heartbeat-interval must be positive")
    if args.heartbeat_stop_after <= 0:
        parser.error("--heartbeat-stop-after must be positive")
    if args.sleep_inhibit_seconds <= 0:
        parser.error("--sleep-inhibit-seconds must be positive")

    if args.identity is None:
        args.identity = choose_default("E:/edk2-samurai-out/kernel72/id_ed25519")
    if args.known_hosts is None:
        args.known_hosts = (
            choose_default("E:/edk2-samurai-out/kernel72/known_hosts")
            or choose_default(str(Path.home() / ".ssh" / "known_hosts"))
        )
    if not args.dry_run:
        if args.identity is None or not args.identity.is_file():
            print("identity file not found; pass --identity", file=sys.stderr)
            return 2
        if args.known_hosts is None or not args.known_hosts.is_file():
            print("known-hosts file not found; pass --known-hosts", file=sys.stderr)
            return 2

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = args.output_dir or (Path.cwd() / f"ncm-stability-{stamp}")
    outdir = outdir.resolve()
    if outdir.exists() and any(outdir.iterdir()) and not args.force:
        print(f"output directory is not empty: {outdir}", file=sys.stderr)
        return 2
    outdir.mkdir(parents=True, exist_ok=True)
    events_path = outdir / "events.jsonl"
    events: list[dict[str, Any]] = []

    def emit(event: dict[str, Any]) -> None:
        events.append(event)
        with events_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    report: dict[str, Any] = {
        "schema": "samurai-usb-ncm-stability-v1",
        "started_utc": utc_now(),
        "dry_run": args.dry_run,
        "link": {
            "host": args.host,
            "user": args.user,
            "port": args.port,
            "identity": str(args.identity) if args.identity else "",
            "known_hosts": str(args.known_hosts) if args.known_hosts else "",
        },
        "matrix": {
            "sizes": list(args.sizes),
            "iterations": args.iterations,
            "directions": args.directions,
        },
        "commands": {
            "ssh": args.ssh,
            "scp": args.scp,
            "timeout_seconds": args.timeout,
            "probe_timeout_seconds": args.probe_timeout,
        },
    }

    host_files: dict[int, Path] = {}
    for size in args.sizes:
        path = outdir / f"host-source-{size}.bin"
        digest = generate_host_file(path, size)
        host_files[size] = path
        emit(
            {
                "kind": "host-source",
                "size": size,
                "path": str(path),
                "sha256": digest,
            }
        )

    report["host_sources"] = {
        str(size): {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for size, path in host_files.items()
    }

    if args.dry_run:
        report["finished_utc"] = utc_now()
        report["summary"] = {"passed": True, "dry_run": True, "transfers": 0}
        write_json(outdir / "result.json", report)
        print(json.dumps(report["summary"], sort_keys=True))
        return 0

    link = Link(args)
    report["host_pre"] = host_snapshot(outdir, "pre") if args.host_snapshot else {}
    preflight = device_snapshot(link, args.probe_timeout)
    report["device_pre"] = preflight
    emit({"kind": "device-pre", **preflight})
    if not preflight["returncode"] == 0 or preflight["timed_out"]:
        report["finished_utc"] = utc_now()
        report["summary"] = {
            "passed": False,
            "error": "device is not reachable over USB NCM SSH",
        }
        write_json(outdir / "result.json", report)
        print("USB NCM SSH preflight failed", file=sys.stderr)
        return 2

    remote_root = f"{DEFAULT_REMOTE_ROOT}/{stamp}"
    setup = link.ssh(
        f"mkdir -p {shlex.quote(remote_root)}; "
        "command -v sha256sum; command -v dd; command -v stat",
        args.probe_timeout,
    )
    report["remote_tools"] = setup.record()
    if not setup.ok:
        report["finished_utc"] = utc_now()
        report["summary"] = {"passed": False, "error": "remote prerequisites missing"}
        write_json(outdir / "result.json", report)
        return 2

    sleep_guard = None
    if not args.no_sleep_inhibit:
        sleep_guard = start_sleep_inhibitor(
            link,
            args.sleep_inhibit_seconds,
            args.probe_timeout,
        )
        report["sleep_inhibit"] = sleep_guard.record()
        if not sleep_guard.ok:
            stop_sleep_inhibitor(link, args.probe_timeout)
            report["finished_utc"] = utc_now()
            report["summary"] = {
                "passed": False,
                "error": "standard elogind sleep inhibitor was not acquired",
            }
            write_json(outdir / "result.json", report)
            print(
                "standard elogind sleep inhibitor was not acquired",
                file=sys.stderr,
            )
            return 2

    directions = (
        ("upload", "download")
        if args.directions == "both"
        else (args.directions,)
    )
    transfers: list[dict[str, Any]] = []
    for direction in directions:
        for size in args.sizes:
            for iteration in range(1, args.iterations + 1):
                print(
                    f"{direction} size={size} iteration={iteration}",
                    flush=True,
                )
                record = transfer_case(
                    link,
                    args,
                    outdir,
                    remote_root,
                    direction,
                    size,
                    iteration,
                    host_files[size] if direction == "upload" else None,
                )
                transfers.append(record)
                emit({"kind": "transfer", **record})
                if not record.get("passed"):
                    record["diagnostics"] = device_snapshot(
                        link,
                        args.probe_timeout,
                    )
                    emit(
                        {
                            "kind": "diagnostics",
                            "direction": direction,
                            "size": size,
                            "iteration": iteration,
                            "diagnostics": record["diagnostics"],
                        }
                    )
    report["transfers"] = transfers

    heartbeat = {
        "requested_seconds": args.heartbeat_seconds,
        "passed": None,
    }
    if args.heartbeat_seconds:
        print(
            f"heartbeat {args.heartbeat_seconds}s interval={args.heartbeat_interval}s",
            flush=True,
        )
        heartbeat = run_heartbeat(link, args, events)
        report["heartbeat"] = heartbeat

    report["device_post"] = device_snapshot(link, args.probe_timeout)
    if args.host_snapshot:
        report["host_post"] = host_snapshot(outdir, "post")

    if not args.keep_remote:
        cleanup = link.ssh(f"rm -rf {shlex.quote(remote_root)}", args.probe_timeout)
        report["cleanup"] = cleanup.record()
    else:
        report["cleanup"] = {"skipped": True, "remote_root": remote_root}

    if sleep_guard is not None:
        released = stop_sleep_inhibitor(link, args.probe_timeout)
        report["sleep_inhibit_release"] = released.record()

    transfer_failures = [
        record
        for record in transfers
        if not record.get("passed")
    ]
    heartbeat_failures = (
        not heartbeat.get("passed") if args.heartbeat_seconds else False
    )
    report["finished_utc"] = utc_now()
    report["summary"] = {
        "passed": not transfer_failures and not heartbeat_failures,
        "transfers": len(transfers),
        "passed_transfers": len(transfers) - len(transfer_failures),
        "failed_transfers": len(transfer_failures),
        "heartbeat_passed": heartbeat.get("passed"),
    }
    write_json(outdir / "result.json", report)
    print(json.dumps(report["summary"], sort_keys=True))
    return 0 if report["summary"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
