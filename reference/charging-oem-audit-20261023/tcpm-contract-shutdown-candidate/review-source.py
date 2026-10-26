"""Bind the review patch, exact ABI structure, tests and objects to final sources."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
OLD = HERE.parent
baseline = {n: OLD / "tcpm-sink-shutdown-candidate" / n for n in [
    "qcom_pmic_typec.c", "qcom_pmic_typec.h", "qcom_pmic_typec_pdphy.c",
    "qcom_pmic_typec_pdphy.h", "qcom_pmic_typec_port.h"]}
baseline.update({n: OLD / "tcpm-usb-budget-candidate" / n for n in [
    "tcpm.c", "qcom_pmic_typec_port.c"]})
baseline["tcpm.h"] = HERE / "tcpm.h.baseline"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tcpc_struct(path):
    text = path.read_text()
    start = text.index("struct tcpc_dev {")
    return text[start:text.index("\n};", start) + 3].encode()


original_struct = tcpc_struct(HERE / "tcpm.h.baseline")
candidate_struct = tcpc_struct(HERE / "tcpm.h")
assert original_struct == candidate_struct
rows, patch = {}, []
for name, previous in baseline.items():
    prefix = "include/linux/usb/" if name == "tcpm.h" else \
        "drivers/usb/typec/tcpm/" if name == "tcpm.c" else "drivers/usb/typec/tcpm/qcom/"
    target = prefix + name
    rows[target] = dict(file=name, baseline=str(previous), baseline_sha256=sha(previous),
                        candidate_sha256=sha(HERE / name))
    patch.extend(difflib.unified_diff(previous.read_text().splitlines(True),
                                    (HERE / name).read_text().splitlines(True),
                                    fromfile="a/" + target, tofile="b/" + target))
(HERE / "shutdown-contract.patch").write_text("".join(patch))
tests = {n: json.loads((HERE / n).read_text()) for n in [
    "test-contract-result.json", "test-qcom-result.json", "test-adc-result.json"]}
assert all(t["passed"] for t in tests.values())
assert tests["test-contract-result.json"]["source_sha256"] == sha(HERE / "tcpm.c")
for name, digest in tests["test-qcom-result.json"]["source_sha256"].items():
    assert digest == sha(HERE / name)
assert tests["test-adc-result.json"]["source_sha256"] == sha(HERE / "qcom_pmic_typec_port.c")
build = json.loads((HERE / "build-result.json").read_text())
assert build["passed"] and build["parent_mounts_unchanged"]
for name, digest in build["build"]["source_sha256"].items():
    assert digest == sha(HERE / name)
result = dict(
    passed=True, sources=rows,
    tcpc_dev_layout_byte_identical=True,
    tcpc_dev_layout_proof=dict(
        bytes=len(original_struct),
        baseline_sha256=hashlib.sha256(original_struct).hexdigest(),
        candidate_sha256=hashlib.sha256(candidate_struct).hexdigest()),
    tests_bound_to_final_sources=True, build_bound_to_final_sources=True,
    patch_sha256=sha(HERE / "shutdown-contract.patch"),
    public_API="tcpm_prepare_sink_shutdown(port, timeout_ms, read_vbus_uv, context)",
    hardware_verified=False, high_voltage_adoption_ready=False,
    remove_failure_safe_voltage_guaranteed=False,
    physical_ADC_calibration_verified=False, phone_accessed=False,
    Image_built=False, installed=False)
(HERE / "source-review.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: result[k] for k in ["passed", "tcpc_dev_layout_proof", "hardware_verified"]}))
