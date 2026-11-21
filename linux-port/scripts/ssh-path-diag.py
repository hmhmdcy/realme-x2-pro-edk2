#!/usr/bin/env python3
"""Decide whether an SSH failure is real, or an artifact of a local proxy.

A fake-IP proxy (mihomo/Clash TUN) answers the TCP handshake itself, so
Test-NetConnection reports "port 22 open" while ssh receives 0 bytes.

The only reliable discriminator is the *local* address of the socket:
if it lies inside the proxy's fake-IP range (198.18.0.0/16 by default),
the connection never reached a physical NIC.

Usage:
  ssh-path-diag.py 172.16.42.1 22
  ssh-path-diag.py 192.168.0.106 22 --bind 192.168.0.104
  ssh-path-diag.py --scan 192.168.0.104
"""
import argparse
import socket
import sys
import threading
from typing import Optional


def fake_ip_range():
    """Best-effort read of the proxy's configured fake-ip range."""
    import os
    import re
    candidates = [
        os.path.expanduser(
            "~/AppData/Roaming/io.github.clash-verge-rev.clash-verge-rev/clash-verge.yaml"
        ),
        os.path.expanduser("~/.config/clash/config.yaml"),
        os.path.expanduser("~/.config/mihomo/config.yaml"),
    ]
    for path in candidates:
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            continue
        match = re.search(r"fake-ip-range:\s*([0-9.]+)/(\d+)", text)
        if match:
            return match.group(1)
    return "198.18.0.1"


def in_fake_range(local_ip, fake_base):
    if not local_ip or "." not in local_ip:
        return False
    try:
        return socket.inet_aton(local_ip.split("/")[0])[:2] == socket.inet_aton(fake_base)[:2]
    except OSError:
        return False


def probe(host, port, source=None, timeout=6.0):
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        if source:
            sock.bind((source, 0))
        sock.connect((host, port))
        local = sock.getsockname()
        sock.settimeout(5)
        try:
            banner = sock.recv(64)
        except socket.timeout:
            banner = b"<timeout: connected but silent>"
        except OSError as exc:
            banner = b"<error: " + str(exc).encode() + b">"
        return {"ok": True, "local": local, "peer": sock.getpeername(),
                "banner": banner}
    except OSError as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "local": None}
    finally:
        sock.close()


def scan(local_ip, port=22, workers=48, timeout=3.0):
 """Scan /24 around local_ip for hosts that accept TCP on `port`.

 A DHCP lease moves; hard-coded addresses in scripts go stale. Binding to
 the real NIC also keeps the proxy out of the result.
 """
 prefix = ".".join(local_ip.split(".")[:3])
 found = []
 lock = threading.Lock()

 def one(index):
     host = f"{prefix}.{index}"
     sock = socket.socket()
     sock.settimeout(timeout)
     try:
         sock.bind((local_ip, 0))
         sock.connect((host, port))
     except OSError:
         return
     finally:
         sock.close()
     with lock:
         found.append(host)

 # Batch the workers: firing 254 sockets at once makes the local stack
 # drop SYNs and silently loses real hosts.
 for start in range(1, 255, workers):
     threads = [threading.Thread(target=one, args=(index,), daemon=True)
                for index in range(start, min(start + workers, 255))]
     for thread in threads:
         thread.start()
     for thread in threads:
         thread.join()

 for host in sorted(found, key=lambda h: int(h.split(".")[-1])):
     print(f"  {host}:{port} open")
 return found


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("host", nargs="?")
    parser.add_argument("port", type=int, nargs="?", default=22)
    parser.add_argument("--bind", help="source IP of the real NIC (bypasses the proxy)")
    parser.add_argument("--scan", metavar="LOCAL_IP",
                        help="scan the /24 around LOCAL_IP for open ports instead")
    parser.add_argument("--timeout", type=float, default=6.0)
    args = parser.parse_args()

    fake_base = fake_ip_range()

    if args.scan:
        print(f"scanning {args.scan.rsplit('.', 1)[0]}.0/24 port {args.port} "
              f"from {args.scan}")
        found = scan(args.scan, args.port)
        if not found:
            print("  no host accepted the connection")
            return 1
        print("\nNext: ssh -i <key> user@<host>  (verify it is the handset)")
        return 0

    if not args.host:
        parser.error("host is required unless --scan is used")

    print(f"proxy fake-ip base: {fake_base}")
    verdict_real = None

    for label, source in (("default route", None), ("bound to NIC", args.bind)):
        if label == "bound to NIC" and not args.bind:
            continue
        result = probe(args.host, args.port, source, args.timeout)
        print(f"\n[{label}] {args.host}:{args.port}")
        if not result["ok"]:
            print(f"  no connection: {result['error']}")
            continue
        local_ip = result["local"][0]
        hijacked = in_fake_range(local_ip, fake_base)
        print(f"  local={result['local']}  peer={result['peer']}")
        print(f"  banner={result['banner']!r}")
        if hijacked:
            print("  VERDICT: proxied. This result says nothing about the device.")
        else:
            print("  VERDICT: real path through a physical interface.")
            verdict_real = result

    if verdict_real is None:
        print("\nConclusion: no evidence of a reachable device on a real NIC.")
        print("Fix the proxy exclusion (tun.route-exclude-address) or the")
        print("device's network service (samurai-usb-network / usb0) before")
        print("treating sshd as broken.")
        return 1

    banner = verdict_real["banner"]
    if banner.startswith(b"SSH-"):
        print("\nsshd answered with a real banner: the server is healthy.")
        return 0
    if banner:
        print("\nReached the device, but sshd did not send a banner.")
        print("Check on device: systemctl status sshd; journalctl -u sshd -u sshdgenkeys")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
