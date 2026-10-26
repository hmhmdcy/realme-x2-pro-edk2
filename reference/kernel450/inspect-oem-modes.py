"""Offline, read-only inventory for the next non-main normal consumer.

Never imports a capture transaction, binds the SDK, or publishes tuning values.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import struct
import subprocess
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("storage449_oem", HERE.parent / "kernel449/storage.py")
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
build = storage.mount.mounted_build()
P = Path("/mnt/e/edk2-samurai-out")
sys.path.append(str(storage.SDK / "usr/lib/python3.14/site-packages"))
import yaml

args = argparse.ArgumentParser()
args.add_argument("--inspect-source", action="store_true")
args.add_argument("--inspect-scaler", action="store_true")
args.add_argument("--inspect-ipe", action="store_true")
opts = args.parse_args()
tree = Path(json.loads((HERE / "source-state.json").read_text())["source"])
pipeline = tree / "src/libcamera/pipeline/camss-vfe/camss_vfe.cpp"
text = pipeline.read_text()

if opts.inspect_ipe:
    for relative in ["src/libcamera/pipeline/camss-vfe/camss_ipe.cpp", "src/libcamera/pipeline/camss-vfe/camss_pd10.h"]:
        path = tree / relative
        print("SOURCE", path)
        lines = path.read_text().splitlines()
        selected = set()
        for i, line in enumerate(lines):
            if any(p in line for p in ["CamssIpe::start", "camssPd10Layout", "format.size", "4608", "3456", "1920", "1080", "1280", "720"]):
                selected.update(range(max(0, i-4), min(len(lines), i+40)))
        for i in sorted(selected):
            print(f"{i+1}: {lines[i]}")
    raise SystemExit(0)

if opts.inspect_scaler:
    camss = build.parent / "source354/drivers/media/platform/qcom/camss"
    for path in camss.glob("*vfe*.c"):
        lines = path.read_text().splitlines()
        selected = set()
        for i, line in enumerate(lines):
            if any(p in line for p in ["V4L2_SEL_TGT_COMPOSE", "V4L2_SEL_TGT_CROP", "vfe_set_selection", "vfe_try_compose"]):
                selected.update(range(max(0, i-10), min(len(lines), i+45)))
        if selected:
            print("SOURCE", path)
            for i in sorted(selected):
                print(f"{i+1}: {lines[i]}")
    raise SystemExit(0)

if opts.inspect_source:
    patterns = ["getFormat(", "getSensorFormat", "sensorConfig", "sensorFormat", "maximumSize", "chooseSize", "generateConfiguration", "CamssVfeConfiguration::validate", "supported_modes", ".width =", ".height =", "clock19_profile", "222mhz_profile", "bestRatio", "bestArea", "bestSize", "size.width <", "size.height <"]
    for path in [pipeline, tree / "src/libcamera/sensor/camera_sensor.cpp", build.parent / "source354/drivers/media/i2c/s5k3m5.c", build.parent / "source354/drivers/media/i2c/imx319.c", build.parent / "source354/drivers/media/i2c/imx471.c"]:
        print("SOURCE", path)
        lines = path.read_text().splitlines()
        selected = set()
        for i, line in enumerate(lines):
            if any(p in line for p in patterns):
                selected.update(range(max(0, i-4), min(len(lines), i+9)))
        for i in sorted(selected):
            print(f"{i+1}: {lines[i]}")
        if path == pipeline:
            for i in range(460, 550):
                print(f"{i+1}: {lines[i]}")
    raise SystemExit(0)

bindings = json.loads((P / "kernel343/bound-mode-configs-private.json").read_text())
ltm = json.loads((P / "kernel351/mode-profiles-private.json").read_text())
tmc = json.loads((P / "kernel412/mode-profiles-private.json").read_text())
gamma = json.loads((P / "kernel350/mode-profiles-private.json").read_text())
rows = []
for model, variant in [("s5kgw1", "sunny_s5kgw1"), ("imx319", "sunny_imx319"), ("s5k3m5", "qtech_s5k3m5sx"), ("imx471", "sunny_imx471")]:
    profile_path = P / f"kernel440/factory-{model}-private.yaml"
    profile = yaml.safe_load(profile_path.read_text())
    dsroots = json.loads((P / f"kernel426/{variant}-ds4-reserves-private.json").read_text())
    dsselections = json.loads((P / f"kernel426/{variant}-ds4-selection-private.json").read_text())
    modes = []
    for m in profile["modes"]:
        size = [m["match"]["width"], m["match"]["height"]]
        b = next((r for r in bindings if r["variant"] == variant and r["usecase"] == "Preview" and r["sensor_size"] == size), None)
        row = dict(sensor_size=size, bound_stock_mode=b["sensor_mode_index"] if b else None,
                   ife_ds4_present="ife_ds4" in m, ipe_tone_present="ipe_tone" in m,
                   profile_keys=sorted(m.keys()))
        if b:
            mode = b["sensor_mode_index"]
            contexts = [r for r in dsselections if r["sensor_mode_index"] == mode and r["tag"] == "ds4to1v10_ife_full_dc4"]
            values = []
            for selected in contexts:
                root = next(r for r in dsroots if r["uid"] == selected["uid"] and r["tag"] == selected["tag"])
                values.append(next(r[1:] for r in root["passes"] if r[0] == 0))
            row["preview_video_stock_ds4_full_equal"] = len(contexts) == 2 and values[0] == values[1]
            row["configured_ds4_equals_bound_stock_full"] = "ife_ds4" in m and m["ife_ds4"] == values[0]
            for name, source in [("ltm_ccm", ltm), ("tmc", tmc), ("gamma", gamma)]:
                selected = [r for r in source[variant] if r["sensor_mode_index"] == mode]
                preview = next(r for r in selected if r["usecase"] == "Preview")
                video = next(r for r in selected if r["usecase"] == "Video")
                payload_key = "root" if name == "gamma" else "modules"
                row[f"preview_video_stock_{name}_equal"] = preview[payload_key] == video[payload_key]
            tone = m.get("ipe_tone", {})
            row["tone_switches"] = dict(enabled=tone.get("enabled"), tmc11=tone.get("tmc_enabled"), tmc10=tone.get("tmc10_enabled"), gtm=tone.get("ife_gtm", {}).get("enabled"), ipe_ccm=tone.get("colour_correction", {}).get("enabled", False))
            row["dc_image_mask_flags_match_441_geometry_contract"] = tone.get("flags", [])[2:] == [1, 1, 1]
        modes.append(row)
    rows.append(dict(model=model, variant=variant, profile_sha256=hashlib.sha256(profile_path.read_bytes()).hexdigest(), modes=modes))

header = tree / "src/libcamera/pipeline/camss-vfe/camss_pd10.h"
assert header.read_bytes() == (HERE.parent / "kernel441/camss_pd10.h").read_bytes()
kernel = build.parent / "source354/drivers/media/platform/qcom/camss"
kproof = json.loads((HERE.parent / "kernel441/kernel-source-state.json").read_text())
source_checks = []
for name in ["camss-icp-a5-ipe.c", "camss-icp-a5-m2m.c", "camss-vfe.c"]:
    actual = hashlib.sha256((kernel / name).read_bytes()).hexdigest()
    expected = next(r["sha256"] for r in kproof["source_hashes"] if r["path"].endswith("/" + name))
    assert actual == expected
    source_checks.append(dict(path=str((kernel / name).relative_to(build.parent / "source354")), sha256=actual))
assert "#define IPE_COARSE_MAX_BYTES 0x40000U" in (kernel / "camss-icp-a5-m2m.c").read_text()
sizes = [(1280, 720), (1920, 1080), (2104, 1560)]
helper = P / "kernel441/layout-host"
q = subprocess.run([str(helper)], input=b"".join(struct.pack("<2I", *size) for size in sizes), capture_output=True)
assert q.returncode == 0 and len(q.stdout) == 20 * len(sizes), (q.returncode, q.stderr.decode())
cached_layout = json.loads((HERE.parent / "kernel441/userspace-layout-validation.json").read_text())
cached_geometry = json.loads((HERE.parent / "kernel441/geometry-prototype-validation.json").read_text())
cached_bl = json.loads((HERE.parent / "kernel441/native-bl-validation.json").read_text())
assert all(p["passed"] for p in [cached_layout, cached_geometry, cached_bl])
geometry = []
for i, size in enumerate(sizes):
    cw, ch, stride, slice_height, length = struct.unpack_from("<5I", q.stdout, i * 20)
    row = dict(full=list(size), pd10=[cw, ch], stride=stride, packed_slice_height=slice_height,
               pd10_bytes=length, fits_current_441_coarse_owner=length <= 0x40000)
    if i < 2:
        old = next(r for r in cached_layout["layouts"] if [r["full_width"], r["full_height"]] == list(size))
        assert [cw, ch, stride, slice_height, length] == [old[k] for k in ["coarse_width", "coarse_height", "stride", "packed_slice_height", "bytes"]]
        g = next(r for r in cached_geometry["rows"] if (r["width"], r["height"]) == size)
        b = next(r for r in cached_bl["rows"] if (r["width"], r["height"]) == size)
        assert g["passed"] and b["passed"] and b["queued_commands_equal"]
        row.update(retained_whole_native_striping_and_bl_equal=True, striping_bytes=g["striping_bytes"],
                   scratch_bytes=b["scratch_bytes"], native_pass_masks=b["native_pass_masks"])
    geometry.append(row)
tele = next(r for r in rows if r["model"] == "s5k3m5")["modes"][0]
assert tele["sensor_size"] == [2104, 1560] and tele["bound_stock_mode"] == 3
assert all(tele[k] for k in ["configured_ds4_equals_bound_stock_full", "preview_video_stock_ds4_full_equal", "preview_video_stock_ltm_ccm_equal", "preview_video_stock_tmc_equal", "preview_video_stock_gamma_equal", "dc_image_mask_flags_match_441_geometry_contract"])

report = dict(stage=450, purpose="Offline next non-main normal-consumer scope",
              retained_formal_profiles=rows,
              current_pipeline_source_sha256=hashlib.sha256(pipeline.read_bytes()).hexdigest(),
              unchanged_441_kernel_geometry_sources=source_checks,
              current_header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
              retained_host_layout_helper_reused_without_compile=True,
              geometry=geometry,
              recommended_consumer=dict(model="s5k3m5", sensor_mode=3, sensor_size=[2104, 1560],
                                        outputs=[[1280, 720], [1920, 1080]],
                                        full_is_post_vfe_compose=True, stock_profile_change_required=False,
                                        centered_16_9_crop_implemented=False, hardware_new_cases_passed=False),
              sources_reused=[343, 350, 351, 412, 426, 438, 439, 440, 441, 443, 446],
              phone_accessed=False, sdk_bound=False, compiled=False,
              production_source_changed=False, oem_coefficients_published=False,
              passed=True)
(HERE / "oem-modes-next-validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
