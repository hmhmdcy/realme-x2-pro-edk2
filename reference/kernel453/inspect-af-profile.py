"""Offline factory AF scope recovery. No phone, SDK bind or compilation."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import math
import os
import re
import resource
import shutil
import signal
import struct
import subprocess
import sys
import posixpath
import urllib.request
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
P = Path("/mnt/e/edk2-samurai-out")
spec = importlib.util.spec_from_file_location("af_profile_storage449", HERE.parent / "kernel449/storage.py")
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
BUILD = storage.mount.mounted_build()
PRIVATE = P / "kernel453/af-profile"
PRIVATE.mkdir(exist_ok=True)

source450 = ast.parse((HERE.parent / "kernel450/inspect-lens-scope.py").read_text())
node = next(node for node in source450.body if isinstance(node, ast.ClassDef) and node.name == "Description")
exec(compile(ast.Module(body=[node], type_ignores=[]), "retained450-description", "exec"))

class AFSchema:
    """Bounded typed reader, independently checked against retained OEM XML."""
    def __init__(self):
        self.ns = {"x": "http://www.w3.org/2001/XMLSchema"}
        self.types = {}
        self.elements = {}
        for path in (PRIVATE / "pinned-sources/chi-cdk/api/chromatix/XSD").rglob("*.xsd"):
            root = ET.parse(path).getroot()
            for node in root:
                name = node.get("name")
                if not name:
                    continue
                if node.tag.endswith("Type"):
                    self.types[name] = node
                elif node.tag.endswith("element"):
                    self.elements[name] = node

    def kind(self, node):
        if isinstance(node, str):
            if node.startswith("xs:"):
                return ("primitive", node)
            return self.kind(self.types[node])
        if node.get("type"):
            return self.kind(node.attrib["type"])
        for child in node:
            tag = child.tag.rsplit("}", 1)[-1]
            if tag in ["simpleType", "complexType"]:
                return self.kind(child)
        if node.tag.endswith("simpleType"):
            restriction = node.find("x:restriction", self.ns)
            assert restriction is not None, ET.tostring(node).decode()
            enums = restriction.findall("x:enumeration", self.ns)
            if enums:
                return ("enum", [e.attrib["value"] for e in enums])
            patterns = restriction.findall("x:pattern", self.ns)
            if patterns:
                assert len(patterns) > 1 and all(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", e.attrib["value"]) for e in patterns)
                return ("enum", [e.attrib["value"] for e in patterns])
            return self.kind(restriction.attrib["base"])
        content = node.find("x:simpleContent/x:extension", self.ns)
        if content is not None:
            return self.kind(content.attrib["base"])
        extension = node.find("x:complexContent/x:extension", self.ns)
        if extension is not None:
            base = self.kind(extension.attrib["base"])
            assert base[0] == "struct" and extension.find("x:sequence", self.ns) is None
            return base
        sequence = node.find("x:sequence", self.ns)
        if sequence is not None:
            minimum, maximum = int(sequence.get("minOccurs", "1")), sequence.get("maxOccurs", "1")
            assert maximum != "unbounded" and minimum == int(maximum), "Nonfixed sequence not implemented"
            fields = [(e.attrib["name"], e) for e in sequence if e.tag.endswith("element")]
            if minimum != 1:
                assert len(fields) == 1
                return ("fixed_sequence", minimum, fields[0])
            return ("struct", fields)
        attrs = node.findall("x:attribute", self.ns)
        assert attrs and all("type" in a.attrib for a in attrs)
        return ("struct", [("@" + a.attrib["name"], a.attrib["type"]) for a in attrs])

    def layout(self, node):
        if not isinstance(node, str) and node.tag.endswith("element"):
            minimum, maximum = int(node.get("minOccurs", "1")), node.get("maxOccurs", "1")
            if maximum == "unbounded" or int(maximum) != minimum:
                return ("variable", self.kind(node))
            if minimum > 1:
                return ("fixed", minimum, self.kind(node))
        return self.kind(node)

    def size(self, kind):
        if kind[0] == "primitive":
            return 16 if kind[1] == "xs:string" else 8
        if kind[0] == "enum":
            return 8
        if kind[0] == "struct":
            return sum(self.size(self.layout(n)) for _, n in kind[1])
        if kind[0] in ["fixed", "fixed_sequence"]:
            sub = self.layout(kind[2][1]) if kind[0] == "fixed_sequence" else kind[2]
            if kind[0] == "fixed" and sub[0] in ["primitive", "enum"] and sub[1] != "xs:string":
                return (kind[1] * 4 + 7) // 8 * 8
            return kind[1] * self.size(sub)
        assert kind[0] == "variable"
        return 16

    def read(self, node, data, offset, d, path=""):
        kind = self.layout(node)
        assert 0 <= offset <= len(data) and self.size(kind) <= len(data) - offset, (path, "bounded schema read")
        tag = kind[0]
        if tag == "primitive":
            t = kind[1]
            if t == "xs:string":
                count, uid = struct.unpack_from("<QQ", data, offset)
                raw = d.payload(uid)
                assert len(raw) == (count + 7) // 8 * 8
                return raw[:count].rstrip(bytes([0])).decode(), offset + 16
            word = struct.unpack_from("<Q", data, offset)[0]
            if t == "xs:float":
                assert word >> 32 == 0
                value = struct.unpack_from("<f", data, offset)[0]
                assert math.isfinite(value)
            elif t == "xs:int":
                assert word <= 0xffffffff
                value = struct.unpack_from("<i", data, offset)[0]
            elif t == "xs:boolean":
                assert word in [0, 1]
                value = bool(word)
            else:
                assert t == "xs:unsignedInt" and word <= 0xffffffff, (path, t)
                value = word
            return value, offset + 8
        if tag == "enum":
            word = struct.unpack_from("<Q", data, offset)[0]
            assert word < len(kind[1]), (path, "enum outside schema")
            return kind[1][word], offset + 8
        if tag == "struct":
            values = {}
            for name, child in kind[1]:
                values[name], offset = self.read(child, data, offset, d, path + "/" + name)
            return values, offset
        if tag in ["fixed", "fixed_sequence"]:
            values = []
            sub = kind[2][1] if tag == "fixed_sequence" else node
            if tag == "fixed":
                # Remove only the enclosing occurrence count, retaining the exact type.
                sub = ET.fromstring(ET.tostring(node))
                sub.attrib.pop("minOccurs", None)
                sub.attrib.pop("maxOccurs", None)
                if kind[2][0] in ["primitive", "enum"] and kind[2][1] != "xs:string":
                    for i in range(kind[1]):
                        scalar = data[offset + 4*i:offset + 4*i+4] + bytes(4)
                        values.append(self.read(sub, scalar, 0, d, path + "[" + str(i) + "]")[0])
                    return values, offset + self.size(kind)
            for i in range(kind[1]):
                value, offset = self.read(sub, data, offset, d, path + "[" + str(i) + "]")
                values.append(value)
            return values, offset
        assert tag == "variable"
        count, uid = struct.unpack_from("<QQ", data, offset)
        assert count <= 65536
        raw = d.payload(uid)
        sub = ET.fromstring(ET.tostring(node))
        sub.attrib.pop("minOccurs", None)
        sub.attrib.pop("maxOccurs", None)
        values = []
        if kind[1][0] in ["primitive", "enum"] and kind[1][1] != "xs:string":
            assert len(raw) == (count * 4 + 7) // 8 * 8
            for i in range(count):
                scalar = raw[4*i:4*i+4] + bytes(4)
                values.append(self.read(sub, scalar, 0, d, path + "[" + str(i) + "]")[0])
        else:
            assert len(raw) == count * self.size(kind[1]), (path, "array size disagrees with schema")
            cursor = 0
            for i in range(count):
                value, cursor = self.read(sub, raw, cursor, d, path + "[" + str(i) + "]")
                values.append(value)
            assert cursor == len(raw)
        return values, offset + 16

    def compare_xml(self, values, xml, path=""):
        if isinstance(values, dict):
            for name, value in values.items():
                target = xml.get(name[1:]) if name.startswith("@") else xml.findall(name)
                if isinstance(value, list):
                    assert len(target) == len(value), (path + "/" + name, "XML array count")
                    for i, (a, b) in enumerate(zip(value, target)):
                        self.compare_xml(a, b, path + "/" + name + "[" + str(i) + "]")
                elif name.startswith("@"):
                    self.compare_xml(value, target, path + "/" + name)
                else:
                    assert len(target) == 1, (path + "/" + name, "XML scalar count")
                    self.compare_xml(value, target[0], path + "/" + name)
        else:
            text = xml if isinstance(xml, str) else xml.text.strip()
            if isinstance(values, bool):
                assert values == (text.lower() in ["1", "true"]), (path, "XML bool mismatch")
            elif isinstance(values, float):
                assert math.isclose(values, float(text), rel_tol=1e-6, abs_tol=1e-8), (path, "XML float mismatch")
            elif isinstance(values, int):
                assert values == int(text), (path, "XML integer mismatch")
            else:
                assert values.strip('"') == text.strip('"'), (path, "XML string mismatch")

if len(sys.argv) > 1 and sys.argv[1] in ["--layout-af", "--diagnose-af"]:
    schema = AFSchema()
    for tag in ["AFAlgoTuning", "ContrastAF"]:
        kind = schema.layout(schema.elements["chromatix" + tag])
        offset = 0
        if sys.argv[1] == "--diagnose-af":
            index = json.loads((P / "kernel333/sunny_imx319-index-private.json").read_text())
            d = Description(P / ("kernel" + str(index["source_stage"])) / index["filename"])
            sys.path.insert(0, str(HERE.parent / "kernel343"))
            from mode_tree import ModeTree
            uid = ModeTree(d.path).select(tag, [0, 2, 0, 0, 0, 0, 0])["uid"]
            data = d.payload(uid)
            xml = ET.parse(PRIVATE / ("parser-af-sunny_imx319-r1/xml/Scenario.Default/XML/STATS/chromatix" + tag + ".xml")).getroot()
        for name, node in kind[1]:
            size = schema.size(schema.layout(node))
            print(tag, offset, size, name, schema.layout(node)[0])
            if sys.argv[1] == "--diagnose-af":
                try:
                    value, end = schema.read(node, data, offset, d, name)
                    schema.compare_xml({name: value}, xml, tag)
                    print("  complete field XML match")
                except (AssertionError, KeyError) as error:
                    print("  diagnostic", str(error))
                    break
            offset += size
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--crosscheck-af":
    schema = AFSchema()
    proof = []
    for variant in ["sunny_imx319", "qtech_s5k3m5sx"]:
        index = json.loads((P / ("kernel333/" + variant + "-index-private.json")).read_text())
        d = Description(P / ("kernel" + str(index["source_stage"])) / index["filename"])
        rows = []
        for tag in ["AFAlgoTuning", "ContrastAF"]:
            element = schema.elements["chromatix" + tag]
            roots = d.find(tag)
            xmls = list((PRIVATE / ("parser-af-" + variant + "-r1/xml")).rglob("chromatix" + tag + ".xml"))
            assert len(roots) == len(xmls)
            for uid, payload in roots:
                assert len(payload) == schema.size(schema.layout(element)), (tag, len(payload), schema.size(schema.layout(element)))
                values, consumed = schema.read(element, payload, 0, d, tag)
                assert consumed == len(payload)
                matched = []
                for path in xmls:
                    try:
                        schema.compare_xml(values, ET.parse(path).getroot(), tag)
                        matched.append(str(path.relative_to(PRIVATE)))
                    except AssertionError:
                        pass
                assert matched, (variant, tag, uid, "No complete typed XML match")
                rows.append(dict(tag=tag, uid=uid, sha256=hashlib.sha256(payload).hexdigest(), values=values, xml_matches=matched))
        (PRIVATE / (variant + "-typed-af-private.json")).write_text(json.dumps(rows, indent=2) + "\n")
        proof.append(dict(variant=variant, roots=len(rows), bounded_full_payload_typed_decode=True, complete_oem_xml_match=True))
    (PRIVATE / "typed-af-proof-private.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof, indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--recover-schemas":
    commit = "9f17f1b568626b393e785b369c5dc94543774d7a"
    repo = Path("/home/cy122/x2pro-linux/refs/CamxChi-k117")
    manifest = json.loads((P / "kernel117/CamxChi/source-manifest.json").read_text())
    assert manifest["commit"] == commit
    paths = set((P / "kernel117/CamxChi/tree-paths.txt").read_text().splitlines())
    root = PRIVATE / "pinned-sources"
    root.mkdir(exist_ok=True)
    queue = ["chi-cdk/api/chromatix/XSD/stats/af/af.xsd"]
    rows = []
    seen = set()
    while queue:
        relative = queue.pop(0)
        if relative in seen:
            continue
        seen.add(relative)
        assert relative in paths and len(seen) <= 50
        target = root / relative
        q = subprocess.run(["git", "-C", str(repo), "show", commit + ":" + relative], capture_output=True, timeout=35)
        if q.returncode == 0:
            raw, origin = q.stdout, "existing pinned git object"
        else:
            url = "https://raw.githubusercontent.com/bjzhou/CamxChi/" + commit + "/" + relative
            with urllib.request.urlopen(url, timeout=40) as response:
                raw = response.read(2_000_001)
            assert len(raw) <= 2_000_000
            origin = "targeted pinned raw source"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        xml = ET.fromstring(raw)
        dependencies = []
        for element in xml:
            if element.tag.rsplit("}", 1)[-1] in ["include", "import"] and element.get("schemaLocation"):
                dep = posixpath.normpath(posixpath.join(posixpath.dirname(relative), element.attrib["schemaLocation"].replace("\\", "/")))
                assert dep.startswith("chi-cdk/api/chromatix/XSD/") and dep in paths, (relative, dep)
                dependencies.append(dep)
                queue.append(dep)
        rows.append(dict(repository="https://github.com/bjzhou/CamxChi", commit=commit, path=relative,
                         url="https://raw.githubusercontent.com/bjzhou/CamxChi/" + commit + "/" + relative,
                         source=origin, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), dependencies=dependencies))
    receipt = dict(commit=commit, git_repository=str(repo), sources=rows)
    (PRIVATE / "pinned-schema-manifest-private.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--replay-step":
    sys.path.insert(0, "/home/cy122/.local/lib/python3.14/site-packages")
    from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn.arm64_const import UC_ARM64_REG_PC, UC_ARM64_REG_SP, UC_ARM64_REG_X23, UC_ARM64_REG_X27, UC_ARM64_REG_X30, UC_ARM64_REG_CPACR_EL1
    binary = P / "kernel281/camera.qcom.so-private"
    raw = binary.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde"
    assert raw[:6] == b"\x7fELF\x02\x01"
    phoff = struct.unpack_from("<Q", raw, 32)[0]
    phsize, phcount = struct.unpack_from("<HH", raw, 54)
    segments = [struct.unpack_from("<IIQQQQQQ", raw, phoff+i*phsize) for i in range(phcount)]
    def at(address, count):
        found = [(offset+address-va) for kind, flags, offset, va, pa, size, mem, align in segments if kind == 1 and va <= address and address+count <= va+size]
        assert len(found) == 1
        return raw[found[0]:found[0]+count]
    # Exact retained HAL instructions, not a math provider or a translated routine.
    assert at(0x4f87e4, 4) == bytes.fromhex("2a01381e")  # FCVTZS W10,S9
    assert at(0x4f87c8, 4) == bytes.fromhex("2929281e")  # FADD S9,S9,S8
    assert at(0x4f87f4, 4) == bytes.fromhex("ca5b3c78")  # STRH to reverse logical index
    code = at(0x4f8000, 0x2000)
    proof = []
    for model in ["imx319", "s5k3m5"]:
        source = P / ("kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx319.bin" if model == "imx319" else "kernel326/qtech_s5k3m5sx-description-private.bin")
        d = Description(source)
        actuator_uid, actuator_body = d.one("actuatorDriver")
        words = d.words(actuator_uid)
        assert len(words) == 28 and words[:3] == (1, 0, 0)
        region_data = d.payload(words[21])
        assert len(region_data) == words[20] * 32
        values = dict(initialCode=words[19], regions=[])
        for i in range(words[20]):
            macro, infinity, cps, qvalue = struct.unpack_from("<4Q", region_data, 32*i)
            assert cps >> 32 == 0
            values["regions"].append(dict(macroStepBoundary=macro, infinityStepBoundary=infinity, codePerStep=struct.unpack("<f", struct.pack("<I", cps))[0], qValue=qvalue))
        regions = values["regions"]
        count = regions[-1]["macroStepBoundary"]
        assert 0 < count <= 1024 and regions[0]["infinityStepBoundary"] == 0
        mu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        mu.mem_map(0x4f8000, 0x2000)
        mu.mem_write(0x4f8000, code)
        for address, size in [(0x96a000, 0x2000), (0x5bf000, 0x1000), (0x1000000, 0x10000), (0x1100000, 0x10000)]:
            mu.mem_map(address, size)
        obj, driver, region_base = 0x1100000, 0x1102000, 0x1104000
        mu.mem_write(obj + 2060, struct.pack("<I", count))
        mu.mem_write(obj + 2064, struct.pack("<Q", driver))
        mu.mem_write(driver + 136, struct.pack("<h", values["initialCode"]))
        for i, region in enumerate(regions):
            mu.mem_write(region_base + 12*i, struct.pack("<HHfI", region["macroStepBoundary"], region["infinityStepBoundary"], region["codePerStep"], region["qValue"]))
        mu.reg_write(UC_ARM64_REG_CPACR_EL1, 3 << 20)
        mu.reg_write(UC_ARM64_REG_SP, 0x1008000)
        mu.mem_write(0x1008000 + 40, struct.pack("<Q", len(regions)))
        mu.reg_write(UC_ARM64_REG_X30, obj)
        mu.reg_write(UC_ARM64_REG_X23, region_base)
        mu.reg_write(UC_ARM64_REG_X27, len(regions))
        executed = []
        def hook(uc, address, size, unused):
            word = struct.unpack("<I", uc.mem_read(address, 4))[0]
            assert word & 0xfc000000 != 0x94000000, "Unexpected native dependency call in step-table core"
            executed.append(address)
        mu.hook_add(UC_HOOK_CODE, hook)
        try:
            mu.emu_start(0x4f8718, 0x4f89b4, count=50000)
        except Exception as error:
            raise RuntimeError("Native step core stopped at " + hex(mu.reg_read(UC_ARM64_REG_PC))) from error
        assert mu.reg_read(UC_ARM64_REG_PC) == 0x4f89b4
        actual = list(struct.unpack("<" + "h" * count, mu.mem_read(obj, count * 2)))
        f32 = lambda v: struct.unpack("<f", struct.pack("<f", v))[0]
        current = f32(values["initialCode"])
        expected = [None] * count
        step = 0
        for region in regions:
            while step < region["macroStepBoundary"]:
                expected[count - 1 - step] = int(current)
                current = f32(current + f32(region["codePerStep"]))
                step += 1
        assert actual == expected and all(0 <= v <= 1023 for v in actual)
        record = dict(model=model, module_source_sha256=hashlib.sha256(d.raw).hexdigest(), binary_sha256=hashlib.sha256(raw).hexdigest(),
                      begin=0x4f8718, end=0x4f89b4, native_core_sha256=hashlib.sha256(at(0x4f8718, 0x4f89b4-0x4f8718)).hexdigest(),
                      step_table=actual, minimum_dac=min(actual), maximum_dac=max(actual),
                      logical_index_zero_is_macro=True, logical_index_last_is_infinity=True,
                      native_instruction_count=len(executed), native_math_equals_independent_f32_model=True,
                      native_core_uses_code_per_step_without_q_division=True,
                      nominal_only_no_eeprom_adjustment=True, individual_safe_search_range_verified=False,
                      no_framework_emulation_no_physical_motion=True)
        (PRIVATE / (model + "-native-step-table-private.json")).write_text(json.dumps(record, indent=2) + "\n")
        proof.append({key: value for key, value in record.items() if key not in ["step_table", "minimum_dac", "maximum_dac"]})
    (PRIVATE / "native-step-proof-private.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof, indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--disassemble-step":
    binary = P / "kernel281/camera.qcom.so-private"
    sha = hashlib.sha256(binary.read_bytes()).hexdigest()
    assert sha == "e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde"
    ranges = [("module-create-sensor-submodules", 0x4f6e10, 0x4f96d0), ("sensor-create-submodules", 0x441148, 0x444bb0),
              ("sensor-finalize-initialization", 0x42d0b0, 0x433654)]
    rows = []
    for name, begin, end in ranges:
        q = subprocess.run(["aarch64-linux-gnu-objdump", "-d", "--start-address=" + hex(begin), "--stop-address=" + hex(end), str(binary)], capture_output=True, timeout=30)
        assert q.returncode == 0
        target = PRIVATE / (name + "-disassembly-private.txt")
        target.write_bytes(q.stdout)
        rows.append(dict(name=name, begin=begin, end=end, bytes=len(q.stdout), sha256=hashlib.sha256(q.stdout).hexdigest()))
    (PRIVATE / "step-disassembly-manifest-private.json").write_text(json.dumps(dict(binary_sha256=sha, ranges=rows), indent=2) + "\n")
    print(json.dumps(rows, indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--recover-native-source":
    repo = Path("/home/cy122/x2pro-linux/refs/CamxChi-k117")
    commit = "9f17f1b568626b393e785b369c5dc94543774d7a"
    names = ["camx/src/core/camxactuatordata.cpp", "camx/src/core/camxactuatordata.h", "camx/src/swl/sensor/camxactuator.cpp", "camx/src/swl/sensor/camxactuator.h",
             "camx/src/core/camxeepromdata.cpp", "chi-cdk/api/stats/chiafcommon.h", "chi-cdk/api/stats/chiafinterface.h"]
    rows = []
    for relative in names:
        q = subprocess.run(["git", "-C", str(repo), "show", commit + ":" + relative], capture_output=True, timeout=35)
        assert q.returncode == 0, relative
        target = PRIVATE / "pinned-sources" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(q.stdout)
        rows.append(dict(path=relative, repository="https://github.com/bjzhou/CamxChi", commit=commit, source="existing pinned git object", bytes=len(q.stdout), sha256=hashlib.sha256(q.stdout).hexdigest()))
    (PRIVATE / "pinned-native-source-manifest-private.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(json.dumps(rows, indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--parse-af":
    schemas = PRIVATE / "pinned-sources/chi-cdk/api/chromatix/XSD"
    parser = Path("/home/cy122/x2pro-linux/parser-k117")
    targets = {"AFAlgoTuning", "ContrastAF"}
    proof = []
    for variant in ["sunny_imx319", "qtech_s5k3m5sx"]:
        work = PRIVATE / ("parser-af-" + variant + "-r1")
        if (work / "parser-proof-private.json").exists():
            proof.append(json.loads((work / "parser-proof-private.json").read_text()))
            continue
        work.mkdir(exist_ok=True)
        schema = work / "api/chromatix/XSD"
        shutil.copytree(schemas, schema, dirs_exist_ok=True)
        shutil.copyfile(P / "kernel117/CamxChi/chi-cdk/api/chromatix/XSD/ParameterTuningTypes.xsd", schema / "stats/af/ParameterTuningTypes.xsd")
        index = json.loads((P / ("kernel333/" + variant + "-index-private.json")).read_text())
        source = P / ("kernel" + str(index["source_stage"])) / index["filename"]
        raw = source.read_bytes()
        data = bytearray(raw)
        _, offset, size = next(s for s in index["sections"] if s[0] == 0)
        allowed = set()
        for pos in range(offset, offset + size, 72):
            uid = struct.unpack_from("<Q", raw, pos)[0]
            if index["entries"][str(uid)]["name"] not in targets:
                struct.pack_into("<I", data, pos + 40, 0)
                allowed.update(range(pos + 40, pos + 44))
        assert all(i in allowed for i, (a, b) in enumerate(zip(raw, data)) if a != b)
        assert all(data[o:o+n] == raw[o:o+n] for kind, o, n in index["sections"] if kind != 0)
        analysis = work / "analysis-private.bin"
        analysis.write_bytes(data)
        dest = work / "xml"
        dest.mkdir(exist_ok=True)
        for path in [work, *work.rglob("*")]:
            os.chown(path, 1000, 1000)
        def limits():
            resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2, 256 * 1024**2))
            resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
            resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
        with (work / "reader-private.log").open("wb") as log:
            proc = subprocess.Popen(["stdbuf", "-oL", "-eL", str(parser / "ParameterParser"), str(dest), "x", str(schema / "stats/af"), "-b" + str(analysis)],
                                    cwd=work, env=dict(os.environ, LD_LIBRARY_PATH=str(parser / "runtime/lib")), user=1000, group=1000,
                                    start_new_session=True, stdin=subprocess.DEVNULL, stdout=log, stderr=log, preexec_fn=limits)
            try:
                ret = proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=3)
                raise RuntimeError("Bounded retained AF parser timed out; see private log")
        assert ret == 0, (variant, ret)
        output = list(dest.rglob("*.xml"))
        counts = {tag: sum(p.name == "chromatix" + tag + ".xml" for p in output) for tag in targets}
        expected = {tag:sum(e["name"] == tag for e in index["entries"].values()) for tag in targets}
        assert counts == expected, (variant, counts, expected)
        row = dict(variant=variant, parser_exit=ret, roots=counts, original_sha256=hashlib.sha256(raw).hexdigest(),
                   original_payload_and_mode_tree_unchanged=True,
                   xml_files=[dict(path=str(p.relative_to(dest)), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in output])
        (work / "parser-proof-private.json").write_text(json.dumps(row, indent=2) + "\n")
        proof.append(row)
    print(json.dumps([dict(variant=r["variant"], roots=r["roots"], parser_exit=r["parser_exit"], original_payload_and_mode_tree_unchanged=True) for r in proof], indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--inventory":
    for label, path in [("imx319", P / "kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx319.bin"),
                        ("s5k3m5", P / "kernel326/qtech_s5k3m5sx-description-private.bin")]:
        d = Description(path)
        matches = [dict(uid=uid, **entry) for uid, entry in d.entries.items() if any(s in entry["name"].lower() for s in ["actuator", "damp", "af", "focus", "region", "infinity", "macro"])]
        print(json.dumps(dict(module=label, schema_roots=matches), indent=2))
    root = P / "kernel117/CamxChi/chi-cdk/api"
    paths = [p for p in root.rglob("*.xsd") if p.name.lower().startswith("af_") or any(s in p.name.lower() for s in ["actuator", "afalgorithm", "afdriver", "aftuning", "autofocus", "eeprom"])]
    print(json.dumps(dict(schemas=[str(p.relative_to(root)) for p in paths]), indent=2))
    for variant in ["sunny_imx319", "qtech_s5k3m5sx"]:
        index = json.loads((P / f"kernel333/{variant}-index-private.json").read_text())
        roots = [{"uid": uid, **entry} for uid, entry in index["entries"].items() if entry["name"] in ["AFAlgoTuning", "AFTuningSoftwareStatistics", "AFMONITOR", "AFExtension"]]
        print(json.dumps(dict(variant=variant, tuning_root_counts={tag:sum(r['name']==tag for r in roots) for tag in ['AFAlgoTuning','AFTuningSoftwareStatistics','AFMONITOR','AFExtension']}), indent=2))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--schema":
    path = P / "kernel117/CamxChi/chi-cdk/api" / sys.argv[2]
    assert path.is_file() and ".." not in Path(sys.argv[2]).parts
    lines = path.read_text().splitlines()
    needles = sys.argv[3].split(",")
    selected = set()
    for i, line in enumerate(lines):
        if any(s.lower() in line.lower() for s in needles):
            selected.update(range(max(0, i - 3), min(len(lines), i + 35)))
    for i in sorted(selected):
        print(f"{i+1}: {lines[i]}")
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--ipa":
    tree = Path(json.loads((HERE.parent / "kernel450/source-state.json").read_text())["source"])
    for relative in ["src/ipa/camss-vfe/camss.cpp", "src/ipa/libipa/contrast_af.h"]:
        path = tree / relative
        print("SOURCE", relative, hashlib.sha256(path.read_bytes()).hexdigest())
        lines = path.read_text().splitlines()
        selected = set()
        for i, line in enumerate(lines):
            if any(p in line for p in ["configureAutofocus(", "settleMs", "coarseStep", "fineStep", "framePeriod", "af_.process(", "focusControl_", "struct Config"]):
                selected.update(range(max(0, i-3), min(len(lines), i+25)))
        for i in sorted(selected):
            print(f"{i+1}: {lines[i]}")
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--select":
    sys.path.insert(0, str(HERE.parent / "kernel343"))
    from mode_tree import ModeTree
    for variant, mode in [("sunny_imx319", 2), ("qtech_s5k3m5sx", 3)]:
        index = json.loads((P / f"kernel333/{variant}-index-private.json").read_text())
        path = P / ("kernel" + str(index["source_stage"])) / index["filename"]
        mode_tree = ModeTree(path)
        for usecase, enum in [("Preview", 0), ("Video", 2)]:
            context = [0, mode, enum, 0, 0, 0, 0]
            selected = mode_tree.select("AFAlgoTuning", context)
            query = "AFAlgoTuning " + " ".join(map(str, context)) + "\n"
            q = subprocess.run([str(P / "kernel343/stock-selection-manager"), str(path)], input=query, capture_output=True, text=True, timeout=30)
            assert q.returncode == 0 and q.stdout.split() == ["0", "AFAlgoTuning", str(selected['uid']), str(selected['mode_id'])]
            print(json.dumps(dict(variant=variant, mode=mode, usecase=usecase, uid=selected['uid'], mode_id=selected['mode_id'], original_manager_match=True)))
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--recover":
    sys.path.insert(0, str(HERE.parent / "kernel343"))
    from mode_tree import ModeTree
    tree = Path(json.loads((HERE.parent / "kernel450/source-state.json").read_text())["source"])
    ipa_path = tree / "src/ipa/camss-vfe/camss.cpp"
    ipa = ipa_path.read_text()
    assert 'tuning["lens"].get<std::string>("")!=lensModel_' in ipa
    assert 'configureAutofocus(tuning["autofocus"].isEmpty()?(*root)["autofocus"]:tuning["autofocus"],ipaControls)' in ipa
    assert 'const uint64_t guard=std::ceil((uint64_t(frameLength_)+sensorContext.exposureLines)*lineUs_*1000)' in ipa
    assert '.name = "bu64253"' in (HERE / "bu64253.c").read_text()
    required = ["lens", "minimumCode", "maximumCode", "coarseStep", "fineStep", "samples", "settleMs", "timeoutMs", "minimumPeak", "peakRatio", "verifyRatio"]
    assert all('tuning["' + key + '"]' in ipa for key in required)
    rows, private_rows = [], []
    retained = P / "kernel450/lens-scope"

    def floatslot(word):
        assert word >> 32 == 0
        return struct.unpack("<f", struct.pack("<I", word))[0]

    def actuator(path, xml_path):
        d = Description(path)
        uid, body = d.one("actuatorDriver")
        w = d.words(uid)
        assert len(w) == 28 and w[:3] == (1, 0, 0)
        xml = ET.parse(xml_path).getroot()
        initial = w[19]
        assert 0 <= initial <= 1023 and initial == int(xml.findtext("tunedParams/initialCode"))
        region_body = d.payload(w[21])
        assert len(region_body) == w[20] * 32
        regions = []
        for i in range(w[20]):
            near, far, cps, q = struct.unpack_from("<4Q", region_body, i * 32)
            regions.append(dict(macroStepBoundary=near, infinityStepBoundary=far, codePerStep=floatslot(cps), qValue=q))
        xr = [dict(macroStepBoundary=int(r.findtext("macroStepBoundary")), infinityStepBoundary=int(r.findtext("infinityStepBoundary")),
                   codePerStep=float(r.findtext("codePerStep")), qValue=int(r.findtext("qValue"))) for r in xml.findall("tunedParams/regionParams/region")]
        assert len(regions) == len(xr)
        for a, b in zip(regions, xr):
            assert all(a[k] == b[k] for k in ["macroStepBoundary", "infinityStepBoundary", "qValue"])
            assert math.isclose(a["codePerStep"], b["codePerStep"], rel_tol=1e-6)
        damping = {}
        for direction, at in [("forward", 22), ("backward", 25)]:
            ringing, count, ref = w[at:at+3]
            buf = d.payload(ref)
            assert len(buf) == count * 16
            scenarios = []
            for i in range(count):
                n, ref = struct.unpack_from("<2Q", buf, 16 * i)
                b = d.payload(ref)
                assert len(b) == n * 24
                scenarios.append([dict(zip(["dampingStep", "dampingDelayUs", "hwParams"], struct.unpack_from("<3Q", b, j * 24))) for j in range(n)])
            base = "tunedParams/" + direction + "Damping"
            expected = [[{key:int(r.findtext(key)) for key in ["dampingStep", "dampingDelayUs", "hwParams"]} for r in s.findall("region")]
                        for s in xml.findall(base + "/scenarioDampingParams/scenario")]
            assert scenarios == expected and ringing == int(xml.findtext(base + "/ringingScenario"))
            damping[direction] = dict(ringingScenario=ringing, scenarios=scenarios)
        assert len(regions) == 1 and regions[0]["qValue"] > 0
        region = regions[0]
        assert region["infinityStepBoundary"] == 0
        count = region["macroStepBoundary"]
        f32 = lambda v: struct.unpack("<f", struct.pack("<f", v))[0]
        current = f32(initial)
        table = [None] * count
        for step in range(count):
            table[count - 1 - step] = int(current)
            current = f32(current + f32(region["codePerStep"]))
        assert all(0 <= value <= 1023 for value in table)
        ep_uid, ep_body = d.one("EEPROMDriverData")
        ep = d.words(ep_uid)
        assert ep[:3] == (1, 0, 0) and len(ep) >= 21
        assert ep[15] in [0, 1] and ep[16] in [0, 1] and ep[18] == ep[20] == 65535
        return d, dict(initialCode=initial, regions=regions, damping=damping,
                       nominal_minimum_dac=min(table), nominal_maximum_dac=max(table), nominal_step_table=table,
                       nominal_native_step_table_rounding_verified=True,
                       eeprom_af_prefix=dict(available=bool(ep[15]), endian=["BIG", "LITTLE"][ep[16]], macro_offset=ep[17], macro_mask=ep[18], infinity_offset=ep[19], infinity_mask=ep[20]),
                       xml_sha256=hashlib.sha256(xml_path.read_bytes()).hexdigest())

    sources = [("imx319", "sunny_imx319", 2, P / "kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx319.bin", "sunny_imx319", P / "kernel299/imx319-eeprom-read1-private.bin", P / "kernel299/imx319-eeprom-read2-private.bin"),
               ("s5k3m5", "qtech_s5k3m5sx", 3, P / "kernel326/qtech_s5k3m5sx-description-private.bin", "qtech_s5k3m5sx-current326", P / "kernel326/reads-r2/s5k3m5-read1-private.bin", P / "kernel326/reads-r2/s5k3m5-read2-private.bin")]
    for model, variant, mode, path, parser_name, read1, read2 in sources:
        xmls = list((retained / ("parser-" + parser_name) / "xml").rglob("actuatorDriver.xml"))
        assert len(xmls) == 1
        parser_proof = json.loads((retained / ("parser-" + parser_name) / "crosscheck-private.json").read_text())
        assert parser_proof["xml_sha256"] == hashlib.sha256(xmls[0].read_bytes()).hexdigest()
        d, values = actuator(path, xmls[0])
        if model == "imx319":
            other, other_values = actuator(P / "kernel115/vendor-camera-bins/com.qti.sensormodule.qtech_imx319.bin", xmls[0])
            assert all(values[key] == other_values[key] for key in ["initialCode", "regions", "damping"])
        raw1, raw2 = read1.read_bytes(), read2.read_bytes()
        assert raw1 == raw2
        prefix = values["eeprom_af_prefix"]
        assert prefix["available"] and prefix["endian"] == "LITTLE"
        unit = {}
        for field in ["macro", "infinity"]:
            offset, mask = prefix[field + "_offset"], prefix[field + "_mask"]
            assert offset + 2 <= len(raw1)
            unit[field] = int.from_bytes(raw1[offset:offset+2], "little") & mask
        unit.update(within_protocol=all(0 <= value <= 1023 for value in unit.values()),
                    duplicate_reads_equal=True, factory_checksum_verified=False,
                    full_af_format_margin_sag_semantics_verified=False, applied=False)
        index = json.loads((P / f"kernel333/{variant}-index-private.json").read_text())
        tuning_path = P / ("kernel" + str(index["source_stage"])) / index["filename"]
        tuning = tuning_path.read_bytes()
        mode_tree = ModeTree(tuning_path)
        selected = []
        for usecase, enum in [("Preview", 0), ("Video", 2)]:
            context = [0, mode, enum, 0, 0, 0, 0]
            selection = mode_tree.select("AFAlgoTuning", context)
            query = "AFAlgoTuning " + " ".join(map(str, context)) + "\n"
            q = subprocess.run([str(P / "kernel343/stock-selection-manager"), str(tuning_path)], input=query, capture_output=True, text=True, timeout=30)
            assert q.returncode == 0 and q.stdout.split() == ["0", "AFAlgoTuning", str(selection['uid']), str(selection['mode_id'])]
            selected.append(dict(usecase=usecase, **selection))
        assert selected[0]["uid"] == selected[1]["uid"]
        entry = index["entries"][str(selected[0]["uid"])]
        algo = tuning[index["base"] + entry["offset"]:index["base"] + entry["offset"] + entry["bytes"]]
        assert len(algo) == entry["bytes"] and entry["version"] == 9
        (PRIVATE / (variant + "-AFAlgoTuning-selected-private.bin")).write_bytes(algo)
        native = json.loads((PRIVATE / (model + "-native-step-table-private.json")).read_text())
        assert native["module_source_sha256"] == hashlib.sha256(d.raw).hexdigest()
        assert native["step_table"] == values["nominal_step_table"] and native["native_math_equals_independent_f32_model"]
        typed = json.loads((PRIVATE / (variant + "-typed-af-private.json")).read_text())
        algo_record = next(row for row in typed if row["tag"] == "AFAlgoTuning" and row["uid"] == selected[0]["uid"])
        assert algo_record["sha256"] == hashlib.sha256(algo).hexdigest()
        contrast_selections = []
        for usecase, enum in [("Preview", 0), ("Video", 2)]:
            context = [0, mode, enum, 0, 0, 0, 0]
            selection = mode_tree.select("ContrastAF", context)
            query = "ContrastAF " + " ".join(map(str, context)) + "\n"
            q = subprocess.run([str(P / "kernel343/stock-selection-manager"), str(tuning_path)], input=query, capture_output=True, text=True, timeout=30)
            assert q.returncode == 0 and q.stdout.split() == ["0", "ContrastAF", str(selection["uid"]), str(selection["mode_id"])]
            contrast_selections.append(dict(usecase=usecase, **selection))
        assert contrast_selections[0]["uid"] == contrast_selections[1]["uid"]
        contrast_record = next(row for row in typed if row["tag"] == "ContrastAF" and row["uid"] == contrast_selections[0]["uid"])
        common = algo_record["values"]["commonElements"]
        translated = {}
        for key, logical in common.items():
            if not key.startswith("position"):
                continue
            translated[key] = dict(logical_index=logical, within_nominal_table=0 <= logical < len(native["step_table"]))
            if translated[key]["within_nominal_table"]:
                translated[key]["nominal_dac"] = native["step_table"][logical]
        common_bounds_valid = all(translated[key]["within_nominal_table"] for key in ["positionNearEnd", "positionFarEnd"])
        mapped = dict(lens="bu64253")
        if common_bounds_valid:
            bound_codes = [translated[key]["nominal_dac"] for key in ["positionNearEnd", "positionFarEnd"]]
            mapped.update(minimumCode=min(bound_codes), maximumCode=max(bound_codes))
        source_single = contrast_record["values"]["singleSearch"]
        source_step = {key: source_single[key] for key in ["index", "TAFStepTable", "CAFStepTable", "optics", "frameDelay", "ignoreFirstInvalidFrame"]}
        step_delta_candidates = {}
        for table_name in ["TAFStepTable", "CAFStepTable"]:
            step_delta_candidates[table_name] = {}
            for lighting, region_steps in source_single[table_name].items():
                step_delta_candidates[table_name][lighting] = {}
                for region_name, logical_step in region_steps.items():
                    delta = sorted({abs(native["step_table"][i+logical_step] - native["step_table"][i]) for i in range(max(0, len(native["step_table"])-logical_step))}) if logical_step > 0 else []
                    step_delta_candidates[table_name][lighting][region_name] = dict(logical_step=logical_step, possible_nominal_absolute_dac_deltas=delta,
                                                                                                     entire_table_translation_only_not_region_schedule=True)
        missing = [key for key in required if key not in mapped]
        field_provenance = {
            "lens": dict(state="mapped", source="453 bu64253.c i2c_driver.driver.name and current CameraLens model matching", value=mapped["lens"]),
            "minimumCode": dict(state="nominal_mode_bound_candidate" if common_bounds_valid else "not_mappable_to_nominal_table", source="selected AFAlgoTuning/commonElements logical bound through exact retained native nominal step table", individual_safe_endpoint=False),
            "maximumCode": dict(state="nominal_mode_bound_candidate" if common_bounds_valid else "not_mappable_to_nominal_table", source="selected AFAlgoTuning/commonElements logical bound through exact retained native nominal step table", individual_safe_endpoint=False),
            "coarseStep": dict(state="decoded_logical_region_tables_not_uniform_dac_policy", source="selected ContrastAF v9 singleSearch/TAFStepTable and CAFStepTable; native quantized delta alternatives retained privately"),
            "fineStep": dict(state="decoded_logical_region_tables_not_uniform_dac_policy", source="selected ContrastAF v9 singleSearch/TAFStepTable and CAFStepTable; native quantized delta alternatives retained privately"),
            "samples": dict(state="not_mapped", source="original AF statistics domain and current ContrastAf sampling policy differ"),
            "settleMs": dict(state="source_phase_frame_delays_decoded_no_fixed_ms_mapping", source="selected ContrastAF fullSweep/frameDelayInf,Norm,Final; singleSearch/frameDelay base,coarse,fine; miscellaneous/frameSkipGoToPeak; dampingDelayUs is a different quantity"),
            "timeoutMs": dict(state="policy_not_selected", source="current ContrastAf total search deadline; no factory equivalent accepted"),
            "minimumPeak": dict(state="metric_not_equivalent", source="current luma FoM requires threshold in its own domain"),
            "peakRatio": dict(state="metric_not_equivalent", source="current luma FoM/coarse-minimum peak policy"),
            "verifyRatio": dict(state="metric_not_equivalent", source="current selected-position verification policy"),
            "frame_guard": dict(state="existing_runtime_value", source="IPACamss::processFocus immutable frameLength + exposureLines, scaled by lineUs; ACK completion clock plus settle handled by ContrastAf"),
        }
        record = dict(model=model, declared_variant=variant, sensor_mode=mode,
                      module_source_sha256=hashlib.sha256(d.raw).hexdigest(),
                      tuning_source_sha256=hashlib.sha256(tuning).hexdigest(),
                      actuator_tuned_values=values, eeprom_candidate=unit,
                      af_algo_selection=selected, selected_af_algo_version=entry["version"],
                      selected_af_algo_sha256=hashlib.sha256(algo).hexdigest(),
                      selected_af_algo_typed_xml_matches=algo_record["xml_matches"],
                      contrast_af_selection=contrast_selections, selected_contrast_af_sha256=contrast_record["sha256"],
                      selected_contrast_af_typed_xml_matches=contrast_record["xml_matches"],
                      common_position_translation=translated, source_common_bounds_valid_in_nominal_table=common_bounds_valid,
                      source_logical_search_step_and_frame_policy=source_step,
                      source_fullsweep=contrast_record["values"]["fullSweep"],
                      source_return_to_peak_policy=contrast_record["values"]["miscellaneous"],
                      source_set_invalid_frame=algo_record["values"]["setInvalidFrame"],
                      translated_step_alternatives=step_delta_candidates,
                      source_optic_index_selection_semantics_not_replayed=True,
                      native_step_core_proof={key: value for key, value in native.items() if key not in ["step_table", "minimum_dac", "maximum_dac"]},
                      candidate_fields=mapped, unresolved_required_fields=missing,
                      field_provenance=field_provenance,
                      supplier_eeprom_identity_independently_verified=False,
                      search_step_and_settle_not_inferred_from_damping=True,
                      current_ipa_defaults_not_used_to_complete_candidate=True,
                      deployable=False, applied=False)
        (PRIVATE / (model + "-af-incomplete-private.json")).write_text(json.dumps(record, indent=2) + "\n")
        (PRIVATE / (model + "-af-source-candidate-private.json")).write_text(json.dumps(record, indent=2) + "\n")
        private_rows.append(record)
        rows.append(dict(model=model, declared_variant=variant, sensor_mode=mode,
                         module_source_sha256=record["module_source_sha256"], actuator_xml_sha256=values["xml_sha256"],
                         matched_actuator_tuned_region_and_both_damping_directions=True,
                         eeprom_prefix_and_duplicate_reads_checked=True, individual_af_applied=False,
                         original_af_mode_manager_match=True, preview_video_af_root_same=True,
                         af_algo_root_uid=selected[0]["uid"], af_algo_root_version=entry["version"],
                         selected_af_algo_sha256=record["selected_af_algo_sha256"],
                         original_contrast_af_mode_manager_match=True,
                         selected_contrast_af_root_uid=contrast_selections[0]["uid"],
                         selected_contrast_af_sha256=contrast_record["sha256"],
                         complete_typed_af_roots_xml_matched=sum(row["tag"] in ["AFAlgoTuning", "ContrastAF"] for row in typed),
                         source_common_bounds_valid_in_nominal_table=common_bounds_valid,
                         selected_logic_step_and_phase_frame_fields_decoded=True,
                         actual_ipa_lens_match_name="bu64253", mapped_fields=sorted(mapped), unresolved_required_fields=missing,
                         field_provenance={key:{k:v for k,v in value.items() if k not in ["value", "integer_candidates"]} for key,value in field_provenance.items()},
                         native_nominal_step_table_replayed_and_equal=True, nominal_only_no_verified_eeprom_margins=True, deployable=False))
    expected_schema_names = ["af.xsd", "afalgotuningelements.xsd", "afcontrastafelements.xsd", "afglobalelements.xsd"]
    pinned = json.loads((P / "kernel117/CamxChi/source-manifest.json").read_text())
    assert pinned["commit"] == "9f17f1b568626b393e785b369c5dc94543774d7a"
    tree_paths = (P / "kernel117/CamxChi/tree-paths.txt").read_text().splitlines()
    required_schema_paths = ["chi-cdk/api/chromatix/XSD/stats/af/" + name for name in expected_schema_names]
    assert all(path in tree_paths for path in required_schema_paths)
    schemas = json.loads((PRIVATE / "pinned-schema-manifest-private.json").read_text())
    native_sources = json.loads((PRIVATE / "pinned-native-source-manifest-private.json").read_text())
    assert schemas["commit"] == pinned["commit"] and len(schemas["sources"]) == 18
    assert all(row["source"] == "existing pinned git object" for row in schemas["sources"] + native_sources)
    assert all(hashlib.sha256((PRIVATE / "pinned-sources" / row["path"]).read_bytes()).hexdigest() == row["sha256"] for row in schemas["sources"] + native_sources)
    typed_proof = json.loads((PRIVATE / "typed-af-proof-private.json").read_text())
    assert sum(row["roots"] for row in typed_proof) == 39 and all(row["complete_oem_xml_match"] for row in typed_proof)
    report = dict(stage=453, scope="offline OEM AF source recovery and nondeployable typed candidates", modules=rows,
                  current_ipa_source_sha256=hashlib.sha256(ipa_path.read_bytes()).hexdigest(),
                  per_mode_autofocus_overrides_root_supported=True,
                  existing_immutable_exposure_plus_readout_guard_preserved=True,
                  damping_delay_not_optical_settle_time=True,
                  protocol_limits_not_used_as_search_limits=True,
                  complete_af_algo_schema_not_retained_in_inspected_sources=False,
                  schemas_recovered_from_existing_pinned_git_objects=True,
                  source_schema_files=18, complete_typed_af_roots_xml_matched=39,
                  af_mode_queries_original_manager_equal=8,
                  schema_sources=[{key:row[key] for key in ["repository", "commit", "path", "bytes", "sha256"]} for row in schemas["sources"]],
                  native_semantics_sources=native_sources,
                  retained_hal_native_step_core=dict(binary_sha256="e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde", begin="0x4f8718", end_exclusive="0x4f89b4", sha256="6f5c25830bbc9eb8eb026f14fd82fd54de60622039ce35807af4c99a8e51769d", modules_replayed=2, every_output_step_equal=True),
                  pinned_schema_commit=pinned["commit"],
                  factory_tuning_values_and_unit_data_private=True,
                  no_phone_sdk_compile_production_changes=True,
                  automatic_focus_ready=False, offline_checks_passed=True)
    (HERE / "af-profile-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(stage=453, modules=[row["model"] for row in rows], source_schema_files=18,
                          complete_typed_af_roots_xml_matched=39, original_manager_queries=8,
                          nominal_native_step_tables_equal=True, deployable=False, offline_checks_passed=True), indent=2))
    raise SystemExit(0)

print("Use --recover-schemas, --recover-native-source, --parse-af, --crosscheck-af, --disassemble-step, --replay-step, then --recover; --inventory/--ipa/--layout-af inspect metadata.")
