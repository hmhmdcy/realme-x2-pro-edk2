"""Prepare a fixed-port, same-boot diagnostic logger; no modem restart."""
from pathlib import Path
import hashlib,importlib.util,json
R=Path(__file__).resolve().parent
s=(R/'diag_fixed.py').read_text()
codes=(0x1477,0x1478,0x147e,0x147f,0x1480,0x1516,0x1596,0x1635,0x1756,0x1886)
s=s.replace('GNSS_LOG_CODES=(0x1477,0x1480,0x1756,0x1886)','GNSS_LOG_CODES='+repr(codes))
s=s.replace('8*1024*1024','24*1024*1024').replace('self.records>8192','self.records>32768')
s=s.replace('exactly four GNSS log bits','exactly ten verified GNSS log bits').replace('No sleep votes, buffering modes, NV or RF settings are sent.','Temporary realtime mode includes the upstream sleep vote; it is released on close.\nNo buffering configuration, NV or RF settings are sent.')
s=s.replace('# Do not reuse the previous published AP endpoints during reconnect.','# Automatic allocation uses guards; explicit ports must come from this boot.')
s=s.replace('gnss_mask_only_four_verified_ids','gnss_mask_only_ten_verified_ids')
compile(s,'diag_resume_rf.py','exec');(R/'diag_resume_rf.py').write_text(s)
spec=importlib.util.spec_from_file_location('diag245resume',R/'diag_resume_rf.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
report=dict(stage=245,prepared=True,regression=m.regression(),source_sha256=hashlib.sha256(s.encode()).hexdigest(),cached_resume_requires_same_boot_and_version_match=True,temporary_realtime_mode_includes_sleep_vote=True)
(R/'resume-library-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
