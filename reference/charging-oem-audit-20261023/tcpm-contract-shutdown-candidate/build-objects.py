"""Compile only affected translation units; all output stays in this candidate.

Use a private mount namespace and read-only old build/source layers. No make,
Image link, configuration generation, source copy-up, or shared-layer write.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "budget_build_readonly", HERE.parent / "tcpm-usb-budget-candidate/build-image.py")
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
FILES = {
    "drivers/usb/typec/tcpm/tcpm.c": "tcpm.c",
    "include/linux/usb/tcpm.h": "tcpm.h",
    **{"drivers/usb/typec/tcpm/qcom/" + name: name for name in [
        "qcom_pmic_typec.c", "qcom_pmic_typec.h", "qcom_pmic_typec_port.c",
        "qcom_pmic_typec_port.h", "qcom_pmic_typec_pdphy.c", "qcom_pmic_typec_pdphy.h"]},
}
LAYERS = [old.OUT] + old.LAYERS
OBJECTS = ["drivers/usb/typec/tcpm/tcpm.o"] + [
    "drivers/usb/typec/tcpm/qcom/" + name + ".o" for name in [
        "qcom_pmic_typec", "qcom_pmic_typec_port", "qcom_pmic_typec_pdphy",
        "qcom_pmic_typec_pdphy_stub", "qcom_pmic_typec_5v"]]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def child():
    subprocess.run(["mount", "--make-rprivate", "/"], check=True)
    subprocess.run(["mount", "-o", "loop,ro,noload",
                    "/mnt/e/edk2-samurai-out/kernel282/full-kernel-build282.ext4",
                    str(HERE / "kernel-base")], check=True)
    subprocess.run(["mount", "--bind", str(HERE / "kernel-base"),
                    "/mnt/samurai-full282"], check=True)
    for name, target in [("source354", old.base.SOURCE), ("build", old.base.BUILD)]:
        lower = [str(x / (name + "-upper")) for x in LAYERS]
        lower.append(str(HERE / "kernel-base" / name))
        merged = HERE / ("source-merged" if name == "source354" else "build-merged")
        subprocess.run(["mount", "-t", "overlay", "overlay", "-o",
                        "ro,lowerdir=" + ":".join(lower), str(merged)], check=True)
        # The original mountpoint belongs to the existing, presently unmounted
        # build image. Bind the read-only views only within this namespace.
        if not target.exists():
            raise RuntimeError("Expected existing source/build mountpoint: " + str(target))
        subprocess.run(["mount", "--bind", str(merged), str(target)], check=True)
    for relative, local in FILES.items():
        subprocess.run(["mount", "--bind", str(HERE / local),
                        str(old.base.SOURCE / relative)], check=True)
    env = old.base.build_environment()
    env["TMPDIR"] = str(HERE / "tmp")
    previous_path = HERE / "build-child-result.json"
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
    previous_rows = {r["object"]: r for r in previous.get("objects", [])}
    sources = {n: sha(HERE / n) for n in FILES.values()}
    rows = []
    for relative in OBJECTS:
        obj = Path(relative)
        destination = HERE / "objects" / obj.name
        dependencies = ["tcpm.h"]
        if obj.name == "tcpm.o":
            dependencies.append("tcpm.c")
        else:
            dependencies.append("qcom_pmic_typec.h")
            for ext in [".c", ".h"]:
                local = obj.stem + ext
                if local in sources:
                    dependencies.append(local)
        prior = previous_rows.get(relative)
        if previous.get("passed") and prior and destination.exists() and \
                sha(destination) == prior["sha256"] and all(
                    sources[n] == previous["source_sha256"].get(n) for n in dependencies):
            rows.append({**prior, "reused": True})
            print(json.dumps(dict(object=relative, reused=True)), flush=True)
            continue
        saved = old.base.BUILD / obj.parent / ("." + obj.name + ".cmd")
        line = saved.read_text().splitlines()[0]
        argv = shlex.split(line.split(":=", 1)[1].strip())
        for i, arg in enumerate(argv):
            if arg.startswith("-Wp,-MMD,"):
                argv[i] = "-Wp,-MMD," + str(destination.with_suffix(".d"))
            if arg == "-o":
                argv[i + 1] = str(destination)
        assert "-c" in argv and str(destination) in argv
        started = time.monotonic()
        p = subprocess.run(argv, cwd=old.base.BUILD, env=env,
                           capture_output=True, text=True)
        (HERE / "objects" / (obj.stem + ".log")).write_text(p.stdout + p.stderr)
        diagnostics = [x for x in (p.stdout + p.stderr).splitlines()
                       if re.search(r"\b(warning:|error:|undefined reference)", x, re.I)]
        rows.append(dict(object=relative, returncode=p.returncode,
                         seconds=time.monotonic() - started, diagnostics=diagnostics,
                         sha256=sha(destination) if destination.exists() else None))
        print(json.dumps(rows[-1]), flush=True)
        if p.returncode or diagnostics:
            print(p.stdout + p.stderr, flush=True)
            break
    result = dict(passed=len(rows) == len(OBJECTS) and all(
        r["returncode"] == 0 and not r["diagnostics"] for r in rows),
        objects=rows, source_sha256={n: sha(HERE / n) for n in FILES.values()},
        no_make=True, no_Image_build=True, read_only_baselines=True,
        phone_accessed=False, installed=False)
    (HERE / "build-child-result.json").write_text(json.dumps(result, indent=2) + "\n")
    raise SystemExit(0 if result["passed"] else 1)


def main():
    # Host C/E and WSL capacity are recorded by the calling PowerShell check.
    free = {p: os.statvfs(p).f_bavail * os.statvfs(p).f_frsize
            for p in ["/", "/mnt/c", "/mnt/e"]}
    assert free["/"] > 1024**3 and free["/mnt/c"] > 2 * 1024**3
    assert free["/mnt/e"] > 2 * 1024**3
    # Existing mountpoint needs the old filesystem present at source354/build.
    # Bind its read-only root to that existing mountpoint in the child first.
    script = Path(__file__).resolve()
    argv = ["unshare", "--mount", "--propagation", "private", "--fork",
            sys.executable, "-B", str(script), "--child"]
    before_mounts = sha(Path("/proc/self/mountinfo"))
    p = subprocess.run(argv, capture_output=True, text=True)
    (HERE / "build.stdout").write_text(p.stdout)
    (HERE / "build.stderr").write_text(p.stderr)
    result = dict(passed=p.returncode == 0, returncode=p.returncode, free_bytes=free,
                  parent_mounts_unchanged=sha(Path("/proc/self/mountinfo")) == before_mounts,
                  only_candidate_written=True, phone_accessed=False,
                  Image_built=False, installed=False)
    if (HERE / "build-child-result.json").exists():
        result["build"] = json.loads((HERE / "build-child-result.json").read_text())
    (HERE / "build-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(p.stdout + p.stderr)
    raise SystemExit(p.returncode)


if __name__ == "__main__":
    child() if sys.argv[1:] == ["--child"] else main()
