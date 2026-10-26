"""Exercise the real role selector on retained hardware graphs and counterexamples."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,re
HERE=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out')
spec=importlib.util.spec_from_file_location('full_role463',HERE/'full-role.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
probe=(private/'kernel457/trace-capabilities-private.json').read_bytes()
graphs=[private/'kernel314/media-before.txt',private/'kernel417/media-inspection-private.log']
results=[]
for path in graphs:
 role=h.discover(probe,path.read_bytes(),'msm_vfe0_pix')
 assert role['full_video_node']=='video3' and role['minor']==3
 results.append(dict(cached_graph_sha256=h.sha(path.read_bytes()),full_node='video3',minor=3))
graph=graphs[-1].read_bytes();role=h.discover(probe,graph,'msm_vfe0_pix')
old=json.loads((private/'kernel459/selection-private.json').read_text())
good=dict(old,full_video_node=role['full_video_node'],full_minor=role['minor'])
h.check_selection(role,good)
rejected=[]
def reject(name,call):
 try:call()
 except (ValueError,KeyError):rejected.append(name)
 else:raise AssertionError('Accepted invalid role: '+name)
reject('actual_r2_RDI0_selection',lambda:h.check_selection(role,old))
reject('explicit_RDI_entity',lambda:h.discover(probe,graph,'msm_vfe0_rdi0'))
reject('wrong_platform',lambda:h.discover(probe,graph.replace(b'platform:acb3000.camss',b'platform:wrong.camss'),'msm_vfe0_pix'))
reject('duplicate_camss_graph',lambda:h.discover(probe,graph+graphs[0].read_bytes(),'msm_vfe0_pix'))
reject('missing_full_backlink',lambda:h.discover(probe,graph.replace(b'<- "msm_vfe0_pix":1 [ENABLED,IMMUTABLE]',b'<- "msm_vfe0_pix":2 [ENABLED,IMMUTABLE]'),'msm_vfe0_pix'))
reject('mutable_full_link',lambda:h.discover(probe,graph.replace(b'-> "msm_vfe0_video3":0 [ENABLED,IMMUTABLE]',b'-> "msm_vfe0_video3":0 [ENABLED]'),'msm_vfe0_pix'))
bad=json.loads(probe);bad['video_nodes']['video3']['name']='wrong'
reject('inventory_name_changed',lambda:h.discover(json.dumps(bad).encode(),graph,'msm_vfe0_pix'))
reject('different_probe_selection',lambda:h.check_selection(role,dict(good,probe_sha256='0'*64)))
expected=dict(pid=123,start_ticks=456,exe_sha256='a'*64,uid=10000,cap_eff=0)
witness=dict(same_process_before_after=True,identity=expected,character_fds=[dict(fd=7,target='/dev/video3',major=81,minor=3)])
assert h.check_open_fd(role,witness,expected)['open_fd_count']==1
reject('no_open_full_fd',lambda:h.check_open_fd(role,dict(witness,character_fds=[]),expected))
reject('replaced_process',lambda:h.check_open_fd(role,dict(witness,same_process_before_after=False),expected))
reject('wrong_process_start',lambda:h.check_open_fd(role,witness,dict(expected,start_ticks=457)))
reject('root_process',lambda:h.check_open_fd(role,dict(witness,identity=dict(expected,uid=0)),dict(expected,uid=0)))
reject('available_but_no_emission',lambda:h.check_emission(role,[]))
reject('RDI0_only_emission',lambda:h.check_emission(role,[dict(event='v4l2_qbuf',minor=0),dict(event='v4l2_dqbuf',minor=0)]))
assert h.check_emission(role,[dict(event='v4l2_qbuf',minor=3),dict(event='v4l2_dqbuf',minor=3)])['actual_v4l2_emission_verified']
# Renumbering both media path and inventory must change the selection, not use a fixed 3.
newprobe=json.loads(probe);newprobe['video_nodes']['video27']=newprobe['video_nodes'].pop('video3');newprobe['video_nodes']['video27']['dev']='81:97'
renumbered=h.discover(json.dumps(newprobe).encode(),graph.replace(b'/dev/video3\n',b'/dev/video27\n'),'msm_vfe0_pix')
assert renumbered['full_video_node']=='video27' and renumbered['minor']==97
spec=importlib.util.spec_from_file_location('guarded463',HERE/'guarded-trace.py')
guarded=importlib.util.module_from_spec(spec);spec.loader.exec_module(guarded)
extra=(private/'kernel457/trace-extra-private.json').read_bytes()
selection=dict(good,pixel_entity='msm_vfe0_pix',full_role_graph_sha256=h.sha(graph))
plan=guarded.GuardedPlan(probe,json.dumps(selection).encode(),extra,graph)
assert plan.filters['v4l2:v4l2_dqbuf']=='minor == 3'
reject('guarded_plan_rejects_actual_r2_minor',lambda:guarded.GuardedPlan(probe,json.dumps(dict(selection,full_video_node='video0',full_minor=0)).encode(),extra,graph))
reject('guarded_plan_requires_graph_hash',lambda:guarded.GuardedPlan(probe,json.dumps(dict(selection,full_role_graph_sha256='0'*64)).encode(),extra,graph))
spec=importlib.util.spec_from_file_location('render463',HERE/'render-role-query.py')
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
query=renderer.render(None,None,None);tree=ast.parse(query)
assert not any(isinstance(n,ast.Attribute) and n.attr in ['write_text','write_bytes','mkdir','unlink','kill','killpg','Popen','chmod','chown'] for n in ast.walk(tree))
assert "[media,'-p','-d',str(device)]" in query and 'Fresh outer camera transaction' in query
patterns=[ast.literal_eval(n.args[0]) for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='fullmatch']
assert len(patterns)==1 and re.fullmatch(patterns[0],'media0') and not re.fullmatch(patterns[0],'media-danger')
try:exec(compile(query,'unbound-readonly-query','exec'),{})
except AssertionError as error:assert 'Fresh outer camera transaction' in str(error)
else:raise AssertionError('Unbound query touched the device')
observation=dict(witness,schema='samurai-full-role-observation-v1',boot_id='model-boot',window_id='model-window',
                 phone_changed=False,video_nodes=json.loads(probe)['video_nodes'],graph=dict(text=graph.decode()),mono_start_ns=1,mono_end_ns=2)
assert h.from_observation(probe,json.dumps(observation).encode(),'msm_vfe0_pix','model-boot','model-window',expected)['runtime_open_fd_verified']
reject('wrong_boot_observation',lambda:h.from_observation(probe,json.dumps(observation).encode(),'msm_vfe0_pix','another-boot','model-window',expected))
reject('wrong_window_observation',lambda:h.from_observation(probe,json.dumps(observation).encode(),'msm_vfe0_pix','model-boot','another-window',expected))
report=dict(stage=463,cached_graphs=results,actual_r2_wrong_role_rejected=True,renumbering_resolved_without_fixed_minor=True,
            negative_cases=rejected,synthetic_fd_and_emission_checks_only=True,fresh_topology_fd_or_emission_proven=False,
            guarded_459_lifecycle_uses_correct_minor=True,readonly_query_default_rejects_missing_handoff_and_application=True,
            no_phone_sdk_build_or_tracefs_access=True,selector_sha256=h.sha((HERE/'full-role.py').read_bytes()),passed=True)
(HERE/'role-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
