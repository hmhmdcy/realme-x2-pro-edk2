"""Retain disassembly privately; publish only candidate CSR writer metadata."""
from pathlib import Path
import hashlib,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;image=P.parent/'kernel352/CAMERA_ICP.elf-private'
assert hashlib.sha256(image.read_bytes()).hexdigest()=='a22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63'
out=P/'firmware-armv7-code-private.asm'
if not out.exists():
 q=subprocess.run(['/usr/bin/arm-linux-gnueabi-objdump','-d','-m','armv7',str(image)],capture_output=True);q.check_returncode();out.write_bytes(q.stdout)
lines=out.read_text().splitlines();function=None;candidates=[];snippets=[]
for i,line in enumerate(lines):
 m=re.match(r'([0-9a-f]+) <(.+)>:',line)
 if m:function=m[2]
 if re.search(r'\bstr\w*\b.*\[.*(?:#76|#0x4c)\]',line):
  address=re.search(r'^\s*([0-9a-f]+):',line)
  if address:candidates.append(dict(address=int(address[1],16),function=function));snippets.extend(lines[max(0,i-9):i+4]+[''])
(P/'offset4c-writes-private.asm').write_text('\n'.join(snippets)+'\n')
report=dict(stage=368,firmware_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),candidate_offset4c_stores=candidates,
    instruction_offset_matches_only_not_proven_csr_writers=True,hardware_accessed=False)
(HERE/'firmware-writer-candidates.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(stage=368,candidate_offset4c_stores=len(candidates),offset_matches_are_not_yet_proven_writers=True,hardware_accessed=False)))
