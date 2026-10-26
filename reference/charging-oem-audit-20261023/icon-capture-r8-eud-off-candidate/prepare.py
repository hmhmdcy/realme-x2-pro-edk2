"""Local-only migration. No imported launch/main and no transport calls."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OLD=REF/'charging-ui-audit-20261023/icon-capture-r7-candidate'
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
TX=PRIVATE/'eud-boot-activation/eud-boot-r2-live-001'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['worker.py','audit.py','baseline-test-result.json']:
 (HERE/name).write_bytes((OLD/name).read_bytes())
pins={}
for name,path in dict(adoption=PRIVATE/'boot-adoption-private.json',adopt_request=TX/'adopt-request-private.json',
 adopt_result=TX/'adopt-stdout-private.json',endpoint=TX/'new-endpoint-private.json',
 postboot=TX/'postboot-r3-01-private/stdout-private.json',receiver=TX/'postboot-r3-01-private/receiver-result-private.json',
 transport=REF/'charging-management-20261023/eud-postboot-transport.py',key_transport=REF/'kernel184/host.py').items():
 pins[name]=dict(path=str(path),sha256=sha(path))
(HERE/'identity-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
s=(OLD/'launcher.py').read_text()
s=s.replace('R7 host launch/status/fetch','R8 EUD-off host launch/status/fetch')
s=s.replace('icon-capture-r7','icon-capture-r8-eud-off')
s=s.replace("MANIFEST = '5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68'", "MANIFEST = '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'")
s=s.replace("'baseline-test-result.json': '4aeb77e82f845a4f79c6cac44e3779ba3ed86561da2dd0f615e4ff2195b1be0f'}", "'baseline-test-result.json': '4aeb77e82f845a4f79c6cac44e3779ba3ed86561da2dd0f615e4ff2195b1be0f',\n          'capture-entry.py': '"+sha(HERE/'capture-entry.py')+"'}")
a=s.index('def reviewed_identity(');b=s.index('\ndef adopt_local(',a)
identity='''def reviewed_identity(pins=PINS):
    entries = json.loads(pins.read_bytes()); evidence = {}
    expected = {'adoption','adopt_request','adopt_result','endpoint','postboot','receiver','transport','key_transport'}
    if set(entries) != expected: raise ValueError('EUD-off reviewed pin set differs')
    for name, entry in entries.items():
        raw = Path(entry['path']).read_bytes()
        if sha(raw) != entry['sha256']: raise ValueError('EUD-off identity/transport bytes differ: '+name)
        if name not in ['transport','key_transport']: evidence[name] = json.loads(raw)
    a, r, result, e, post, receiver = [evidence[n] for n in
        ['adoption','adopt_request','adopt_result','endpoint','postboot','receiver']]
    raw = post['raw']; checks = post['result']['checks']
    if not (a.get('original_key_verified') is True and a.get('baseline481_verified') is True
            and a.get('charging_manifest_sha256') == r.get('manifest') == MANIFEST
            and a.get('candidate_boot_sha256') == raw['boot_partition']['sha256'] == '4126a2978bc79b5cb95b6e1b86bb432a6b16ece627776237c163b93b323bbfcf'
            and a.get('postboot_raw_sha256') == r.get('postboot_raw_sha256') == entries['postboot']['sha256']
            and result.get('guard_created') is True and result.get('old_guards_preserved') is True
            and receiver.get('passed') is True and receiver.get('transport_exit') == 0
            and post.get('schema') == 'samurai-eud-postboot-readonly-v1' and post['result']['passed'] is True
            and checks['R8_install']['R8_disk_and_live_notes'] is True
            and checks['camera481']['camera481_files_packages_notes'] is True
            and checks['EUD_producers']['DT_disabled_no_EUD_cmdline_or_active_producer'] is True):
        raise ValueError('adopted R8/481/EUD-off baseline not proved')
    boot, guard = r['boot'], r['guard']; path = PurePosixPath(guard)
    if str(uuid.UUID(boot)) != boot: raise ValueError('invalid adopted boot')
    if guard != a.get('guard_path') or guard != '/var/lib/samurai/eud-boot-r2-live-001-adopted/boot-id-private.txt' or '..' in path.parts:
        raise ValueError('actual adopted EUD-off guard differs')
    if not (raw['identity_before'] == raw['identity_after'] and raw['identity_after']['boot_id'] == boot
            and e.get('kind') == 'usb-ipv6' and e.get('original_key_verified') is True and e.get('postboot_R3_passed') is True
            and e.get('host_key_alias') == '169.254.42.1' and e.get('interface_index') == 29
            and e.get('peer') == 'fe80::62:bcff:fe28:a101%29' and e.get('observed_new_boot') == boot and e.get('guard_path') == guard):
        raise ValueError('strict original-key EUD-off endpoint/boot differs')
    return boot, guard, entries


def runtime_expected(pins=PINS):
    _, _, entries = reviewed_identity(pins)
    r = json.loads(Path(entries['adopt_request']['path']).read_bytes())
    return {k:r[k] for k in ['release','version','rootfs','notes']}

'''
s=s[:a]+identity+s[b:]
s=s.replace('charging-icon-r7-migration-tests-v1','charging-icon-r8-eud-off-migration-tests-v1')
s=s.replace("'worker.py','audit.py','baseline-test-result.json'", "'worker.py','audit.py','baseline-test-result.json','capture-entry.py'")
s=s.replace("str(bundle/'worker.py')", "str(bundle/'capture-entry.py')")
s=s.replace("remote_bundle + '/worker.py'", "remote_bundle + '/capture-entry.py'")
s=s.replace('max_seconds=180','max_seconds=300').replace('default=180','default=300')
s=s.replace('deadline_remaining) - roundtrip < 45:', 'deadline_remaining) - roundtrip < 130:').replace('less than 45 seconds remain', 'less than 130 seconds remain')
s=s.replace("if not 50 <= max_seconds <= 600: raise ValueError('invalid bounded deadline')", "if max_seconds != 300: raise ValueError('this reviewed capture has a fixed 300-second deadline')")
s=s.replace('candidate_revision="r7-ipv6-180-v1"', 'candidate_revision="r8-eud-off-300-v1", identity_expected=runtime_expected(pins)')
s=s.replace("request.get('identity_pins_sha256') != sha(pins.read_bytes()):", "request.get('identity_pins_sha256') != sha(pins.read_bytes()) or request.get('identity_expected') != runtime_expected(pins):")
old=" assert sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())==data['manifest_sha256']\n return True"
new='\n'.join([" assert sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())==data['manifest_sha256']", " e=data['identity_expected'];assert os.uname().release==e['release'] and os.uname().version==e['version']", " assert sha(Path('/etc/samurai-rootfs-release').read_bytes())==e['rootfs']", " for name,digest in e['notes'].items():", "  assert sha(Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes())==digest", "  assert Path('/sys/module',name,'initstate').read_text().strip()=='live'", " return True"])
assert old in s;s=s.replace(old,new)
s=s.replace(" identity()\n if data['action']=='launch':", " identity()\n assert data['max_seconds']==300\n if data['action']=='launch':")
# Fetch must recover this worker's originals even after a captured live-note/rootfs
# failure. Same boot/guard remain mandatory, and launch/status stay strict.
s=s.replace("def identity():\n boot=", "def boot_identity():\n boot=")
s=s.replace(" assert boot==data['expected_boot']==guard.read_text().strip()\n assert sha(", " assert boot==data['expected_boot']==guard.read_text().strip()\n return True\ndef identity():\n boot_identity()\n assert sha(")
s=s.replace("def save(path,value):", "identity_errors=[]\ndef checked_identity():\n boot_identity()\n if data['action']!='fetch':return identity()\n try:return identity()\n except Exception:\n  identity_errors.append(traceback.format_exc());return False\ndef save(path,value):")
s=s.replace("try:\n identity()\n assert data['max_seconds']==300", "try:\n identity_before=checked_identity()\n assert data['max_seconds']==300")
s=s.replace(" response['identity_unchanged']=identity();print(json.dumps(response),flush=True)", " identity_after=checked_identity()\n response['identity_unchanged']=identity_before and identity_after\n response['identity_errors']=identity_errors;print(json.dumps(response),flush=True)")
s=s.replace("parser.add_argument('action', choices=['launch', 'status', 'fetch'])", "parser.add_argument('action', nargs='?', default='check-local', choices=['check-local','launch','status','fetch'])")
s=s.replace("parser.add_argument('--transaction', required=True)", "parser.add_argument('--transaction')")
s=s.replace("    print(json.dumps(run(args.action", "    if args.action == 'check-local':\n        adopt_local(); print(json.dumps({'local_inputs_verified':True,'device_accessed':False,'deadline_seconds':300})); return\n    if not args.transaction: raise ValueError('fresh transaction required')\n    print(json.dumps(run(args.action")
(HERE/'launcher.py').write_bytes(s.encode())
assert '/icon-capture-r7' not in s and 'max_seconds=180' not in s
compile(s,'new-launcher','exec')
print(json.dumps(dict(prepared=True,worker_unchanged=sha(HERE/'worker.py')==sha(OLD/'worker.py'),audit_unchanged=sha(HERE/'audit.py')==sha(OLD/'audit.py'))))
