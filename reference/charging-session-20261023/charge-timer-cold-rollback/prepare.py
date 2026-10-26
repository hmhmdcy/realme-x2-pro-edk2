"""Extract the proven disk-only recovery core; bind current charger pair."""
from pathlib import Path
import ast,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'irq-native-usb-pm-cold-rollback-candidate'
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
FORWARD=HERE.parent/'charge-timer-cold-update'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def main():
    old=(OLD/'restore-worker.py').read_text();tree=ast.parse(old)
    receipt=json.loads((OLD/'delivery.json').read_bytes());assert receipt['passed']
    assert sha((OLD/'restore-worker.py').read_bytes())==receipt['files']['restore-worker.py']['sha256']
    forward_root=BASE/'charge-timer-cold-update-live-20261024-01'
    request_raw=(forward_root/'request-private.json').read_bytes();request=json.loads(request_raw)
    stage=(FORWARD/'stage-worker.py').read_bytes();assert sha(stage)==request['worker_sha256']
    cohort=json.loads((HERE.parent/'charge-timer-hold-r2-candidate/cohort-result.json').read_bytes())
    oldmeta=json.loads((BASE/'charge-timer-hold-cohort-private-02/manifest-old.json').read_bytes())
    newmeta=json.loads((BASE/'charge-timer-hold-cohort-private-02/manifest-new.json').read_bytes())
    wrapper=("import io,sys,runpy\nsys.stdin=io.TextIOWrapper(io.BytesIO("+repr(request_raw)+"))\nsys.argv=['stage','--execute-stage']\nrunpy.run_path("+repr('/root/charging-management-20261023/'+request['transaction_id']+'/stage-worker.py')+",run_name='__main__')\n").encode()
    supervisor=(HERE.parent/'irq-native-usb-pm-postboot-host-candidate/pm-smoke-supervisor.py').read_bytes()
    target=oldmeta['modules']['samurai-mp2650']['target'];manifest='/usr/share/samurai-charging/manifest.json'
    notes={'samurai-usb-input':'028ea63c24b0b46ec6edb03b9c3cbfc999c4b7a119034dc18ac70d1bcbf064e6','samurai-gauge-protection':'bf148be50cb3a4c30bf3ab194f90163fbd47ce5dcbcaf1adb7d84392d242ecdd','samurai-mp2650':'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'}
    constants=dict(OLD_FILES={target:cohort['source_charger_sha256'],manifest:cohort['source_manifest_sha256']},
        NEW_FILES={target:cohort['target_charger_sha256'],manifest:cohort['target_manifest_sha256']},OLD_NOTES=notes,
        NEW_NOTES={**notes,'samurai-mp2650':cohort['target_charger_note_sha256']},NEW_MANIFEST=newmeta,
        RELEASE=oldmeta['release'],VERSION504=request['identity']['version'],BOOT='eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06',
        LOGDUMP504='4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83',ROOT='/root/charging-management-20261023',
        SERVICE='/usr/sbin/samurai-charging',MANAGER=cohort['retained_service_sha256'],LIVE_SHA=oldmeta['installed_files']['/usr/lib/samurai-charging/live-session.py'],
        STARTUP_SHA='2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a',LOCK='/run/lock/samurai-charging.lock',INSTANCE='/sys/devices/platform/samurai-gauge-protection',
        MANIFEST=manifest,TARGET=target,ORDER=[target,manifest],ROLLBACK_PAYLOAD=cohort['rollback']['sha256'],SOURCE_IDENTITY=request['identity'],
        SOURCE_TX=request['transaction_id'],SOURCE_REQUEST_SHA=sha(request_raw),SOURCE_COHORT=request['cohort_delivery_sha256'],FORWARD_PAYLOAD=request['payload_sha256'],
        STAGE_WORKER=sha(stage),STAGE_SUPERVISOR=sha(supervisor),STAGE_WRAPPER=sha(wrapper))
    functions={n.name:ast.get_source_segment(old,n) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    names=['need','sha','detail','encode','read_owned','validate_lease','AtomicFailure','atomic_replace','active','safe_electrical','safe_stopped','idle','legacy_retained']
    source='''"""Default inert. Current charger two-file cold rollback; no module/carrier activation."""
from pathlib import Path,PurePosixPath
from types import SimpleNamespace
import argparse,base64,copy,hashlib,io,json,math,os,re,runpy,stat,struct,sys,tarfile,time,uuid
sys.dont_write_bytecode=True
'''
    source+='\n'.join(key+'='+repr(value) for key,value in constants.items())+'\n\n'
    source+='\n\n'.join(functions[name] for name in names)+'\n\n'
    source+=functions['restore'].replace('samurai-irq-native-usb-pm-cold-rollback-result-v1','samurai-charger-timer-cold-rollback-result-v1')+'\n\n'
    source+=functions['BaseDevice']+'\n\n'
    device=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Device')
    source+='class Device(BaseDevice):\n'
    methods=[]
    for node in device.body:
        if isinstance(node,ast.FunctionDef) and node.name!='source_proof':
            source+=' '+ast.get_source_segment(old,node)+'\n\n';methods.append(node.name)
    source+=(HERE/'current-body.py.inc').read_text()+'\n\n'+functions['main']+"\n\nif __name__=='__main__':raise SystemExit(main())\n"
    compile(source,'current-charger-cold-rollback','exec')
    with (HERE/'restore-worker.py').open('x') as f:f.write(source)
    result=dict(passed=True,original_worker_sha256=sha((OLD/'restore-worker.py').read_bytes()),worker_sha256=sha(source.encode()),
        exact_functions=names,restore_changed_only_result_schema=True,BaseDevice_all_twenty_methods_exact=True,exact_current_Device_methods=methods,
        source_authentication='current completed stage seventeen actual artifacts; no fabricated carrier-flash action',
        write_scope=[target,manifest],payload_sha256=cohort['rollback']['sha256'],phone_accessed=False,request_created=False)
    with (HERE/'derivation.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(prepared=True,exact_functions=len(names),exact_Device_methods=len(methods),phone_accessed=False)))
if __name__=='__main__':main()
