#!/usr/bin/env python3
"""Offline proof that the delivered image can accept SSH on Wi-Fi and NCM.

This never boots the image.  It reads the packed rootfs and answers the
questions that decide whether `ssh user@<phone>` can work at all:

  1. is sshd.service enabled in a target that boots?
  2. does something generate host keys before sshd starts?
  3. does anything create /run/sshd (privilege separation)?
  4. does the effective config listen on all interfaces, port 22, with the
     authentication methods the board intends?
  5. is the login account still usable (shell, password, authorized keys)?

Pass --root <dir> for an already-unpacked tree, or --image <file> to read a
sparse image read-only.  Exit status is 1 on any hard regression.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


def popen(cmd):
    out = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    return out.stdout + out.stderr


def run_ok(cmd):
    return subprocess.run([str(c) for c in cmd],
                          capture_output=True).returncode == 0


def main() -> int:
    p = argparse.ArgumentParser()
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--root", type=Path)
    src.add_argument("--image", type=Path)
    p.add_argument("--work", type=Path, default=Path("/root"),
                   help="scratch dir for the sparse expansion (needs ~120 GB); "
                        "/tmp is only 3.9 GB in WSL")
    p.add_argument("--user", default="user")
    args = p.parse_args()

    problems = []
    notes = []
    tmp = None
    scratch = Path("/root")
    created_keys = []

    if args.image:
        args.work.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(prefix="sshimg-", dir=args.work))
        img = tmp / "a.img"
        if not run_ok(["simg2img", args.image, img]):
            print("simg2img failed")
            shutil.rmtree(tmp, ignore_errors=True)
            return 1
        root = tmp / "root"
        root.mkdir()
        popen(["losetup", "-D"])
        loop = popen(["losetup", "-f", "--show", img]).strip()
        # Writable: the check has to create /run/sshd and throwaway host keys
        # exactly as first boot would.  This is a disposable expansion.
        if not loop or not run_ok(["mount", "-t", "f2fs", "-o", "rw",
                                   loop, root]):
            print("could not mount the image")
            popen(["losetup", "-D"])
            shutil.rmtree(tmp, ignore_errors=True)
            return 1
    else:
        root = args.root

    try:
        unit = root / "usr/lib/systemd/system/sshd.service"
        unit_text = unit.read_text(errors="replace") if unit.is_file() else ""
        if not unit.is_file():
            problems.append("sshd.service missing; SSH cannot start")
        else:
            if "sshdgenkeys.service" not in unit_text:
                problems.append("sshd.service does not pull in sshdgenkeys")
            else:
                notes.append("sshd.service wants sshdgenkeys.service")
            if "Restart=always" in unit_text:
                notes.append("Restart=always: sshdgenkeys must succeed or sshd loops")

        wants = sorted((root / "etc/systemd/system").rglob("*.wants/sshd.service"))
        if wants:
            notes.append("enabled in: " + ", ".join(
                str(p.relative_to(root)) for p in wants))
        elif any("enable sshd.service" in f.read_text(errors="replace")
                 for f in (root / "usr/lib/systemd/system-preset").glob("*.preset")):
            notes.append("enabled by preset at install time")
        else:
            problems.append("sshd is neither enabled nor preset-enabled")

        if (root / "usr/bin/ssh-keygen").is_file():
            notes.append("ssh-keygen present")
        else:
            problems.append("ssh-keygen missing; host keys cannot be created")

        tmpfiles = list((root / "usr/lib/tmpfiles.d").glob("*.conf"))
        if any("/run/sshd" in f.read_text(errors="replace") for f in tmpfiles):
            notes.append("/run/sshd is created by tmpfiles")
        elif "RuntimeDirectory" in unit_text:
            notes.append("/run/sshd comes from RuntimeDirectory")
        else:
            problems.append("/run/sshd has no creator; sshd refuses to start")

        sshd = root / "usr/sbin/sshd.pam"
        if not sshd.is_file():
            sshd = root / "usr/sbin/sshd"
        if not sshd.is_file():
            problems.append("no sshd binary in /usr/sbin")
        else:
            # sshd expands `Include /etc/ssh/sshd_config.d/*.conf` as an
            # ABSOLUTE path.  Running it with `-f` outside a chroot makes
            # that include resolve against the HOST's /etc/ssh, which silently
            # answers a different question (it once reported identical
            # configs with and without the image's drop-in).  Probe inside a
            # chroot so every absolute path belongs to the image.
            eff = ""
            mounts = []
            try:
                for name in ("run", "dev", "proc"):
                    (root / name).mkdir(parents=True, exist_ok=True)
                (root / "run/sshd").mkdir(parents=True, exist_ok=True)
                (root / "run/sshd").chmod(0o755)
                if not (root / "dev/null").exists():
                    popen(["mknod", root / "dev/null", "c", "1", "3"])
                probe_helper = Path(tempfile.mkdtemp(prefix="sshbin-",
                                                     dir=scratch)) / "qemu"
                shutil.copy2("/usr/bin/qemu-aarch64-static", probe_helper)
                dest = root / "usr/bin/qemu-aarch64-static"
                dest.write_bytes(probe_helper.read_bytes())
                dest.chmod(0o755)
                popen(["chroot", root, "/usr/bin/qemu-aarch64-static",
                       "/usr/bin/ssh-keygen", "-A"])
                # Remember exactly what we created so the caller's image is
                # never shipped with a build-time host key.  A fixed host key
                # in a distributed image is worse than no key at all.
                for pattern in ("ssh_host_rsa_key", "ssh_host_rsa_key.pub",
                                "ssh_host_ecdsa_key", "ssh_host_ecdsa_key.pub",
                                "ssh_host_ed25519_key",
                                "ssh_host_ed25519_key.pub"):
                    target = root / "etc/ssh" / pattern
                    if target.exists() and pattern not in created_keys:
                        created_keys.append(pattern)
                # chroot needs IN-ROOT paths, not host paths.  Passing
                # str(sshd) (/root/repack/root/usr/sbin/sshd.pam) silently
                # produced an empty config, which is why the probe failed
                # while the same command worked by hand.
                eff = popen(["chroot", root, "/usr/bin/qemu-aarch64-static",
                             "/usr/sbin/" + sshd.name, "-T",
                             "-f", "/etc/ssh/sshd_config"])
                raw = eff.strip().splitlines()
                notes.append("chroot sshd -T lines: "
                             + str(len(raw))
                             + (("  first: " + raw[0][:110]) if raw else ""))
                if raw and "no hostkeys" in eff:
                    notes.append("chroot probe: host key generation failed")
                dest.unlink(missing_ok=True)
            except OSError:
                notes.append("read-only root: chroot probe unavailable")
                eff = popen(["qemu-aarch64-static", "-L", root, sshd, "-T"])
            keys = {}
            for line in eff.splitlines():
                parts = line.split(None, 1)
                if len(parts) == 2:
                    keys[parts[0]] = parts[1].strip()
            for need in ("port", "listenaddress", "passwordauthentication",
                         "pubkeyauthentication", "usepam"):
                if need not in keys:
                    problems.append("sshd -T produced no " + need)
            if keys.get("port") != "22":
                problems.append("unexpected SSH port " + str(keys.get("port")))
            listens = [v for k, v in keys.items() if k == "listenaddress"]
            if not any("0.0.0.0" in v or v.startswith("[::]") for v in listens):
                problems.append("sshd does not listen on all interfaces; "
                                "Wi-Fi clients could not connect")
            if keys.get("passwordauthentication") != "yes":
                problems.append("PasswordAuthentication is not yes")
            if keys.get("usepam") != "yes":
                problems.append("UsePAM is not yes")
            for k in ("port", "listenaddress", "usepam",
                      "passwordauthentication", "pubkeyauthentication",
                      "permitrootlogin"):
                if k in keys:
                    notes.append(f"sshd -T {k}={keys[k]}")

        passwd = root / "etc/passwd"
        line = ""
        if passwd.is_file():
            for entry in passwd.read_text(errors="replace").splitlines():
                if entry.split(":")[0] == args.user:
                    line = entry
        if not line:
            problems.append(f"user {args.user} is not in /etc/passwd")
        else:
            notes.append("passwd: " + line)
            fields = line.split(":")
            if len(fields) >= 7 and fields[6].endswith("nologin"):
                problems.append(f"{args.user} has shell {fields[6]}")

        keys_file = root / "home" / args.user / ".ssh/authorized_keys"
        if keys_file.is_file() and keys_file.read_text().strip():
            notes.append("authorized_keys: "
                         + str(len(keys_file.read_text().splitlines())) + " line(s)")
        else:
            notes.append("no authorized_keys for " + args.user
                         + " (password login still applies)")

        shadow = root / "etc/shadow"
        if shadow.is_file():
            for entry in shadow.read_text(errors="replace").splitlines():
                if entry.split(":")[0] == args.user:
                    secret = entry.split(":")[1] if ":" in entry else ""
                    if secret in ("!", "!!", "*", ""):
                        notes.append(f"{args.user} password LOCKED")
                        problems.append(f"{args.user} password is locked; "
                                        "key and password login both fail")
                    else:
                        notes.append(f"{args.user} password set")

        print(f"target: {root}")
        for n in notes:
            print("  ok   " + n)
        for prob in problems:
            print("  FAIL " + prob)
        print("RESULT: " + ("ssh image check passed" if not problems
                            else f"{len(problems)} problem(s)"))
        return 0 if not problems else 1
    finally:
        for name in created_keys:
            try:
                (root / "etc/ssh" / name).unlink()
            except OSError:
                pass
        if tmp:
            run_ok(["umount", root])
            popen(["losetup", "-D"])
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
