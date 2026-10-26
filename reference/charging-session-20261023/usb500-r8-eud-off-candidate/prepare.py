"""Offline R8/EUD-off profile migration; never invokes USB/SSH/SDK."""
from pathlib import Path
import ast,difflib,hashlib,json
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
OLD=REF/'charging-oem-audit-20261023/usb500-r7-candidate'
PRIVATE=Path('E:/edk2-samurai-out/charging-management-20261023') if __import__('os').name=='nt' else Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
REL='eud-boot-activation/eud-boot-r2-live-001/postboot-r3-01-private/stdout-private.json'
ENDPOINT='eud-boot-activation/eud-boot-r2-live-001/new-endpoint-private.json'
MANIFEST='320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
GUARD='/var/lib/samurai/eud-boot-r2-live-001-adopted/boot-id-private.txt'
TRANSPORT_SHA='f493a73a3eaf17cac4a56ac68b2cdffc90f52d6783eaae4beed5bb6307fd3336'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
old_receipt=json.loads((OLD/'orchestration-test-result.json').read_bytes())
for n,digest in old_receipt['tested_files'].items():assert sha((OLD/n).read_bytes())==digest
for n,digest in old_receipt['device_files'].items():assert sha((OLD/'device-candidate'/n).read_bytes())==digest
assert sha((REF/'charging-management-20261023/eud-postboot-transport.py').read_bytes())==TRANSPORT_SHA
baseline=(PRIVATE/REL).read_bytes();b=json.loads(baseline);raw=b['raw'];adoption=json.loads((PRIVATE/'boot-adoption-private.json').read_bytes())
assert b['result']['passed'] and raw['manifest']['sha256']==MANIFEST
assert adoption['baseline481_verified'] and adoption['guard_path']==GUARD and adoption['postboot_raw_sha256']==sha(baseline)
assert raw['config_max_power_ma']=='100'
MODULES={n:{'sha256':r['sha256'],'note_sha256':r['loaded_note_sha256']} for n,r in raw['charging_modules'].items()}
diffs=[]
def write(name,text,old=None):
 p=HERE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='\n')
 if old is not None:diffs.extend(difflib.unified_diff(old.splitlines(True),text.splitlines(True),'r7/'+name,'r8-eud-off/'+name))
def once(text,old,new):
 assert text.count(old)==1,old[:100]
 return text.replace(old,new)
base=(OLD/'device-candidate/r7-base.py').read_text()
v=base.replace("GUARD = '/var/lib/samurai/charging-r7-8162b1e7040030d514a83534-adopted/boot-id-private.txt'",'GUARD = '+repr(GUARD))
v=once(v,"NEW = '5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68'",'NEW = '+repr(MANIFEST))
v=once(v,"KO: 'fac827cfd3d1d847cb1db82f0a29e451652bd16a996b20666be2d9b330889cb6'","KO: "+repr(MODULES['samurai-mp2650']['sha256']))
write('device-candidate/r8-base.py',v,base)
(HERE/'device-candidate/health.py').write_bytes((OLD/'device-candidate/health.py').read_bytes())

# Only USB port-bound fields change in the decoder/native GET session.
decoder=(OLD/'UsbHubReadOnly.cs').read_text()
d=decoder.replace('data[6] <= 15','data[6] <= 255').replace('expectedPort <= 15','expectedPort <= 255').replace('port > 15','port > 255')
# data[6] is a byte; avoid a compiler warning for its tautological <=255 test.
d=once(d,'data[6] >= 1 && data[6] <= 255','data[6] >= 1')
write('UsbHubReadOnly.cs',d,decoder)
reader=(OLD/'watch-one-hub.ps1').read_text()
start=reader.index('    # Same observed EUD interface discovery')
end=reader.index('    $diagnosticSession = ',start)
reader=reader[:start]+'''    $diagnosticTopology = Get-Usb500NcmRootHub
    $diagnosticPath = $diagnosticTopology.Interface
'''+reader[end:]
reader=reader.replace('HubInstance=$diagnosticHubs[0].InstanceId;',
 '''HubInstance=$diagnosticTopology.HubInstance; NcmInstance=$diagnosticTopology.NcmInstance
        DirectRootHub=$true;''')
helper=r'''function Get-Usb500NcmRootHub {
    # Sole exact present composite NCM; exclude MI children and old EUD hub.
    $ncm = @(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^USB\\VID_0525&PID_A4A1\\[^\\]+$' })
    if ($ncm.Count -ne 1 -or $ncm[0].InstanceId -notmatch '^USB\\VID_0525&PID_A4A1\\62BC28A1$') {
        throw 'Expected the sole exact original NCM composite identity'
    }
    $parents = @(Get-PnpDeviceProperty -InstanceId $ncm[0].InstanceId -KeyName 'DEVPKEY_Device_Parent')
    if ($parents.Count -ne 1 -or $parents[0].Type -ne 'String' -or
        $parents[0].Data -notmatch '^USB\\ROOT_HUB(?:20|30)?\\[^\\]+$') {
        throw 'NCM must currently be a direct child of a root hub; no EUD/other hub fallback'
    }
    $hubs = @(Get-PnpDevice -PresentOnly -InstanceId $parents[0].Data)
    if ($hubs.Count -ne 1 -or $hubs[0].InstanceId -ne $parents[0].Data) { throw 'Current parent root hub is not unique/present' }
    $text = (& pnputil /enum-devices /instanceid $hubs[0].InstanceId /interfaces | Out-String)
    if ($LASTEXITCODE -ne 0) { throw 'Read-only root-hub interface enumeration failed' }
    $expectedInterface = '\\?\' + $hubs[0].InstanceId.Replace('\','#') + '#{f18a0e88-c30c-11d0-8815-00a0c906bed8}'
    $pattern = [regex]::Escape($expectedInterface)
    $matches = [regex]::Matches($text, $pattern, 'IgnoreCase')
    if ($matches.Count -ne 1) { throw 'Expected one interface of that exact present root hub' }
    return [ordered]@{ NcmInstance=$ncm[0].InstanceId; HubInstance=$hubs[0].InstanceId; Interface=$matches[0].Value }
}

'''
reader=reader.replace('try {\n    $diagnosticTopology',helper+'try {\n    $diagnosticTopology',1)
write('watch-one-hub.ps1',reader,(OLD/'watch-one-hub.ps1').read_text())
DECODER=sha((HERE/'UsbHubReadOnly.cs').read_bytes());COLLECTOR=sha((HERE/'watch-one-hub.ps1').read_bytes())
worker=(OLD/'device-candidate/worker.py').read_text()
w=worker.replace('usb500-r7-','usb500-r8-eud-off-').replace('usb500_r7_base','usb500_r8_eud_off_base').replace('r7-base.py','r8-base.py')
w=w.replace("BASE_SHA = 'cef5c0f585e4f77db77c93652a7d30c0edf1903e7586f21e7fb89a62a3129902'",'BASE_SHA = '+repr(sha((HERE/'device-candidate/r8-base.py').read_bytes()))).replace('<= 15','<= 255')
w=w.replace('9fe2ffb2792bf5feb7113167056bec4466fced9dc1b591bffbcbe8373b5e7716',DECODER).replace('31c0f8e99f8ba4878b489f9b8dda34e5a688bb1e6b44415ce40a88c17fcfb6f5',COLLECTOR)
w=once(w,"isinstance(ready['capture_id'], str) and ready['capture_id'].endswith(nonce)","ready['capture_id'] == 'usb500-r8-eud-off-' + nonce")
w=w.replace('one volatile r7 USB500 diagnostic','one volatile R8/EUD-off USB500 diagnostic').replace('only actual r7 transaction','only actual R8/EUD-off transaction').replace('actual installed r7 manifest','actual installed R8 manifest')
write('device-candidate/worker.py',w,worker)
parent=(OLD/'host-parent.ps1').read_text()
p=parent.replace('usb500-r7-','usb500-r8-eud-off-').replace('$meta.PortCount -gt 15','$meta.PortCount -gt 255')
p=p.replace('9fe2ffb2792bf5feb7113167056bec4466fced9dc1b591bffbcbe8373b5e7716',DECODER).replace('31c0f8e99f8ba4878b489f9b8dda34e5a688bb1e6b44415ce40a88c17fcfb6f5',COLLECTOR)
p=once(p,"$ready.Armed -ne $true -or $ready.DurationSeconds -ne 140)","$ready.Armed -ne $true -or $ready.DurationSeconds -ne 140 -or $meta.DirectRootHub -ne $true -or\n        $meta.NcmInstance -notmatch '^USB\\\\VID_0525&PID_A4A1\\\\62BC28A1$' -or\n        $meta.HubInstance -notmatch '^USB\\\\ROOT_HUB(?:20|30)?\\\\[^\\\\]+$')")
write('host-parent.ps1',p,parent)
launch=(OLD/'host-launcher.py').read_text()
h=launch.replace('usb500-r7-','usb500-r8-eud-off-').replace('r7-base.py','r8-base.py').replace('usb500-r7-migration-v1','usb500-r8-eud-off-migration-v1').replace('<= 15','<= 255')
h=h.replace('5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68',MANIFEST).replace('/var/lib/samurai/charging-r7-8162b1e7040030d514a83534-adopted/boot-id-private.txt',GUARD)
h=h.replace('23f2281d0b89fcc8eba0c7b7372d6774e7f16ca6e5bd5a612da64fd94aadef1a',TRANSPORT_SHA)
h=h.replace('9fe2ffb2792bf5feb7113167056bec4466fced9dc1b591bffbcbe8373b5e7716',DECODER).replace('31c0f8e99f8ba4878b489f9b8dda34e5a688bb1e6b44415ce40a88c17fcfb6f5',COLLECTOR)
h=h.replace('charging-management-20261023/r7-transport.py','charging-management-20261023/eud-postboot-transport.py').replace('usb500_r7_ipv6','usb500_r8_eud_off_ipv6')
h=h.replace("b'/root/charging-management-20261023/usb500-r8-eud-off-diagnostic-v1-'", "b'/root/charging-management-20261023/usb500-r7-diagnostic-v1-',b'/root/charging-management-20261023/usb500-r8-eud-off-diagnostic-v1-'")
start=h.index('def load_baseline(private):');end=h.index('\n\ndef transport():',start)
loader='''def load_baseline(private):
    content=(private/BASELINE_REL).read_bytes()
    if sha(content)!=BASELINE_SHA:raise ValueError('exact adopted R3 baseline bytes required')
    before=json.loads(content); raw=before['raw']; result=before['result']
    adoption=json.loads((private/'boot-adoption-private.json').read_bytes())
    endpoint=json.loads((private/ENDPOINT_REL).read_bytes())
    manifest=json.loads(raw['manifest_text'])
    if not (before['schema']=='samurai-eud-postboot-readonly-v1' and result['passed'] is True
            and result['read_only'] is True and result['hardware_writes']==0
            and raw['manifest']['sha256']==MANIFEST
            and result['checks']['R8_install']['R8_disk_and_live_notes'] is True
            and result['checks']['camera481']['camera481_files_packages_notes'] is True
            and result['checks']['EUD_producers']['DT_disabled_no_EUD_cmdline_or_active_producer'] is True
            and result['checks']['EUD_ring_receipt']['ready'] is True
            and result['checks']['charging']['ready'] is True
            and result['checks']['charging']['source_type']=='SDP'
            and all(result['checks']['charging'][k]==100000 for k in ['budget_ua','native_ua','input_ua'])
            and raw['config_max_power_ma']=='100'
            and raw['source']['usb_type']=='Unknown [SDP] DCP CDP C'
            and raw['source']['online']=='1'
            and raw['source']['current_max']==raw['source']['input_current_limit']=='100000'):
        raise ValueError('complete adopted R8/EUD-off SDP100 baseline required; not a fresh device gate')
    if set(raw['charging_modules'])!=set(MODULES):raise ValueError('exact R8 module set')
    for name,pin in MODULES.items():
        module=raw['charging_modules'][name]
        if not (module['sha256']==pin['sha256']==manifest['modules'][name]['sha256']
                and module['loaded_note_sha256']==module['disk_note_sha256']==pin['note_sha256']
                and module['loaded_note_matches_disk'] is True and raw['charging_module_live'][name]=='live'):
            raise ValueError('actual R8 disk/live module identity differs: '+name)
    boot=raw['identity_after']['boot_id']
    if not (raw['identity_before']==raw['identity_after']
            and adoption['original_key_verified'] is True and adoption['baseline481_verified'] is True
            and adoption['charging_manifest_sha256']==MANIFEST and adoption['guard_path']==GUARD
            and adoption['candidate_boot_sha256']==raw['boot_partition']['sha256']==CANDIDATE_BOOT
            and adoption['postboot_raw_sha256']==BASELINE_SHA
            and endpoint['kind']=='usb-ipv6' and endpoint['original_key_verified'] is True
            and endpoint['postboot_R3_passed'] is True and endpoint['guard_path']==GUARD
            and endpoint['peer']=='fe80::62:bcff:fe28:a101%29' and endpoint['interface_index']==29
            and endpoint['host_key_alias']=='169.254.42.1' and endpoint['observed_new_boot']==boot):
        raise ValueError('new R8/EUD-off adoption/481/IPv6/boot guard disagree')
    before['state']={'boot_id':boot}
    return before
'''
h=h[:start]+loader+h[end:]
idx=h.index('REVIEWED = ');end=h.index('\nsha = ',idx)
reviewed={n:sha((HERE/'device-candidate'/n).read_bytes()) for n in ['worker.py','r8-base.py','health.py']}
reviewed['test-result.json']=sha((HERE/'device-candidate/test-result.json').read_bytes()) if (HERE/'device-candidate/test-result.json').exists() else 'PENDING_DIRECTED_R8_TEST'
h=h[:idx]+('BASELINE_REL = '+repr(REL)+'\nBASELINE_SHA = '+repr(sha(baseline))+'\nENDPOINT_REL = '+repr(ENDPOINT)+'\nCANDIDATE_BOOT = '+repr(adoption['candidate_boot_sha256'])+'\nMODULES = '+repr(MODULES)+'\nREVIEWED = '+repr(reviewed))+h[end:]
# Default is local syntax/hash/baseline check, never import/call transport.
idx=h.index("if __name__=='__main__':")
h=h[:idx]+'''def check_local():
    load_baseline(PRIVATE)
    source=HERE.parents[1]/'charging-management-20261023/eud-postboot-transport.py'
    if sha(source.read_bytes())!=TRANSPORT_SHA:raise ValueError('new exact transport required')
    compile(source.read_bytes(),str(source),'exec')
    compile(REMOTE_LAUNCH,'remote-launch','exec');compile(REMOTE_FETCH,'remote-fetch','exec')
    for name,digest in REVIEWED.items():
        if sha((HERE/'device-candidate'/name).read_bytes())!=digest:raise ValueError('unqualified candidate bytes')
    return {'checked_local_only':True,'profile':'R8/EUD-off','device_accessed':False,'usb_accessed':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',nargs='?',default='check-local',choices=['check-local','launch','fetch'])
    p.add_argument('--nonce');p.add_argument('--host-ready-file');p.add_argument('--window-confirmed',action='store_true')
    a=p.parse_args()
    print(json.dumps(check_local() if a.action=='check-local' else run(a.action,a.nonce,a.host_ready_file,a.window_confirmed),indent=2))
'''
write('host-launcher.py',h,launch)
for n in ['device-candidate/worker.py','device-candidate/r8-base.py','host-launcher.py']:ast.parse((HERE/n).read_text())
(HERE/'migration.patch').write_text(''.join(diffs),encoding='utf-8',newline='\n')
result={'profile':'R8/EUD-off; offline only','base_receipt_sha256':sha((OLD/'orchestration-test-result.json').read_bytes()),
 'baseline_sha256':sha(baseline),'manifest':MANIFEST,'guard':GUARD,'transport_sha256':TRANSPORT_SHA,'modules':MODULES,
 'device_files':reviewed,'host_source_hashes':{n:sha((HERE/n).read_bytes()) for n in ['host-parent.ps1','host-launcher.py','watch-one-hub.ps1','UsbHubReadOnly.cs']},
 'old_suites_rerun':False,'device_access':False,'usb_access':False,'sdk':False}
(HERE/'generation-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'generated':True,'profile':'R8/EUD-off','host_pins_final':reviewed['test-result.json']!='PENDING_DIRECTED_R8_TEST','device_access':False}))
