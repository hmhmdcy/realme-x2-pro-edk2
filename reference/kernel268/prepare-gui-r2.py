"""Activate the owned window through the observed Phosh application launcher."""
from pathlib import Path

R=Path(__file__).resolve().parent
s=(R/'gui-auto.py').read_text().replace('k268-snapshot-gui','k268-snapshot-gui-r2')
s=s.replace('def scan():','def scan(target_pid=pid):').replace('if owner_pid(n)==pid','if owner_pid(n)==target_pid')
s=s.replace('len(entries)<200','len(entries)<1200').replace('if depth<12:','if depth<20:')
s=s.replace('def click(a):','def click(a,target_pid=pid):').replace("assert owner_pid(a['bus'])==pid","assert owner_pid(a['bus'])==target_pid")
s=s.replace("if action(entries,{'win.take-picture'}):break","if entries:break")
needle=" assert await_camera('front'),'Front sensor not active for owned window'"
assert s.count(needle)==1
s=s.replace(needle,""" phosh_pid=int(desktop.name)
 shell_entries=scan(phosh_pid)
 launches=[dict(**e,action_name=a[0],action_index=i) for e in shell_entries for i,a in enumerate(e['actions'])
  if e.get('name')=='Camera (Snapshot)' and a[0]=='Click']
 assert len(launches)==1,'Observed Camera (Snapshot) desktop launcher is not unique'
 assert Path('/proc',str(pid),'comm').read_text().strip()=='snapshot'
 click(launches[0],phosh_pid)
"""+needle)
s=s.replace('accessible_shutter_action_accepted=True,','accessible_shutter_action_accepted=True,observed_desktop_launcher_clicked=True,')
compile(s,'gui-auto-r2.py','exec');(R/'gui-auto-r2.py').write_text(s)
s=(R/'native-snapshot-gui.py').read_text().replace('k268-snapshot-gui','k268-snapshot-gui-r2').replace('k268_snapshot_gui','k268_snapshot_gui_r2')
s=s.replace('k268-tools/gui-auto.py','k268-tools/gui-auto-r2.py')
compile(s,'native-snapshot-gui-r2.py','exec');(R/'native-snapshot-gui-r2.py').write_text(s)
s=(R/'run-gui.py').read_text().replace('k268-tools/gui-auto.py','k268-tools/gui-auto-r2.py').replace("R/'gui-auto.py'","R/'gui-auto-r2.py'")
s=s.replace("R/'native-snapshot-gui.py'","R/'native-snapshot-gui-r2.py'").replace('snapshot-gui-private.log','snapshot-gui-r2-private.log').replace('snapshot-gui-validation.json','snapshot-gui-r2-validation.json')
compile(s,'run-gui-r2.py','exec');(R/'run-gui-r2.py').write_text(s)
print('Prepared a fresh GUI context using the observed Phosh Camera (Snapshot) Click action.')
