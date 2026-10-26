from pathlib import Path
import hashlib, json, xml.etree.ElementTree as ET

root = Path('/mnt/e/edk2-samurai-out/rx61')
report = json.loads((root / 'package-inputs.json').read_text())
wd = Path(report['source_tree']) / 'src/windows/wdfserial'
inf = (wd / 'qceudexp.inf').read_text()
assert (root / 'qceudexp.inf').read_bytes() == (wd / 'qceudexp.inf').read_bytes()
assert inf.count('KmdfLibraryVersion=$KMDFVERSION$') == 1
assert 'KmdfService=qceudexp,EudKmdf' in inf
assert inf.count('USB\\VID_05C6&PID_9505') == 1
assert 'EudCopy=13' in inf and 'ServiceBinary=%13%\\qcwdfserial.sys' in inf
assert 'HKLM' not in inf and 'QCDeviceZLPEnabled' not in inf
ns = {'m': 'http://schemas.microsoft.com/developer/msbuild/2003'}
baseline = ET.parse(wd / 'qcwdfserial.vcxproj')
candidate = ET.parse(wd / 'qceudexp.vcxproj')
def modules(tree):
    return [e.attrib['Include'] for e in tree.findall('.//m:ClCompile', ns) if 'Include' in e.attrib]
assert modules(baseline) == modules(candidate) and len(modules(candidate)) == 9
assert [e.attrib['Include'] for e in candidate.findall('.//m:Inf', ns)] == ['qceudexp.inf']
report['inf_sha256'] = hashlib.sha256((wd / 'qceudexp.inf').read_bytes()).hexdigest()
report['authored_input_validation'] = 'PASS; not WDK InfVerif or a driver build'
report['notes'].append('Literal KMDF stamp token checked after script quoting error; no build or device action used the malformed intermediate draft.')
(root / 'package-inputs.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'inf_sha256': report['inf_sha256'], 'modules': modules(candidate), 'input_validation': 'PASS', 'full_wdk_build': False}))
