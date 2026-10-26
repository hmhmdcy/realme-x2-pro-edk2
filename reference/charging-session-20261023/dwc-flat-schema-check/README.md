# Flat USB target schema check

The unchanged flat DTB `3c66a954d94ee4e9f59aac8190272dac0f247e592aac254772b043bd9cded9ae` was checked with the fixed #503 kernel bindings and official dtschema 2026.9. The original binding rejects exactly one target property, `usb-psy-name`. A private binding copy declaring that existing string property passes the target check. Neither the frozen DT nor the driver was changed.

| Binding used | Schema document check | Target diagnostics | Result |
| --- | --- | --- | --- |
| Unmodified #503 `qcom,snps-dwc3.yaml` | rc0, empty output | One: unexpected `usb-psy-name` | Rejected; original report retained |
| Same binding plus six-line local declaration | rc0, empty output | Zero | Target accepted with the documented local extension |

`dt-validate` returns zero even when it emits a validation error. The results therefore use the actual diagnostic arrays, rather than exit status alone. See [original-result.json](original-result.json), [original-target-diagnostics.json](original-target-diagnostics.json), [local-result.json](local-result.json), and [local-target-diagnostics.json](local-target-diagnostics.json).

## Scope and original inputs

Only `/soc@0/usb@a600000`, selected by the `qcom,snps-dwc3` schema, is the validation target. The eight kernel binding files in its recursive `$ref` closure were copied byte for byte from `/home/cy122/charging-management-20261023/dwc-image503-start-recovery-01/source354/Documentation/devicetree/bindings`. The package's standard core schemas provide `types.yaml` and `graph.yaml` and the normal dtschema fixups. [binding-closure.json](binding-closure.json) pins the exact files and hashes. The USB common, DRD, XHCI/HCD/device, connector, and graph constraints remain active through their references.

Both actual runs emit the same two type-registry warnings: `extcon: missing type definition` and `usb-role-switch: missing type definition`. This limited closure does not include the unrelated kernel schemas that globally define those property types. Both properties are absent from the target raw node, as recorded by the frozen DT decoder in [target-evidence.json](target-evidence.json). The warnings are retained verbatim in both stderr reports. This is not an all-tree check or a claim that other DT nodes pass.

The local [binding patch](usb-psy-name-local-binding.patch) adds only a string type and a description for the existing native input-budget provider name. It does not remove the property, change its value, weaken `unevaluatedProperties: false`, change clocks/interrupts/reg/ports, or modify any common schema. Original binding SHA: `d6f619e153675f5bc5e66f7e142d14e4f570c839ca9d23f3a9649a6a165b727b`; patched private binding SHA: `59d6d53097c4dbe0332229ca075e794ccefd94e44fda04aae84c0341610dbf70`.

## Tools and execution

No existing dtschema installation was found in the checked WSL PATH or four existing venvs. The already cached CPython 3.14 pylibfdt wheel was reused: its `origin.json` binds the official [pylibfdt 1.7.2.post2 source archive](https://pypi.org/project/pylibfdt/1.7.2.post2/), SHA `b23d03d10ab62ad1f4e7eedde0eb8a7a8872cc08d2a5c2bba7b48bb6fd3c69f4`. The [official dtschema 2026.9 wheel](https://pypi.org/project/dtschema/2026.9/) was verified as SHA `defcbe1be176dec69c65b9700c9cd992cba3b409976a1404b9c0b5080aa5f4c1`. Binary dependency wheels were obtained from the official PyPI index; all nine exact wheel versions/hashes were locked before a `--no-index --require-hashes` install.

The venv, wheelhouse, original schemas, patched schemas, install/download logs, and original reports are private under `/home/cy122/charging-management-20261023/dwc-flat-schema-check-01`. [tool-provenance.json](tool-provenance.json) and [requirements.lock](requirements.lock) preserve package sources, versions, hashes, actual commands, and waited PIDs. System Python and the SDK were not installation targets.

The actual validation commands were:

```text
<private>/venv/bin/dt-doc-validate <all eight copied closure YAML files>
<private>/venv/bin/dt-validate -s <private>/original-bindings -l qcom,snps-dwc3 --json-output <private>/original-target-diagnostics.json <frozen-flat.dtb>
<private>/venv/bin/dt-doc-validate <all eight local-copy closure YAML files>
<private>/venv/bin/dt-validate -s <private>/local-bindings -l qcom,snps-dwc3 --json-output <private>/local-target-diagnostics.json <same-frozen-flat.dtb>
```

Original doc/target PIDs 785/790 and local doc/target PIDs 722/781 all returned rc0 after real waits. All four complete stdout/stderr streams are retained here with `.log` suffixes; [raw-artifact-map.json](raw-artifact-map.json) records the lossless mapping to the private originals. Setup used native exec session 90752, which reached exit0; validation calls also reached native exit0. There is no live tool process to resume.

This closes the target schema gap with an explicit local binding extension. It does not validate physical probe, IRQ delivery, DMA recovery, enumeration, USB current, or PM behavior. No Image, boot carrier, module, mount, SDK, device, SSH, USB, or deployment operation was performed.
