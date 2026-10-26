"""Two read-only CSR observations in an explicitly owned device window."""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import json
import time

REF = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
BASE_SHA = 'a1dffafa5d24448c90015ed19ebab142e2e07b04cc7d1a8e893463742f0a3369'
OLD_READER_SHA = '5671f3062919d4ce2a7106ec45b40426875a34d7677d2d4b0c8ed1025d99a835'

EUD_CODE = r'''
import mmap,struct,sys
dev=Path('/sys/bus/platform/devices/88e0000.serial')
driver=Path('/sys/bus/platform/drivers/qcom_eud_com')
def eud_context():
 assert (dev/'driver').resolve(strict=True)==driver
 assert (dev/'of_node/compatible').read_bytes()==b'qcom,sm8150-eud-com\0'
 assert (dev/'of_node/reg').read_bytes()==struct.pack('>IIII',0,0x088e0000,0,0x2000)
 assert 'console=eud' in Path('/proc/cmdline').read_text().split()
 assert os.sysconf('SC_PAGE_SIZE')==4096
 return (dev/'power/runtime_status').read_text().strip()
def stats():
 raw=(dev/'rx_stats').read_text()
 fields=dict(x.split('=') for x in raw.split())
 assert int(fields['f1'])==0 and int(fields['queued'])==0
 return raw,int(fields['polls'])
runtime_before=eud_context()
stats_before,polls_before=stats()
time.sleep(.2)
stats_live,polls_live=stats()
assert polls_live>polls_before, 'No fresh existing EUD MMIO poll evidence'
csr=[]
fd=os.open('/dev/mem',os.O_RDONLY|os.O_SYNC|os.O_CLOEXEC)
try:
 with mmap.mmap(fd,4096,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ,offset=0x088e1000) as view:
  for index in range(2):
   eud_context()
   before=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
   csr_word=struct.unpack_from('<I',view,0x14)[0]
   after=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
   csr.append({'value':csr_word,'hex':'0x%08x'%csr_word,'boottime_before_ns':before,'boottime_after_ns':after})
   print(json.dumps({'phase':'csr_read','sample':csr[-1]}),file=sys.stderr,flush=True)
   if index==0:time.sleep(.2)
finally:
 os.close(fd)
print(json.dumps({'phase':'csr_read','csr':csr}),file=sys.stderr,flush=True)
runtime_after=eud_context()
stats_after,polls_after=stats()
assert polls_after>polls_live
assert runtime_before==runtime_after
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert sha('/usr/share/samurai-charging/manifest.json')==expected
assert all(sha('/sys/module/'+n+'/notes/.note.gnu.build-id')==h for n,h in notes.items())
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
print(json.dumps({'passed':True,'manifest_sha256':expected,'notes':notes,'limits':limits,'samples':samples,'post_sample':post,'camera_pm':pm,'m2m':m2m,'services':services,'eud_driver':'qcom_eud_com','eud_runtime_status_before':runtime_before,'eud_runtime_status_after':runtime_after,'eud_rx_stats_before':stats_before,'eud_rx_stats_live':stats_live,'eud_rx_stats_after':stats_after,'csr_address':'0x088e1014','csr_width_bits':32,'csr':csr,'csr_equal':csr[0]['value']==csr[1]['value'],'csr_accepted_by_frozen_boot_candidate':all(x['value'] in [0,1] for x in csr),'helper_absent':True,'explicit_mmio_bytes_read':8,'hardware_writes':0,'taint':0}))
'''


def local_code():
    base_path = REF/'preflight-usbin-init.py'
    assert hashlib.sha256(base_path.read_bytes()).hexdigest() == BASE_SHA
    old = REF.parent/'kernel367/restart-bootloader.py'
    assert hashlib.sha256(old.read_bytes()).hexdigest() == OLD_READER_SHA
    spec = importlib.util.spec_from_file_location('csr_preflight_source', base_path)
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    marker = "p=Path('/sys/kernel/debug/regmap/0-02')"
    assert base.CODE.count(marker) == 1
    code = base.CODE.split(marker)[0] + EUD_CODE
    compile(code, '<read-only-eud-csr>', 'exec')
    tree = ast.parse(code)
    forbidden = {'write_text', 'write_bytes', 'pack_into', 'write', 'writelines', 'system', 'Popen'}
    assert not any(isinstance(n, ast.Attribute) and n.attr in forbidden for n in ast.walk(tree))
    assert 'O_RDWR' not in code and 'PROT_WRITE' not in code
    assert code.count("fd=os.open('/dev/mem',os.O_RDONLY|os.O_SYNC|os.O_CLOEXEC)") == 1
    assert code.count('struct.unpack_from(\'<I\',view,0x14)') == 1
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--window-confirmed', action='store_true')
    args = parser.parse_args()
    code = local_code()
    digest = hashlib.sha256(code.encode()).hexdigest()
    if not args.execute:
        print(json.dumps({'local_checks_passed': True, 'device_accessed': False,
                          'device_source_sha256': digest}))
        return 0
    assert args.window_confirmed
    spec = importlib.util.spec_from_file_location('eud_csr_window', REF/'device-window.py')
    window = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(window)
    out = PRIVATE/('eud-csr-read-'+str(time.time_ns()))
    out.mkdir(mode=0o700)
    (out/'executed-device-source.py').write_text(code)
    response = window.host.ssh('python3 -', input=code.encode(), timeout=35, check=False)
    (out/'stdout-private.json').write_bytes(response.stdout)
    (out/'stderr-private.txt').write_bytes(response.stderr)
    (out/'host-result-private.json').write_text(json.dumps({'exit_code':response.returncode,
        'device_source_sha256':digest,'base_preflight_sha256':BASE_SHA,'old_reader_sha256':OLD_READER_SHA})+'\n')
    if response.returncode:
        print(json.dumps({'passed':False,'exit_code':response.returncode,
                          'private_evidence_directory':str(out)}))
        print(response.stderr.decode(errors='replace')[-1500:])
        return response.returncode
    result = json.loads(response.stdout)
    result.update(device_source_sha256=digest, base_preflight_sha256=BASE_SHA,
                  old_reader_sha256=OLD_READER_SHA)
    (REF/'eud-csr-r8-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['passed','limits','services','csr',
        'csr_equal','csr_accepted_by_frozen_boot_candidate','hardware_writes','taint']},indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
