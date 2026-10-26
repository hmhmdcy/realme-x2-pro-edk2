"""One private Image501 LoadOptions BDS build. Default read-only; no firmware or device."""
from pathlib import Path
import hashlib, importlib.util, json, os, re, shlex, shutil, struct, subprocess, sys, traceback

sys.dont_write_bytecode = True
own = Path(__file__).resolve().parent
base_path = own.parent/'eud-bds-baseline-relink/run-baseline.py'
assert hashlib.sha256(base_path.read_bytes()).hexdigest() == 'ad66353d080dd9bdffa9c26d7fa00823730ade884a9e89ebd564fd90cd006667'
spec = importlib.util.spec_from_file_location('baseline_helpers',base_path)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)  # definitions only; __main__ entry is not invoked
sha, write, files = base.sha, base.write, base.files
repo, bds, survey = base.repo, base.module, base.survey
platform = repo/'workspace/Build/samurai/RELEASE_GCC5/AARCH64/Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBootManagerLib'
source = repo/'Platform/RenegadePkg/Library/PlatformBootManagerLib'
candidate = own/'PlatformBm.c.candidate'
candidate_sha = 'cfae4eef298d751b41b11e326c32f9330ecfc3d55b87b53cf45d1087d44ffd21'
original = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-bds-r2-private-01')
private = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/gauge-image501-bds-private-01')
r2_receipt = own.parent/'eud-bds-r2-build/result.json'
assert sha(r2_receipt.read_bytes()) == '69241e6c22ea0daf10570a7745a30fdfab93f361073bb565cf22ecc3d5c66231'
r2 = json.loads(r2_receipt.read_bytes()); assert r2['passed']
copies = [(private/'source',source),(private/'PlatformBootManagerLib',platform),(private/'BdsDxe',bds)]
archive = platform/'OUTPUT/PlatformBootManagerLib.lib'
platform_object = platform/'OUTPUT/PlatformBm.obj'
def ar_members(data):
    assert data[:8] == b'!<arch>\n'
    offset, result = 8, []
    while offset < len(data):
        head = data[offset:offset+60]
        assert len(head) == 60 and head[58:] == b'`\n'
        size = int(head[48:58]); body = data[offset+60:offset+60+size]
        assert len(body) == size
        result.append({'name':head[:16].decode().strip(),'bytes':size,'sha256':sha(body)})
        offset += 60 + size + size%2
    assert offset == len(data)
    return result
def mounts():
    value = base.mount_state()
    value['targets'] = {str(p):{'inode':p.stat().st_ino,'device':p.stat().st_dev} for _,p in copies}
    return value
def command(module, rule, target=None):
    variables = {'ARCHCC_FLAGS':'','SLINK_FLAGS':'','EDK_TOOLS_PATH':str(repo/'Common/edk2/BaseTools')}
    for line in (module/'GNUmakefile').read_text().splitlines():
        match = re.fullmatch(r'([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*)',line)
        if match: variables[match[1]] = match[2]
    for _ in range(20):
        if '$(' not in rule: break
        def expand(match):
            assert match[1] in variables, 'unresolved variable '+match[1]
            return variables[match[1]]
        rule = re.sub(r'\$\(([^)]+)\)',expand,rule)
    if target is not None: rule = rule.replace('$@',str(target))
    assert '$' not in rule and not any(c in rule for c in ['\n',';','|'])
    return shlex.split(rule)
def pe_receipt(data):
    assert data[:2] == b'MZ'
    pe = struct.unpack_from('<I',data,0x3c)[0]
    assert data[pe:pe+4] == b'PE\0\0'
    machine, count = struct.unpack_from('<HH',data,pe+4)
    optional_size = struct.unpack_from('<H',data,pe+20)[0]
    opt = pe+24
    assert machine == 0xaa64 and 0<count<32 and optional_size >= 240
    assert struct.unpack_from('<H',data,opt)[0] == 0x20b
    entry = struct.unpack_from('<I',data,opt+16)[0]
    section_alignment,file_alignment = struct.unpack_from('<II',data,opt+32)
    image_size,headers_size = struct.unpack_from('<II',data,opt+56)
    subsystem = struct.unpack_from('<H',data,opt+68)[0]
    assert subsystem == 11 and section_alignment == file_alignment == 0x1000
    assert headers_size <= len(data) and headers_size % file_alignment == 0
    assert image_size % section_alignment == 0
    sections=[]
    for i in range(count):
        at=opt+optional_size+i*40
        name=data[at:at+8].rstrip(b'\0').decode('ascii')
        virtual_size,rva,raw_size,raw_offset=struct.unpack_from('<IIII',data,at+8)
        flags=struct.unpack_from('<I',data,at+36)[0]
        assert rva % section_alignment == 0 and raw_offset % file_alignment == 0
        assert raw_offset+raw_size <= len(data) and rva+virtual_size <= image_size
        sections.append({'name':name,'rva':rva,'virtual_size':virtual_size,'raw_offset':raw_offset,'raw_size':raw_size,'flags':flags})
    assert any(s['rva'] <= entry < s['rva']+s['virtual_size'] and s['flags'] & 0x20000000 for s in sections)
    reloc_rva,reloc_size=struct.unpack_from('<II',data,opt+112+5*8)
    assert reloc_rva and reloc_size and any(s['rva'] <= reloc_rva and reloc_rva+reloc_size <= s['rva']+s['virtual_size'] for s in sections)
    assert b'[SAMURAI-EUD-OFF]' in data
    assert str(bds/'DEBUG/BdsDxe.dll').encode()+b'\0' in data
    return {'machine':hex(machine),'optional_magic':'0x20b','subsystem':subsystem,'entry_rva':entry,
            'image_size':image_size,'headers_size':headers_size,'sections':sections,
            'relocation_directory':{'rva':reloc_rva,'bytes':reloc_size},
            'R2_debug_marker_present':True,'original_ELF_path_present':True}

def child():
    result={'passed':False,'commands':[],'binds':[]}
    try:
        request=json.loads((private/'request.json').read_text())
        result['namespace']=os.readlink('/proc/self/ns/mnt')
        result['parent_namespace']=request['parent_namespace']
        assert result['namespace'] != result['parent_namespace']
        raw=Path('/proc/self/mountinfo').read_text()
        assert not any(w.startswith(('shared:','master:','propagate_from:')) for l in raw.splitlines() for w in l.split()[6:l.split().index('-')])
        result['all_mounts_private_before_bind']=True
        (private/'mountinfo-before-bind.txt').write_text(raw)
        write(private/'child-receipt.json',result)
        for clone,target in copies:
            done=subprocess.run(['/usr/bin/mount','--bind',str(clone),str(target)],capture_output=True,text=True)
            result['binds'].append({'source':str(clone),'target':str(target),'returncode':done.returncode,'stderr':done.stderr})
            assert done.returncode == 0
            assert clone.stat().st_ino == target.stat().st_ino and clone.stat().st_dev == target.stat().st_dev
        (private/'mountinfo-after-bind.txt').write_text(Path('/proc/self/mountinfo').read_text())
        assert sha((source/'PlatformBm.c').read_bytes()) == candidate_sha
        env=dict(os.environ,PATH='/usr/bin:/bin',TMPDIR=str(private/'tmp'))
        for key in ['GCC_EXEC_PREFIX','COMPILER_PATH','LIBRARY_PATH']:env.pop(key,None)
        plines=(platform/'GNUmakefile').read_text().splitlines()
        blines=(bds/'GNUmakefile').read_text().splitlines()
        stages=[('compile',platform,next(l.strip() for l in plines if l.startswith('\t"$(CC)" $(DEPS_FLAGS)')),'/usr/bin/aarch64-linux-gnu-gcc'),
                ('archive',platform,next(l.strip() for l in plines if l.startswith('\t"$(SLINK)" cr ')),'/usr/bin/aarch64-linux-gnu-gcc-ar'),
                ('link',bds,next(l.strip() for l in blines if l.startswith('\t"$(DLINK)" -o ')),'/usr/bin/aarch64-linux-gnu-gcc'),
                ('GenFw',bds,next(l.strip() for l in blines if l.startswith('\t"$(GENFW)" -e ')),str(repo/'Common/edk2/BaseTools/Source/C/bin/GenFw'))]
        for name,cwd,rule,tool in stages:
            if name == 'archive':
                # Original make rule removes then recreates this single-object archive.
                assert ar_members(archive.read_bytes()) == request['original_archive_members']
                archive.unlink()  # child bind points exclusively to the private copied library
            argv=command(cwd,rule,platform_object if name=='compile' else None);argv[0]=tool
            entry={'stage':name,'original_cached_rule':rule,'argv':argv,'cwd':str(cwd)}
            result['commands'].append(entry);write(private/'child-receipt.json',result)
            with (private/(name+'.stdout')).open('wb') as stdout,(private/(name+'.stderr')).open('wb') as stderr:
                done=subprocess.run(argv,cwd=cwd,env=env,stdout=stdout,stderr=stderr,timeout=120)
            entry['returncode']=done.returncode;write(private/'child-receipt.json',result)
            assert done.returncode == 0,name+' failed'
        result['source_sha256']=sha((source/'PlatformBm.c').read_bytes())
        result['archive_members']=ar_members(archive.read_bytes())
        expected=[m for m in result['archive_members'] if m['name'] != '/']
        assert len(expected)==1 and expected[0]['name']=='PlatformBm.obj/'
        assert expected[0]['sha256']==sha(platform_object.read_bytes())
        result['libraries_after']=[dict(path=x['path'],sha256=sha(Path(x['path']).read_bytes())) for x in survey['libraries']]
        changed=[x['path'] for x,y in zip(result['libraries_after'],r2['child']['libraries_after']) if x['sha256']!=y['sha256']]
        assert changed == [str(archive)],'unexpected library changes'
        result['changed_library_paths']=changed
        result['passed']=True
    except BaseException as exc:
        result['error']=repr(exc);result['traceback']=traceback.format_exc()
    finally:write(private/'child-receipt.json',result)
    return 0 if result['passed'] else 1

def parent():
    assert not private.exists(),'unique directory exists; no replay'
    assert sha(candidate.read_bytes())==candidate_sha
    baseline=json.loads((own.parent/'eud-bds-baseline-relink/result.json').read_text())
    assert baseline['passed'] and baseline['EFI_equals_cached_and_actual_a30']
    original_members=ar_members((original/'PlatformBootManagerLib/OUTPUT/PlatformBootManagerLib.lib').read_bytes())
    assert [m['name'] for m in original_members] == ['/','PlatformBm.obj/']
    assert original_members[1]['sha256']==sha((original/'PlatformBootManagerLib/OUTPUT/PlatformBm.obj').read_bytes())
    paths=[Path(x['path']) for field in ['inputs','libraries','tools','compiler_resources','PlatformBm_compile_dependency_current_hashes'] for x in survey[field]]
    paths += [p for _,target in copies for p in target.rglob('*') if p.is_file()]
    paths += [p for p in original.rglob('*') if p.is_file()]
    paths += [candidate,r2_receipt,Path(__file__).resolve()]
    paths += [Path('/usr/bin')/name for name in ['aarch64-linux-gnu-ar','aarch64-linux-gnu-as','aarch64-linux-gnu-nm','unshare','mount']]
    before,before_mount=files(paths),mounts()
    for field in ['inputs','libraries','tools','compiler_resources','PlatformBm_compile_dependency_current_hashes']:
        for value in survey[field]:assert before[value['path']]['sha256']==value['sha256'],'survey input changed '+value['path']
    private.mkdir(parents=True);(private/'tmp').mkdir();(private/'original').mkdir()
    write(private/'parent-before.json',{'files':before,'mount':before_mount})
    result={'passed':False,'scope':'unpackaged undeployed Image501 LoadOptions-only BDS candidate','private_directory':str(private),
            'candidate_source_sha256':candidate_sha,'base_R2_source_sha256':'c1ce63b3cc8df1c44b5351f53d15294505df919915fa8773636054305617cee8','LoadOptions_parameter':'bq27xxx_battery.samurai_instant_current=1','baseline_result_sha256':sha((own.parent/'eud-bds-baseline-relink/result.json').read_bytes()),
            'original_archive_members':original_members,'make_or_AutoGen_run':False,'unrelated_libraries_compiled':False,
            'firmware_or_FD_FV_boot_packed':False,'device_SDK_Git_accessed':False}
    result['host_linux_pid']=os.getpid()
    print(json.dumps({'started':True,'host_linux_pid':os.getpid(),'private_directory':str(private)}),flush=True)
    try:
        for clone,target in copies:
            cached = original/clone.name
            shutil.copytree(cached,clone,copy_function=shutil.copy2)
            assert {str(p.relative_to(cached)):sha(p.read_bytes()) for p in cached.rglob('*') if p.is_file()} == {str(p.relative_to(clone)):sha(p.read_bytes()) for p in clone.rglob('*') if p.is_file()}
        shutil.copy2(candidate,private/'source/PlatformBm.c')
        for path in [archive,platform_object,bds/'DEBUG/BdsDxe.dll',bds/'OUTPUT/BdsDxe.efi']:
            cached = original/('PlatformBootManagerLib' if path in [archive,platform_object] else 'BdsDxe')/path.relative_to(platform if path in [archive,platform_object] else bds)
            shutil.copy2(cached,private/'original'/path.name)
        write(private/'request.json',{'parent_namespace':before_mount['namespace'],'original_archive_members':original_members})
        argv=['/usr/bin/unshare','--mount','--propagation','private','--fork',sys.executable,str(Path(__file__).resolve()),'--child']
        result['unshare_argv']=argv
        with (private/'unshare.stdout').open('wb') as stdout,(private/'unshare.stderr').open('wb') as stderr:
            done=subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=600)
        result['unshare_returncode']=done.returncode
        assert done.returncode == 0,'child failed; retain evidence and stop'
        result['child']=json.loads((private/'child-receipt.json').read_text())
        assert result['child']['passed']
        new_efi=(private/'BdsDxe/OUTPUT/BdsDxe.efi').read_bytes()
        result['PE32_plus']=pe_receipt(new_efi)
        commandline=b'console=tty0 loglevel=7 ignore_loglevel panic=15 clk_ignore_unused pd_ignore_unused regulator_ignore_unused bq27xxx_battery.samurai_instant_current=1'.decode()
        assert commandline.encode('utf-16-le')+b'\0\0' in new_efi
        result['exact_LoadOptions_in_actual_EFI']=True
        result['artifacts']=files([private/'original'/n for n in ['PlatformBootManagerLib.lib','PlatformBm.obj','BdsDxe.dll','BdsDxe.efi']]+[private/'PlatformBootManagerLib/OUTPUT'/n for n in ['PlatformBootManagerLib.lib','PlatformBm.obj']]+[private/'BdsDxe/DEBUG/BdsDxe.dll',private/'BdsDxe/OUTPUT/BdsDxe.efi'])
        assert new_efi != (private/'original/BdsDxe.efi').read_bytes()
        assert sha((private/'source/PlatformBm.c').read_bytes())==candidate_sha
        result['passed']=True
    except BaseException as exc:
        result['error']=repr(exc);result['traceback']=traceback.format_exc()
    finally:
        after,after_mount=files(paths),mounts();write(private/'parent-after.json',{'files':after,'mount':after_mount})
        result['parent_file_count']=len(before);result['parent_files_unchanged']=before==after
        result['parent_mount_state_unchanged']=before_mount==after_mount
        result['passed'] &= result['parent_files_unchanged'] and result['parent_mount_state_unchanged']
        result['evidence']={p.name:sha(p.read_bytes()) for p in private.iterdir() if p.is_file()}
        write(private/'result.json',result);write(own/'result.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['child','traceback','artifacts']},indent=2))
    return 0 if result['passed'] else 1

if __name__=='__main__':
    if sys.argv[1:] == ['--child']: raise SystemExit(child())
    elif sys.argv[1:] == ['--execute-bds']: raise SystemExit(parent())
    elif sys.argv[1:] in [[], ['--check-local']]:
        assert sha(candidate.read_bytes()) == candidate_sha
        original_source=(original/'source/PlatformBm.c').read_bytes()
        assert sha(original_source)=='c1ce63b3cc8df1c44b5351f53d15294505df919915fa8773636054305617cee8'
        prior=b'console=tty0 loglevel=7 ignore_loglevel panic=15 clk_ignore_unused pd_ignore_unused regulator_ignore_unused'
        assert original_source.count(prior)==1 and candidate.read_bytes()==original_source.replace(prior,prior+b' bq27xxx_battery.samurai_instant_current=1')
        print(json.dumps({'checked':True,'build_started':False,'unique_private_exists':private.exists(),'candidate_source_sha256':candidate_sha}))
    else: raise SystemExit('default --check-local; explicit --execute-bds only')
