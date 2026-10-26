"""Pure saved-proof/current-probe reviewer and request binder. No transport owner."""
from pathlib import Path
import argparse,base64,hashlib,importlib.util,json,os,re,secrets,sys
if sys.flags.optimize:raise RuntimeError('nonoptimized Python required')
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROLLBACK=HERE.parent/'usb-irq-protection-rollback-candidate'
AUTH=HERE.parent/'irq-cohort-postboot-host-candidate'
PRIVATE=Path('E:/edk2-samurai-out/charging-management-20261023/usb-irq-protection-cohort-private-01')
PEER='fe80::62:bcff:fe28:a101%29'
PAYLOAD='5ecae1f5799a1c01d132553b1ad4fb5923d643d1e13fcde8007f5380253fa339'
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def need(value,message):
    if not value:raise ValueError(message)


def local(path):
    text=str(path).replace('\\','/')
    return Path('/mnt/e/'+text[3:] if os.name!='nt' and text.startswith('E:/') else text)


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def encode(value):return (json.dumps(value,indent=2)+'\n').encode()


def source_check():
    pins=json.loads((HERE/'source-pins.json').read_bytes())
    need(set(pins)=={'rollback_delivery','worker','saved_proof','auth_delivery','auth_host','payload'},'source pin set')
    for name,item in pins.items():need(sha(local(item['path']).read_bytes())==item['sha256'],'frozen source changed: '+name)
    need(pins['rollback_delivery']['sha256']=='8ac464757630d72fc5ce3da377501651e84bf8c7f74fc5fbffd4156914eddfad'
         and pins['worker']['sha256']=='f0767ce2506f500b5893ddfdf28f7aa7d7a4d0930ccde092970170f1b7fa4142'
         and pins['saved_proof']['sha256']=='3c16d34bbf6d1454d1a3dc09bc03815f3be9dceafd23c8720bb3ff32cc810092','exact rollback code')
    need(pins['auth_delivery']['sha256']=='8a4301cb9850dcab65069f6ec0e2ca47b8be72b1fcbb2676357863518f640d2a'
         and pins['auth_host']['sha256']=='58d0cbf0dd4ec2db29725bdfd2b01467cbe04c4401b1ca411960438e66dca6e7','exact original-key R2 receipt reviewer')
    need(pins['payload']['sha256']==PAYLOAD and local(pins['payload']['path']).stat().st_size==44194,'exact original R8 archive')
    for name in ('rollback_delivery','auth_delivery'):
        path=local(pins[name]['path']);delivery=json.loads(path.read_bytes())
        need(delivery['passed'] is delivery['frozen'] is True,'frozen source delivery')
        for relative,entry in delivery['files'].items():need(sha((path.parent/relative).read_bytes())==entry['sha256'],'delivery file changed: '+relative)
    auth=load(local(pins['auth_host']['path']),'rollback_original_key_auth');auth.source_check()
    return pins


def review_sources(profile,stage_directory,stage_fetch_directory,context_path=None):
    pins=source_check();saved=load(local(pins['saved_proof']['path']),'rollback_actual_saved_profile')
    return saved.review_profile_sources(profile,stage_directory,stage_fetch_directory,context_path)


def probe_request(reviewed,endpoint):
    need(endpoint==PEER,'only actual observed original-key peer is supported')
    binding={key:reviewed[key] for key in ('profile','source_identity','source_stage','activation')}
    return dict(schema='samurai-irq-rollback-current-probe-v1',new_endpoint=endpoint,
                profile=reviewed['profile'],saved_source_binding_sha256=sha(encode(binding)))


def probe_payload(profile,stage_directory,stage_fetch_directory,context_path=None,*,endpoint=PEER):
    reviewed=review_sources(profile,stage_directory,stage_fetch_directory,context_path)
    return ('PROBE_REQUEST='+repr(probe_request(reviewed,endpoint))+'\n').encode()+(HERE/'current-probe.py').read_bytes()


def transport_argv(endpoint=PEER):
    need(endpoint==PEER,'no endpoint fallback')
    pins=source_check();auth=load(local(pins['auth_host']['path']),'rollback_original_key_argv')
    return auth.transport_argv(endpoint)


def review_current(profile,stage_directory,stage_fetch_directory,probe_directory,context_path=None):
    reviewed=review_sources(profile,stage_directory,stage_fetch_directory,context_path)
    request=probe_request(reviewed,PEER)
    payload=('PROBE_REQUEST='+repr(request)+'\n').encode()+(HERE/'current-probe.py').read_bytes()
    pins=source_check();auth=load(local(pins['auth_host']['path']),'rollback_actual_original_key_transport')
    stdout,_,terminal=auth.saved_transport(probe_directory,payload,PEER)
    need(terminal['returncode']==0 and terminal.get('primary_error') is None and not terminal.get('cleanup_errors'),
         'original current probe child not clean terminal0')
    report=json.loads(stdout)
    need(report['schema']==request['schema'] and report['request']==request,'actual current probe source binding')
    current=report['current'];identity=current['identity']
    need(report['identity_before']==identity==report['identity_after'],'actual current double identity bracket')
    need(type(report['started_boottime_ns']) is type(report['ended_boottime_ns']) is int
         and 0<report['started_boottime_ns']<=report['ended_boottime_ns'],'current probe time bracket')
    worker=load(local(pins['worker']['path']),'rollback_actual_current_profile')
    projected=dict(profile=profile,identity=identity,source_identity=reviewed['source_identity'],activation=reviewed['activation'])
    worker.validate_profile(projected,current)
    return dict(saved=reviewed,current=current,identity=identity,new_endpoint=PEER,
        proof=dict(stdin_sha256=sha(payload),stdout_sha256=sha(stdout),
                   child_sha256=sha((Path(probe_directory)/'child-private.json').read_bytes()),
                   terminal_sha256=sha((Path(probe_directory)/'terminal-private.json').read_bytes())),
        whole_postboot_pass_required=False,current_freshness_or_stopping_authorized=False)


def make_request(transaction_id,profile,stage_directory,stage_fetch_directory,probe_directory,context_path=None):
    need(re.fullmatch(r'usb-irq-protection-rollback-[a-z0-9-]{8,48}',transaction_id),'new unique rollback name')
    reviewed=review_current(profile,stage_directory,stage_fetch_directory,probe_directory,context_path)
    pins=source_check();payload=local(pins['payload']['path']).read_bytes()
    source=reviewed['saved']
    request=dict(schema='samurai-usb-irq-protection-rollback-request-v1',transaction_id=transaction_id,profile=profile,
        identity=reviewed['identity'],source_identity=source['source_identity'],source_stage=source['source_stage'],activation=source['activation'],
        payload_sha256=PAYLOAD,payload_base64=base64.b64encode(payload).decode(),worker_sha256=pins['worker']['sha256'],lease_token=secrets.token_hex(24))
    worker=load(local(pins['worker']['path']),'rollback_actual_request_validator');worker.unpack(request)
    return request,reviewed


def bind(out,transaction_id,profile,stage_directory,stage_fetch_directory,probe_directory,context_path=None):
    request,reviewed=make_request(transaction_id,profile,stage_directory,stage_fetch_directory,probe_directory,context_path)
    # No output directory exists until original source/action/current evidence
    # and exact archive/request validation have all succeeded.
    out=Path(out);need(out.is_absolute() and not out.exists(),'new private output directory')
    pins=source_check();worker=local(pins['worker']['path']).read_bytes()
    mask=os.umask(0o077)
    try:
        out.mkdir(mode=0o700)
        for name,raw in [('request-private.json',encode(request)),('restore-worker.py',worker),('current-binding-private.json',encode(reviewed))]:
            with (out/name).open('xb') as file:file.write(raw);file.flush();os.fsync(file.fileno())
    finally:os.umask(mask)
    return dict(request_sha256=sha(encode(request)),worker_sha256=sha(worker),identity=request['identity'],
        profile=profile,runtime_request_materialized=True,lease_written=False,worker_launched=False,device_or_transport_accessed=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-local',action='store_true');parser.parse_args()
    source_check();print(json.dumps(dict(source_only=True,actual_source_or_current_identity_reviewed=False,
        runtime_request_or_guard_or_lease_generated=False,device_or_transport_accessed=False,connected_owner_implemented=False)))


if __name__=='__main__':main()
