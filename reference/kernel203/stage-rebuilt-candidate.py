from pathlib import Path
import hashlib,json,host

host.download('/var/lib/samurai/k203-mm-rebuild/summary.json',host.PRIVATE/'mm-clean-rebuild-private.json')
report=json.loads((host.PRIVATE/'mm-clean-rebuild-private.json').read_text());assert report['byte_identical_to_validated191']
candidate=host.PRIVATE/'ModemManager203-candidate';assert not candidate.exists()
host.download('/var/lib/samurai/k203-mm-rebuild/ModemManager',candidate)
assert hashlib.sha256(candidate.read_bytes()).hexdigest()==report['candidate_sha256']
(Path(__file__).resolve().parent/'mm-clean-rebuild-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(stage=203,clean_rebuild_and_full_transfer_verified=True,candidate_sha256=report['candidate_sha256'])))
