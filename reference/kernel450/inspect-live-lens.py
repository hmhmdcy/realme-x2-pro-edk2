"""Read-only exact Image363 config and live lens attachment prerequisites."""
from pathlib import Path
import gzip
import hashlib
import importlib.util
import json
import re
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("live_lens_storage449", HERE.parent / "kernel449/storage.py")
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
BUILD = storage.mount.mounted_build()
SOURCE = BUILD.parent / "source354"
PRIVATE = Path("/mnt/e/edk2-samurai-out/kernel450/live-lens")
IMAGE = PRIVATE.parent.parent / "kernel363/Image-k363-private"
proof = json.loads((HERE.parent / "kernel363/boot-candidate-build-validation.json").read_text())
raw = IMAGE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == proof["artifacts"]["arch/arm64/boot/Image"]["sha256"]
start = raw.find(b"IKCFG_ST")
end = raw.find(b"IKCFG_ED", start + 8) if start != -1 else -1
print(json.dumps(dict(image_sha256=hashlib.sha256(raw).hexdigest(), ikconfig_start=start, ikconfig_end=end)), flush=True)
if start != -1 and end != -1:
    config = gzip.decompress(raw[start + 8:end])
    assert hashlib.sha256(config).hexdigest() == proof["artifacts"][".config"]["sha256"]
    PRIVATE.mkdir(exist_ok=True)
    config_path = PRIVATE / "Image363-extracted.config"
    if config_path.exists():
        assert config_path.read_bytes() == config
    else:
        config_path.write_bytes(config)
    keys = ["OF", "OF_DYNAMIC", "OF_OVERLAY", "OF_CONFIGFS", "CONFIGFS_FS", "IKCONFIG", "IKCONFIG_PROC", "VIDEO_V4L2_SUBDEV_API", "V4L2_ASYNC", "V4L2_FWNODE", "SOFT_I2C", "I2C", "I2C_MUX", "VIDEO_BU64253", "VIDEO_DW9807_VCM", "SYSFS", "MODULES", "MODULE_UNLOAD", "MODVERSIONS", "TRIM_UNUSED_KSYMS"]
    lines = config.decode().splitlines()
    selected = {"CONFIG_" + key: next((line.split("=", 1)[1] if "=" in line else "n" for line in lines if line.startswith("CONFIG_" + key + "=") or line == "# CONFIG_" + key + " is not set"), "absent") for key in keys}
    print(json.dumps(dict(exact_image_config_sha256=hashlib.sha256(config).hexdigest(), config=selected), indent=2), flush=True)
else:
    raise SystemExit("Exact Image has no embedded IKCONFIG; do not infer live config from mutable build/.config")

tree = Path(json.loads((HERE / "source-state.json").read_text())["source"])
if len(sys.argv) > 1 and sys.argv[1] in ["--grep", "--lines"]:
    assert len(sys.argv) == 4
    kind, relative = sys.argv[2].split(":", 1)
    assert kind in ["kernel", "libcamera"] and ".." not in Path(relative).parts and not Path(relative).is_absolute()
    target = (SOURCE if kind == "kernel" else tree) / relative
    lines = target.read_text().splitlines()
    print("SOURCE", target, "sha256", hashlib.sha256(target.read_bytes()).hexdigest())
    if sys.argv[1] == "--grep":
        selected = set()
        needles = sys.argv[3].split(",")
        for i, line in enumerate(lines):
            if any(needle in line for needle in needles):
                selected.update(range(max(0, i-3), min(len(lines), i+35)))
    else:
        first, last = map(int, sys.argv[3].split(":"))
        selected = range(first-1, min(len(lines), last))
    for i in sorted(selected):
        print(f"{i+1}: {lines[i]}")
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--exports":
    image_vmlinux = BUILD / "vmlinux"
    with image_vmlinux.open("rb") as stream:
        vhash = hashlib.file_digest(stream, "sha256").hexdigest()
    assert vhash == proof["artifacts"]["vmlinux"]["sha256"]
    output = subprocess.check_output(["aarch64-linux-gnu-nm", "--defined-only", str(image_vmlinux)], text=True)
    names = {line.split()[-1] for line in output.splitlines() if line.split()}
    api = ["of_overlay_fdt_apply", "of_overlay_remove", "device_add_software_node", "device_remove_software_node", "fwnode_property_get_reference_args", "i2c_new_client_device"]
    for name in api:
        assert name in names and "__ksymtab_" + name in names, name
    for line in output.splitlines():
        if any(p in line for p in ["of_overlay_fdt_apply", "of_overlay_remove", "device_add_software_node", "device_remove_software_node", "set_secondary_fwnode", "fwnode_property_get_reference_args", "i2c_new_client_device"]):
            print(line)
    framework = ["drivers/of/overlay.c", "drivers/of/Kconfig", "drivers/of/Makefile", "drivers/base/property.c", "drivers/base/swnode.c", "drivers/i2c/i2c-core-of.c", "drivers/i2c/i2c-core-base.c", "drivers/media/v4l2-core/v4l2-fwnode.c", "drivers/media/v4l2-core/v4l2-async.c"]
    for path in framework:
        current = subprocess.check_output(["git", "-C", str(SOURCE), "show", "HEAD:" + path])
        original = subprocess.check_output(["git", "-C", str(SOURCE), "show", proof["commit"] + ":" + path])
        assert current == original, path
    configfs = subprocess.run(["git", "-C", str(SOURCE), "grep", "-n", "configfs", "--", "drivers/of"], capture_output=True, text=True)
    assert configfs.returncode == 1 and not configfs.stdout
    bu_sources = list((SOURCE / "drivers/media/i2c").glob("*bu64253*"))
    report = dict(exact_image_sha256=hashlib.sha256(raw).hexdigest(), exact_config_sha256=hashlib.sha256(config).hexdigest(),
                  exact_vmlinux_sha256=vhash, framework_files_unchanged_since_Image363=framework,
                  verified_exported_api=api, config=selected,
                  of_configfs_frontend_present=False, bu64253_sources_present=[str(path) for path in bu_sources],
                  phone_accessed=False, sdk_bound=False, compiled=False)
    (PRIVATE / "inspection-private.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--dt":
    dt_proof = json.loads((HERE.parent / "charging-management-20261023/usb-boot-result.json").read_text())
    dt = PRIVATE.parent.parent / "charging-management-20261023/usb-dt/samurai-charging-usb-private.dtb"
    blob = dt.read_bytes()
    assert hashlib.sha256(blob).hexdigest() == dt_proof["dtb_sha256"]
    header = struct.unpack_from(">10I", blob)
    assert header[0] == 0xd00dfeed and header[1] == len(blob)
    at, strings_start = header[2], header[3]
    stack, nodes = [], {}
    while True:
        token = struct.unpack_from(">I", blob, at)[0]
        at += 4
        if token == 1:
            end = blob.index(bytes([0]), at)
            stack.append(blob[at:end].decode())
            path = "/" + "/".join(stack[1:])
            nodes[path] = {}
            at = (end + 4) & ~3
        elif token == 2:
            stack.pop()
        elif token == 3:
            length, name_offset = struct.unpack_from(">2I", blob, at)
            at += 8
            name_at = strings_start + name_offset
            name = blob[name_at:blob.index(bytes([0]), name_at)].decode()
            nodes["/" + "/".join(stack[1:])][name] = blob[at:at+length]
            at = (at + length + 3) & ~3
        elif token == 4:
            continue
        elif token == 9:
            break
        else:
            raise AssertionError(token)
    report = dict(current_retained_boot=dt_proof["boot_sha256"], dtb_sha256=dt_proof["dtb_sha256"],
                  dtb_has_symbols="/__symbols__" in nodes,
                  existing_lens_references=[path for path, properties in nodes.items() if "lens-focus" in properties],
                  added_lens_needs_real_target_path_or_checked_phandle=True,
                  dt_readonly=True, phone_accessed=False)
    (PRIVATE / "dt-inspection-private.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0)

print("Use --exports, --dt, --grep kernel:relative/path comma,separated,needles or --lines libcamera:relative/path first:last.")
