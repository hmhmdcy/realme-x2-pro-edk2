from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


TRIAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TRIAL_DIR))

import trial_common  # noqa: E402


class ProductionManifestTests(unittest.TestCase):
    def test_packaged_linux_text_uses_lf(self) -> None:
        for path in TRIAL_DIR.rglob("*"):
            if not path.is_file() or path.name.startswith(("test-run-", "test-results")):
                continue
            if (
                path.suffix not in {".py", ".ps1", ".md", ".json"}
                and path.name != "samurai-charging"
            ):
                continue
            self.assertNotIn(b"\r\n", path.read_bytes(), path.relative_to(TRIAL_DIR))

    def test_manifest_pins_bundled_files_and_real_carriers(self) -> None:
        manifest = trial_common.read_json(TRIAL_DIR / "manifest.json")
        self.assertEqual(manifest["schema"], 1)
        self.assertEqual(manifest["trial_id"], trial_common.TRIAL_ID)
        self.assertEqual(manifest["kernel_version"], trial_common.VERSION)
        self.assertEqual(manifest["watch_seconds"], 300)
        self.assertEqual(manifest["token"], trial_common.TOKEN)
        self.assertIs(manifest["high_voltage_permitted"], False)
        self.assertEqual(
            manifest["device_root"],
            trial_common.DEVICE_ROOT.as_posix(),
        )
        self.assertEqual(manifest["image"]["sha256"], trial_common.IMAGE_SHA256)
        self.assertEqual(manifest["image"]["bytes"], trial_common.IMAGE_BYTES)
        fat_receipt_path = Path(manifest["image"]["fat_receipt_path"])
        self.assertTrue(fat_receipt_path.is_file())
        self.assertEqual(
            manifest["image"]["fat_receipt_sha256"],
            trial_common.sha256_file(fat_receipt_path),
        )
        fat_receipt = json.loads(fat_receipt_path.read_text())
        image_pin = fat_receipt.get("unchanged_image") or fat_receipt.get(
            "Image507_R2"
        )
        self.assertIsNotNone(image_pin)
        self.assertEqual(
            image_pin["sha256"], manifest["image"]["sha256"]
        )
        self.assertEqual(manifest["fastboot"]["serial"], "62bc28a1")
        self.assertEqual(manifest["fastboot"]["product"], "msmnile")
        self.assertIs(manifest["fastboot"]["host_fetch_unavailable"], True)
        self.assertIs(manifest["fastboot"]["guard_carrier_readback_required"], True)
        self.assertEqual(
            manifest["fastboot"]["path"],
            r"C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe",
        )
        self.assertEqual(manifest["postboot"]["apsd_vbus_min_uv"], 4_400_000)
        self.assertEqual(manifest["postboot"]["apsd_vbus_max_uv"], 5_500_000)
        self.assertEqual(
            manifest["postboot"]["measured_sdp_vbus_min_uv"], 4_511_408
        )
        self.assertEqual(
            manifest["postboot"]["measured_sdp_vbus_max_uv"], 4_672_304
        )
        self.assertEqual(
            manifest["postboot"]["typec_supply_property_check"],
            "presence of charger@5c/typec-supply",
        )
        self.assertEqual(
            manifest["postboot"]["adc_label_property_check"],
            "adc@3100/channel@8/label == usb_in_v_div_16",
        )

        required_targets = {
            "/usr/lib/samurai-charging/trial_common.py",
            "/usr/lib/samurai-charging/trial_guard.py",
            "/usr/lib/samurai-charging/postboot_audit.py",
            "/usr/lib/samurai-charging/trial_autoaudit.py",
            "/etc/init.d/samurai-charging",
        }
        self.assertEqual(set(manifest["device_files"]), required_targets)
        expected_modes = {
            "/usr/lib/samurai-charging/trial_common.py": 0o644,
            "/usr/lib/samurai-charging/trial_guard.py": 0o755,
            "/usr/lib/samurai-charging/postboot_audit.py": 0o644,
            "/usr/lib/samurai-charging/trial_autoaudit.py": 0o755,
            "/etc/init.d/samurai-charging": 0o755,
        }
        for target, row in manifest["device_files"].items():
            source = TRIAL_DIR / row["source"]
            self.assertTrue(source.is_file(), source)
            self.assertEqual(trial_common.sha256_file(source), row["sha256"])
            self.assertIn(row["target"], required_targets)
            self.assertEqual(row["mode"], expected_modes[target])
        module = manifest["kernel_module"]
        self.assertEqual(
            module,
            {
                "name": trial_common.MODULE_NAME,
                "source": trial_common.MODULE_SOURCE,
                "target": trial_common.MODULE_PATH.as_posix(),
                "mode": trial_common.MODULE_MODE,
                "old_sha256": trial_common.MODULE_OLD_SHA256,
                "old_bytes": trial_common.MODULE_OLD_BYTES,
                "new_sha256": trial_common.MODULE_NEW_SHA256,
                "new_bytes": trial_common.MODULE_NEW_BYTES,
            },
        )
        module_source = TRIAL_DIR / module["source"]
        self.assertTrue(module_source.is_file())
        self.assertEqual(module_source.stat().st_size, module["new_bytes"])
        self.assertEqual(trial_common.sha256_file(module_source), module["new_sha256"])
        self.assertEqual(
            manifest["main_manifest"],
            {
                "old_sha256": trial_common.MAIN_MANIFEST_SHA256,
                "service_target": trial_common.SERVICE_PATH.as_posix(),
                "target": trial_common.MAIN_MANIFEST_PATH.as_posix(),
            },
        )

        for name, size in trial_common.PARTITION_BYTES.items():
            row = manifest["carriers"][name]
            self.assertEqual(row["bytes"], size)
            self.assertEqual(row["old"], trial_common.OLD_CARRIER_SHA256[name])
            self.assertEqual(row["new"], trial_common.NEW_CARRIER_SHA256[name])
            for side in ("old", "new"):
                image = Path(row[f"{side}_path"])
                self.assertTrue(image.is_file(), image)
                self.assertEqual(image.stat().st_size, size)
                self.assertEqual(trial_common.sha256_file(image), row[side])

        dtb = manifest["dtb"]
        dtb_path = Path(dtb["path"])
        self.assertTrue(dtb_path.is_file())
        self.assertEqual(dtb["sha256"], trial_common.NEW_DTB_SHA256)
        self.assertEqual(dtb["bytes"], trial_common.NEW_DTB_BYTES)
        self.assertEqual(dtb_path.stat().st_size, trial_common.NEW_DTB_BYTES)
        self.assertEqual(trial_common.sha256_file(dtb_path), dtb["sha256"])
        self.assertIs(dtb["embedded_in_boot"], True)
        self.assertIn(b"realme,apsd-handoff-trial", dtb_path.read_bytes())

        runtime_dtb = manifest["runtime_dtb"]
        runtime_path = Path(runtime_dtb["path"])
        self.assertTrue(runtime_path.is_file())
        self.assertEqual(runtime_dtb["sha256"], trial_common.RUNTIME_DTB_SHA256)
        self.assertEqual(runtime_dtb["bytes"], trial_common.RUNTIME_DTB_BYTES)
        self.assertEqual(runtime_path.stat().st_size, trial_common.RUNTIME_DTB_BYTES)
        self.assertEqual(
            trial_common.sha256_file(runtime_path), runtime_dtb["sha256"]
        )
        self.assertEqual(runtime_dtb["fat_path"], "::/samurai.dtb")
        self.assertEqual(
            runtime_dtb["fat_receipt_sha256"],
            trial_common.sha256_file(Path(runtime_dtb["fat_receipt_path"])),
        )
        for feature in (
            b"typec-supply",
            b"usb_in_v_div_16",
            b"realme,apsd-handoff-trial",
        ):
            self.assertIn(feature, runtime_path.read_bytes())

        receipt_pin = manifest["boot_receipt"]
        receipt_path = Path(receipt_pin["path"])
        self.assertTrue(receipt_path.is_file())
        self.assertEqual(receipt_pin["bytes"], receipt_path.stat().st_size)
        self.assertEqual(receipt_pin["sha256"], trial_common.sha256_file(receipt_path))
        receipt = json.loads(receipt_path.read_text())
        self.assertIs(receipt["passed"], True)
        self.assertEqual(receipt["boot_sha256"], manifest["carriers"]["boot"]["new"])
        self.assertEqual(receipt["native_DTB_sha256"], dtb["sha256"])
        self.assertTrue(
            receipt["boot_path"].replace("\\", "/").endswith(
                receipt_pin["boot_path_suffix"].replace("\\", "/")
            )
        )
        dtb_suffix = receipt_pin["dtb_path_suffix"].replace("\\", "/")
        for side in ("parent_inputs_before", "parent_inputs_after"):
            matches = [
                value
                for name, value in receipt[side].items()
                if name.replace("\\", "/").endswith(dtb_suffix)
                and value == dtb["sha256"]
            ]
            self.assertEqual(len(matches), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
