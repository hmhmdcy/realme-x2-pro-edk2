"""Source/current-probe authentication and local request binding. No transport owner."""
from pathlib import Path
import argparse,base64,copy,hashlib,importlib.util,json,os,re,secrets,sys
sys.dont_write_bytecode=True
if sys.flags.optimize:raise RuntimeError('non-optimized Python required')
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('current_rollback_shared_bind',HERE/'shared.py')
shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
need=shared.need;local=shared.local;load=shared.load;encode=shared.encode;sha=shared.sha;source_check=shared.source_check
PEER='fe80::62:bcff:fe28:a101%29'
PAYLOAD='6ff66d182f7b0dc7ac32e3e58ae756e259c246b4edddf85d48878ff561835ab8'
def review_sources(profile,stage_directory,stage_fetch_directory,context_path=None):
 source_check();saved=load(HERE/'saved-proof.py','current_cold_saved_action_sources')
 return saved.review_profile_sources(profile,stage_directory,stage_fetch_directory,context_path)
def probe_request(reviewed,endpoint):
 need(endpoint==PEER,'original observed strict-key peer only')
 binding={key:reviewed[key] for key in ['profile','source_identity','source_stage','source_stage_observations','activation']}
 return dict(schema='samurai-irq-native-usb-pm-rollback-current-probe-v1',new_endpoint=endpoint,profile=reviewed['profile'],
  saved_source_binding_sha256=sha(encode(binding)))
def probe_payload(profile,stage_directory,stage_fetch_directory,context_path=None,*,endpoint=PEER):
 reviewed=review_sources(profile,stage_directory,stage_fetch_directory,context_path)
 return ('PROBE_REQUEST='+repr(probe_request(reviewed,endpoint))+'\n').encode()+(HERE/'current-probe.py').read_bytes()
def auth_module():
 pins=source_check();auth=load(pins['auth_host']['path'],'original_R2_current_probe_receipt_auth')
 original=auth.transport_argv
 def compressed(endpoint,*,collection=False):
  need(collection is False,'current probe does not invoke postboot collection actions')
  argv=original(endpoint,collection=False);need(argv[1:3]==['-6','-T'],'original strict-key argv shape')
  return [argv[0],'-C',*argv[1:]]
 auth.transport_argv=compressed
 return auth
def transport_argv(endpoint=PEER):
 need(endpoint==PEER,'no endpoint/key fallback');return auth_module().transport_argv(endpoint)
def review_current(profile,stage_directory,stage_fetch_directory,probe_directory,context_path=None):
 reviewed=review_sources(profile,stage_directory,stage_fetch_directory,context_path)
 request=probe_request(reviewed,PEER);payload=('PROBE_REQUEST='+repr(request)+'\n').encode()+(HERE/'current-probe.py').read_bytes()
 auth=auth_module();stdout,stderr,terminal=auth.saved_transport(local(probe_directory),payload,PEER)
 need(terminal['returncode']==0 and terminal.get('primary_error') is None and not terminal.get('cleanup_errors'),
  'actual original-key current probe must have clean wait0')
 report=json.loads(stdout);need(report['schema']==request['schema'] and report['request']==request,'exact current source-bound request')
 current=report['current'];identity=current['identity']
 need(report['identity_before']==identity==report['identity_after'] and
  report['cache_before']==current['current_cache']==report['cache_after'],'actual identity and same cache double bracket')
 need(type(report['started_boottime_ns']) is type(report['ended_boottime_ns']) is int and
  0<report['started_boottime_ns']<=report['ended_boottime_ns'],'actual current probe clock bracket')
 pins=source_check();worker=load(pins['worker']['path'],'actual_current_cold_profile_gate')
 projected=dict(profile=profile,identity=identity,source_identity=reviewed['source_identity'],activation=reviewed['activation'],
  current_cache=current['current_cache'])
 worker.validate_cache(current['current_cache']);worker.validate_profile(projected,current)
 directory=local(probe_directory)
 return dict(saved=reviewed,current=current,identity=identity,new_endpoint=PEER,
  proof=dict(stdin_sha256=sha(payload),stdout_sha256=sha(stdout),child_sha256=sha((directory/'child-private.json').read_bytes()),
   terminal_sha256=sha((directory/'terminal-private.json').read_bytes())),
  whole_postboot_pass_required=False,current_freshness_or_stopping_authorized=False)
def make_request(transaction_id,profile,stage_directory,stage_fetch_directory,probe_directory,context_path=None):
 need(re.fullmatch(r'irq-native-usb-pm-rollback-[a-z0-9-]{8,48}',transaction_id),'new explicit rollback transaction')
 reviewed=review_current(profile,stage_directory,stage_fetch_directory,probe_directory,context_path)
 pins=source_check();payload=local(pins['payload']['path']).read_bytes();saved=reviewed['saved']
 request=dict(schema='samurai-irq-native-usb-pm-cold-rollback-request-v1',transaction_id=transaction_id,profile=profile,
  identity=reviewed['identity'],source_identity=saved['source_identity'],source_stage=saved['source_stage'],
  source_stage_observations=saved['source_stage_observations'],activation=saved['activation'],current_cache=reviewed['current']['current_cache'],
  payload_sha256=PAYLOAD,payload_base64=base64.b64encode(payload).decode(),worker_sha256=pins['worker']['sha256'],lease_token=secrets.token_hex(24))
 worker=load(pins['worker']['path'],'actual_current_cold_request_gate');worker.unpack(request)
 return request,reviewed
def bind(out,transaction_id,profile,stage_directory,stage_fetch_directory,probe_directory,context_path=None):
 request,reviewed=make_request(transaction_id,profile,stage_directory,stage_fetch_directory,probe_directory,context_path)
 out=local(out);need(out.is_absolute() and not out.exists(),'new private output only')
 pins=source_check();worker=local(pins['worker']['path']).read_bytes();mask=os.umask(0o077)
 try:
  out.mkdir(mode=0o700)
  for name,raw in [('request-private.json',encode(request)),('restore-worker.py',worker),('current-binding-private.json',encode(reviewed))]:
   with (out/name).open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
  if os.name!='nt':
   fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY)
   try:os.fsync(fd)
   finally:os.close(fd)
 finally:os.umask(mask)
 return dict(request_sha256=sha(encode(request)),worker_sha256=sha(worker),identity=request['identity'],profile=profile,
  runtime_request_materialized=True,lease_written=False,worker_launched=False,device_or_transport_accessed=False)
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-local',action='store_true');parser.parse_args()
 source_check();print(json.dumps({'source_only':True,'runtime_request_created':False,'device_accessed':False,'connected_owner_implemented':False}))
