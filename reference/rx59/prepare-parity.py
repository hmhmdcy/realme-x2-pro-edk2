"""Prepare a bounded parity experiment within the continuing authorization."""
from pathlib import Path
from hashlib import sha256
root=Path(__file__).resolve().parent
old=root.parent/'rx58'
raw=(old/'driver-log-etw-admin.ps1').read_bytes()
assert sha256(raw).hexdigest()=='dcee7311408c7d61201645b0ec74e701235775428d9c78dd72ee8acd260db09e'
s=raw.decode()
s=s.replace("$rxRoot='E:\\edk2-samurai-out\\rx58'","$rxRoot='E:\\edk2-samurai-out\\rx59'")
s=s.replace('first-status-01','parity-01').replace('EUD-RX58-FIRST-STATUS-01','EUD-RX59-PARITY-01')
s=s.replace(r'rx(?:57|58)[\\/]capture-windows(?:-02|-first-status)?\.ps1',r'rx(?:57|58|59)[\\/]capture-windows(?:-02|-first-status|-parity)?\.ps1')
s=s.replace('serial_owner_count=3;data_commands_only_in_final_owner=$true','serial_owner_count=2;first_owner_one_unexecuted_frame=$true;data_commands_only_in_final_owner=$false')
s=s.replace('measurement-plan-01.json','parity-plan-01.json')
s=s.replace('separately approved administrator run','continuously authorized administrator run')
(root/'driver-log-etw-admin.ps1').write_text(s)
h=sha256(s.encode()).hexdigest()
launch=(old/'launch-authorized-measurement.ps1').read_text().replace("$rxRoot='E:\\edk2-samurai-out\\rx58'","$rxRoot='E:\\edk2-samurai-out\\rx59'").replace('first-status','parity').replace('dcee7311408c7d61201645b0ec74e701235775428d9c78dd72ee8acd260db09e',h).replace('after the RX58 joint capture plan was presented.','for the same scoped COM14 diagnostics; RX59 parity protocol recorded before launch.')
(root/'launch-authorized-parity.ps1').write_text(launch)
for name in ('eud-terminal-rx-perf.ps1','EudRxAudit.cs','EudSerialPerf.cs'):
    (root/name).write_bytes((old/name).read_bytes())
test=(old/'test-measurement.ps1').read_text().replace('rx58','rx59').replace('capture-windows-first-status.ps1','capture-windows-parity.ps1').replace('control-first-status-01','control-parity-01').replace('prepared-measurement-tests.json','prepared-parity-tests.json').replace('separately approved administrator run','continuously authorized administrator run')
(root/'test-parity.ps1').write_text(test)
print(h)
