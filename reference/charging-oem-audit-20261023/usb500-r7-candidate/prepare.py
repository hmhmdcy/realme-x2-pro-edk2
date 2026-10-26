"""Offline directed R6->R7 USB500 profile port; no device/transport/SDK access."""
from pathlib import Path
import ast,difflib,hashlib,json
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
OLD=REF/'charging-session-20261023/usb500-diagnostic'
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
MANIFEST='5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68'
adoption=json.loads((PRIVATE/'boot-adoption-private.json').read_text())
assert adoption['original_key_verified'] and adoption['baseline440_verified']
assert adoption['charging_manifest_sha256']==MANIFEST
GUARD=adoption['guard_path']
assert GUARD.startswith('/var/lib/samurai/charging-r7-') and GUARD.endswith('-adopted/boot-id-private.txt')
TRANSPORT_SHA=sha((REF/'charging-management-20261023/r7-transport.py').read_bytes())
pins={
 'device-candidate/worker.py':'b9f7cc4c741ca85608ec769640b920e0783d76e383ad0c36c7c8e3c912e81f21',
 'device-candidate/r6-base.py':'b5cfad278a1d1887e0cb38e47edcb796929b760151e5cb5bb59e775f1e2b2e98',
 'device-candidate/health.py':'a41942f21773c97b22d0b3760b1e256650f8e5506ee6cd0883db7145a39f4b4f',
 'device-candidate/test-result.json':'faf128cf133e0c91127d1d7cef466a402abdc23c93f02d46d1a9bc5910d42348',
 'watch-one-hub.ps1':'31c0f8e99f8ba4878b489f9b8dda34e5a688bb1e6b44415ce40a88c17fcfb6f5',
 'UsbHubReadOnly.cs':'9fe2ffb2792bf5feb7113167056bec4466fced9dc1b591bffbcbe8373b5e7716',
 'host-launcher.py':'911021dd92b756f8d94f11dea5b250d4cb51c620db1fcb9b702d584001fdd4d1',
 'host-parent.ps1':'9e5c39bb80d36e0c300bbbed05461d6aa61334e86d9242f69ed1e4b391c66348'}
for name,digest in pins.items():assert sha((OLD/name).read_bytes())==digest,name
device=HERE/'device-candidate';device.mkdir(exist_ok=True)
diffs=[]
def write(name,text,old=None):
 target=HERE/name;target.parent.mkdir(exist_ok=True)
 target.write_text(text,encoding='utf-8',newline='\n')
 if old is not None:diffs.append(''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='r6/'+name,tofile='r7/'+name)))

# Keep updater methods inert and unchanged; Diagnostic never calls them.
base=(OLD/'device-candidate/r6-base.py').read_text()
ported=base.replace("GUARD = '/var/lib/samurai/k449-adopted/boot-id-private.txt'",'GUARD = '+repr(GUARD))
ported=ported.replace("NEW = '944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d'",'NEW = '+repr(MANIFEST))
target="'native_ua': int((live.PSY / 'samurai-usb-input/input_current_limit').read_text()),"
assert ported.count(target)==1
ported=ported.replace(target,target+"\n                           'source_budget_ua': int((live.PSY / 'samurai-usb-input/current_max').read_text()),",1)
ported=ported.replace("s.get('budget_ua') == lim['native_ua'], 'fresh sample/source budget agreement'", "s.get('budget_ua') == lim['source_budget_ua'], 'fresh sample/effective source budget agreement'")
write('device-candidate/r7-base.py',ported,base)
(device/'health.py').write_bytes((OLD/'device-candidate/health.py').read_bytes())

worker=(OLD/'device-candidate/worker.py').read_text()
w=worker.replace("BASE_SHA = 'b5cfad278a1d1887e0cb38e47edcb796929b760151e5cb5bb59e775f1e2b2e98'",'BASE_SHA = '+repr(sha((device/'r7-base.py').read_bytes())))
w=w.replace("'usb500_r6_base', 'r6-base.py'","'usb500_r7_base', 'r7-base.py'")
w=w.replace('usb500-r6-','usb500-r7-').replace('samurai-usb500-r6-','samurai-usb500-r7-')
w=w.replace('only actual r6 transaction','only actual r7 transaction').replace('actual installed r6 manifest','actual installed r7 manifest')
w=w.replace('one volatile r6 USB500 diagnostic','one volatile r7 USB500 diagnostic')
anchor="    need(source['input_current_limit'] == source['current_max'] == str(ma * 1000), 'native host callback allowance')"
assert w.count(anchor)==1
w=w.replace(anchor,anchor+"\n    need(row['limits']['source_budget_ua'] == int(source['current_max']) == row['sample']['budget_ua'], 'effective source budget and fresh sample agree')",1)
begin=w.index('    def network(self, deadline):')
end=w.index('    def finish(self, result):',begin)
w=w[:begin]+'''    def network(self, deadline):
        # Existing observed Linux usb0 link-local peer. No host IPv4 privilege,
        # static address injection, interface/address fallback or sysctl write.
        need(Path(GADGET, 'functions/ncm.usb0/ifname').read_text().strip() == 'usb0', 'original NCM usb0')
        self.net_command(['ip', 'link', 'set', 'usb0', 'up'], deadline)
        ready_deadline = min(deadline, self.now() + 3)
        while self.now() < ready_deadline:
            links = json.loads(self.net_command(['ip', '-j', '-6', 'addr', 'show', 'dev', 'usb0'], ready_deadline))
            if ipv6_ready(links):
                return
            self.pause(min(.2, max(0, ready_deadline-self.now())))
        raise RuntimeError('observed original IPv6 peer not ready; no address/IPv4 fallback')

'''+w[end:]
before='class Diagnostic(r6.Device):'
assert w.count(before)==1
w=w.replace(before,'''def ipv6_ready(links):
    # The peer is the original-key-verified r7-postboot observation, not a
    # guessed EUI64 or a new address to add. Reject incomplete DAD state.
    for link in links:
        for address in link.get('addr_info', []):
            if (address.get('local') == 'fe80::62:bcff:fe28:a101'
                    and address.get('prefixlen') == 64 and address.get('scope') == 'link'
                    and not any(address.get(k, False) for k in ('tentative', 'dadfailed'))
                    and not set(address.get('flags', [])).intersection(('tentative', 'dadfailed'))):
                return True
    return False


'''+before,1)
write('device-candidate/worker.py',w,worker)

# Host GET collector and decoder are byte-for-byte frozen. Never invoke here.
for name in ['watch-one-hub.ps1','UsbHubReadOnly.cs']:(HERE/name).write_bytes((OLD/name).read_bytes())
parent=(OLD/'host-parent.ps1').read_text()
write('host-parent.ps1',parent.replace('usb500-r6-','usb500-r7-'),parent)

launch=(OLD/'host-launcher.py').read_text()
h=launch.replace('usb500-r6-','usb500-r7-').replace('samurai-usb500-r6-','samurai-usb500-r7-')
h=h.replace('r6-base.py','r7-base.py').replace("MANIFEST = '944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d'",'MANIFEST = '+repr(MANIFEST))
h=h.replace("guard=Path('/var/lib/samurai/k449-adopted/boot-id-private.txt')",'guard=Path('+repr(GUARD)+');assert data[\'guard\']==str(guard)')
start=h.index('REVIEWED = ');end=h.index('sha = ',start)
# Device receipt is emitted by the directed device test, then prepare reruns
# to finalize host pins. The placeholder cannot qualify a launch.
reviewed={n:sha((device/n).read_bytes()) for n in ['worker.py','r7-base.py','health.py']}
reviewed['test-result.json']=sha((device/'test-result.json').read_bytes()) if (device/'test-result.json').exists() else 'PENDING_DIRECTED_R7_TEST'
h=h[:start]+'GUARD = '+repr(GUARD)+'\nTRANSPORT_SHA = '+repr(TRANSPORT_SHA)+'\nREVIEWED = '+repr(reviewed)+'\n'+h[end:]
start=h.index('def transport():');end=h.index('\n\ndef validate_receipt',start)
h=h[:start]+'''def load_baseline(private):
    before=json.loads((private/'r7-handoff/snapshot-private.json').read_bytes())
    adoption=json.loads((private/'boot-adoption-private.json').read_bytes())
    endpoint=json.loads((private/'r7-postboot/usb-ipv6-transport-private.json').read_bytes())
    if not (before['result']['passed'] is True and before['result']['modules_exact'] is True
            and before['result']['manifest_sha256']==MANIFEST
            and before['source_budget_ua']==before['limits']['native_ua']==before['limits']['input_ua']==100000
            and '[SDP]' in before['source_type']):
        raise ValueError('R7 verified SDP100 baseline required; stored baseline is not a fresh device gate')
    if not (adoption['original_key_verified'] is True and adoption['baseline440_verified'] is True
            and adoption['charging_manifest_sha256']==MANIFEST and adoption['guard_path']==GUARD
            and endpoint['kind']=='usb-ipv6' and endpoint['original_key_verified'] is True
            and endpoint['peer']=='fe80::62:bcff:fe28:a101%29' and endpoint['interface_index']==29
            and endpoint['host_key_alias']=='169.254.42.1'
            and endpoint['observed_new_boot']==before['state']['boot_id']):
        raise ValueError('original-key R7 guard/IPv6 endpoint/baseline disagree')
    return before


def transport():
    # Fixed observed IPv6 + original HostKeyAlias. Never the optional IPv4 path.
    load_baseline(PRIVATE)
    source=HERE.parents[1]/'charging-management-20261023/r7-transport.py'
    if sha(source.read_bytes())!=TRANSPORT_SHA:raise ValueError('reviewed original-key IPv6 helper changed')
    spec=importlib.util.spec_from_file_location('usb500_r7_ipv6',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    def same_boot(command,**kwargs):
        module.raw_ssh('cmp -s /proc/sys/kernel/random/boot_id '+shlex.quote(GUARD),timeout=15).check_returncode()
        return module.raw_ssh(command,**kwargs)
    return same_boot
'''+h[end:]
h=h.replace("tested['cases']==51", "tested['schema']=='usb500-r7-migration-v1' and tested['cases']>=8")
h=h.replace("tested['cases'] != 51", "tested.get('schema')!='usb500-r7-migration-v1' or tested['cases']<8")
h=h.replace('different reviewed candidate/51-case receipt','different reviewed R7 migration candidate/receipt')
oldbaseline="        before=json.loads((private/'r6-update/handoff-private.json').read_bytes())\n        if before['manifest_sha256']!=MANIFEST: raise ValueError('expected deployed r6 baseline')"
assert h.count(oldbaseline)==1
h=h.replace(oldbaseline,"        before=load_baseline(private)",1)
h=h.replace("'manifest_sha256':MANIFEST,'token':secrets.token_hex(24)","'manifest_sha256':MANIFEST,'guard':GUARD,'token':secrets.token_hex(24)")
h=h.replace("before['observation']['state']['boot_id']","before['state']['boot_id']")
h=h.replace("or item.get('worker_sha256')!=REVIEWED['worker.py']", "or item.get('guard')!=GUARD or item.get('transaction')!=TX or item.get('worker_sha256')!=REVIEWED['worker.py']")
# Never allow an archived R6 worker to be missed simply because this profile is R7.
h=h.replace("a.startswith(b'/root/charging-management-20261023/usb500-r7-diagnostic-v1-')", "a.startswith((b'/root/charging-management-20261023/usb500-r6-diagnostic-v1-',b'/root/charging-management-20261023/usb500-r7-diagnostic-v1-'))")
write('host-launcher.py',h,launch)
for name in ['device-candidate/worker.py','device-candidate/r7-base.py','device-candidate/health.py','host-launcher.py']:ast.parse((HERE/name).read_text())
(HERE/'migration.patch').write_text(''.join(diffs),encoding='utf-8',newline='\n')
result={'profile':'R7 offline port; not executed','frozen_source_pins':pins,
 'r7_guard':GUARD,'manifest_sha256':MANIFEST,'transport_helper_sha256':TRANSPORT_SHA,
 'device_files':reviewed,'host_source_hashes':{n:sha((HERE/n).read_bytes()) for n in ['host-parent.ps1','host-launcher.py','watch-one-hub.ps1','UsbHubReadOnly.cs']},
 'full_frozen_suites_rerun':False,'device_access':False,'sdk_access':False}
(HERE/'generation-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'prepared':True,'host_pins_final':reviewed['test-result.json']!='PENDING_DIRECTED_R7_TEST','device_access':False},indent=2))
