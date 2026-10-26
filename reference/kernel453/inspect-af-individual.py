"""Read-only cached telephoto AF individual-data audit. No phone or SDK."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import math
import os
import re
import struct
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
P = Path("/mnt/e/edk2-samurai-out")
spec = importlib.util.spec_from_file_location("af_individual_storage449", HERE.parent / "kernel449/storage.py")
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
BUILD = storage.mount.mounted_build()
PRIVATE = P / "kernel453/af-individual"
PRIVATE.mkdir(exist_ok=True)

source450 = ast.parse((HERE.parent / "kernel450/inspect-lens-scope.py").read_text())
node = next(node for node in source450.body if isinstance(node, ast.ClassDef) and node.name == "Description")
exec(compile(ast.Module(body=[node], type_ignores=[]), "retained450-description", "exec"))

HAL = P / "kernel281/camera.qcom.so-private"
HAL_SHA = "e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde"
DESCRIPTION = P / "kernel326/qtech_s5k3m5sx-description-private.bin"
DESCRIPTION_SHA = "823404fcc1d9cf3afa4fa126ecfa456d160188e594a9defd0bf519786988bc77"

def hal_bytes():
    raw = HAL.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == HAL_SHA
    return raw

def hal_at(address, size):
    raw = hal_bytes()
    offset = struct.unpack_from("<Q", raw, 32)[0]
    stride, count = struct.unpack_from("<HH", raw, 54)
    segments = [struct.unpack_from("<II6Q", raw, offset+i*stride) for i in range(count)]
    matches = [off+address-va for kind, flags, off, va, pa, filesz, memsz, align in segments if kind == 1 and va <= address and address+size <= va+filesz]
    assert len(matches) == 1
    return raw[matches[0]:matches[0]+size]

def machine():
    sys.path.insert(0, "/home/cy122/.local/lib/python3.14/site-packages")
    spec = importlib.util.spec_from_file_location("af_individual_native426", HERE.parent / "kernel426/ds4-model.py")
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_PC, UC_ARM64_REG_LR
    class IndividualMachine(native.Machine):
        def step(self, u, pc, size, unused):
            if pc == 0x5b1460:
                self.providers[hex(pc)] = self.providers.get(hex(pc), 0)+1
                pointer, char = u.reg_read(UC_ARM64_REG_X0), u.reg_read(UC_ARM64_REG_X1)
                text = self.string(pointer)
                index = text.rfind(bytes([char & 255]))
                u.reg_write(UC_ARM64_REG_X0, pointer+index if index >= 0 else 0)
                u.reg_write(UC_ARM64_REG_PC, u.reg_read(UC_ARM64_REG_LR))
                return
            if pc == 0x451610:
                self.providers["native logger output suppressed"] = self.providers.get("native logger output suppressed", 0)+1
                u.reg_write(UC_ARM64_REG_X0, 0)
                u.reg_write(UC_ARM64_REG_PC, u.reg_read(UC_ARM64_REG_LR))
                return
            super().step(u, pc, size, unused)
    return native, IndividualMachine()

def reserve(m, size):
    address = (m.cursor + 31) & ~31
    m.cursor = address + ((size+31) & ~31)
    assert m.cursor < 0x7000000
    m.allocations[address] = size
    m.u.mem_write(address, bytes(size))
    return address

def parse_description():
    d = Description(DESCRIPTION)
    assert hashlib.sha256(d.raw).hexdigest() == DESCRIPTION_SHA
    native, m = machine()
    table = reserve(m, 32)
    entries = reserve(m, len(d.entries) * 88)
    payloads = reserve(m, len(d.raw))
    m.u.mem_write(payloads, d.raw)
    m.u.mem_write(table, struct.pack("<I", len(d.entries)))
    m.u.mem_write(table+16, struct.pack("<Q", entries))
    m.description_entries = {}
    root_entry = None
    for i, (uid, entry) in enumerate(d.entries.items()):
        at = entries+i*88
        m.description_entries[uid] = at
        m.u.mem_write(at, struct.pack("<QI", table, uid))
        m.u.mem_write(at+12, entry["name"].encode()+b"\0")
        m.u.mem_write(at+45, struct.pack("<Q", 1))
        m.u.mem_write(at+68, struct.pack("<IQQ", entry["size"], payloads+d.base+entry["offset"], 0))
        if entry["name"] == "EEPROMDriverData":
            assert root_entry is None
            root_entry = at
            root_size = entry["size"]
    prototype = reserve(m, 128)
    m.u.mem_write(prototype+16, b"EEPROMDriverData\0")
    m.u.mem_write(prototype+56, struct.pack("<Q", 1))
    result = m.call(0x179268, prototype, 0, root_entry, 8, phase="actual-target-EEPROMDriverDataClass-Parse")
    assert result and m.read64(root_entry+80) == root_size
    parsed = bytes(m.u.mem_read(result, m.allocations[result]))
    (PRIVATE / "s5k3m5-native-description-struct-private.bin").write_bytes(parsed)
    proof = dict(description_sha256=DESCRIPTION_SHA, hal_sha256=HAL_SHA, root_payload_consumed_fully=True,
                 parsed_struct_bytes=len(parsed), native_parser_instructions=m.instructions, providers=m.providers,
                 parsed_struct_sha256=hashlib.sha256(parsed).hexdigest(), parser_entry="0x179268", parameter_module_prefix_bytes=88)
    (PRIVATE / "native-description-parser-proof-private.json").write_text(json.dumps(proof, indent=2)+"\n")
    assert hal_at(0x4f9728, 4) == bytes.fromhex("09600191")
    proof["caller_adds_88_at"] = "0x4f9728"
    (PRIVATE / "native-description-parser-proof-private.json").write_text(json.dumps(proof, indent=2)+"\n")
    return native, m, result+88, proof

def decode_af_descriptor(m, data):
    d = Description(DESCRIPTION)
    uid, payload = d.one("EEPROMDriverData")
    words = d.words(uid)
    def mem(at):
        return dict(offset=struct.unpack("<H", m.u.mem_read(data+at, 2))[0], mask=m.read32(data+at+4))
    scalar_fields = {"available":(96,15,"I"), "endian":(100,16,"I"),
                     "dacOf50cmAvailable":(128,23,"I"), "dacOf100cmAvailable":(140,26,"I"),
                     "calibrationInfoCount":(144,27,"I"), "hallRegisterAddr":(176,33,"I"),
                     "macroMargin":(212,42,"f"), "infinityMargin":(216,43,"f"),
                     "lensSagCalMac":(220,44,"I"), "lensSagCalInf":(224,45,"I"),
                     "avgGravityOfs0to90":(244,50,"h"), "avgGravityOfs90to180":(246,51,"h")}
    memory_fields = {"macro":(104,17), "infinity":(112,19), "dacOf50cm":(120,21), "dacOf100cm":(132,24),
                     "hall":(160,29), "hallBias":(168,31), "verticalMacro":(180,34), "verticalInfinity":(188,36),
                     "horizontalMacro":(196,38), "horizontalInfinity":(204,40), "otpGravityOfs0to90":(228,46), "otpGravityOfs90to180":(236,48)}
    values = {}
    for name, (at, slot, fmt) in scalar_fields.items():
        value = struct.unpack("<"+fmt, m.u.mem_read(data+at, struct.calcsize(fmt)))[0]
        if fmt == "f":
            assert words[slot] >> 32 == 0
            expected = struct.unpack("<f", struct.pack("<I", words[slot]))[0]
            assert math.isfinite(value)
        elif fmt == "h":
            expected = struct.unpack("<h", struct.pack("<H", words[slot] & 65535))[0]
        else:
            expected = words[slot]
        assert value == expected, (name, "Actual native field differs from bounded serialized value")
        values[name] = value
    for name, (at, slot) in memory_fields.items():
        value = mem(at)
        assert value == dict(offset=words[slot], mask=words[slot+1]), (name, "Actual native memory mapping differs from serialized descriptor")
        values[name] = value
    assert values["available"] in [0,1] and values["endian"] in [0,1]
    assert values["lensSagCalMac"] <= 4 and values["lensSagCalInf"] <= 4
    assert values["calibrationInfoCount"] == 0 and d.entries[words[28]]["name"] == "calibrationInfo" and d.payload(words[28]) == b""
    (PRIVATE / "s5k3m5-actual-af-descriptor-private.json").write_text(json.dumps(dict(fields=values,
        scalar_fields={k:dict(runtime_offset=a, serialized_slot=s, type=f) for k,(a,s,f) in scalar_fields.items()},
        memory_fields={k:dict(runtime_offset=a, serialized_slot=s) for k,(a,s) in memory_fields.items()},
        field_mapping_confirmed_by_actual_native_parser=True, standard_af_fields_compatible_after_explicit_oem_additions=True,
        additional_oem_distance_points_not_used_as_distance_mapping=True), indent=2)+"\n")
    return values

def format_af(available_override=None):
    native, m, parsed, parser_proof = parse_description()
    descriptor = decode_af_descriptor(m, parsed)
    if available_override is not None:
        assert available_override is False
        m.u.mem_write(parsed+96, bytes(4))
    from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ
    from unicorn.arm64_const import UC_ARM64_REG_PC, UC_ARM64_REG_SP, UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X22
    read1 = (P / "kernel326/reads-r2/s5k3m5-read1-private.bin").read_bytes()
    read2 = (P / "kernel326/reads-r2/s5k3m5-read2-private.bin").read_bytes()
    assert len(read1) == 12272 and read1 == read2
    eeprom = reserve(m, len(read1))
    m.u.mem_write(eeprom, read1)
    sensor_info = reserve(m, 65536)
    obj = reserve(m, 512)
    m.u.mem_write(obj, struct.pack("<QQ", parsed, sensor_info))
    m.u.mem_write(obj+136, struct.pack("<QI", eeprom, len(read1)))
    m.u.mem_write(0x96aac0, bytes(2048))
    m.u.mem_write(0x5bf2b0+16, bytes(4))
    stack = 0x20e0000
    m.u.reg_write(UC_ARM64_REG_SP, stack)
    m.u.mem_write(stack+136, struct.pack("<Q", obj))
    m.u.reg_write(UC_ARM64_REG_X22, obj)
    trace, raw_reads, integer_calls = [], [], []
    def code_hook(u, pc, size, unused):
        trace.append(pc)
        if pc == 0x506328:
            at = u.reg_read(UC_ARM64_REG_X1)
            integer_calls.append(dict(descriptor_offset=at-parsed, byte_offset=struct.unpack("<H", u.mem_read(at, 2))[0], mask=struct.unpack("<I", u.mem_read(at+4, 4))[0], endian=u.reg_read(UC_ARM64_REG_X2)))
    def read_hook(u, access, address, size, value, unused):
        if eeprom <= address < eeprom+len(read1):
            assert address+size <= eeprom+len(read1)
            raw_reads.append(dict(pc=hex(u.reg_read(UC_ARM64_REG_PC)), offset=address-eeprom, bytes=size))
    hook1 = m.u.hook_add(UC_HOOK_CODE, code_hook)
    hook2 = m.u.hook_add(UC_HOOK_MEM_READ, read_hook)
    m.phase = "actual-target-inline-FormatAFData"
    m.u.emu_start(0x4fb9d0, 0x4fd14c, timeout=15000000, count=3000000)
    assert m.u.reg_read(UC_ARM64_REG_PC) == 0x4fd14c
    m.u.hook_del(hook1)
    m.u.hook_del(hook2)
    output = bytes(m.u.mem_read(sensor_info+12552, 168))
    suffix = "" if available_override is None else "-disabled-counterfactual"
    (PRIVATE / ("s5k3m5-native-af-formatted"+suffix+"-private.bin")).write_bytes(output)
    def raw_integer(field):
        mask = field["mask"]
        bits = max(1, mask.bit_length())
        count = (bits+7)//8
        assert 0 <= field["offset"] and field["offset"]+count <= len(read1)
        value = int.from_bytes(read1[field["offset"]:field["offset"]+count], "little" if descriptor["endian"] else "big")
        shifted = (value << (32-count*8)) & 0xffffffff
        signed = shifted-0x100000000 if shifted & 0x80000000 else shifted
        return signed >> (32-bits)
    def s16(value):
        return ((value+32768) & 65535)-32768
    source_model = dict(available=descriptor["available"] if available_override is None else 0)
    if source_model["available"]:
        assert descriptor["calibrationInfoCount"] == 0, "This audit has not added a distance-map consumer"
        source_model.update(macro_dac=s16(raw_integer(descriptor["macro"])), infinity_dac=s16(raw_integer(descriptor["infinity"])))
        for endpoint, sag in [("macro_dac", descriptor["lensSagCalMac"]), ("infinity_dac", descriptor["lensSagCalInf"])]:
            gravity = 0
            if sag == 1 and descriptor["otpGravityOfs0to90"]["mask"]:
                gravity = -s16(raw_integer(descriptor["otpGravityOfs0to90"]))
            elif sag == 3 and descriptor["otpGravityOfs90to180"]["mask"]:
                gravity = s16(raw_integer(descriptor["otpGravityOfs90to180"]))
            elif sag == 2:
                gravity = -descriptor["avgGravityOfs0to90"]
            elif sag == 4:
                gravity = descriptor["avgGravityOfs90to180"]
            source_model[endpoint] = s16(source_model[endpoint]+gravity)
        if descriptor["horizontalMacro"]["mask"] and descriptor["verticalMacro"]["mask"]:
            source_model["macro_dac"] = max(s16(raw_integer(descriptor["horizontalMacro"])), s16(raw_integer(descriptor["verticalMacro"])))
        if descriptor["horizontalInfinity"]["mask"] and descriptor["verticalInfinity"]["mask"]:
            source_model["infinity_dac"] = min(s16(raw_integer(descriptor["horizontalInfinity"])), s16(raw_integer(descriptor["verticalInfinity"])))
        source_model.update(macro_margin=descriptor["macroMargin"], infinity_margin=descriptor["infinityMargin"])
    native_values = dict(available=struct.unpack_from("<I", output, 0)[0], macro_dac=struct.unpack_from("<h", output, 4)[0], infinity_dac=struct.unpack_from("<h", output, 6)[0],
                         macro_margin=struct.unpack_from("<f", output, 132)[0], infinity_margin=struct.unpack_from("<f", output, 136)[0])
    assert all(native_values[key] == value for key,value in source_model.items())
    if source_model["available"]:
        for name, output_offset, flag_offset in [("dacOf50cm",148,152),("dacOf100cm",156,160)]:
            flag = descriptor[name+"Available"]
            assert struct.unpack_from("<I",output,flag_offset)[0] == flag
            if flag:
                assert struct.unpack_from("<h",output,output_offset)[0] == s16(raw_integer(descriptor[name]))
        assert struct.unpack_from("<I",output,128)[0] == 0
        assert struct.unpack_from("<I",output,144)[0] == descriptor["hallRegisterAddr"]
        assert struct.unpack_from("<H",output,140)[0] == (((raw_integer(descriptor["hall"]) & 255) << 8) | (raw_integer(descriptor["hallBias"]) & 255))
    if available_override is False:
        assert not raw_reads and not integer_calls and output == bytes(len(output))
    record = dict(hal_sha256=HAL_SHA, description_sha256=DESCRIPTION_SHA, parser_proof=parser_proof,
                  actual_af_descriptor=descriptor,
                  duplicate_reads_equal=True, read_bytes=len(read1), parsed_pointer=parsed,
                  raw_eeprom_sha256_private=hashlib.sha256(read1).hexdigest(),
                  begin="0x4fb9d0", end_exclusive="0x4fd14c", path_instructions=len(trace),
                  executed_pcs=sorted(set(hex(pc) for pc in trace)), raw_reads=raw_reads, integer_calls=integer_calls,
                  formatted_values=native_values, independent_cached_raw_field_model_equal=True, emulated_available_override=available_override,
                  output_sha256=hashlib.sha256(output).hexdigest(), providers=m.providers,
                  transport_and_framework_not_executed=True, checksum_or_physical_supplier_not_certified=True)
    (PRIVATE / ("s5k3m5-native-af-format-proof"+suffix+"-private.json")).write_text(json.dumps(record, indent=2)+"\n")
    return native, m, parsed, sensor_info, obj, record

def calibrate_conditional():
    native, m, parsed, sensor_info, obj, format_proof = format_af()
    from unicorn import UC_HOOK_CODE
    from unicorn.arm64_const import UC_ARM64_REG_PC, UC_ARM64_REG_SP, UC_ARM64_REG_X20, UC_ARM64_REG_W19, UC_ARM64_REG_W25, UC_ARM64_REG_W28
    d = Description(DESCRIPTION)
    uid, payload = d.one("actuatorDriver")
    root_entry = m.description_entries[uid]
    m.u.mem_write(root_entry+80, bytes(8))
    prototype = reserve(m, 128)
    m.u.mem_write(prototype+16, b"actuatorDriver\0")
    m.u.mem_write(prototype+56, struct.pack("<Q", 1))
    module = m.call(0x1773a8, prototype, 0, root_entry, 8, phase="actual-target-ActuatorDriverDataClass-Parse")
    assert module and m.read64(root_entry+80) == len(payload)
    driver = module+88
    words = d.words(uid)
    actuator_type = m.read32(driver+40)
    bits = struct.unpack("<H", m.u.mem_read(driver+44, 2))[0]
    region_count, regions = m.read32(driver+144), m.read64(driver+152)
    assert actuator_type == words[7] == 0 and bits == words[8] == 10
    assert region_count == words[20] == 1
    count = struct.unpack("<H", m.u.mem_read(regions+(region_count-1)*12, 2))[0]
    assert count > 0
    assert struct.unpack("<h", m.u.mem_read(driver+136, 2))[0] == words[19]
    lower_bound, upper_bound = 0, (1 << bits)-1
    actor_data = reserve(m, 4096)
    m.u.mem_write(actor_data+2064, struct.pack("<Q", driver))
    m.u.mem_write(0x96aac0, bytes(2048))
    stack = 0x20e0000
    m.u.reg_write(UC_ARM64_REG_SP, stack)
    for at, raw in [(20,struct.pack("<I",count)), (32,struct.pack("<QQ",regions,region_count)), (56,struct.pack("<QQ",sensor_info,actor_data))]:
        m.u.mem_write(stack+at, raw)
    m.u.reg_write(UC_ARM64_REG_X20, sensor_info)
    m.u.reg_write(UC_ARM64_REG_W19, actuator_type)
    m.u.reg_write(UC_ARM64_REG_W25, upper_bound)
    m.u.reg_write(UC_ARM64_REG_W28, lower_bound)
    trace = []
    def hook(u, pc, size, unused):
        trace.append(pc)
        word = struct.unpack("<I", u.mem_read(pc,4))[0]
        assert word & 0xfc000000 != 0x94000000, "Unexpected helper call in calibrated numeric and step core"
    hook_id = m.u.hook_add(UC_HOOK_CODE, hook)
    m.phase = "conditional-default-bounds-actual-calibration-and-step-core"
    m.u.emu_start(0x4f8474, 0x4f89cc, timeout=15000000, count=3000000)
    assert m.u.reg_read(UC_ARM64_REG_PC) == 0x4f89cc
    m.u.hook_del(hook_id)
    actual_table = list(struct.unpack("<"+"h"*count, m.u.mem_read(actor_data, count*2)))
    actual_initial = struct.unpack("<h", m.u.mem_read(driver+136,2))[0]
    actual_cps = struct.unpack("<f", m.u.mem_read(regions+4,4))[0]
    f32 = lambda v: struct.unpack("<f", struct.pack("<f",v))[0]
    s16 = lambda v: ((v+32768)&65535)-32768
    formatted = format_proof["formatted_values"]
    infinity, macro = formatted["infinity_dac"], formatted["macro_dac"]
    delta = abs(macro-infinity)
    infinity = s16(infinity+int(f32(f32(formatted["infinity_margin"])*f32(delta)))*(1 if infinity > 0 else -1))
    macro = s16(macro+int(f32(f32(formatted["macro_margin"])*f32(delta)))*(1 if macro > 0 else -1))
    infinity, macro = max(lower_bound,infinity), min(upper_bound,macro)
    cps = f32(f32(macro-infinity)/f32(count))
    expected = [None]*count
    current = f32(infinity)
    for step in range(count):
        expected[count-1-step] = int(current)
        current = f32(current+cps)
    assert actual_initial == infinity and actual_cps == cps and actual_table == expected
    assert all(lower_bound <= v <= upper_bound for v in actual_table)
    assert actual_table != json.loads((P / "kernel453/af-profile/s5k3m5-native-step-table-private.json").read_text())["step_table"]
    selected = json.loads((P / "kernel453/af-profile/s5k3m5-af-source-candidate-private.json").read_text())
    candidate = dict(model="s5k3m5", declared_variant="qtech_s5k3m5sx", sensor_mode=3, usecases=["Preview","Video"],
                     description_sha256=DESCRIPTION_SHA, hal_sha256=HAL_SHA,
                     selected_af_algo_sha256=selected["selected_af_algo_sha256"], selected_contrast_af_sha256=selected["selected_contrast_af_sha256"],
                     source_formatted_af_values=formatted, supplied_clip_bounds=dict(lower=lower_bound,upper=upper_bound),
                     clip_bounds_condition="original default VCM protocol bounds, only when external OemCamActuatorSettingMap does not select an override",
                     external_override_selection_verified=False, individual_initial_code=actual_initial, individual_code_per_step=actual_cps,
                     step_table=actual_table, minimum_code=min(actual_table), maximum_code=max(actual_table),
                     native_core_begin="0x4f8474", native_core_end_exclusive="0x4f89cc", native_core_sha256=hashlib.sha256(hal_at(0x4f8474,0x4f89cc-0x4f8474)).hexdigest(),
                     native_core_instructions=len(trace), raw_native_parser_formatter_margin_clip_and_every_step_equal=True,
                     calibration_data_availability_predicate_from_description=True, checksum_certified=False, supplier_identity_certified=False,
                     default_clip_bounds_are_not_search_endpoints=True, physical_search_safety_verified=False, conditional_only=True, deployable=False, applied=False)
    (PRIVATE / "s5k3m5-conditional-individual-step-candidate-private.json").write_text(json.dumps(candidate,indent=2)+"\n")
    return candidate, format_proof

def runtime_sag_scope():
    source = ast.parse((HERE / "inspect-af-profile.py").read_text())
    schema_node = next(node for node in source.body if isinstance(node,ast.ClassDef) and node.name == "AFSchema")
    namespace = dict(PRIVATE=P / "kernel453/af-profile", ET=ET, struct=struct, math=math, re=re)
    exec(compile(ast.Module(body=[schema_node],type_ignores=[]),"retained453-afschema", "exec"),namespace)
    schema = namespace["AFSchema"]()
    index = json.loads((P / "kernel333/qtech_s5k3m5sx-index-private.json").read_text())
    d = Description(P / ("kernel"+str(index["source_stage"])) / index["filename"])
    selected = json.loads((P / "kernel453/af-profile/s5k3m5-af-source-candidate-private.json").read_text())
    uid = selected["af_algo_selection"][0]["uid"]
    payload = d.payload(uid)
    assert hashlib.sha256(payload).hexdigest() == selected["selected_af_algo_sha256"]
    used = {uid}
    original_payload = d.payload
    def tracked_payload(reference):
        used.add(reference)
        return original_payload(reference)
    d.payload = tracked_payload
    values, consumed = schema.read(schema.elements["chromatixAFAlgoTuning"],payload,0,d)
    assert consumed == len(payload)
    typed = json.loads((P / "kernel453/af-profile/qtech_s5k3m5sx-typed-af-private.json").read_text())
    assert values == next(row["values"] for row in typed if row["tag"] == "AFAlgoTuning" and row["uid"] == uid)
    native, m = machine()
    table = reserve(m,32)
    entries = reserve(m,len(used)*88)
    m.u.mem_write(table,struct.pack("<I",len(used)))
    m.u.mem_write(table+16,struct.pack("<Q",entries))
    root_entry = None
    for i,reference in enumerate(sorted(used)):
        entry = d.entries[reference]
        body = original_payload(reference)
        target = reserve(m,len(body))
        m.u.mem_write(target,body)
        at = entries+88*i
        version = index["entries"][str(reference)]["version"]
        m.u.mem_write(at,struct.pack("<QI",table,reference))
        m.u.mem_write(at+12,entry["name"].encode()+b"\0")
        m.u.mem_write(at+45,struct.pack("<Q",version))
        m.u.mem_write(at+68,struct.pack("<IQQ",len(body),target,0))
        if reference == uid:
            root_entry = at
    prototype = reserve(m,128)
    m.u.mem_write(prototype+16,b"AFAlgoTuning\0")
    m.u.mem_write(prototype+56,struct.pack("<Q",9))
    from unicorn import UC_HOOK_CODE
    from unicorn.arm64_const import UC_ARM64_REG_X1
    loader_destinations = []
    def parser_hook(u,pc,size,unused):
        if pc == 0x1b0e88:
            loader_destinations.append(u.reg_read(UC_ARM64_REG_X1))
    hook_id = m.u.hook_add(UC_HOOK_CODE,parser_hook)
    module = m.call(0x1b0c90,prototype,0,root_entry,8,phase="actual-target-selected-AFAlgoTuning-v9-parse")
    m.u.hook_del(hook_id)
    assert module and m.read64(root_entry+80) == len(payload)
    assert len(loader_destinations) == 1
    data = loader_destinations[0]
    expected = values["moduleTuning"]["lensSagCompensation"]
    assert m.read32(data+384) == expected["enable"]
    # Native stores count at 388, its symbol ID at 392, and the array pointer at 400.
    assert hal_at(0x1b1ef0,4) == bytes.fromhex("6a8601b9")
    count, pointer = m.read32(data+388), m.read64(data+400)
    assert count == len(expected["fDAC"]), ("AF runtime loader destination relative to module",data-module,"fDAC count mismatch at offset388")
    actual_fdac = list(struct.unpack("<"+"I"*count,m.u.mem_read(pointer,count*4)))
    assert actual_fdac == expected["fDAC"]
    disabled_return_zero = False
    if not expected["enable"]:
        actor = reserve(m,256)
        m.u.mem_write(actor+112,struct.pack("<Q",data))
        before = dict(m.providers)
        result = m.call(0x41d508,actor,phase="actual-target-CalLensSagComp-selected-disabled-gate")
        assert result == 0 and m.providers == before
        disabled_return_zero = True
    numeric_cases = []
    candidate_path = PRIVATE / "s5k3m5-conditional-individual-step-candidate-private.json"
    if expected["enable"] and candidate_path.exists():
        from unicorn.arm64_const import UC_ARM64_REG_PC, UC_ARM64_REG_X20, UC_ARM64_REG_W19, UC_ARM64_REG_W20
        candidate = json.loads(candidate_path.read_text())
        assert candidate["description_sha256"] == DESCRIPTION_SHA and candidate["conditional_only"]
        actor_data = reserve(m,4096)
        table_count = len(candidate["step_table"])
        infinity, macro = candidate["individual_initial_code"], candidate["step_table"][0]
        assert macro != infinity
        m.u.mem_write(actor_data+2056,struct.pack("<hhI",infinity,macro,table_count))
        actor = reserve(m,256)
        m.u.mem_write(actor+24,struct.pack("<Q",actor_data))
        m.u.mem_write(actor+112,struct.pack("<Q",data))
        m.u.mem_write(0x96aac0,bytes(2048))
        f32 = lambda v: struct.unpack("<f",struct.pack("<f",v))[0]
        gravity_unit = struct.unpack("<f",struct.pack("<I",0x411cf5c3))[0]
        signed32 = lambda v: v-0x100000000 if v & 0x80000000 else v
        for gravity in [0.0, gravity_unit, -gravity_unit, f32(gravity_unit/2), -f32(gravity_unit/2)]:
            m.u.mem_write(actor+120,struct.pack("<f",gravity))
            m.u.reg_write(UC_ARM64_REG_X20,actor)
            def first_stop(u,pc,size,unused):
                if pc in [0x41d5b8,0x41d76c]:
                    u.emu_stop()
            stop_hook = m.u.hook_add(UC_HOOK_CODE,first_stop)
            m.phase = "actual-target-runtime-sag-numeric-core-explicit-gravity-input"
            m.u.emu_start(0x41d564,0x41d830,timeout=15000000,count=1000)
            assert m.u.reg_read(UC_ARM64_REG_PC) in [0x41d5b8,0x41d76c]
            m.u.hook_del(stop_hook)
            native_dac_delta = signed32(m.u.reg_read(UC_ARM64_REG_W19))
            m.u.emu_start(0x41d76c,0x41d7a0,timeout=15000000,count=1000)
            assert m.u.reg_read(UC_ARM64_REG_PC) == 0x41d7a0
            native_logical_delta = signed32(m.u.reg_read(UC_ARM64_REG_W20))
            source_dac_delta = 0 if gravity == 0 else int(f32(f32(abs(gravity)/gravity_unit)*f32(expected["fDAC"][2 if gravity > 0 else 1]-expected["fDAC"][0])))
            source_logical_delta = int(f32(f32(f32(-table_count)/f32(macro-infinity))*f32(source_dac_delta)))
            assert native_dac_delta == source_dac_delta and native_logical_delta == source_logical_delta
            numeric_cases.append(dict(gravity_z=gravity,dac_delta=native_dac_delta,logical_delta=native_logical_delta,
                                      actual_core_and_independent_f32_model_equal=True,explicit_test_input_not_device_measurement=True))
    record = dict(hal_sha256=HAL_SHA, description_sha256=DESCRIPTION_SHA, sensor_mode=3, usecases=["Preview","Video"],
                  selected_af_algo_sha256=selected["selected_af_algo_sha256"], selected_uid=uid,
                  exact_native_af_parser_consumed_fully=True, sag_enable_and_fdac_match_complete_typed_xml_proof=True,
                  selected_sag_tuning=expected, native_runtime_data_offset=384,
                  selected_tuning_disables_runtime_sag=not bool(expected["enable"]), disabled_function_returns_zero_without_providers=disabled_return_zero,
                  explicit_gravity_numeric_cases=numeric_cases, runtime_numeric_cores_replayed=bool(numeric_cases),
                  conditional_step_candidate_sha256=hashlib.sha256(candidate_path.read_bytes()).hexdigest() if numeric_cases else None,
                  complete_runtime_static_feature_gate_not_replayed=True,
                  enabled_path_requires_static_feature_gate_and_live_gravity=True, live_gravity_not_sampled=True,
                  no_individual_distance_mapping_applied=True)
    (PRIVATE / "s5k3m5-runtime-sag-proof-private.json").write_text(json.dumps(record,indent=2)+"\n")
    return record

if len(sys.argv) > 1 and sys.argv[1] == "--inventory":
    d = Description(DESCRIPTION)
    rows = [dict(uid=uid, **entry) for uid, entry in d.entries.items() if any(t in entry["name"].lower() for t in ["af", "macro", "infinit", "sag", "margin", "gravity", "calib", "checksum", "valid", "moduleid", "vendor", "supplier", "hall"])]
    print(json.dumps(rows, indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--strings":
    rows = []
    for match in re.finditer(rb"[ -~]{8,}", hal_bytes()):
        text = match.group().decode()
        if any(term in text.lower() for term in ["macro", "checksum", "gravity", "af calib", "infinity", "margin", "check sum"]):
            rows.append(dict(file_offset=hex(match.start()), text=text))
    (PRIVATE / "af-related-hal-strings-private.json").write_text(json.dumps(rows, indent=2)+"\n")
    print(json.dumps(rows, indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--literals":
    for word in sys.argv[2].split(","):
        address = int(word, 0)
        raw = hal_at(address, 1024).split(b"\0", 1)[0]
        assert raw and all(32 <= value < 127 for value in raw)
        print(hex(address), raw.decode())
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--cached-config-inventory":
    rows = []
    for relative in ["kernel115/camera-config-list-private.tar.gz", "kernel115/vendor-camera-source-private.tar.gz"]:
        with tarfile.open(P / relative, "r:gz") as archive:
            rows.append(dict(archive=relative, files=[m.name for m in archive.getmembers() if m.isfile()]))
    (PRIVATE / "cached-config-inventory-private.json").write_text(json.dumps(rows, indent=2)+"\n")
    q = subprocess.run(["aarch64-linux-gnu-readelf", "-d", str(HAL)], capture_output=True, text=True, timeout=30)
    assert q.returncode == 0
    print(json.dumps(rows, indent=2))
    print("\n".join(line for line in q.stdout.splitlines() if "NEEDED" in line))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--cached-vendor-authority":
    output = PRIVATE / "vendor-authority"
    output.mkdir(exist_ok=True)
    rows = []
    image = None
    for stage, source_relative in [(248, "kernel248/linux-return-partitions/vendor.img"), (242, "kernel242/android-rom/vendor.img")]:
        candidate = P / source_relative
        assert candidate.is_file() and candidate.stat().st_size == 1711276032
        target = output / ("camera.qcom-k" + str(stage) + ".so")
        q = subprocess.run(["debugfs", "-R", "dump -p /lib64/hw/camera.qcom.so " + str(target), str(candidate)], capture_output=True, timeout=45)
        (output / (target.name+"-debugfs-private.log")).write_bytes(q.stdout+q.stderr)
        assert q.returncode == 0 and target.is_file() and target.read_bytes()[:4] == b"\x7fELF"
        data = target.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        matched = sha == HAL_SHA
        rows.append(dict(image=str(candidate), filesystem_path="/lib64/hw/camera.qcom.so", bytes=len(data), sha256=sha, matches_retained_current_hal=matched, debugfs_readonly=True))
        if matched:
            image = candidate
            break
    (output / "hal-image-comparison-private.json").write_text(json.dumps(rows, indent=2)+"\n")
    if image is None:
        print(json.dumps(dict(inspected_cached_images=rows,current_vendor_authority_verified=False,
                              mismatched_images_rejected=True,no_library_or_configuration_accepted=True),indent=2))
        raise SystemExit(0)
    for relative in ["/lib64/libhwconfigurationutil.so"]:
        target = output / Path(relative).name
        q = subprocess.run(["debugfs", "-R", "dump -p " + relative + " " + str(target), str(image)], capture_output=True, timeout=45)
        (output / (target.name+"-debugfs-private.log")).write_bytes(q.stdout+q.stderr)
        assert q.returncode == 0 and target.is_file() and target.read_bytes()[:4] == b"\x7fELF", relative
        data = target.read_bytes()
        rows.append(dict(image=str(image), filesystem_path=relative, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), debugfs_readonly=True))
    lib = output / "libhwconfigurationutil.so"
    paths = [match.group().decode() for match in re.finditer(rb"[ -~]{6,}", lib.read_bytes()) if any(term in match.group().lower() for term in [b".xml", b"/vendor/", b"oemcam", b"locale"])]
    (output / "configuration-path-literals-private.json").write_text(json.dumps(paths, indent=2)+"\n")
    (output / "source-private.json").write_text(json.dumps(rows, indent=2)+"\n")
    print(json.dumps(dict(sources=rows, configuration_path_literals=paths), indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--checksum-source-facts":
    repo = Path("/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git")
    commit = "9668fcdc6ec15be7a10d66f7b93c347829e0fdb6"
    base = "drivers/media/platform/msm/camera/cam_sensor_module/cam_eeprom/"
    names = ["cam_eeprom_core.c", "cam_eeprom_dev.c", "cam_eeprom_core.h", "cam_eeprom_dev.h"]
    rows = []
    for name in names:
        relative = base+name
        q = subprocess.run(["git","-C",str(repo),"show",commit+":"+relative],capture_output=True,timeout=35)
        assert q.returncode == 0, relative
        target = PRIVATE / ("gpl-"+name)
        target.write_bytes(q.stdout)
        source = q.stdout.decode()
        rows.append(dict(commit=commit,path=relative,bytes=len(q.stdout),sha256=hashlib.sha256(q.stdout).hexdigest(),
                         checksum_crc_named_terms=[dict(line=i+1,text=line.strip()) for i,line in enumerate(source.splitlines()) if re.search(r"checksum|check.sum|crc|factory.valid",line,re.I)]))
    authority = P / "kernel453/af-profile/pinned-sources/camx/src/core/camxeepromdata.cpp"
    source = authority.read_text()
    start,end = source.index("VOID EEPROMData::FormatAFData()"),source.index("/// EEPROMData::FormatWBData")
    af = source[start:end]
    assert not re.search(r"checksum|check.sum|crc",af,re.I)
    remote = subprocess.run(["git","-C",str(repo),"remote","get-url","origin"],capture_output=True,text=True,timeout=30)
    assert remote.returncode == 0
    report = dict(gpl_repository=remote.stdout.strip(), gpl_sources=rows, fixed_camx_commit="9f17f1b568626b393e785b369c5dc94543774d7a", fixed_camx_source_sha256=hashlib.sha256(authority.read_bytes()).hexdigest(),
                  fixed_camx_af_formatter_has_no_checksum_validation=True, actual_hal_af_availability_copies_description_flag=True,
                  gpl_named_checksum_is_caller_start_address_sparse_sum_returned_without_factory_comparison=True,
                  covered_scope="AF formatter, its actual raw read path, and fixed GPL EEPROM core; no factory checksum acceptance claimed")
    (PRIVATE / "checksum-source-facts-private.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--disassemble":
    hal_bytes()
    ranges = [("module-create-eeprom", 0x4f96d0, 0x4f9e68), ("eeprom-constructor", 0x4fa058, 0x50459c), ("eeprom-native-format-loader", 0x179d48, 0x1803c4),
              ("eeprom-native-root-parser", 0x179268, 0x179d48), ("integer-format", 0x506328, 0x506574),
              ("actuator-calibration-and-table", 0x4f7e10, 0x4f89d4), ("runtime-sag-compensation", 0x41d508, 0x41d830),
              ("afalgo-native-root-parser",0x1b0c90,0x1b0e84), ("afalgo-native-root-loader",0x1b0e88,0x1b5d9c)]
    rows = []
    for name, begin, end in ranges:
        q = subprocess.run(["aarch64-linux-gnu-objdump", "-d", "--start-address="+hex(begin), "--stop-address="+hex(end), str(HAL)], capture_output=True, timeout=30)
        assert q.returncode == 0
        (PRIVATE / (name+"-private.asm")).write_bytes(q.stdout)
        rows.append(dict(name=name, begin=hex(begin), end_exclusive=hex(end), sha256=hashlib.sha256(hal_at(begin, end-begin)).hexdigest(), disassembly_sha256=hashlib.sha256(q.stdout).hexdigest()))
    (PRIVATE / "native-range-manifest-private.json").write_text(json.dumps(dict(hal_sha256=HAL_SHA, ranges=rows), indent=2)+"\n")
    print(json.dumps(rows, indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--parse-description":
    native, m, result, proof = parse_description()
    print(json.dumps(proof, indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--format-af":
    native, m, parsed, sensor_info, obj, record = format_af()
    print(json.dumps({key:record[key] for key in ["hal_sha256", "description_sha256", "duplicate_reads_equal", "begin", "end_exclusive", "path_instructions", "transport_and_framework_not_executed", "checksum_or_physical_supplier_not_certified"]}, indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--check-disabled-af":
    native, m, parsed, sensor_info, obj, record = format_af(False)
    print(json.dumps(dict(counterfactual_available_false=True, raw_reads=0, formatted_struct_zero=True, passed=True),indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--calibrate-conditional":
    candidate, proof = calibrate_conditional()
    print(json.dumps({key:candidate[key] for key in ["model","description_sha256","hal_sha256","raw_native_parser_formatter_margin_clip_and_every_step_equal","external_override_selection_verified","conditional_only","deployable","applied"]},indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--runtime-sag-scope":
    record = runtime_sag_scope()
    print(json.dumps({key:record[key] for key in ["hal_sha256","sensor_mode","usecases","exact_native_af_parser_consumed_fully","sag_enable_and_fdac_match_complete_typed_xml_proof","selected_tuning_disables_runtime_sag","disabled_function_returns_zero_without_providers","live_gravity_not_sampled"]},indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--report":
    formatter = json.loads((PRIVATE / "s5k3m5-native-af-format-proof-private.json").read_text())
    disabled = json.loads((PRIVATE / "s5k3m5-native-af-format-proof-disabled-counterfactual-private.json").read_text())
    individual = json.loads((PRIVATE / "s5k3m5-conditional-individual-step-candidate-private.json").read_text())
    sag = json.loads((PRIVATE / "s5k3m5-runtime-sag-proof-private.json").read_text())
    checksums = json.loads((PRIVATE / "checksum-source-facts-private.json").read_text())
    ranges = json.loads((PRIVATE / "native-range-manifest-private.json").read_text())
    images = json.loads((PRIVATE / "vendor-authority/hal-image-comparison-private.json").read_text())
    protected = {"AF-PROFILE-NEXT.md":"bcbb2362f95bb3d3ff9e917686ff964d1bdcad74d29830f37603df84809934f9",
                 "inspect-af-profile.py":"29069e359eb30488f56c51cd0f897b8ac2716fc7936e1aff336b31fcb5151c8a",
                 "af-profile-validation.json":"2bfae79de28171ab7141ead5ad0b0262aacdbcc74fe5eacf284fa594d2a24194"}
    assert all(hashlib.sha256((HERE/name).read_bytes()).hexdigest() == sha for name,sha in protected.items())
    assert formatter["emulated_available_override"] is None and formatter["independent_cached_raw_field_model_equal"]
    assert formatter["parser_proof"]["caller_adds_88_at"] == "0x4f9728"
    assert disabled["emulated_available_override"] is False and disabled["raw_reads"] == [] and disabled["integer_calls"] == []
    assert individual["raw_native_parser_formatter_margin_clip_and_every_step_equal"] and individual["conditional_only"]
    assert not individual["external_override_selection_verified"] and not individual["deployable"]
    assert sag["exact_native_af_parser_consumed_fully"] and sag["sag_enable_and_fdac_match_complete_typed_xml_proof"]
    assert len(sag["explicit_gravity_numeric_cases"]) == 5 and all(row["actual_core_and_independent_f32_model_equal"] for row in sag["explicit_gravity_numeric_cases"])
    assert sag["conditional_step_candidate_sha256"] == hashlib.sha256((PRIVATE / "s5k3m5-conditional-individual-step-candidate-private.json").read_bytes()).hexdigest()
    assert not any(row["matches_retained_current_hal"] for row in images)
    descriptor = formatter["actual_af_descriptor"]
    report = dict(stage=453, scope="offline current Qtech S5K3M5SX individual AF formatter and conditional calibration",
                  description_sha256=DESCRIPTION_SHA, hal_sha256=HAL_SHA, sensor_mode=3, usecases=["Preview","Video"],
                  selected_af_algo_sha256=individual["selected_af_algo_sha256"], selected_contrast_af_sha256=individual["selected_contrast_af_sha256"],
                  cached_eeprom_duplicate_reads_equal=True, raw_unit_fingerprints_values_and_positions_private=True,
                  actual_target_description_parser_consumed_full_payload=True, actual_target_description_struct_bytes=formatter["parser_proof"]["parsed_struct_bytes"],
                  parameter_module_prefix_explicitly_removed_and_verified_by_original_caller=True,
                  rejected_initial_trial=dict(reason="ParameterModule object start was not EEPROMDriverData member", corrected_by="0x4f9728 ADD +88 and complete runtime-field/serialized-slot parity", counted_as_final_proof=False),
                  actual_af_tail_field_parity=True, calibration_sag_branch=dict(macro_default=descriptor["lensSagCalMac"] == 0, infinity_default=descriptor["lensSagCalInf"] == 0,
                                                                                           vertical_horizontal_override_declared=bool(descriptor["verticalMacro"]["mask"] and descriptor["horizontalMacro"]["mask"] or descriptor["verticalInfinity"]["mask"] and descriptor["horizontalInfinity"]["mask"])),
                  source_oem_distance_points=dict(dacOf50cm_present_in_native_format=True,dacOf50cm_enabled=bool(descriptor["dacOf50cmAvailable"]),
                                                 dacOf100cm_present_in_native_format=True,dacOf100cm_enabled=bool(descriptor["dacOf100cmAvailable"]),distance_mapping_applied=False),
                  native_integer_getter_and_formatter_equal_independent_raw_model=True,
                  unavailable_descriptor_counterfactual=dict(raw_reads=0,integer_calls=0,formatted_output_zero=True),
                  af_available_source="factory description flag, not verified EEPROM unit checksum/acceptance flag",
                  factory_af_checksum_algorithm_and_acceptance_verified=False,
                  fixed_camx_af_formatter_has_no_checksum_validation=True,
                  gpl_named_checksum_is_caller_start_sparse_sum_without_stored_checksum_comparison=True,
                  gpl_repository=checksums["gpl_repository"],
                  gpl_sources=[{key:row[key] for key in ["commit","path","bytes","sha256"]} for row in checksums["gpl_sources"]],
                  fixed_camx_commit=checksums["fixed_camx_commit"],fixed_camx_source_sha256=checksums["fixed_camx_source_sha256"],
                  native_margin_clip_and_every_individual_step_equal=True,
                  conditional_clip_branch="default VCM bounds only; external OemCamActuatorSettingMap selection remains unverified",
                  external_authority_needed=dict(library="vendor:lib64/libhwconfigurationutil.so", section="OemCamActuatorSettingMap",backing_configuration_path_not_guessed=True),
                  inspected_cached_vendor_images=[dict(stage=248 if "kernel248" in row["image"] else 242,hal_sha256=row["sha256"],matches_current_hal=False) for row in images],
                  runtime_sag=dict(actual_selected_af_v9_native_parser_and_fdac_equal=True, selected_tuning_enabled=not sag["selected_tuning_disables_runtime_sag"],
                                   explicit_gravity_numeric_cases=5, all_actual_instructions_equal_independent_f32_model=True,
                                   static_feature_gate_and_live_gravity_verified=False, numeric_cases_are_not_device_measurements=True),
                  native_ranges=ranges["ranges"], protected_nominal_files_sha256=protected,
                  individual_candidate_conditional_only=True, individual_factory_acceptance_or_physical_search_safety_verified=False,
                  deployable=False,applied=False,no_phone_sdk_build_production_driver_or_tuning_changes=True,offline_checks_passed=True)
    (HERE / "af-individual-validation.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(dict(stage=453,actual_tail_and_formatter_parity=True,conditional_individual_steps_equal=True,
                          runtime_sag_numeric_cases=5,checksum_verified=False,external_override_verified=False,
                          nominal_files_unchanged=True,deployable=False,offline_checks_passed=True),indent=2))
    raise SystemExit(0)

print("Use --disassemble, --parse-description, --format-af, --check-disabled-af, --calibrate-conditional, --runtime-sag-scope, --checksum-source-facts, --cached-vendor-authority, then --report.")
