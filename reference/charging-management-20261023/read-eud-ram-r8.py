"""Bounded read-only capture of the existing reserved firmware EUD RAM ring."""
from pathlib import Path
import argparse
import ast
import base64
import hashlib
import importlib.util
import json
import re
import time

REF = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
REPO = Path('/home/cy122/edk2-samurai/repo')
BASE_SHA = 'a1dffafa5d24448c90015ed19ebab142e2e07b04cc7d1a8e893463742f0a3369'
SOURCE_PATHS = [
    'Platform/Realme/sm8150/Library/EudSerialPortLib/EudLog.h',
    'Platform/Realme/sm8150/Library/EudSerialPortLib/EudSerialPortLib.c',
    'Silicon/Qualcomm/sm8150/Library/PlatformMemoryMapLib/PlatformMemoryMapLib.c',
]

READ_CODE = r'''
import base64,mmap,struct,sys
start,total=0x9ffe3000,0x14000
assert os.sysconf('SC_PAGE_SIZE')==4096
cover=[]
for line in Path('/proc/iomem').read_text().splitlines():
 match=re.fullmatch(r'\s*([0-9a-f]+)-([0-9a-f]+) : (.*)',line)
 if match and int(match[1],16)<=start and int(match[2],16)>=start+total-1:
  cover.append((line,match[3]))
assert cover and cover[-1][1]=='reserved', 'RAM range not covered by a reserved leaf'
fd=os.open('/dev/mem',os.O_RDONLY|os.O_SYNC|os.O_CLOEXEC)
try:
 with mmap.mmap(fd,total,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ,offset=start) as view:
  before=bytes(view[:32])
  fields=struct.unpack('<8I',before)
  print(json.dumps({'phase':'header','fields':fields}),file=sys.stderr,flush=True)
  assert fields[:3]==(0x474f4c45,0x10000,total-32), 'Unexpected ring header; no data read'
  assert ((fields[3]-fields[4])&0xffffffff)<=total-32, 'Invalid head/tail distance'
  raw=bytes(view[:total])
  after=bytes(view[:32])
finally:
 os.close(fd)
print(json.dumps({'phase':'private_raw','raw_b64':base64.b64encode(raw).decode(),'header_before':list(fields),'header_after':list(struct.unpack('<8I',after))}),flush=True)
assert before==raw[:32]==after, 'Ring header changed; keep private capture only'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert sha('/usr/share/samurai-charging/manifest.json')==expected
assert all(sha('/sys/module/'+n+'/notes/.note.gnu.build-id')==h for n,h in notes.items())
assert not Path('/sys/module/samurai_usbin_init').exists()
post={k:int(v) for k,v in (x.split('=') for x in Path('/sys/bus/i2c/devices/0-005c/telemetry').read_text().split())}
assert post['valid']==post['online']==post['protection_ok']==1 and 0<=post['age_ms']<=3000
assert all(post[k]==0 for k in ['shadow','fault','error','stop_error','latched','source_inhibit','thermal_inhibit','cycle_timeout','gauge_charge_stop'])
assert not post['flags']&0xc000
assert all((Path('/sys/bus/platform/devices')/n/'power/runtime_status').read_text().strip()==v for n,v in pm.items())
assert json.loads(Path('/sys/bus/platform/devices/ac10000.icp/m2m_status').read_text())==m2m
for service in services:
 proc=Path('/proc')/str(service['pid'])
 assert (proc/'comm').read_text().strip()==service['comm']
 assert int(re.search(r'^Uid:\s+(\d+)',(proc/'status').read_text(),re.M)[1])==service['uid']
post_limits={'source_budget_ua':value('samurai-usb-input','current_max'),'native_ua':value('samurai-usb-input','input_current_limit'),'input_ua':value('mp2650-input','input_current_limit'),'charge_ua':value('mp2650-input','constant_charge_current'),'cv_pack_uv':value('mp2650-input','constant_charge_voltage')}
assert post_limits==limits
print(json.dumps({'passed':True,'manifest_sha256':expected,'notes':notes,'limits':limits,'post_sample':post,'camera_pm':pm,'m2m':m2m,'services':services,'header':dict(zip(['magic','version','size','head','tail','drops','drop_events','pad'],fields)),'header_stable':True,'reserved_cover':[x[0] for x in cover],'physical_start':start,'mapped_bytes':total,'explicit_memory_bytes_read':total+64,'hardware_writes':0,'taint':0}))
'''


def local_code():
    base_path = REF/'preflight-usbin-init.py'
    assert hashlib.sha256(base_path.read_bytes()).hexdigest() == BASE_SHA
    spec = importlib.util.spec_from_file_location('ram_preflight_source', base_path)
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    marker = "p=Path('/sys/kernel/debug/regmap/0-02')"
    assert base.CODE.count(marker) == 1
    code = base.CODE.split(marker)[0] + READ_CODE
    tree = ast.parse(code)
    forbidden = {'write_text','write_bytes','pack_into','write','writelines','system','Popen'}
    assert not any(isinstance(n,ast.Attribute) and n.attr in forbidden for n in ast.walk(tree))
    assert 'O_RDWR' not in code and 'PROT_WRITE' not in code
    compile(code,'<read-only-reserved-eud-ram>','exec')
    sources = {p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in SOURCE_PATHS}
    header=(REPO/SOURCE_PATHS[0]).read_text()
    assert '#define EUD_LOG_BASE     0x9FFE3000U' in header
    assert '#define EUD_LOG_SIZE     0x00014000U' in header
    assert 'UINT32           Data[1];' in header
    mapping=(REPO/SOURCE_PATHS[2]).read_text()
    assert '{"EUD Log",             0x9FFE3000, 0x00014000, AddMem, SYS_MEM, SYS_MEM_CAP, Reserv, WRITE_BACK_XN}' in mapping
    return code,sources


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--window-confirmed',action='store_true')
    args=parser.parse_args()
    code,sources=local_code()
    digest=hashlib.sha256(code.encode()).hexdigest()
    if not args.execute:
        print(json.dumps({'local_checks_passed':True,'device_accessed':False,'device_source_sha256':digest,'source_hashes':sources}))
        return 0
    assert args.window_confirmed
    spec=importlib.util.spec_from_file_location('ram_window',REF/'device-window.py')
    window=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(window)
    out=PRIVATE/('eud-ram-read-'+str(time.time_ns()))
    out.mkdir(mode=0o700)
    (out/'executed-device-source.py').write_text(code)
    response=window.host.ssh('python3 -',input=code.encode(),timeout=35,check=False)
    (out/'stdout-private.json').write_bytes(response.stdout)
    (out/'stderr-private.txt').write_bytes(response.stderr)
    (out/'host-result-private.json').write_text(json.dumps({'exit_code':response.returncode,'device_source_sha256':digest,'source_hashes':sources})+'\n')
    if response.returncode:
        print(json.dumps({'passed':False,'exit_code':response.returncode,'private_evidence_directory':str(out)}))
        print(response.stderr.decode(errors='replace')[-1500:])
        return response.returncode
    capture_line,result_line=response.stdout.splitlines()
    capture=json.loads(capture_line)
    assert capture['phase']=='private_raw'
    result=json.loads(result_line)
    raw=base64.b64decode(capture['raw_b64'],validate=True)
    assert len(raw)==0x14000
    (out/'eud-ring-private.bin').write_bytes(raw)
    result.update(device_source_sha256=digest,source_hashes=sources,raw_sha256=hashlib.sha256(raw).hexdigest())
    # Retained ring history includes drained bytes; Tail is not a deletion marker.
    head=result['header']['head']
    size=result['header']['size']
    count=min(head,size)
    oldest=head-count
    data=raw[32:]
    history=bytes(data[(oldest+i)%size] for i in range(count))
    (out/'retained-history-private.bin').write_bytes(history)
    result['history_assumption']='No 32-bit Head wrap proven; count=min(Head,Size) is a bounded decode only.'
    result['eud_off_receipts']=[line.decode('ascii') for line in history.splitlines() if re.fullmatch(rb'\[SAMURAI-EUD-OFF\] attempted=[01] write=[01] arm=[0-9a-fA-F]{8} before=[0-9a-fA-F]{8} after=[0-9a-fA-F]{8} status=[A-Za-z0-9 _-]{1,64}',line)]
    result['R2_deployed']=False
    result['receipt_absence_is_not_callback_failure']=True
    (out/'decoded-result-private.json').write_text(json.dumps(result,indent=2)+'\n')
    public={k:result[k] for k in ['passed','manifest_sha256','header','header_stable','physical_start','mapped_bytes','explicit_memory_bytes_read','hardware_writes','taint','device_source_sha256','source_hashes','raw_sha256','history_assumption','eud_off_receipts','R2_deployed','receipt_absence_is_not_callback_failure']}
    public['R8_protection_limits_camera_and_services_checks_passed']=True
    (REF/'eud-ram-r8-result.json').write_text(json.dumps(public,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['passed','header','header_stable','raw_sha256','eud_off_receipts','hardware_writes','taint']},indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
