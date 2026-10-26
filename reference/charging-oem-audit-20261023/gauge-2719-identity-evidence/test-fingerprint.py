"""New saved identity parser boundaries, no previous protocol suite rerun."""
from pathlib import Path
import copy,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('actual_identity_fingerprint',HERE/'identity-fingerprint.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
paths=[Path('E:/edk2-samurai-out/kernel80/firmware-version.txt'),Path('E:/edk2-samurai-out/kernel85/chemistry-query.txt')]
expected=['7bdf619c59e1c79202bec4ea4012e0dbeb0d44106f74710c4c99e73ea863fc53','572ab13398aa75525baf9d54fe3e08f24006fd25f2bd84f68eed6e76655f725b']
cases=[];values=[]
for index,path in enumerate(paths):
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==expected[index]
    value=m.decode_saved(raw);assert value['historical_payload_match'] is True and value['new_mac_query_authorized'] is False
    values.append(value);cases.append('actual_cached_firmware_frame_'+str(index))
assert values[0]==values[1]
raw=paths[0].read_bytes();record=next(x for x in raw.splitlines() if x.startswith(b'FirmwareVersion'))
variants={
 'duplicate_complete':raw+b'\n'+record+b'\n',
 'complete_plus_malformed_prefix':raw+b'FirmwareVersion truncated\n',
 'wrong_command':raw.replace(b'command=0x0002',b'command=0x0056'),
 'wrong_route':raw.replace(b'request=000200',b'request=3e0200'),
 'nonzero_query_validation':raw.replace(b'validation=0',b'validation=1'),
 'short_frame':raw.replace(b'response=0200',b'response=02'),
 'bad_echo':raw.replace(b'response=0200',b'response=0300'),
 'bad_checksum':raw.replace(b'00290f',b'00280f'),
 'wrong_length':raw.replace(b'00290f',b'00290e'),
 'inconsistent_printed_size':raw.replace(b'payload=11',b'payload=12'),
 'duplicate_field':raw.replace(b'validation=0',b'validation=0 validation=0')}
for name,value in variants.items():
    try:m.decode_saved(value)
    except ValueError:cases.append(name)
    else:raise AssertionError('accepted '+name)
result=dict(passed=True,case_count=len(cases),cases=cases,actual_cached_frames=2,new_real_frames_or_queries=0,
    compared_cached_outputs_identical=values[0]==values[1],parser_sha256=hashlib.sha256((HERE/'identity-fingerprint.py').read_bytes()).hexdigest(),
    test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),old_suites_rerun=False,device_accessed=False)
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result))
