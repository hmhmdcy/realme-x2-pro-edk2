from pathlib import Path
import re,json
out=Path('/mnt/e/edk2-samurai-out/kernel103')
s=(out/'postflash-enumerated-read-wsl.txt').read_text(errors='replace')
identity=json.loads((out/'fastboot-identity.json').read_text())['serial']
s=s.replace(identity,'[private-serial]')
s=re.sub(r'(?i)\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b','[private-address]',s)
for line in s.splitlines():
    if re.search(r'panic|Oops|BUG:|Unable to handle|Call trace|samurai-audio|max989|ASoC|q6asm|q6afe|q6adm|wcd934|Run /init|USB|gadget|ttyGS|NCM|g_ether|rmtfs|qrtr',line,re.I):print(line)
print('REDACTED_CAPTURE_TAIL')
print('\n'.join(s.splitlines()[-24:]))
