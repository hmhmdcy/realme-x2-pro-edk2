from pathlib import Path
import hashlib, importlib.util, json, re, struct, sys, tarfile

out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
trial=sys.argv[1] if len(sys.argv)>1 else 'v9'
assert re.fullmatch(r'v\d+|census14|attributes15',trial)
parser=out/'ulog-reference/slpi-ulog-coredump.py'
assert hashlib.sha256(parser.read_bytes()).hexdigest()==json.loads((ref/'ulog-parser-reference.json').read_text())['sha256']
spec=importlib.util.spec_from_file_location('samurai_private_ulog',parser)
mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
with tarfile.open(out/f'sensor-ram-{trial}.tar') as tar:
    data={m.name.removeprefix('./'):tar.extractfile(m).read() for m in tar if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
assert int(data['coredump-read-exit.txt'])==0
dumpfile=out/f'slpi-coredump-{trial}-private.elf'
dumpfile.write_bytes(data['slpi-coredump.elf'])
firmware=sys.argv[2] if len(sys.argv)>2 else 'original'
assert firmware in ('original','c28','c35')
fwroot=(Path('/mnt/e/edk2-samurai-out/kernel111/source-files/k111-sensor-sources-readonly/firmware') if firmware=='original'
        else out/(firmware+'-reference-private')/'firmware')
if firmware!='original':
    expected=json.loads((ref/(firmware+'-reference-validation.json')).read_text())['files']
    for name,digest in expected.items():
        assert hashlib.sha256((fwroot/name).read_bytes()).hexdigest()==digest
mdt=(fwroot/'slpi.mdt').read_bytes()
assert mdt[:6]==b'\x7fELF\x01\x01'
off=struct.unpack_from('<I',mdt,28)[0]
step,count=struct.unpack_from('<HH',mdt,42)
assert step==32 and off+step*count<=len(mdt)
maps=[]
for i in range(count):
    kind,offset,va,pa,filesz,memsz,flags,align=struct.unpack_from('<IIIIIIII',mdt,off+step*i)
    if kind==1 and memsz and flags & (7<<24) != 2<<24:
        maps.append(dict(index=i,va=va,pa=pa,filesz=filesz,size=memsz,flags=flags))

class PhoneDump(mod.Dump):
    # VA->PA comes from this phone's matching split ELF, never a guessed delta.
    def pointer_address(self,pointer):
        matches=[m['pa']+pointer-m['va'] for m in maps if m['va']<=pointer<m['va']+m['size']]
        if len(set(matches))!=1: raise KeyError('pointer lacks unique matching-firmware VA mapping')
        return matches[0]
    def string(self,pointer,relocation,limit=1024):
        return super().string(self.pointer_address(pointer),0,limit)

dump=PhoneDump(dumpfile,0)
assert [(s.address,s.size) for s in dump.segments]==[(m['pa'],m['size']) for m in maps]
code_matches=[]
for m in maps:
    if not m['filesz'] or not m['flags'] & 1: continue
    source=(fwroot/f"slpi.b{m['index']:02d}").read_bytes()
    assert len(source)==m['filesz']
    verified=0
    for offset in (0,128,4096,8192):
        block=source[offset:offset+128]
        if len(block)==128 and len(set(block))>=8 and dump.read(m['pa']+offset,128)==block:
            verified+=1
    code_matches.append(dict(segment_index=m['index'],unique_128byte_blocks_matched=verified))
assert sum(m['unique_128byte_blocks_matched'] for m in code_matches)>=8
logs=dump.logs()
decoded={}; summaries={}
for log in logs:
    lines=[]; invalid=0
    for offset,message,error in mod.messages(dump,log):
        if error:
            invalid+=1; lines.append(error); continue
        lines.append(mod.decode_message(dump,message,0))
    key=f'{log.name}@{log.address:x}'
    decoded[key]=lines
    summaries[key]=dict(ring_bytes=log.size,records=len(lines),invalid_records=invalid,
                        unresolved_records=sum('unresolved=' in line for line in lines))
(out/f'ulog-{trial}-decoded-private.json').write_text(json.dumps(decoded,indent=2)+'\n')
(out/f'ulog-{trial}-map-private.json').write_text(json.dumps(dict(maps=maps,code_matches=code_matches,summaries=summaries),indent=2)+'\n')
report=dict(coredump_sha256=hashlib.sha256(data['slpi-coredump.elf']).hexdigest(),
            firmware_reference=firmware,
            coredump_bytes=len(data['slpi-coredump.elf']),load_segments=len(dump.segments),
            matching_firmware_va_pa_mapping_verified=True,
            original_code_blocks_matched=sum(m['unique_128byte_blocks_matched'] for m in code_matches),
            valid_ulog_count=len(logs),log_names=sorted(set(log.name for log in logs)),
            decoded_records=sum(v['records'] for v in summaries.values()),
            invalid_records=sum(v['invalid_records'] for v in summaries.values()),
            unresolved_records=sum(v['unresolved_records'] for v in summaries.values()),
            format_mapping_uses_other_device_defaults=False,raw_contents_private=True,
            sensor_function_accepted=False)
(ref/f'ulog-{trial}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
for key,lines in decoded.items():
    if any(name in key.lower() for name in ('i2c','spi','icb','gpi','pmic')):
        errors=[line for line in lines if re.search(r'error|fail|invalid|nack',line,re.I)]
        safe=sorted(set(re.sub(r'ts=\d+ ','',line) for line in errors))
        print(json.dumps(dict(log=key.split('@')[0],records=len(lines),error_records=len(errors),error_formats=safe[:20])))
