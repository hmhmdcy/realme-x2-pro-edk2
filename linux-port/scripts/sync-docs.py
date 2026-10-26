#!/usr/bin/env python3
"""Copy the documentation manifest; preserve differing mirror files before updating."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import importlib.util
import shutil
import subprocess
import os
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--repo", type=Path, default=Path("/home/cy122/edk2-samurai/repo"))
    parser.add_argument("--stage", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--files", nargs="+", metavar="PATH", help="Copy only these workspace-relative manifest files.")
    args = parser.parse_args()
    root = args.workspace.resolve()
    mirror = args.repo.resolve() / "Platform/Realme/sm8150"
    if not (mirror / "samurai.dsc").is_file():
        raise SystemExit("Expected the samurai platform checkout at the mirror destination.")
    spec = importlib.util.spec_from_file_location("docs_check", root / "linux-port/scripts/docs-health-check.py")
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    manifest = checker.load_manifest(root)
    files = checker.selected_files(root, manifest, args.files) if args.files else checker.sync_files(root, manifest)
    exporter = checker.public_module(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup = root / "out/docs-mirror-backups" / stamp
    changed = []
    backed_up = 0
    for relative in files:
        source = checker.safe_path(root, relative)
        target = checker.safe_path(mirror, relative)
        data = exporter.public_bytes(root, relative)
        if target.is_file() and data == target.read_bytes():
            continue
        if target.exists() and not target.is_file():
            raise SystemExit(f"Mirror destination is not a regular file: {relative}")
        changed.append(relative)
        if not args.dry_run:
            if target.is_file():
                saved = checker.safe_path(backup, relative)
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
                backed_up += 1
            target.parent.mkdir(parents=True, exist_ok=True)
            # Replace atomically in the editable mirror, including historical root-owned files.
            descriptor, name = tempfile.mkstemp(prefix='.docs-sync-', dir=target.parent)
            temporary = Path(name)
            try:
                with os.fdopen(descriptor, 'wb') as output:
                    output.write(data)
                temporary.chmod((target.stat().st_mode & 0o777) if target.exists() else 0o644)
                temporary.replace(target)
            finally:
                if temporary.exists():
                    temporary.unlink()
    if args.stage and not args.dry_run:
        # Avoid unrelated DTB/BDS/source edits: add only paths in this manifest.
        path_names = [str(Path("Platform/Realme/sm8150") / path) for path in files]
        ignored = subprocess.run(['git','-C',str(args.repo),'check-ignore','-z','--stdin'],input=b'\0'.join(name.encode() for name in path_names)+b'\0',capture_output=True,check=False)
        if ignored.returncode not in (0,1):
            raise SystemExit('Unable to check ignored files before staging.')
        excluded = {name.decode() for name in ignored.stdout.split(b'\0') if name}
        files = [path for path,name in zip(files,path_names) if name not in excluded]
        for start in range(0, len(files), 100):
            paths = [str(Path("Platform/Realme/sm8150") / path) for path in files[start:start + 100]]
            subprocess.run(["git", "-C", str(args.repo), "add", "--", *paths], check=True)
    scope = "selected scope" if args.files else "manifest"
    print(f"{'Would copy' if args.dry_run else 'Copied'} {len(changed)} changed files; {scope} covers {len(files)} files.")
    if backed_up:
        print(f"Preserved {backed_up} differing mirror files in {backup}.")
    if not args.stage:
        print("No commit, staging or push performed.")


if __name__ == "__main__":
    main()
