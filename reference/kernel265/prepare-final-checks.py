from pathlib import Path
import ast
R=Path(__file__).parent;B=R.parent/'kernel264'
tree=ast.parse((B/'final-health.py').read_text());code=next(n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
code=code.replace('k264-final-health','k265-final-health').replace('stage=264','stage=265').replace('k264-services-current-private','k265-services-current-private')
code=code.replace("assert sha(Path('/usr/lib/gstreamer-1.0/libgstpipewire.so'))==base['plugin_sha256']","assert sha(Path('/usr/lib/gstreamer-1.0/libgstpipewire.so'))==proof['payload_sha256']['usr/lib/gstreamer-1.0/libgstpipewire.so']")
code=code.replace("['pipewire-libs','pipewire-spa-libcamera']","['pipewire-libs','pipewire-spa-libcamera','gst-plugin-pipewire']").replace("name+'=1.6.9-r2'","name+'=1.6.9-r3'")
code=code.replace("assert not any('/var/lib/samurai/k264-' in l and '.so' in l for l in maps.splitlines())","assert not any(('/var/lib/samurai/k264-' in l or '/var/lib/samurai/k265-' in l) and '.so' in l for l in maps.splitlines())")
needle="states=list(root.glob('k264-*/state-private.json'));assert len(states)==25";assert code.count(needle)==1
replacement="""states=list(root.glob('k265-*/state-private.json'))
expected_states={*('k265-camera-'+str(i) for i in [*range(1,15),16,17]),*('k265-compat-'+str(i) for i in [6000091,6000092,6000093,6000101,6000111,6000121,6000141,6000142,6000143,6000151,6000152,6000153,6000154]),'k265-policy-candidate','k265-package-transaction','k265-services','k265-snapshot-gui'}
assert {p.parent.name for p in states}==expected_states,{p.parent.name for p in states}^expected_states
assert b'SAMURAI_CAMERA_COPY=' not in Path('/proc',str(phosh['pid']),'environ').read_bytes()"""
code=code.replace(needle,replacement).replace("p.name.startswith('k264')","p.name.startswith(('k264','k265'))")
code=code.replace("root/'k264-pipewire-6000041-r2/dmesg-before-private.txt'","root/'k265-camera-1/dmesg-before-private.txt'")
code=code.replace("production_common_packages='1.6.9-r2'","production_common_packages='1.6.9-r3'").replace('gstreamer_plugin_unchanged=True','gstreamer_shared_frame_lifetime_fixed=True').replace('all_natural_production_tests_and_gui_used_same_daemons=True','all_post_deployment_tests_and_gui_used_same_daemons=True')
outer='''from pathlib import Path
import json,shlex
import host
R=Path(__file__).parent;B=R.parent/'kernel264'
proof=json.loads((R/'package-install-validation.json').read_text());base=json.loads((B/'baseline-validation.json').read_text());launch=json.loads((B/'launcher-update-validation.json').read_text())
CODE
payload=json.dumps([proof,base,launch]).encode()+b'\\n';wrapper='import sys;source='+repr(code)+';exec(compile(source,\"k265-final-health\",\"exec\"))'
q=host.ssh('python3 -c '+shlex.quote(wrapper),input=payload,timeout=30,check=False);(host.PRIVATE/'final-health-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,'Inspect final-health state before retry'
d=json.loads(q.stdout);(R/'final-health-validation.json').write_text(json.dumps(d,indent=2)+'\\n');print(json.dumps(d,indent=2))
'''
p=R/'final-health.py';assert not p.exists();p.write_text(outer.replace('CODE','code='+repr(code)))
s=(B/'analyze-gui.py').read_text().replace('k264-snapshot-gui','k265-snapshot-gui').replace('stage=264','stage=265')
p=R/'analyze-gui.py';assert not p.exists();p.write_text(s)
print('Prepared final health and actual-window flow checks')

