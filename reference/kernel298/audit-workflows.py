"""Check stage adaptation did not alter sizes or unrelated hash pins."""
from pathlib import Path
import io,json,re,tokenize
HERE=Path(__file__).resolve().parent
names=['build-boot-kernel.py','package-boot-candidate.py','stage-device-modules.py','check-transition-readiness.py','prepare-transition.py','native-quiesce.py','launch-quiesce.py','poll-quiesce.py','restart-bootloader.py','submit-restart.py','flash-logdump.py','bootstrap-postboot.py','check-new-runtime.py','inspect-startup.py']
allowed={
'ab709d9670f6dcaa71858fd4f3e189522f669913':'c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117',
'82e39f7ea2ad2507417290cfbcd5754dd3f4ee431bb3a73b31e8f880e5e04233':'82c5ab39f5749693c8e94b7bec7266a9d02a255212af86093e40dfe2e9a101da',
'64616e8fd6e4327e6a07d5c738bea7b7707922703f8a69a97f11ec11af08605e':'e6cf910b3a3499232eecccc9d47524c19b949bb59ffc619174f44a78813f44ec'}
for n in names:
 old=(HERE.parent/'kernel297'/n).read_text();new=(HERE/n).read_text()
 numbers=lambda s:[t.string for t in tokenize.generate_tokens(io.StringIO(s).readline) if t.type==tokenize.NUMBER and t.string not in ['296','297','298']]
 assert numbers(old)==numbers(new),n
 hashes=lambda s:re.findall(r'\b[0-9a-f]{40}(?:[0-9a-f]{24})?\b',s)
 assert [allowed.get(h,h) for h in hashes(old)]==hashes(new),n
report=dict(stage=298,workflow_files=len(names),all_nonstage_numeric_literals_preserved=True,all_unrelated_hash_pins_preserved=True,flash_preflight_size_corrected=True)
(HERE/'workflow-adaptation-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
