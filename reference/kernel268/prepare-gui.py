"""Prepare the owned Snapshot test with observed labelled accessibility actions."""
from pathlib import Path

R=Path(__file__).resolve().parent;B=R.parent/'kernel265'
s=(B/'native-snapshot-gui.py').read_text().replace('k260-work','k267-work').replace('stage=265','stage=268')
s=s.replace('k265-services-current-private','k268-services-current-private').replace('k265-snapshot-gui','k268-snapshot-gui').replace('k265_snapshot_gui','k268_snapshot_gui')
s=s.replace('/var/lib/samurai/k265-tools/gui-auto.py','/var/lib/samurai/k268-tools/gui-auto.py').replace('libcamera=99990.7.2-r15','libcamera=99990.7.2-r19')
compile(s,'native-snapshot-gui.py','exec');(R/'native-snapshot-gui.py').write_text(s)
s=(B/'gui-auto.py').read_text().replace('k265-snapshot-gui','k268-snapshot-gui')
s=s.replace('import hashlib,json,os,pwd,time,traceback','import hashlib,json,os,pwd,re,time,traceback')
needle="desktop=next(p for p in Path('/proc')"
assert s.count(needle)==1;s=s.replace(needle,"tree_file=(root/'accessible-tree-private.json').open('w')\n\n"+needle)
s=s.replace("entries.append(dict(bus=name,path=path,name=props.get('Name'),actions=actions))",
 "entries.append(dict(bus=name,path=path,name=props.get('Name'),description=props.get('Description'),actions=actions))")
needle=" entries=scan();switch=action(entries,{'win.next-camera','win.switch-camera','win.change-camera','win.toggle-camera'})\n switched=False"
assert s.count(needle)==1
s=s.replace(needle,""" entries=scan();tree_file.write(json.dumps(entries,indent=2));tree_file.flush()
 switch=action(entries,{'win.next-camera','win.switch-camera','win.change-camera','win.toggle-camera'})
 if switch is None:
  candidates=[dict(**e,action_name=a[0],action_index=i) for e in entries for i,a in enumerate(e['actions'])
   if re.search(r'(switch|change|flip|toggle).*(camera)|camera.*(switch|change)|切换.*(摄像头|相机)',
                str(e.get('name') or '')+' '+str(e.get('description') or ''),re.I)]
  assert len(candidates)<=1,'Ambiguous labelled camera control'
  switch=candidates[0] if candidates else None
 switched=False""")
needle="  click(switch);switched=await_camera('rear')"
assert s.count(needle)==1
s=s.replace(needle,"""  click(switch);time.sleep(.5)
  if not active('rear'):
   entries=scan();tree_file.seek(0);tree_file.truncate();tree_file.write(json.dumps(entries,indent=2));tree_file.flush()
   candidates=[dict(**e,action_name=a[0],action_index=i) for e in entries for i,a in enumerate(e['actions'])
    if re.search(r'Built.in Back Camera|Back Camera|后置',str(e.get('name') or ''),re.I)]
   assert len(candidates)<=1,'Ambiguous rear-camera menu action'
   if candidates:click(candidates[0])
  switched=await_camera('rear')""")
s=s.replace('finally:summary_file.close();request_file.close()','finally:summary_file.close();request_file.close();tree_file.close()')
compile(s,'gui-auto.py','exec');(R/'gui-auto.py').write_text(s)
s=(B/'run-gui.py').read_text().replace('k265-tools','k268-tools')
compile(s,'run-gui.py','exec');(R/'run-gui.py').write_text(s)
print('Prepared Snapshot preview, shutter and labelled camera-switch control.')
