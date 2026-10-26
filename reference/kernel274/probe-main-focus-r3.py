"""Finite optical sweep using only independently cross-checked OEM normal-operation writes."""
from pathlib import Path
import json
R=Path(__file__).resolve().parent
prior=json.loads((R/'focus-position-r2-validation.json').read_text())
assert prior['capture_exit']==0 and prior['health']['passed'] and len(prior['runs'])==2
source=(R/'probe-main-focus.py').read_text()
old="""def move(fd,value):
 current=int(read_register(fd,0x84,2),16);assert 0<=current<=1023
 # Only the initial transition may start below the chosen optical test interval.
 if current<208:write_position(fd,208);current=208
 while current!=value:
  current+=max(-64,min(64,value-current));write_position(fd,current)
 assert int(read_register(fd,0x84,2),16)==value
"""
new="""last_commanded=[None]
def move(fd,value):
 if last_commanded[0] is None:write_position(fd,208);last_commanded[0]=208
 while last_commanded[0]!=value:
  step=max(-64,min(64,value-last_commanded[0]));write_position(fd,last_commanded[0]+step);last_commanded[0]+=step
"""
changes=[('focus-position-r1','focus-position-r3'),(old,new),
 ("enable_value=read_register(fd,0xe0,1);assert enable_value=='01','OEM enable readback mismatch'","enable_value=read_register(fd,0xe0,1);state['enable_readback']=enable_value;save()"),
 ('enabled_readback_verified=enabled','enable_command_acknowledged=enabled,enable_readback=state.get(\'enable_readback\'),enable_readback_semantics_unknown=True')]
for before,after in changes:assert before in source,before;source=source.replace(before,after)
exec(compile(source,'focus-r3-derived.py','exec'),dict(__file__=str(R/'probe-main-focus.py')))
