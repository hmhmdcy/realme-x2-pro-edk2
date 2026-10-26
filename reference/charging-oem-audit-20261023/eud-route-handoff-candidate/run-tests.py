from pathlib import Path
import hashlib,json,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def function(text,name):
    match=re.search(r'(?m)^STATIC\n(?:VOID|BOOLEAN|EFI_STATUS)\n(?:EFIAPI\n)?'+name+r'\s*\([^;]*?\)\s*\{',text);assert match,name
    end=match.end();depth=1
    while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[match.start():end]+'\n'
def clean(text):return '\n'.join(line for line in text.splitlines() if not line.startswith('#include'))+'\n'
source=(HERE/'PlatformBm.c.candidate').read_text()
start=source.index('typedef struct {\n  EFI_EVENT   Event;',source.index('#define SAMURAI_EUD_CSR_ADDRESS'))
end=source.index('} SAMURAI_EUD_OFF_HANDOFF;',start)+len('} SAMURAI_EUD_OFF_HANDOFF;')
firmware=source[source.index('#define SAMURAI_EUD_CSR_ADDRESS'):start]+source[start:end]+'\nSTATIC SAMURAI_EUD_OFF_HANDOFF mSamuraiEudOffHandoff;\n'
firmware+=(HERE/'firmware-record-functions.inc').read_text()+'\n'
for name in ['SamuraiEudCsrKnown','SamuraiEudBeforeExitBootServices','SamuraiArmEudOffHandoff','SamuraiDisarmEudOffHandoff']:firmware+=function(source,name)
fixture=(HERE/'test-channel.c').read_text().replace('/* ACTUAL_WIRE */',(HERE/'samurai-eud-handoff-wire.h').read_text())
fixture=fixture.replace('/* ACTUAL_FIRMWARE */',firmware).replace('/* ACTUAL_KERNEL */',clean((HERE/'samurai-eud-handoff.c').read_text()))
flags=['-std=gnu11','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
with tempfile.TemporaryDirectory(prefix='samurai-eud-handoff-') as directory:
    root=Path(directory);code=root/'actual.c';code.write_text(fixture);binary=root/'test'
    child=subprocess.run(['gcc',*flags,str(code),'-o',str(binary)],capture_output=True,text=True);assert child.returncode==0,child.stderr
    ran=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30);assert ran.returncode==0,(ran.returncode,ran.stdout,ran.stderr)
    groups=ran.stdout.splitlines();assert len(groups)==10 and not ran.stderr
result=dict(passed=True,groups=groups,group_count=len(groups),flags=flags,actual_BDS_arm_callback_disarm_and_kernel_receiver=True,
    actual_shared_wire_parser=True,firmware_services_EFI_table_iteration_memmap_mapping_MMIO_modeled=True,
    retained_failed_pages_disposed_only_by_fake_poweroff=True,fixture_sha256=sha(fixture.encode()),
    files={name:sha((HERE/name).read_bytes()) for name in ['PlatformBm.c.candidate','firmware-record-functions.inc','samurai-eud-handoff-wire.h','samurai-eud-handoff.c','samurai-eud-handoff.h','test-channel.c','run-tests.py']},
    phone_accessed=False,route_ownership_or_authorization_created=False)
with (HERE/'test-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,groups=10,route_authorized=False)))
