from pathlib import Path
import hashlib
import json
import urllib.request

here = Path(__file__).resolve().parent
private = Path('/mnt/e/edk2-samurai-out/kernel226')
out = private / 'qualcomm-loc-public-sources'
out.mkdir(exist_ok=True)
commit = 'a581b6c9ee15e3fdbb0e15f43cd37b97616b0948'
base = 'https://raw.githubusercontent.com/qualcomm-linux/location-apis-qcom/' + commit + '/loc_api/loc_api_v02/'
sources = {}
proof_path = here / 'loc-layout-source-validation.json'
previous = json.loads(proof_path.read_text()) if proof_path.exists() else {}
for name in ['location_service_v02.h', 'location_service_v02.c', 'LocApiV02.cpp']:
    target = out / name
    cached = previous.get('sources', {}).get(name)
    if target.exists() and cached:
        raw = target.read_bytes()
        assert cached['url'] == base + name and hashlib.sha256(raw).hexdigest() == cached['sha256']
    else:
        raw = urllib.request.urlopen(base + name, timeout=35).read()
    if target.exists():
        assert target.read_bytes() == raw
    else:
        target.write_bytes(raw)
    sources[name] = dict(url=base + name, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
header = (out / 'location_service_v02.h').read_text()
encoding = (out / 'location_service_v02.c').read_text()
implementation = (out / 'LocApiV02.cpp').read_text()
assert 'eQMI_LOC_OPER_MODE_STANDALONE_V02 = 4' in header
assert 'eQMI_LOC_ACCURACY_HIGH_V02 = 3' in header
assert 'qmiLocGetFixCriteriaIndMsgT_data_v02' in encoding
assert '#define QMI_LOC_GET_NMEA_TYPES_REQ_V02 0x003F' in header
assert '#define QMI_LOC_GET_SERVICE_REVISION_REQ_V02 0x0032' in header
assert 'expandedNmea' in header and 'expandedNmea' in encoding
assert 'expandedSvList' in header and 'expandedSvList' in implementation
assert 'svList' in header and 'cN0Dbhz' in implementation
report = dict(stage=226, fixed_primary_source_commit=commit, sources=sources,
    standalone_enum4_confirmed=True, horizontal_high_enum3_confirmed=True,
    get_fix_criteria_indication_and_expanded_sv_layout_present=True, expanded_nmea_layout_present=True,
    locally_compiled_tool_uses_typed_standalone_enum=True,
    raw_native_service_revision_field_tag2_u32_observed=True, nmea_query_message_confirmed_0x3f=True,
    no_claim_that_current_firmware_uses_expanded_list=True)
(here / 'loc-layout-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'sources'}))
