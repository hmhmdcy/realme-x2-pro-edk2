"""Prepare, render and validate a worker-only Camss wire-compatible draft."""
from pathlib import Path
import difflib
import hashlib
import json
import pickle
import sys
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/"kernel449"))
import storage

build = storage.mount.mounted_build()
source = build.parent/"libcamera450-stats-retirement/src/libcamera-v0.7.2"
private = Path("/mnt/e/edk2-samurai-out/kernel450/ipa-wire-draft")
private.mkdir(mode=0o700, parents=True, exist_ok=True)
templates = source/"utils/codegen/ipc/generators/libcamera_templates"
relative_templates = templates.relative_to(source)
function_name = "proxy_functions.tmpl"
worker_name = "module_ipa_proxy_worker.cpp.tmpl"
old_function = (templates/function_name).read_text()
old_worker = (templates/worker_name).read_text()
new_function = old_function.replace(
    "macro serialize_call(params, buf, fds)",
    "macro serialize_call(params, buf, fds, camss_byte_vector = false)",
)
old_encode = """\t\tIPADataSerializer<{{param|name_full}}>::serialize({{param.mojom_name}}
{{- ", &controlSerializer_" if param|needs_control_serializer -}}
);"""
new_encode = """{%- if camss_byte_vector and param.mojom_name == "parameters" and param|name_full == "std::vector<uint8_t>" %}
\t\tcamssSerializeByteVector({{param.mojom_name}});
{%- else %}
""" + old_encode + """
{%- endif %}"""
assert new_function.count(old_encode) == 1
new_function = new_function.replace(old_encode, new_encode)
old_call = 'proxy_funcs.serialize_call(method|method_param_outputs, "_response.data()", "_response.fds()")'
new_call = 'proxy_funcs.serialize_call(method|method_param_outputs, "_response.data()", "_response.fds()", camss_byte_vector = (module_name == "camss" and method.mojom_name in ["prepareFocusedIpe", "prepareIpeParameters"]))'
assert old_worker.count(old_call) == 1
new_worker = old_worker.replace(old_call, new_call)
old_include = '#include "libcamera/internal/ipa_data_serializer.h"'
new_include = old_include + """
{%- if module_name == "camss" %}
#include "libcamera/internal/camss_byte_serializer.h"
{%- endif %}"""
assert new_worker.count(old_include) == 1
new_worker = new_worker.replace(old_include, new_include)
header_name = "include/libcamera/internal/camss_byte_serializer.h"
header = """/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include <cstdint>
#include <cstring>
#include <limits>
#include <tuple>
#include <utility>
#include <vector>
#include <libcamera/base/log.h>
#include <libcamera/base/shared_fd.h>

namespace libcamera {

/* Camss tone returns only: retain the existing vector<uint8_t> wire bytes.
 * This is not a global IPADataSerializer specialization. */
inline std::tuple<std::vector<uint8_t>, std::vector<SharedFD>>
camssSerializeByteVector(const std::vector<uint8_t> &input)
{
    ASSERT(input.size() <= (std::numeric_limits<uint32_t>::max() - 4) / 9);
    std::vector<uint8_t> result(4 + input.size() * 9);
    const uint32_t count = input.size(), one = 1, zero = 0;
    std::memcpy(result.data(), &count, sizeof count);
    for (size_t i = 0; i < input.size(); ++i) {
        uint8_t *at = result.data() + 4 + i * 9;
        std::memcpy(at, &one, sizeof one);
        std::memcpy(at + 4, &zero, sizeof zero);
        at[8] = input[i];
    }
    return std::make_tuple(std::move(result), std::vector<SharedFD>{});
}

} /* namespace libcamera */
"""
changes = {
    str(relative_templates/function_name): (old_function, new_function),
    str(relative_templates/worker_name): (old_worker, new_worker),
    header_name: ("", header),
}
patch = ""
for name, (old, new) in changes.items():
    patch += "".join(difflib.unified_diff(
        old.splitlines(keepends=True), new.splitlines(keepends=True),
        fromfile="a/"+name if old else "/dev/null", tofile="b/"+name,
    ))
    destination = private/"files"/name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(new)
(HERE/"ipa-wire-generator-draft.patch").write_text(patch)

# Render the exact cached module with the exact generator/filter functions and
# isolated template overlay; do not regenerate anything inside the source tree.
sys.path.insert(0, str(source/"utils/codegen/ipc/mojo/public/tools/mojom"))
sys.path.insert(0, str(source/"utils/codegen/ipc/generators"))
import jinja2
import mojom_libcamera_generator as generator

def render(module, template_name, overlay):
    g = generator.Generator(module)
    g.module_name = generator.ModuleClassName(module)
    loader = jinja2.ChoiceLoader([
        jinja2.DictLoader(overlay),
        jinja2.FileSystemLoader(str(templates)),
    ])
    env = jinja2.Environment(loader=loader, keep_trailing_newline=True,
                            **g.GetJinjaParameters())
    env.globals.update(g.GetGlobals())
    env.filters.update(g.GetFilters())
    return env.get_template(template_name).render(g._GetJinjaExports())

overlay = {function_name: new_function, worker_name: new_worker}
checked = []
for module_file in sorted((source/"output/include/libcamera/ipa").glob("*.mojom-module")):
    if module_file.name == "core.mojom-module":
        continue
    with module_file.open("rb") as handle:
        module = pickle.load(handle)
    module_name = generator.ModuleName(module.path)
    for template_name in (worker_name, "module_ipa_proxy.cpp.tmpl"):
        old = render(module, template_name, {})
        new = render(module, template_name, overlay)
        if template_name == worker_name:
            cached = source/f"output/src/libcamera/proxy/worker/{module_name}_ipa_proxy_worker.cpp"
        else:
            cached = source/f"output/src/libcamera/proxy/{module_name}_ipa_proxy.cpp"
        assert cached.is_file()
        cached_text = cached.read_text()
        # Meson's precompile uses Jinja's default keep_trailing_newline=False;
        # direct filesystem rendering above otherwise retains one final LF.
        if not cached_text.endswith("\n") and old.endswith("\n"):
            old = old[:-1]
            assert new.endswith("\n")
            new = new[:-1]
        assert old == cached_text, ("Cached baseline mismatch", str(cached))
        if module_name == "camss" and template_name == worker_name:
            assert old.count("IPADataSerializer<std::vector<uint8_t>>::serialize(parameters)") == 2
            assert new.count("camssSerializeByteVector(parameters)") == 2
            expected = old.replace(old_include, old_include+'\n#include "libcamera/internal/camss_byte_serializer.h"')
            expected = expected.replace("IPADataSerializer<std::vector<uint8_t>>::serialize(parameters)",
                                        "camssSerializeByteVector(parameters)")
            assert new == expected, "Unexpected generated Camss worker changes"
            (private/"camss_ipa_proxy_worker-before.cpp").write_text(old)
            (private/"camss_ipa_proxy_worker-after.cpp").write_text(new)
        else:
            assert new == old, (module_name, template_name)
        checked.append({"module": module_name, "template": template_name,
                        "changed": new != old, "baseline_matches_cached_generated": True})

proof = json.loads((HERE/"ipa-latency-validation.json").read_text())["host_wire_proof"]
assert proof and proof["passed"] and proof["proposed_encoder_preserves_existing_wire"]
result = {
    "stage": 450,
    "draft_for": 451,
    "production_tree_modified": False,
    "sdk_or_phone_accessed": False,
    "compiled": False,
    "rendered_modules": checked,
    "changed_generated_files": ["camss_ipa_proxy_worker.cpp"],
    "changed_generated_encoder_calls": 2,
    "protocol_version_6_compatible": True,
    "core_ipa_signature_mojom_unchanged": True,
    "old_decoder_reads_new_bytes": True,
    "host_wire_proof": proof,
    "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
    "passed": True,
}
(HERE/"ipa-wire-draft-validation.json").write_text(json.dumps(result, indent=2)+"\n")
print(json.dumps(result, indent=2))
