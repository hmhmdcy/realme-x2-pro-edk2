from __future__ import annotations

import sys
import unittest
from pathlib import Path


TRIAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TRIAL_DIR))

import trial_common  # noqa: E402


class ProductionManifestTests(unittest.TestCase):
    def test_manifest_pins_bundled_files_and_real_carriers(self) -> None:
        manifest = trial_common.read_json(TRIAL_DIR / "manifest.json")
        self.assertEqual(manifest["schema"], 1)
        self.assertEqual(manifest["trial_id"], trial_common.TRIAL_ID)
        self.assertEqual(manifest["kernel_version"], trial_common.VERSION)
        self.assertEqual(manifest["watch_seconds"], 300)
        self.assertEqual(manifest["token"], trial_common.TOKEN)
        self.assertIs(manifest["high_voltage_permitted"], False)
        self.assertEqual(manifest["fastboot"]["serial"], "62bc28a1")
        self.assertEqual(manifest["fastboot"]["product"], "msmnile")
        self.assertEqual(
            manifest["fastboot"]["path"],
            r"C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe",
        )

        required_targets = {
            "/usr/lib/samurai-charging/trial_common.py",
            "/usr/lib/samurai-charging/trial_guard.py",
            "/etc/init.d/samurai-charging",
        }
        self.assertEqual(set(manifest["device_files"]), required_targets)
        for row in manifest["device_files"].values():
            source = TRIAL_DIR / row["source"]
            self.assertTrue(source.is_file(), source)
            self.assertEqual(trial_common.sha256_file(source), row["sha256"])
            self.assertIn(row["target"], required_targets)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
