"""Keep successful stream evidence; retry the claim from the real active session."""
from pathlib import Path
import ast
import json
import host

ref = Path(__file__).resolve().parent
tree = ast.parse((ref / 'test-native-sensors.py').read_text())
node = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'code' for t in n.targets))
code = ast.literal_eval(node.value)


def change(old, new):
    global code
    assert code.count(old) == 1, old[:80]
    code = code.replace(old, new, 1)


change("out=root/'k228-native-sensors';assert not out.exists()", "out=root/'k228-native-sensors-r2';assert not out.exists()")
change("ssc_before=json.loads(Path('/run/samurai-ssc/state.json').read_text());assert ssc_before['started']", """ssc_before=json.loads(Path('/run/samurai-ssc/state.json').read_text());assert ssc_before['started']
old=root/'k228-native-sensors';assert json.loads((old/'state-private.json').read_text())['exit_code']==1
assert 'Sensor claim not allowed' in (old/'ordinary-user-claims-private.log').read_text()
assert 'line 52' in (old/'failure-private.txt').read_text()
""")
change("""  result=subprocess.run(['ssccli','--debug','--sensor',name,'--timeout','2'],capture_output=True,env=env,timeout=20)
  raw=result.stdout+result.stderr;(out/(name+'-private.log')).write_bytes(raw);text=raw.decode(errors='replace')""", """  raw=(old/(name+'-private.log')).read_bytes();(out/(name+'-retained-private.log')).write_bytes(raw);text=raw.decode(errors='replace')""")
change("assert result.returncode==0 and count>0 and disabled,name", "assert count>0 and disabled,name")
change("streams[name]=dict(measurements=count,clean_disable=True,exit_code=0)",
       "streams[name]=dict(measurements=count,clean_disable=True,original_script_asserted_exit0_before_claim_failure=True,remeasured=False)")
change(" user=pwd.getpwuid(10000)\n def demote():", """ user=pwd.getpwuid(10000)
 b=dbus.SystemBus(private=True);m=dbus.Interface(b.get_object('org.freedesktop.login1','/org/freedesktop/login1'),'org.freedesktop.login1.Manager');sessions=[]
 for row in m.ListSessions():
  if int(row[1])!=10000:continue
  v=dbus.Interface(b.get_object('org.freedesktop.login1',row[4]),'org.freedesktop.DBus.Properties').GetAll('org.freedesktop.login1.Session')
  if v['Active'] and v['Type']=='wayland' and v['Seat'][0]=='seat0':sessions.append(v)
 assert len(sessions)==1;session=sessions[0];leader=Path('/proc')/str(int(session['Leader']));cgroup=(leader/'cgroup').read_text();b.close()
 rows=[l.split(':',2) for l in cgroup.splitlines()];assert len(rows)==1 and rows[0][:2]==['0','']
 base=Path('/sys/fs/cgroup').resolve(strict=True);group=(base/rows[0][2].lstrip('/')).resolve(strict=True)
 assert group!=base and group.is_relative_to(base) and (group/'cgroup.procs').is_file()
 (out/'active-session-cgroup-private.json').write_text(json.dumps(dict(cgroup=cgroup,leader=int(session['Leader'])))+'\\n')
 def demote():
  assert (leader/'cgroup').read_text()==cgroup
  (group/'cgroup.procs').write_text(str(os.getpid()))""")
change("has={n:bool(p.Get('net.hadess.SensorProxy',n))", """m=dbus.Interface(b.get_object('org.freedesktop.login1','/org/freedesktop/login1'),'org.freedesktop.login1.Manager');sp=m.GetSessionByPID(os.getpid());sv=dbus.Interface(b.get_object('org.freedesktop.login1',sp),'org.freedesktop.DBus.Properties').GetAll('org.freedesktop.login1.Session');assert sv['Active'] and sv['Type']=='wayland' and sv['Seat'][0]=='seat0' and int(sv['User'][0])==10000
has={n:bool(p.Get('net.hadess.SensorProxy',n))""")
change("report=dict(stage=228,new_boot228=True", "report=dict(stage=228,initial_uid_only_claim_denied=True,active_wayland_claim_child_verified=True,polkit_policy_unchanged=True,prior_five_streams_preserved=True,new_boot228=True")
compile(code, 'native228-claims-r2', 'exec')
result = host.ssh('python3 -', input=code.encode(), timeout=100)
(host.PRIVATE / 'native-sensors-r2-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(ref / 'native-sensors-validation.json').write_text(json.dumps(report, indent=2) + '\n')
state = json.loads((host.PRIVATE / 'current-work-private.json').read_text())
state.update(state='new candidate pins1to2to1; five SSC streams and active Wayland UID10000 claims passed; OOT taint4096 only',
             active_native_session=None, active_native_context=None, runtime_deployed=True,
             next='Build accepted source with actual in-tree target, then stage and controlled clean boot; retain metadata/claim failure evidence')
(host.PRIVATE / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(report))
