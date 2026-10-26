"""Adapt audited #297 workflows with explicit current/candidate identities."""
from pathlib import Path
import json,re
HERE=Path(__file__).resolve().parent
commit=json.loads((HERE/'source-validation.json').read_text())['commit']
names=['build-boot-kernel.py','package-boot-candidate.py','stage-device-modules.py',
 'check-transition-readiness.py','prepare-transition.py','native-quiesce.py','launch-quiesce.py','poll-quiesce.py',
 'restart-bootloader.py','submit-restart.py','flash-logdump.py','refresh-usb-endpoint.ps1',
 'bootstrap-postboot.py','check-new-runtime.py','inspect-startup.py']
for name in names:
 s=(HERE.parent/'kernel297'/name).read_text()
 # Simultaneous replacement retains the previous-runtime guards at #297.
 s=re.sub(r'(?<![0-9a-f])29[67](?![0-9a-f])',lambda m: str(int(m[0])+1),s)
 s=s.replace('ab709d9670f6dcaa71858fd4f3e189522f669913',commit)
 s=s.replace('82e39f7ea2ad2507417290cfbcd5754dd3f4ee431bb3a73b31e8f880e5e04233','82c5ab39f5749693c8e94b7bec7266a9d02a255212af86093e40dfe2e9a101da')
 s=s.replace('64616e8fd6e4327e6a07d5c738bea7b7707922703f8a69a97f11ec11af08605e','e6cf910b3a3499232eecccc9d47524c19b949bb59ffc619174f44a78813f44ec')
 target=HERE/name;assert not target.exists();target.write_text(s)
 if name.endswith('.py'):compile(s,name,'exec')
print('Prepared build and one-transition workflows; review before execution.')
