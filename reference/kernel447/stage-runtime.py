from pathlib import Path
import json,hashlib,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
gst=(HERE.parent/'kernel444/gst-capture-body.py').read_text().replace('for isolated in [False,True]:','for isolated in [True]:')
mode=sys.argv[2] if len(sys.argv)>2 else 'observe';assert mode in ['observe','big-cpu-control']
sys.argv=sys.argv[:2]
if mode=='big-cpu-control':
 marker="plugin=Path(next(iter(plugins)));plugin_sha=hashlib.sha256(plugin.read_bytes()).hexdigest();break"
 assert gst.count(marker)==1
 gst=gst.replace(marker,"""plugin=Path(next(iter(plugins)));plugin_sha=hashlib.sha256(plugin.read_bytes()).hexdigest()
      tids={int(t) for t in re.findall(r'\\[\\d+:\\d+:\\d+\\.\\d+\\] \\[(\\d+)\\] DEBUG CamssVfe .* FOCUS_EXECUTION epoch=1',text)}
      assert len(tids)==1;focus_tid=next(iter(tids));assert focus_tid!=actual_pid
      capacities={i:int(Path('/sys/devices/system/cpu/cpu%d/cpu_capacity'%i).read_text()) for i in range(8)}
      allowed=os.sched_getaffinity(focus_tid);big={i for i in allowed if capacities[i]>min(capacities.values())}
      assert big=={4,5,6,7} and allowed==set(range(8))
      os.sched_setaffinity(focus_tid,big);assert os.sched_getaffinity(focus_tid)==big
      with (case/'affinity-private.log').open('x') as output:json.dump(dict(tid=focus_tid,application_pid=actual_pid,before=sorted(allowed),during=sorted(big),capacities=capacities,only_camera_manager_thread=True),output)
      break""")
 gst=gst.replace("summary['actual_sensor']=[4608,2592]", "summary['actual_sensor']=[4608,2592]\n   assert not Path('/proc',str(focus_tid)).exists()\n   summary['thread_affinity_experiment']=dict(only_camera_manager_thread=True,mask=[4,5,6,7],applied_after_first_gst_image=True,target_thread_gone_after_exit=True)")
end=" state['candidate_final_status']=status();state['candidate_final_core']=core();verified=True\n"
assert gst.count(end)==1;gst=gst.replace(end,'')
prefix=""" observer_log=(root/'cpu-observations.log').open('xb')
 observer=subprocess.Popen(['python3',str(root/'cpu-observer.py')],stdin=subprocess.DEVNULL,stdout=observer_log,stderr=subprocess.STDOUT,start_new_session=True)
 try:
"""
suffix=""" finally:
  observer.terminate()
  try:observer.wait(timeout=3)
  except subprocess.TimeoutExpired:observer.kill();observer.wait(timeout=3)
  observer_log.close()
 assert observer.returncode==0
"""
(HERE/'capture-body.py').write_text(prefix+''.join(' '+line if line.strip() else line for line in gst.splitlines(True))+suffix+end)
source=(HERE.parent/'kernel441/stage-runtime.py').read_text().replace("'stage':441","'stage':447").replace('stage=441','stage=447').replace('k441-variable-pd10-','k447-focus-execution-')
source=source.replace("(HERE/(name+'-validation.json'))", "((HERE if name in ['preflight','runtime-inputs','reentry'] else HERE.parent/('kernel443' if name=='client-build' else 'kernel442'))/(name+'-validation.json'))")
source=source.replace("HERE/'intree-build-validation.json'", "HERE.parent/'kernel441/intree-build-validation.json'").replace("userspace['private_ipa_version']==5", "userspace['private_ipa_version']==6").replace("HERE/'auto-capture-body.py'", "HERE/'capture-body.py'")
source=source.replace("P.parent/'kernel440/factory-s5kgw1-private.yaml'", "P.parent/'kernel443/factory-s5kgw1-private.yaml'")
source=source.replace("for n in ['capture','pd10-ipe']:files[n]=P/n", "files['gst-hardware-probe']=P.parent/'kernel443/gst-hardware-probe';files['cpu-observer.py']=HERE/'cpu-observer.py'")
source=source.replace("HERE/'client-build-validation.json'", "HERE.parent/'kernel443/client-build-validation.json'")
source=source.replace("['capture','pd10-ipe','pipeline-fixture','proxy/camss_ipa_proxy']", "['gst-hardware-probe','pipeline-fixture','proxy/camss_ipa_proxy']")
exec(compile(source,str(HERE/'stage-runtime.py'),'exec'))
attempt=__import__('sys').argv[1] if len(__import__('sys').argv)>1 else 'r1';p=HERE/f'runtime-staging-{attempt}-validation.json';r=json.loads(p.read_text())
r.update(core_sha256=inputs['lib/libcamera.so.0.7.2']['sha256'],profile_sha256=hashlib.sha256((P.parent/'kernel443/factory-s5kgw1-private.yaml').read_bytes()).hexdigest(),private_ipa_version=6,diagnostic_only=True,read_only_cpu_policy_observer=True,experiment_mode=mode)
p.write_text(json.dumps(r,indent=2)+'\n')
