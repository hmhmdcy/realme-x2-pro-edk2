from pathlib import Path
import json
R=Path(__file__).resolve().parent;old=R.parent/'kernel247'
for name in ['native-quiesce.py','launch-quiesce.py','poll-quiesce.py','normal-reboot.py','submit-normal-reboot.py']:
 s=(old/name).read_text().replace('kernel247','kernel248').replace('kernel246/host.py','kernel247/host.py').replace('k246-runtime','k247-runtime').replace('k247-quiesce','k248-quiesce').replace('k247-tools','k248-tools').replace('k247-reboot-phase','k248-reboot-phase').replace('stage=247','stage=248').replace("P.parent/'kernel246/transport-last-failure-private.log'","P.parent/'kernel247/transport-last-failure-private.log'")
 if name=='normal-reboot.py':
  s=s.replace("assert Path('/etc/runlevels/default/samurai-diag247').resolve()==Path('/etc/init.d/samurai-diag247')","assert not Path('/etc/samurai-rootfs-release').exists() and Path('/etc/samurai-rootfs-release.k248-before-rescue').is_file()")
 compile(s,name,'exec');(R/name).write_text(s)
print('Prepared current247 normal restart into existing RAM fallback; no Android or partition flash.')
