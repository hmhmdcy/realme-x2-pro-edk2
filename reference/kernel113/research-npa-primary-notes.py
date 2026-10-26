from pathlib import Path
import hashlib,json,re,subprocess

repo='/home/cy122/x2pro-linux/refs/hotdog-haptics-k99'
revision='47087509c4289c2580c54f5433e55366b2e00445'
assert subprocess.check_output(['git','-C',repo,'rev-parse','HEAD']).decode().strip()==revision
pattern=r'SPI_QUP_DDR|NO_ROUTE_TO_SLAVE|ICB.*(fix|Fix|route)|master.*(87|99)'
names=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',revision,'docs/evidence']).decode().splitlines()
selected=[name for name in names if re.search('icb|npa|spi|platform|driver-set|sensor-dsp',name,re.I)]
print(json.dumps(dict(relevant_paths=selected)))
payload=[]
for name in ['docs/evidence/2026-08-10-slpi-sensor-dsp.md','docs/evidence/2026-08-19-npa-client-type-gate.md',
    'docs/evidence/2026-08-19-icb-arbiter-qup-client.md','docs/evidence/2026-08-19-icb-info-devcfg.md',
    'docs/evidence/2026-08-23-the-spi-bus-never-initialises.md']:
    data=subprocess.check_output(['git','-C',repo,'-c','http.version=HTTP/1.1','show',revision+':'+name],timeout=40).decode()
    if name.endswith('the-spi-bus-never-initialises.md'):
        print('PRIMARY_SPI_NOTE')
        print(re.sub(r'(?i)(?:0x)?[a-f][0-9a-f]{7,15}', '<address>',data)[:12500])
    for index,line in enumerate(data.splitlines()):
        if re.search(pattern if name.endswith(('sensor-dsp.md','type-gate.md')) else
            r'BLSP|QUP|route|tree|fail|wrong|client_value|master|fix',line,re.I):
            payload.append(f'{name}:{index+1}: {line}')
result='\n'.join(payload).encode()
out=Path('/mnt/e/edk2-samurai-out/kernel113/npa-primary-notes-private.txt')
out.write_bytes(result)
lines=result.decode().splitlines()
print(json.dumps(dict(primary_revision=revision,matches=len(lines),private_source_sha256=hashlib.sha256(result).hexdigest())))
for line in lines[75:]:
    line=re.sub(r'(?i)(?:0x)?[a-f][0-9a-f]{7,15}', '<address>',line)
    print(line[:450])
