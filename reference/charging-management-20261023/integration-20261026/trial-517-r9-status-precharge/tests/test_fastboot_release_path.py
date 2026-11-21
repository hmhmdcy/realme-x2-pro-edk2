from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPERATOR = ROOT / "fastboot_operator.ps1"

IMAGE523_SHA = "c3b8ad79877bb4a00d1046fb30e110e170a690ac44b9a6cb70147322faf08e7e"
IMAGE524_SHA = "8340243e4078761a05a5de65cb132e59bd6f43854e3dc4cc4951173c078f0f6c"
ROLLBACK_523_LOGDUMP_SHA = "e0de506322cf15d2e86c2b62d12d1927f5ce25785c8b4275f93c9f58412e49a8"
ROLLBACK_524_LOGDUMP_SHA = "432ce058e0e220dbcee90db8468cd24c91f79e83e3136c42c9349abed3802721"
LOGDUMP_524_SHA = "22d2ab82d45dd3d2fe3e348c5b3c2d1373bc1ece2f0f80442dc031a210ade28e"
DTB_SHA = "d7d8a7da7a3fc68b37faceda0fd7c7f506fbbd17b7a510c15cb978b9160acf1b"
IMAGE_BYTES = 59374080
LOGDUMP_BYTES = 67108864
DTB_BYTES = 116962
REAL_FAT_06 = Path(
    r"E:\edk2-samurai-out\charging-management-20261023"
    r"\charging-integration-20261027-fat-private-06\result.json"
)
REAL_FAT_07 = Path(
    r"E:\edk2-samurai-out\charging-management-20261023"
    r"\charging-integration-20261027-fat-private-07\result.json"
)


def manifest(image_sha: str = IMAGE524_SHA, logdump_sha: str = LOGDUMP_524_SHA):
    return {
        "image": {"sha256": image_sha, "bytes": IMAGE_BYTES},
        "carriers": {
            "logdump": {"new": logdump_sha, "bytes": LOGDUMP_BYTES},
        },
        "dtb": {"sha256": DTB_SHA, "bytes": DTB_BYTES},
    }


def fat_private_06():
    return {
        "passed": True,
        "scope": "private #523 Image replacement in #518 FAT; no device access",
        "rollback_logdump_sha256": ROLLBACK_524_LOGDUMP_SHA,
        "Image523_sha256": IMAGE523_SHA,
        "logdump_bytes": LOGDUMP_BYTES,
        "logdump_sha256": ROLLBACK_523_LOGDUMP_SHA,
        "only_Image_file_changed": True,
        "Image_readback_exact": True,
        "fsck_readonly_passed": True,
        "candidate": {
            "path": "logdump-status-precharge-r9-private.img",
            "sha256": ROLLBACK_523_LOGDUMP_SHA,
            "bytes": LOGDUMP_BYTES,
        },
        "rollback": {
            "path": "logdump-tcpm-sink507-r2-private.img",
            "sha256": ROLLBACK_524_LOGDUMP_SHA,
            "bytes": LOGDUMP_BYTES,
        },
        "Image523": {"sha256": IMAGE523_SHA, "bytes": IMAGE_BYTES},
    }


def fat_private_07():
    return {
        "passed": True,
        "scope": "private #524 Image replacement in #523 FAT; no device access",
        "rollback_logdump_sha256": ROLLBACK_523_LOGDUMP_SHA,
        "Image524_sha256": IMAGE524_SHA,
        "logdump_bytes": LOGDUMP_BYTES,
        "logdump_sha256": LOGDUMP_524_SHA,
        "only_Image_file_changed": True,
        "Image_readback_exact": True,
        "fsck_readonly_passed": True,
        "candidate": {
            "path": "logdump-mp2650-r10-private.img",
            "sha256": LOGDUMP_524_SHA,
            "bytes": LOGDUMP_BYTES,
        },
        "rollback": {
            "path": "logdump-status-precharge-r9-private.img",
            "sha256": ROLLBACK_523_LOGDUMP_SHA,
            "bytes": LOGDUMP_BYTES,
        },
        "Image524": {"sha256": IMAGE524_SHA, "bytes": IMAGE_BYTES},
    }


def real_receipt_or_fixture(path: Path, fallback):
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return fallback


def old_image507_receipt():
    return {
        "passed": True,
        "Image_readback_exact": True,
        "fsck_readonly_passed": True,
        "only_Image_file_changed": True,
        "Image507_R2_sha256": IMAGE524_SHA,
        "Image507_R2": {"sha256": IMAGE524_SHA, "bytes": IMAGE_BYTES},
        "logdump_sha256": LOGDUMP_524_SHA,
        "logdump_bytes": LOGDUMP_BYTES,
        "candidate": {"sha256": LOGDUMP_524_SHA, "bytes": LOGDUMP_BYTES},
        "rollback_logdump_sha256": ROLLBACK_523_LOGDUMP_SHA,
        "rollback": {"sha256": ROLLBACK_523_LOGDUMP_SHA, "bytes": LOGDUMP_BYTES},
    }


def candidate_fat_receipt():
    return {
        "passed": True,
        "fat_integrity": {"only_dtb_file_changed": True},
        "unchanged_image": {"sha256": IMAGE524_SHA, "bytes": IMAGE_BYTES},
        "candidate_fat": {
            "sha256": LOGDUMP_524_SHA,
            "bytes": LOGDUMP_BYTES,
            "fsck": {"returncode": 0},
        },
        "candidate_dtb": {"sha256": DTB_SHA, "bytes": DTB_BYTES},
    }


def generic_candidate_receipt():
    return {
        "passed": True,
        "Image_readback_exact": True,
        "fsck_readonly_passed": True,
        "only_Image_file_changed": True,
        "candidate": {"sha256": IMAGE524_SHA, "bytes": IMAGE_BYTES},
        "logdump": {"sha256": LOGDUMP_524_SHA, "bytes": LOGDUMP_BYTES},
    }


def find_powershell() -> str | None:
    for name in ("powershell.exe", "powershell", "pwsh.exe", "pwsh"):
        path = shutil.which(name)
        if path:
            return path
    return None


class FastbootReleasePathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.powershell = find_powershell() if os.name == "nt" else None

    def setUp(self):
        if os.name != "nt":
            self.skipTest("PowerShell operator execution tests run on Windows")
        if self.powershell is None:
            self.skipTest("PowerShell is required for operator execution tests")

    def invoke(self, body: str, receipt, manifest_data, expected_failure: bool = False):
        with tempfile.TemporaryDirectory(prefix="fastboot-release-test-") as raw:
            temp = Path(raw)
            receipt_path = temp / "receipt.json"
            manifest_path = temp / "manifest.json"
            wrapper_path = temp / "wrapper.ps1"
            receipt_path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
            manifest_path.write_text(json.dumps(manifest_data) + "\n", encoding="utf-8")
            wrapper_path.write_text(
                r'''
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $env:FASTBOOT_OPERATOR_PATH,
    [ref]$tokens,
    [ref]$parseErrors
)
if ($parseErrors.Count -ne 0) {
    throw (($parseErrors | ForEach-Object { $_.Message }) -join '; ')
}
$definitions = $ast.FindAll(
    { param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] },
    $true
)
foreach ($definition in $definitions) {
    . ([scriptblock]::Create($definition.Extent.Text))
}
$script:ExpectedProductionManifestSha256 = [string]$env:SAMURAI_EXPECTED_PRODUCTION_MANIFEST_SHA256
$script:ExpectedProductionImageSha256 = [string]$env:SAMURAI_EXPECTED_PRODUCTION_IMAGE_SHA256
$receipt = Get-Content -LiteralPath $env:FASTBOOT_RECEIPT_PATH -Raw | ConvertFrom-Json
$manifest = Get-Content -LiteralPath $env:FASTBOOT_MANIFEST_PATH -Raw | ConvertFrom-Json
try {
    $result = $null
    BODY
    if ($null -eq $result) {
        $result = [pscustomobject]@{ threw = $false }
    }
}
catch {
    $result = [pscustomobject]@{
        threw = $true
        message = $_.Exception.Message
    }
}
$result | ConvertTo-Json -Depth 12 -Compress
'''.replace("BODY", body),
                encoding="utf-8",
            )
            env = dict(os.environ)
            env["FASTBOOT_OPERATOR_PATH"] = str(OPERATOR)
            env["FASTBOOT_RECEIPT_PATH"] = str(receipt_path)
            env["FASTBOOT_MANIFEST_PATH"] = str(manifest_path)
            env.pop("SAMURAI_EXPECTED_PRODUCTION_MANIFEST_SHA256", None)
            env.pop("SAMURAI_EXPECTED_PRODUCTION_IMAGE_SHA256", None)
            completed = subprocess.run(
                [
                    self.powershell,
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(wrapper_path),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        if completed.returncode != 0:
            self.fail(
                f"PowerShell wrapper failed ({completed.returncode})\n"
                f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            self.fail(f"invalid PowerShell output: {error}\n{completed.stdout}\n{completed.stderr}")
        if result.get("threw") and not expected_failure:
            self.fail(result.get("message", "PowerShell function threw"))
        return result

    def test_real_fat_private_06_schema_selects_image523_not_candidate(self):
        result = self.invoke(
            r'''
$pin = Get-FatReceiptImagePin -FatReceipt $receipt
Assert-FatReceiptAgainstManifest -FatReceipt $receipt -ManifestData $manifest
$result = [pscustomobject]@{
    source = $pin.source
    sha256 = $pin.sha256
}
''',
            real_receipt_or_fixture(REAL_FAT_06, fat_private_06()),
            manifest(IMAGE523_SHA, ROLLBACK_523_LOGDUMP_SHA),
        )
        self.assertEqual("Image523", result["source"])
        self.assertEqual(IMAGE523_SHA, result["sha256"])

    def test_real_fat_private_07_schema_selects_image524_not_logdump_candidate(self):
        result = self.invoke(
            r'''
$pin = Get-FatReceiptImagePin -FatReceipt $receipt
Assert-FatReceiptAgainstManifest -FatReceipt $receipt -ManifestData $manifest
$result = [pscustomobject]@{
    source = $pin.source
    sha256 = $pin.sha256
}
''',
            real_receipt_or_fixture(REAL_FAT_07, fat_private_07()),
            manifest(),
        )
        self.assertEqual("Image524", result["source"])
        self.assertEqual(IMAGE524_SHA, result["sha256"])

    def test_manifest_image_pin_mismatch_is_rejected(self):
        result = self.invoke(
            r'''
try {
    Assert-FatReceiptAgainstManifest -FatReceipt $receipt -ManifestData $manifest
    $result = [pscustomobject]@{ threw = $false }
}
catch {
    $result = [pscustomobject]@{ threw = $true; message = $_.Exception.Message }
}
''',
            fat_private_07(),
            manifest(IMAGE523_SHA, LOGDUMP_524_SHA),
            expected_failure=True,
        )
        self.assertTrue(result["threw"])
        self.assertIn("Image pin mismatch", result["message"])

    def test_old_image507_schema_is_supported(self):
        result = self.invoke(
            r'''
$pin = Get-FatReceiptImagePin -FatReceipt $receipt
Assert-FatReceiptAgainstManifest -FatReceipt $receipt -ManifestData $manifest
$result = [pscustomobject]@{ source = $pin.source; sha256 = $pin.sha256 }
''',
            old_image507_receipt(),
            manifest(),
        )
        self.assertEqual("Image507_R2", result["source"])
        self.assertEqual(IMAGE524_SHA, result["sha256"])

    def test_old_candidate_fat_schema_is_supported(self):
        result = self.invoke(
            r'''
$pin = Get-FatReceiptImagePin -FatReceipt $receipt
Assert-FatReceiptAgainstManifest -FatReceipt $receipt -ManifestData $manifest
$result = [pscustomobject]@{ source = $pin.source; sha256 = $pin.sha256 }
''',
            candidate_fat_receipt(),
            manifest(),
        )
        self.assertEqual("unchanged_image", result["source"])
        self.assertEqual(IMAGE524_SHA, result["sha256"])

    def test_generic_candidate_image_schema_is_supported(self):
        result = self.invoke(
            r'''
$pin = Get-FatReceiptImagePin -FatReceipt $receipt
Assert-FatReceiptAgainstManifest -FatReceipt $receipt -ManifestData $manifest
$result = [pscustomobject]@{ source = $pin.source; sha256 = $pin.sha256 }
''',
            generic_candidate_receipt(),
            manifest(),
        )
        self.assertEqual("candidate", result["source"])
        self.assertEqual(IMAGE524_SHA, result["sha256"])

    def test_host_fetch_unavailable_defaults_to_no_fetch(self):
        receipt = fat_private_07()
        receipt["host_fetch_unavailable"] = True
        result = self.invoke(
            r'''
$policy = Resolve-FetchPolicy -Receipt $receipt -ExplicitNoFetch $false
$result = [pscustomobject]@{
    no_fetch = [bool]$policy.no_fetch
    host_fetch_unavailable = [bool]$policy.host_fetch_unavailable
}
''',
            receipt,
            manifest(),
        )
        self.assertTrue(result["no_fetch"])
        self.assertTrue(result["host_fetch_unavailable"])

    def test_explicit_no_fetch_with_fetchable_host_is_rejected(self):
        receipt = fat_private_07()
        receipt["host_fetch_unavailable"] = False
        result = self.invoke(
            r'''
try {
    $null = Resolve-FetchPolicy -Receipt $receipt -ExplicitNoFetch $true
    $result = [pscustomobject]@{ threw = $false }
}
catch {
    $result = [pscustomobject]@{ threw = $true; message = $_.Exception.Message }
}
''',
            receipt,
            manifest(),
            expected_failure=True,
        )
        self.assertTrue(result["threw"])
        self.assertIn("host_fetch_unavailable=true", result["message"])

    def test_manifest_image_pin_is_authoritative_without_a_script_pin(self):
        result = self.invoke(
            r'''
$script:ExpectedProductionImageSha256 = ''
$pin = Assert-ProductionImagePin -ManifestData $manifest -IsProductionManifest $true
$result = [pscustomobject]@{ sha256 = $pin }
''',
            fat_private_07(),
            manifest(),
        )
        self.assertEqual(IMAGE524_SHA, result["sha256"])

    def test_optional_script_pin_is_only_a_consistency_check(self):
        result = self.invoke(
            r'''
try {
    $script:ExpectedProductionImageSha256 = '0000000000000000000000000000000000000000000000000000000000000000'
    $null = Assert-ProductionImagePin -ManifestData $manifest -IsProductionManifest $true
    $result = [pscustomobject]@{ threw = $false }
}
catch {
    $result = [pscustomobject]@{ threw = $true; message = $_.Exception.Message }
}
''',
            fat_private_07(),
            manifest(),
            expected_failure=True,
        )
        self.assertTrue(result["threw"])
        self.assertIn("configured consistency pin", result["message"])

    def test_operator_entry_auto_selects_no_fetch_from_receipt(self):
        import test_trial_suite as suite

        with tempfile.TemporaryDirectory(prefix="fastboot-entry-no-fetch-") as raw:
            fixture = suite.make_fastboot_fixture(
                Path(raw), host_fetch_unavailable=True
            )
            result, report = suite.run_fastboot_operator(
                fixture,
                fixture["base"] / "work",
                execute=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(report["passed"])
        self.assertTrue(report["no_fetch"])
        self.assertTrue(report["host_fetch_unavailable"])
        self.assertFalse(report["device_touched"])

    def test_operator_entry_accepts_versioned_receipt(self):
        import test_trial_suite as suite

        with tempfile.TemporaryDirectory(prefix="fastboot-entry-versioned-") as raw:
            fixture = suite.make_fastboot_fixture(
                Path(raw), host_fetch_unavailable=True
            )
            fat_receipt_path = fixture["fat_receipt_path"]
            fat_receipt = json.loads(fat_receipt_path.read_text(encoding="utf-8"))
            fat_receipt["Image524_sha256"] = fat_receipt.pop("Image507_R2_sha256")
            fat_receipt["Image524"] = fat_receipt.pop("Image507_R2")
            fat_receipt_path.write_text(
                json.dumps(fat_receipt, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            fixture["manifest"]["image"]["fat_receipt_sha256"] = suite.sha(
                fat_receipt_path
            )
            fixture["manifest_path"].write_text(
                json.dumps(fixture["manifest"], indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            stage_receipt = json.loads(
                fixture["receipt_path"].read_text(encoding="utf-8")
            )
            stage_receipt["manifest_sha256"] = suite.sha(fixture["manifest_path"])
            fixture["receipt_path"].write_text(
                json.dumps(stage_receipt, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            result, report = suite.run_fastboot_operator(
                fixture,
                fixture["base"] / "work",
                execute=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(report["passed"])
        self.assertEqual(report["outcome"], "local_validation_only")

    def test_operator_has_no_release_specific_523_image_pin(self):
        text = OPERATOR.read_text(encoding="utf-8")
        self.assertNotIn(IMAGE523_SHA, text)
        self.assertNotIn("production #523 Image", text)


if __name__ == "__main__":
    unittest.main()
