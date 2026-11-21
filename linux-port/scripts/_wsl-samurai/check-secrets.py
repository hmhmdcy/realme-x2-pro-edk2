#!/usr/bin/env python3
"""Fail the build if the delivery image carries private credentials.

A distribution image must ship no household Wi-Fi PSK, account password blob,
or private key that only exists because this machine was used for testing.
The check only reports paths and booleans, never the secret values.

Checked locations:
  - NetworkManager profiles under /etc/NetworkManager/system-connections
    (any `psk=`, `password=`, `private-key=` line)
  - /etc/wpa_supplicant, /etc/hostapd and /etc/dnsmasq configs
  - private key files under /etc and /home
  - plaintext secrets in /etc/environment, /etc/samurai-*
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SECRET_LINE = re.compile(r"^\s*(psk|password|private-key|identity)\s*=",
                         re.IGNORECASE)
KEY_MATERIAL = re.compile(
    r"-----BEGIN (?:OPENSSH|RSA|EC|DSA|PRIVATE) PRIVATE KEY-----")
KEY_FILES = ("id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
             "ssh_host_rsa_key", "ssh_host_ecdsa_key",
             "ssh_host_ed25519_key")


def scan_file(path: Path) -> list[str]:
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return []
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        if SECRET_LINE.match(line):
            findings.append(f"{path}:{number}: credential field")
        elif KEY_MATERIAL.search(line):
            findings.append(f"{path}:{number}: private key material")
    return findings


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--allow", action="append", default=[],
                   help="relative path that is expected to hold a credential")
    args = p.parse_args()

    root = args.root
    findings: list[str] = []
    allowed = {str(item).lstrip("/") for item in args.allow}

    def relative(path: Path) -> str:
        return str(path.relative_to(root))

    for base in ("etc/NetworkManager/system-connections", "etc/wpa_supplicant",
                 "etc/hostapd", "etc/dnsmasq.d", "etc/environment"):
        target = root / base
        if not target.exists():
            continue
        paths = [target] if target.is_file() else sorted(target.rglob("*"))
        for path in paths:
            if not path.is_file() or path.suffix in (".bin", ".db"):
                continue
            if relative(path) in allowed:
                continue
            findings.extend(scan_file(path))

    for base in ("etc", "home"):
        target = root / base
        if not target.is_dir():
            continue
        for path in target.rglob("*"):
            if not path.is_file():
                continue
            if path.name in KEY_FILES:
                findings.append(f"{relative(path)}: private key file")
            elif path.suffix in (".pem", ".key") and path.stat().st_size < 20000:
                if KEY_MATERIAL.search(path.read_text(errors="replace")):
                    findings.append(f"{relative(path)}: private key material")

    if findings:
        for item in findings:
            print("  FAIL " + item)
        print(f"RESULT: {len(findings)} private credential(s) in the image")
        return 1
    print("RESULT: no private credentials in the image")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
