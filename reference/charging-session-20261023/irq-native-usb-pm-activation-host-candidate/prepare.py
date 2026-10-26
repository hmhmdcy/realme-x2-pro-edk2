"""Derive the current stage controller from the original owned R2 host."""
from pathlib import Path
import ast,hashlib,json,sys
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OLD=HERE.parent/'usb-irq-protection-activation-host-candidate'
DEVICE=HERE.parent/'irq-native-usb-pm-activation-device-candidate'
sha=lambda b:hashlib.sha256(b).hexdigest()
def definitions(text):return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
def substitute(text,name,new):
 old=definitions(text)[name];assert text.count(old)==1;return text.replace(old,new)
def write(name,text):
 assert not (HERE/name).exists(),name
 (HERE/name).write_text(text,encoding='utf-8',newline='\n')
def main():
 assert sys.argv[1:]==['--prepare'],'explicit local generation only'
 baseline=(OLD/'controller.py').read_text()
 assert sha((OLD/'controller.py').read_bytes())=='98fb6dfd750cd1d273b4d59e4157b64c4481830265f1f95103ffd77c3edffdb8'
 assert sha((DEVICE/'delivery.json').read_bytes())=='69419fee308847a9978b830c396f1919bf227497c60befe3f62b63841e17f7b7'
 oldpins=json.loads((OLD/'source-pins.json').read_bytes());pins={name:oldpins[name] for name in ['key_transport','camera_wrapper']}
 for name,path in [('device_delivery',DEVICE/'delivery.json'),('device_contract',DEVICE/'prepare-contract.json'),
  ('device_common',DEVICE/'common.py'),('quiesce',DEVICE/'eud-quiesce.py'),('restart',DEVICE/'eud-restart.py'),
  ('stage_proof',DEVICE/'stage-proof.py'),('baseline_controller',OLD/'controller.py'),('baseline_remote',OLD/'remote.py'),
  ('baseline_supervisor',OLD/'supervisor.py'),('baseline_delivery',OLD/'delivery.json'),
  ('materialization_result',DEVICE/'materialization-result.json')]:
  raw=path.read_bytes();pins[name]={'path':str(path.resolve()),'sha256':sha(raw),'bytes':len(raw)}
 value=json.loads((DEVICE/'materialization-result.json').read_bytes())
 material=Path(value['private_directory'])/'materialization.json'
 if sys.platform!='win32':material=Path('/mnt/e/'+str(material).replace('\\','/')[3:])
 assert sha(material.read_bytes())==value['materialization_sha256']=='91c85dbe1e5f249c41d6961d17066bed646ab4f3a751f0c2b2b77a2e87620a94'
 pins['materialization']={'path':str(material.resolve()),'sha256':sha(material.read_bytes()),'bytes':material.stat().st_size}
 current=baseline.replace("WORKERS = REF / 'charging-session-20261023/usb-irq-protection-restart-candidate'","WORKERS = REF / 'charging-session-20261023/irq-native-usb-pm-activation-device-candidate'")
 current=current.replace("STAGE = REF / 'charging-oem-audit-20261023/irq-cohort-postboot-host-candidate'","STAGE = WORKERS")
 current=current.replace('usb-irq-protection-activate-','irq-native-usb-pm-activate-')
 current=current.replace('usb-irq-protection-activation','irq-native-usb-pm-activation')
 current=current.replace('samurai-usb-irq-protection','samurai-irq-native-usb-pm')
 current=current.replace('generated_from_actual_Image502','generated_from_actual_runtime_update')
 for old,new in [('43c5bd1952949504e918c660b208ca6bb45cfa103be9c9be575268b64ef9036e',pins['quiesce']['sha256']),
                 ('56a58c08bd3f79813d95955279f3ad07f7338d522239d32a7cfec4ea8d3b05be',pins['restart']['sha256'])]:current=current.replace(old,new)
 current=substitute(current,'source_check','''def source_check():
    pins=load_json(HERE/'source-pins.json')
    for name,item in pins.items():
        raw=local(item['path']).read_bytes()
        need(sha(raw)==item['sha256'] and len(raw)==item['bytes'],'frozen source changed: '+name)
    need(pins['device_delivery']['sha256']=='69419fee308847a9978b830c396f1919bf227497c60befe3f62b63841e17f7b7','current device delivery')
    need(pins['key_transport']['sha256']=='7f49a922e0babf167c77ad6e9bd7edf63e437418d5134e3d081fb8a0082a4f4c','original strict key')
    delivery=load_json(local(pins['device_delivery']['path']))
    need(delivery['passed'] is True and delivery['frozen'] is True,'frozen current device tools')
    for name,row in delivery['files'].items():
        raw=(WORKERS/name).read_bytes();need(sha(raw)==row['sha256'] and len(raw)==row['bytes'],'device source changed: '+name)
    material=load_json(local(pins['materialization']['path']));result=load_json(local(pins['materialization_result']['path']))
    need(material['passed'] is True and result['passed'] is True and
         result['materialization_sha256']==pins['materialization']['sha256'],'completed materialization002 required')
    for name,digest in material['source_files'].items():need(sha((WORKERS/name).read_bytes())==digest,'materialized source differs: '+name)
    directory=local(pins['materialization']['path']).parent
    for name,digest in material['files'].items():need(sha((directory/name).read_bytes())==digest,'materialized file changed: '+name)
    need(material['worker_hashes']==WORKER_HASHES,'actual materialized worker tuple')
    for name,digest in WORKER_HASHES.items():need(sha((WORKERS/name).read_bytes())==digest,'exact worker: '+name)
    for name in ['controller.py','remote.py','supervisor.py']:ast.parse((HERE/name).read_bytes())
    return pins''')
 current=substitute(current,'make_guard','''def make_guard(tx, token, review, projection):
    need(re.fullmatch(TX_PATTERN,tx) and re.fullmatch('[0-9a-f]{48}',token),'new activation identity')
    fixed=load_json(WORKERS/'prepare-contract.json')['fixed_guard_fields']
    need(review['schema']=='samurai-irq-native-usb-pm-stage-review-v1' and review['stage']==projection,'current completed stage review')
    request=review['request'];identity=request['identity']
    need(identity['version']==fixed['source_kernel_version'] and request['cohort_delivery_sha256']==fixed['cohort_delivery_sha256'] and
         review['source_runtime']['manifest_sha256']==fixed['source_manifest_sha256'],'actual current502/runtime18e8 required')
    need(review['source_runtime']['boot_id']==identity['boot_id'] and
         review['source_runtime']['guard_path']==request['adoption']['guard_path'] and
         review['source_runtime']['guard_sha256']==request['adoption']['guard_sha256'],'same actual source identity')
    need(set(request['adoption'])=={'transaction_id','guard_path','guard_sha256'},'original IRQ adopted guard')
    return dict(fixed,transaction_id=tx,token=token,boot_id=identity['boot_id'],
        soc_serial_sha256=identity['serial_sha256'],compatible_sha256=identity['compatible_sha256'],
        rootfs_release_sha256=identity['rootfs_sha256'],adoption=dict(request['adoption']),stage=projection)''')
 current=substitute(current,'endpoint_from_stage','''def endpoint_from_stage(stage_directory, review):
    raw=(local(stage_directory)/'binding-private.json').read_bytes();binding=json.loads(raw)
    need(sha(raw)==review['stage']['host_binding_sha256'],'authenticated original stage binding')
    endpoint=binding['endpoint'];identity=review['request']['identity'];adoption=review['request']['adoption']
    need(endpoint==review['source_runtime']['endpoint'] and endpoint['kind']=='usb-ipv6' and
        endpoint['peer']=='fe80::62:bcff:fe28:a101%29' and endpoint['interface_index']==29 and
        endpoint['host_key_alias']=='169.254.42.1' and endpoint['original_key_verified'] is True and
        endpoint['observed_new_boot']==identity['boot_id'] and endpoint['guard_path']==adoption['guard_path'],
        'actual original-key runtime endpoint')
    return endpoint''')
 current=current.replace("return [key.SSH, '-6', '-T'","return [key.SSH, '-C', '-6', '-T'")
 export=definitions(current)['export_context']
 export=export.replace("stage_fetch_directory=binding['stage_fetch_directory'])", "stage_fetch_directory=binding['stage_fetch_directory'],\n        source_review_inputs=binding['stage_review']['source_review_inputs'])")
 assert 'source_review_inputs=' in export;current=substitute(current,'export_context',export)
 compile(current,'controller.py','exec');write('controller.py',current)
 original_remote=(OLD/'remote.py').read_text()
 remote=original_remote.replace('usb-irq-protection-activate-','irq-native-usb-pm-activate-').replace('samurai-usb-irq-protection-activation-owner','samurai-irq-native-usb-pm-activation-owner')
 remote=substitute(remote,'preflight','''def preflight(request, root, allow_inhibit=False):
    raw=(root/'common.py').read_bytes();need(sha(raw)==request['common_sha256'],'exact current device common')
    ns={};exec(compile(raw,'pinned-current-stage-guard','exec'),ns)
    primary=None
    try:
        meta,output,phase=ns['validate_activation_guard'](root/'guard-private.json',allow_inhibit=allow_inhibit)
        need(meta['transaction_id']==request['transaction_id'] and meta['token']==request['token'] and
             meta['boot_id']==request['expected_boot'],'fresh current activation identity')
        return meta,output,phase
    except BaseException as error:
        primary=error;raise
    finally:
        errors=[]
        for name in ['_MAC_FD','_SERVICE_FD']:
            fd=ns.get(name)
            if fd is not None:
                try:ns['os'].close(fd)
                except BaseException as error:errors.append((name,repr(error)))
                finally:ns[name]=None
        if errors:
            if primary is not None:primary.add_note('owned preflight descriptor close errors: '+repr(errors))
            else:raise RuntimeError('owned preflight descriptor close errors: '+repr(errors))''')
 compile(remote,'remote.py','exec');write('remote.py',remote);write('supervisor.py',(OLD/'supervisor.py').read_text())
 write('source-pins.json',json.dumps(pins,indent=2)+'\n')
 before=definitions(baseline);after=definitions(current)
 unchanged=[name for name,body in before.items() if after.get(name)==body]
 oldremote=definitions(original_remote);newremote=definitions(remote)
 r_unchanged=[name for name,body in oldremote.items() if newremote.get(name)==body]
 assert all(name in unchanged for name in ['ssh_worker','terminal_job','start_job','reconcile','run','bound'])
 write('source-reuse.json',json.dumps(dict(passed=True,unchanged_controller_functions=unchanged,
  unchanged_remote_functions=r_unchanged,supervisor_byte_exact=True,
  old_controller_sha256=sha((OLD/'controller.py').read_bytes()),old_remote_sha256=sha((OLD/'remote.py').read_bytes()),
  new_remote_scope='only current namespace/transaction and closing both owned preflight descriptors',
  actual_runtime_binding_or_device_action=False),indent=2)+'\n')
 print(json.dumps({'prepared':True,'unchanged_controller_functions':len(unchanged),'unchanged_remote_functions':len(r_unchanged),'device_accessed':False}))
if __name__=='__main__':main()
