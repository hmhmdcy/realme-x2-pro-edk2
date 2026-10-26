"""Derive the original one-shot logdump operator; never execute USB actions."""
from pathlib import Path
import ast,hashlib,json,sys
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OLD=REF/'charging-oem-audit-20261023/image502-logdump-activation-candidate'
HOST=HERE.parent/'irq-native-usb-pm-stage-host-candidate'
RUNTIME=HERE.parent/'icon-capture-irq-reattach-runtime-candidate'
STAGE=REF/'charging-oem-audit-20261023/irq-native-usb-pm-stage-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def functions(path):
 text=path.read_text();return text,{n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
def replace_function(text,name,new):
 old=functions_from(text)[name];assert text.count(old)==1;return text.replace(old,new)
def functions_from(text):return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
def write(name,value):
 assert not (HERE/name).exists(),name
 (HERE/name).write_text(value,encoding='utf-8',newline='\n')
def main():
 assert sys.argv[1:]==['--prepare'],'explicit offline preparation only'
 old,oldfunctions=functions(OLD/'fastboot-operator.py')
 assert sha((OLD/'fastboot-operator.py').read_bytes())=='7f473d8698e2e2f83ff768db98de167998a6d7b53e948421b8019fec141d2121'
 text=old.replace('image502-notify-materialized-001','irq-native-usb-pm-materialized-002')
 for before,after in [('samurai-image502-notify','samurai-irq-native-usb-pm'),
                      ("r'image502-notify-live-001'","r'irq-native-usb-pm-activate-[a-z0-9-]{8,48}'"),
                      ("guard['kernel_version'].startswith('#501 ')","guard['source_kernel_version']=='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'")]:
  assert before in text;text=text.replace(before,after)
 text=text.replace('One-shot logdump-only Image502 fastboot operator','One-shot current IRQ Image504 logdump-only fastboot operator')
 fn=functions_from(text)['validate_context'];assert fn.count('    return context')==1
 fn=fn.replace('    return context','''    import importlib.util
    spec=importlib.util.spec_from_file_location('current_irq_stage_review',HERE/'stage-proof.py')
    proof=importlib.util.module_from_spec(spec);spec.loader.exec_module(proof)
    stage=proof.review_stage(context['stage_directory'],context['stage_fetch_directory'])
    require(proof.guard_stage_fields(stage)==guard['stage'],'original completed stage differs')
    require(context['source_review_inputs']==stage['source_review_inputs'] and guard['adoption']==stage['request']['adoption'],
            'original IRQ adoption plus completed runtime update differs')
    identity=stage['request']['identity']
    require((guard['boot_id'],guard['soc_serial_sha256'],guard['compatible_sha256'],guard['rootfs_release_sha256'])==
            (identity['boot_id'],identity['serial_sha256'],identity['compatible_sha256'],identity['rootfs_sha256']),
            'actual stage source identity differs')
    return context''')
 text=replace_function(text,'validate_context',fn)
 unchanged=[name for name,body in oldfunctions.items() if functions_from(text).get(name)==body]
 assert all(n in unchanged for n in ['command','once','run_action','reboot_binding','prior_terminal','claim_action','pinned_tools'])
 compile(text,'fastboot-operator.py','exec');write('fastboot-operator.py',text)
 runtime,rfn=functions(RUNTIME/'update-review.py')
 proof='''"""Review one original current-stage fetch. No transport or device operation."""
from pathlib import Path
import ast,base64,copy,hashlib,importlib.util,json,os,re,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
SOURCE_MANIFEST='18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
'''
 for name in ['need','local','load']:proof+=rfn[name]+'\n\n'
 proof+='''def source_check():
    pins=json.loads((HERE/'stage-source-pins.json').read_bytes());values={}
    for name,row in pins.items():
        data=local(row['path']).read_bytes()
        need(sha(data)==row['sha256'],'fixed source changed: '+name);values[name]=data
    for delivery_name,source_name,filename in [('stage_host_delivery','stage_host','host.py'),
        ('stage_worker_delivery','stage_worker','stage-worker.py')]:
        delivery=json.loads(values[delivery_name])
        need(delivery['passed'] and delivery['frozen'] and delivery['files'][filename]['sha256']==pins[source_name]['sha256'],'frozen stage source mismatch')
    return pins,values

'''
 proof+=rfn['fetch_raw']+'\n\n'+rfn['process_chain']+'\n\n'+(HERE/'stage-proof-body.py.inc').read_text()
 proof+='''
if __name__=='__main__':
    source_check();print(json.dumps({'source_only':True,'device_accessed':False,'stage_or_runtime_identity_created':False}))
'''
 compile(proof,'stage-proof.py','exec');write('stage-proof.py',proof)
 rows={}
 for name,path in [('stage_host',HOST/'host.py'),('stage_host_delivery',HOST/'delivery.json'),
  ('stage_remote',HOST/'remote.py'),('stage_supervisor',HOST/'supervisor.py'),
  ('stage_worker',STAGE/'stage-worker.py'),('stage_worker_delivery',STAGE/'delivery.json'),
  ('reused_fetch_review',RUNTIME/'update-review.py'),('common',HERE/'common.py')]:
  rows[name]={'path':str(path.resolve()),'sha256':sha(path.read_bytes())}
 write('stage-source-pins.json',json.dumps(rows,indent=2)+'\n')
 write('operator-source-reuse.json',json.dumps({'passed':True,'original_operator_sha256':sha((OLD/'fastboot-operator.py').read_bytes()),
  'unchanged_operator_functions':unchanged,'original_fetch_process_chain_functions_exact':['fetch_raw','process_chain'],
  'original_fetch_review_sha256':sha((RUNTIME/'update-review.py').read_bytes()),'device_accessed':False},indent=2)+'\n')
 print(json.dumps({'prepared':True,'unchanged_operator_functions':len(unchanged),'USB_accessed':False}))
if __name__=='__main__':main()
