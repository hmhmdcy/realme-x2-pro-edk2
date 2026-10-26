from pathlib import Path
import hashlib,json,re,subprocess
import host
binary=Path('/mnt/e/edk2-samurai-out/kernel281/camera.qcom.so-private')
assert hashlib.sha256(binary.read_bytes()).hexdigest()=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
for name,start,length in [('bhist-execute',0x311f50,0x4dc),('bls-execute',0x3128a0,0x788),('bhist-create',0x311d40,0x20c),('bls-calculate',0x3c35b8,0x114)]:
 p=host.PRIVATE/(name+'-disassembly-private.txt')
 if not p.exists():p.write_text(subprocess.check_output(['aarch64-linux-gnu-objdump','-d',f'--start-address={start:#x}',f'--stop-address={start+length:#x}',str(binary)],text=True))
 lines=p.read_text().splitlines();selected=set()
 for i,l in enumerate(lines):
  if re.search(r'\b52cb10\b|\b52d2e8\b',l):selected.update(range(max(0,i-11),min(len(lines),i+4)))
 print(name+' packet windows\n'+'\n'.join(lines[i] for i in sorted(selected)))
 print(name+' literals\n'+'\n'.join(l for l in lines if re.search(r'\b(?:mov|and|orr|ubfiz|bfi|ubfx)\b.*#0x',l)))
