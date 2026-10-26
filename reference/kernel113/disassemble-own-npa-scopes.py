from pathlib import Path
import hashlib,json,re,subprocess

out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
elf=out/'original-slpi-analysis-private.elf'
assert hashlib.sha256(elf.read_bytes()).hexdigest()==json.loads((ref/'npa-forensic-elf-validation.json').read_text())['analysis_elf_sha256']
segments=json.loads((out/'original-slpi-analysis-segments-private.json').read_text())
root=next(s for s in segments if s['index']==4)
base=out/'original-slpi-disassembly-private.txt'
addresses=[int(m.group(1),16) for m in re.finditer(r'^\s*([0-9a-f]+):',base.read_text(),re.M)]
assert addresses
covered_last=max(addresses)
print(json.dumps(dict(initial_full_disassembly_complete=False,
    initial_present_sections=re.findall(r'Disassembly of section ([^:]+):',base.read_text()),
    last_root_instruction_relative=covered_last-root['va'])),flush=True)
jobs=[('text7','.text7',None,None),('npa','.text4',root['va']+0xb5500,root['va']+0xb6500)]
completed=[]
for name,section,start,stop in jobs:
    output=out/f'original-slpi-{name}-disassembly-private.txt'
    errors=out/f'original-slpi-{name}-objdump-private.err'
    command=['llvm-objdump-21','-d','--no-show-raw-insn','--triple=hexagon','--section='+section,str(elf)]
    if start is not None: command.extend(['--start-address='+hex(start),'--stop-address='+hex(stop)])
    with output.open('wb') as listing, errors.open('wb') as error:
        result=subprocess.run(command,stdout=listing,stderr=error,timeout=60)
    assert result.returncode==0
    lines=output.read_text()
    assert 'Disassembly of section '+section+':' in lines
    completed.append(dict(scope=name,section=section,bytes=output.stat().st_size,
        sha256=hashlib.sha256(output.read_bytes()).hexdigest(),returncode=result.returncode,
        full_section=start is None))
    print(json.dumps(completed[-1]),flush=True)
(ref/'npa-disassembly-coverage.json').write_text(json.dumps(dict(
    initial_full_disassembly_complete=False,initial_output_preserved=True,
    initial_unrecorded_terminal_result_not_assumed_success=True,
    scopes=completed,other_device_addresses_used=False,phone_changed=False),indent=2)+'\n')
