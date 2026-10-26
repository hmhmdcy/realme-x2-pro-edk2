"""Test only OEM initial focus optically; OEM configuration defines writes, not echo reads."""
from pathlib import Path
import json
R=Path(__file__).resolve().parent
prior=json.loads((R/'focus-position-r1-validation.json').read_text())
assert prior['capture_exit']==0 and prior['health']['passed'] and not prior['runs']
source=(R/'probe-main-focus.py').read_text()
changes=[('focus-position-r1','focus-position-r2'),
 ("  assert int(read_register(fd,0x84,2),16)==value\n",''),
 (" enable_value=read_register(fd,0xe0,1);assert enable_value=='01','OEM enable readback mismatch'"," enable_value=read_register(fd,0xe0,1);state['enable_readback']=enable_value;save()"),
 ("  state.update(state='enable-oem-actuator');save();write_enable(fd)\n  enable_value=read_register(fd,0xe0,1);state['enable_readback']=enable_value;save()\n  enabled=True\n  for index,position in enumerate([208,304,400,496,592,688,784,880,208]):",
  "  for index,position in enumerate([0,208]):\n   if position:\n    state.update(state='enable-oem-actuator');save();write_enable(fd)\n    enable_value=read_register(fd,0xe0,1);state['enable_readback']=enable_value;save();enabled=True"),
 ("   state.update(state='position',index=index,position=position);save();move(fd,position);time.sleep(.15)",
  "   state.update(state='position',index=index,position=position);save()\n   if position:write_position(fd,position)\n   time.sleep(.5)"),
 ("  move(fd,208);parked=True","  parked=True"),
 ('enabled_readback_verified=enabled','enable_command_acknowledged=enabled,enable_readback=state.get(\'enable_readback\'),enable_readback_semantics_unknown=True'),
 ('len(runs)==9','len(runs)==2')]
for before,after in changes:
 # The echoed-position assertion is removed with the source's exact indentation.
 if before not in source and before.startswith('  assert int(read_register'):before=before[1:]
 assert before in source,before;source=source.replace(before,after)
compile(source,'focus-r2-derived.py','exec')
exec(compile(source,'focus-r2-derived.py','exec'),dict(__file__=str(R/'probe-main-focus.py')))
