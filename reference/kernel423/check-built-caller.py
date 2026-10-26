"""Inspect the compiled IPA selection call, independent of source timestamps."""
from pathlib import Path
import json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
name='_ZN9libcamera16CamssVfePipeline7initIPAEPNS_12CamssVfeDataE'
q=subprocess.run(['aarch64-linux-gnu-objdump','-d','--disassemble='+name,str(P/'libcamera.so.0.7.2')],capture_output=True,check=True)
(P/'init-ipa-after-rebuild-private.asm').write_bytes(q.stdout)
lines=q.stdout.decode().splitlines();call=next(i for i,l in enumerate(lines) if 'bl\t' in l and 'IPAManager9createIPA' in l)
before='\n'.join(lines[max(0,call-8):call]);assert re.search(r'mov\s+w3, #0x3\b',before) and re.search(r'mov\s+w2, w3',before),before
old=(P/'r2-init-ipa-before-rebuild-private.asm').read_text();assert re.search(r'mov\s+w3, #0x2\b',old)
r=dict(stage=423,actual_rebuilt_pipeline_requests_private_ipa3=True,prior_inconsistent_artifact_confirmed_requested_ipa2=True,source_only_version_assertion_insufficient=True,passed=True)
(HERE/'built-caller-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
