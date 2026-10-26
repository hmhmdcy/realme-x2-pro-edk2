"""Offline 449 IPC phase correlation; no phone, SDK, compilation or source edit."""
from pathlib import Path
import bisect
import collections
import hashlib
import importlib.util
import json
import re
import statistics
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / "kernel449"
sys.path.insert(0, str(PREV))
import storage

PRIVATE = Path("/mnt/e/edk2-samurai-out/kernel450")
LOG = Path("/mnt/e/edk2-samurai-out/kernel449/runtime-collected-r2/user-sustained-1080/client.log")


def summary(us):
    values = sorted(us)
    assert values
    return {
        "n": len(values),
        "median_ms": round(statistics.median(values) / 1000, 3),
        "p95_ms": round(values[min(len(values)-1, len(values)*95//100)] / 1000, 3),
        "p99_ms": round(values[min(len(values)-1, len(values)*99//100)] / 1000, 3),
        "maximum_ms": round(values[-1] / 1000, 3),
    }


text = LOG.read_text()
frames = collections.defaultdict(dict)
host_events = []
consumed = []
resync = []
stamp_re = re.compile(r"^\[(\d+):(\d+):(\d+)\.(\d{9})\] \[(\d+)\]")
field_re = re.compile(r"([a-z][a-z0-9-]*)=([^ ]+)")
markers = {
    "af": "AF frame ",
    "tone": "IPE_TONE_PREPARE ",
    "bootstrap": "IPE_TONE_BOOTSTRAP ",
    "ccm": "IPE_CCM_PREPARE ",
    "return": "FRAME_IPA_PREPARE ",
    "pair": "IPE_PAIR ",
    "pd10": "PD10_READY ",
    "observe": "IPE_OBSERVE ",
    "queue": "IPE_TONE_QUEUE ",
    "receipt": "IPE_RECEIPT ",
    "focus": "FOCUS_EXECUTION ",
}
for line in text.splitlines():
    fields = dict(field_re.findall(line))
    if line.startswith("GST_IMAGE "):
        consumed.append(int(fields["sequence"]))
    match = stamp_re.match(line)
    if not match:
        continue
    h, m, sec, ns, tid = map(int, match.groups())
    timestamp = ((h*60+m)*60+sec)*10**9+ns
    if "Resynced image/request mapping " in line:
        resync.append(timestamp)
    if "CamssVfe " in line:
        host_events.append((timestamp, line.split(".cpp:", 1)[-1].split(" ", 1)[-1].split(" ", 1)[0]))
    if "sof" not in fields:
        continue
    sof = int(fields["sof"])
    for label, marker in markers.items():
        if marker not in line:
            continue
        if label == "receipt" and fields.get("success") != "1":
            continue
        assert label not in frames[sof], (sof, label)
        frames[sof][label] = {"ns": timestamp, "tid": tid, "fields": fields}

assert len(consumed) == len(set(consumed)) == 9000
assert consumed == sorted(consumed)
host_events.sort()
host_stamps = [t for t, marker in host_events]
rows = []
for sof in consumed:
    row = frames[sof]
    end = row["return"]["ns"]
    dispatch_us = int(row["return"]["fields"]["dispatch-us"])
    begin = end - dispatch_us*1000
    af = row["af"]["ns"]
    tone = row.get("tone", row.get("bootstrap"))
    assert tone is not None
    last_tone = max(tone["ns"], row.get("ccm", tone)["ns"])
    # Log stamps bracket phases, not precise method entry/return CPU accounting.
    assert begin <= af <= tone["ns"] <= last_tone <= end, sof
    a = bisect.bisect_left(host_stamps, begin)
    b = bisect.bisect_right(host_stamps, end)
    nested = collections.Counter(marker for _, marker in host_events[a:b] if marker not in ("FRAME_IPA_PREPARE",))
    f = row["focus"]["fields"]
    rows.append({
        "sof": sof,
        "dispatch_us": dispatch_us,
        "estimated_call_to_af_log_us": (af-begin)/1000,
        "af_to_tone_log_us": (last_tone-af)/1000,
        "tone_log_to_host_return_log_us": (end-last_tone)/1000,
        "focus_sample_us": int(f["sample-wall-us"]),
        "focus_sample_cpu_us": int(f["sample-cpu-us"]),
        "host_events_during_dispatch": dict(nested),
    })

missing = [sof for a, b in zip(consumed, consumed[1:]) for sof in range(a+1, b)]
by_sof = {row["sof"]: row for row in rows}
near = sorted({sof for gap in missing for sof in range(gap-4, gap+3) if sof in by_sof})
metric_keys = [
    "dispatch_us", "estimated_call_to_af_log_us", "af_to_tone_log_us",
    "tone_log_to_host_return_log_us", "focus_sample_us", "focus_sample_cpu_us",
]
all_summary = {key: summary([row[key] for row in rows]) for key in metric_keys}
near_summary = {key: summary([by_sof[sof][key] for sof in near]) for key in metric_keys}
slow = [row for row in rows if row["dispatch_us"] >= 25000]
slow_summary = {key: summary([row[key] for row in slow]) for key in metric_keys}
counter = collections.Counter()
for row in slow:
    counter.update(row["host_events_during_dispatch"])
gap_lead = {
    str(k): {
        "samples": sum(g-k in by_sof for g in missing),
        "dispatch_ge_25ms": sum(by_sof.get(g-k, {}).get("dispatch_us", 0) >= 25000 for g in missing),
        "tail_ge_20ms": sum(by_sof.get(g-k, {}).get("tone_log_to_host_return_log_us", 0) >= 20000 for g in missing),
    }
    for k in (1, 2, 3, 4)
}
gap_lead["any_last_four_dispatch_ge_25ms"] = sum(
    any(by_sof.get(g-k, {}).get("dispatch_us", 0) >= 25000 for k in (1, 2, 3, 4))
    for g in missing
)

# All ext4 access, including output/generated files, starts after the mount guard.
build = storage.mount.mounted_build()
source = build.parent / "libcamera448-capacity-lease/src/libcamera-v0.7.2"
source_files = [
    "include/libcamera/internal/ipa_data_serializer.h",
    "src/libcamera/ipa_data_serializer.cpp",
    "output/src/libcamera/proxy/worker/camss_ipa_proxy_worker.cpp",
    "output/src/libcamera/proxy/camss_ipa_proxy.cpp",
    "src/ipa/camss-vfe/camss.cpp",
    "src/libcamera/ipc_pipe_unixsocket.cpp",
    "src/libcamera/pipeline/camss-vfe/camss_vfe.cpp",
]
source_hashes = {name: hashlib.sha256((source/name).read_bytes()).hexdigest() for name in source_files}
source450 = build.parent / "libcamera450-stats-retirement/src/libcamera-v0.7.2"
unchanged450 = {
    name: (source450/name).is_file() and hashlib.sha256((source450/name).read_bytes()).hexdigest() == source_hashes[name]
    for name in source_files
    if name != "src/libcamera/pipeline/camss-vfe/camss_vfe.cpp"
}
assert all(unchanged450.values())
serializer = (source/source_files[0]).read_text()
assert "for (const auto &value : data)" in serializer
assert "IPADataSerializer<V>::serialize(value, cs)" in serializer
assert "appendPOD<uint32_t>(dataVec, dvec.size());" in serializer
assert "appendPOD<uint32_t>(dataVec, fvec.size());" in serializer
assert "IPADataSerializer<std::vector<uint8_t>>::serialize(parameters)" in (source/source_files[2]).read_text()
assert "IPADataSerializer<std::vector<uint8_t>>::deserialize(" in (source/source_files[3]).read_text()
assert (source/source_files[2]).read_text().count("IPADataSerializer<std::vector<uint8_t>>::serialize(parameters)") == 2
assert (source/source_files[3]).read_text().count("IPADataSerializer<std::vector<uint8_t>>::deserialize(") == 2
assert (source/"include/libcamera/ipa/camss.mojom").read_text().count("array<uint8> parameters") == 2
u8_vector = re.compile(r"IPADataSerializer\s*<\s*std::vector\s*<\s*uint8_t\s*>\s*>")
assert not [
    q for root in (source/"include", source/"output/include")
    for q in root.rglob("*.h") if u8_vector.search(q.read_text())
], "Unexpected header specialization must be audited first"
packet_bytes = {int(frames[sof]["tone"]["fields"]["bytes"]) for sof in consumed if "tone" in frames[sof]}
assert packet_bytes == {6008}

wire_proof = None
if "--wire-probe" in sys.argv:
    # Compile only an isolated native host executable. The vector template,
    # arithmetic helpers, primary declaration and scalar POD macro are copied
    # verbatim from the exact retained source; no SDK or libcamera tree writes.
    pod_source = (source/"src/libcamera/ipa_data_serializer.cpp").read_text()
    exact_template = serializer[
        serializer.index("namespace {\n"):
        serializer.index("/*\n * Serialization format for map")
    ].replace("#ifndef __DOXYGEN__", "")
    exact_pod = pod_source[
        pod_source.index("#define DEFINE_POD_SERIALIZER(type)"):
        pod_source.index("DEFINE_POD_SERIALIZER(bool)")
    ] + "\nDEFINE_POD_SERIALIZER(uint8_t)\n"
    preamble = r"""
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>
#define ASSERT assert
struct SharedFD {};
struct ControlSerializer {};
static uint64_t allocations = 0;
void *operator new(std::size_t n) {
    ++allocations;
    if (void *p = std::malloc(n ? n : 1)) return p;
    throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void *p) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }
"""
    program = r"""
// Draft private Camss encoder: identical existing vector wire representation.
static std::tuple<std::vector<uint8_t>, std::vector<SharedFD>>
camssSerializeByteVector(const std::vector<uint8_t> &input)
{
    assert(input.size() <= UINT32_MAX);
    std::vector<uint8_t> result(4 + input.size()*9);
    const uint32_t count = input.size(), one = 1, zero = 0;
    std::memcpy(result.data(), &count, sizeof count);
    for (std::size_t i = 0; i < input.size(); ++i) {
        uint8_t *at = result.data() + 4 + i*9;
        std::memcpy(at, &one, sizeof one);
        std::memcpy(at+4, &zero, sizeof zero);
        at[8] = input[i];
    }
    return std::make_tuple(std::move(result), std::vector<SharedFD>{});
}

int main()
{
    std::printf("{\"cases\":[");
    bool first = true;
    for (std::size_t length : {0, 1, 16, 256, 6008}) {
        std::vector<uint8_t> input(length);
        for (std::size_t i = 0; i < length; ++i) input[i] = (i*73+17)&255;
        allocations = 0;
        auto [oldBytes, oldFds] =
            IPADataSerializer<std::vector<uint8_t>>::serialize(input);
        const uint64_t oldAllocations = allocations;
        allocations = 0;
        auto [newBytes, newFds] = camssSerializeByteVector(input);
        const uint64_t newAllocations = allocations;
        assert(oldFds.empty() && newFds.empty() && oldBytes == newBytes);
        auto roundTrip = IPADataSerializer<std::vector<uint8_t>>::deserialize(newBytes);
        assert(roundTrip == input);
        assert(oldBytes.size() == 4+length*9);
        assert(newAllocations == 1);
        std::printf("%s{\"bytes\":%zu,\"wire_bytes\":%zu,\"old_allocations\":%llu,\"fast_allocations\":%llu}",
                    first ? "" : ",", length, oldBytes.size(),
                    (unsigned long long)oldAllocations, (unsigned long long)newAllocations);
        first = false;
    }
    std::vector<uint8_t> input(6008, 0xc7);
    constexpr int repetitions = 100;
    volatile uint64_t checksum = 0;
    auto start = std::chrono::steady_clock::now();
    for (int i = 0; i < repetitions; ++i) {
        auto [bytes, fds] = IPADataSerializer<std::vector<uint8_t>>::serialize(input);
        checksum = checksum + bytes[i];
    }
    const auto oldEnd = std::chrono::steady_clock::now();
    for (int i = 0; i < repetitions; ++i) {
        auto [bytes, fds] = camssSerializeByteVector(input);
        checksum = checksum + bytes[i];
    }
    const auto newEnd = std::chrono::steady_clock::now();
    std::printf("],\"old_100_calls_us\":%lld,\"fast_100_calls_us\":%lld,\"checksum\":%llu,\"passed\":true}\n",
        (long long)std::chrono::duration_cast<std::chrono::microseconds>(oldEnd-start).count(),
        (long long)std::chrono::duration_cast<std::chrono::microseconds>(newEnd-oldEnd).count(),
        (unsigned long long)checksum);
}
"""
    work = PRIVATE/"ipa-wire-proof"
    work.mkdir(mode=0o700, parents=True, exist_ok=True)
    proof_source = work/"wire-proof.cpp"
    proof_source.write_text(preamble + exact_template + exact_pod + program)
    compiler = ["g++", "-O2", "-std=c++20", "-Wall", "-Wextra", "-Werror",
                "-Wno-mismatched-new-delete", str(proof_source), "-o", str(work/"wire-proof")]
    subprocess.run(compiler, check=True, capture_output=True, text=True)
    wire_proof = json.loads(subprocess.check_output([str(work/"wire-proof")], text=True))
    wire_proof.update({
        "source_sha256": hashlib.sha256(proof_source.read_bytes()).hexdigest(),
        "exact_source_template_and_uint8_pod_macro": True,
        "synthetic_bytes_only": True,
        "host_timing_not_arm_or_camera_timing": True,
        "proposed_encoder_preserves_existing_wire": True,
    })
    (PRIVATE/"ipa-wire-proof-private.json").write_text(json.dumps(wire_proof, indent=2)+"\n")

result = {
    "stage": 450,
    "scope": "offline-only analysis of unchanged 448 core in 449 r2",
    "frames": 9000,
    "missing_sofs": len(missing),
    "missing_sofs_with_statistics_and_pd10_without_pair": sum(
        "observe" in frames[sof] and "pd10" in frames[sof] and "pair" not in frames[sof]
        for sof in missing
    ),
    "phase_definitions": {
        "estimated_call_to_af_log_us": "FRAME_IPA_PREPARE timestamp minus dispatch-us estimates call entry; AF log is after AF state processing",
        "af_to_tone_log_us": "AF log to last same-SOF tone/CCM log; most numeric tone work is inside this bracket",
        "tone_log_to_host_return_log_us": "last tone/CCM log to pipeline return log; includes serialization, IPC, deserialization, scheduling and nested events",
    },
    "all_frames": all_summary,
    "frames_near_missing_sofs": {"n": len(near), "metrics": near_summary},
    "gap_lead_correlation": gap_lead,
    "slow_dispatch": {"threshold_ms": 25, "frames": len(slow), "metrics": slow_summary, "host_markers_during_dispatch": dict(counter)},
    "wire_field": {
        "packet_bytes": 6008,
        "serialized_vector_bytes": 4 + 6008*(4+4+1),
        "per_element_temporary_vectors": 6008,
        "wire_layout_may_be_preserved_by_specialized_encoder": True,
    },
    "host_wire_proof": wire_proof,
    "resync_mapping_events": len(resync),
    "source_sha256": source_hashes,
    "relevant_450_sources_identical": unchanged450,
    "vector_uint8_header_specializations_found": 0,
    "actual_parameter_vector_encoder_calls": 2,
    "actual_parameter_vector_decoder_calls": 2,
    "cpu_time_or_actual_worker_cpu_not_measured": True,
    "full_buffer_queue_starvation_not_proven": True,
    "drop_root_cause_proven": False,
    "production_source_changed": False,
    "phone_or_sdk_accessed": False,
    "passed": True,
}
PRIVATE.mkdir(mode=0o700, exist_ok=True)
(PRIVATE/"ipa-latency-analysis-private.json").write_text(json.dumps({
    "log_sha256": hashlib.sha256(LOG.read_bytes()).hexdigest(),
    "rows": rows,
    "missing_sofs": missing,
    "near_missing_sofs": near,
}, indent=2)+"\n")
(HERE/"ipa-latency-validation.json").write_text(json.dumps(result, indent=2)+"\n")
print(json.dumps(result, indent=2))
