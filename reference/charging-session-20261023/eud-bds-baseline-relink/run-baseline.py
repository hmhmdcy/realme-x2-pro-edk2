"""One private baseline relink only. No make, AutoGen, library compile or firmware packing."""
from pathlib import Path
import hashlib, json, os, re, shlex, shutil, subprocess, sys, traceback

workspace = Path('/mnt/e/RealmeX2Pro edk2')
own = workspace/'reference/charging-session-20261023/eud-bds-baseline-relink'
survey_dir = own.parent/'eud-boot-policy-r2-independent-review'
survey = json.loads((survey_dir/'cache-survey-result.json').read_text())
repo = Path('/home/cy122/edk2-samurai/repo')
module = repo/'workspace/Build/samurai/RELEASE_GCC5/AARCH64/MdeModulePkg/Universal/BdsDxe/BdsDxe'
private = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-bds-baseline-private-01')
copy = private/'BdsDxe'
sha = lambda b: hashlib.sha256(b).hexdigest()
def write(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')
def files(paths):
    return {str(p): {'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size,
                     'mtime_ns': p.stat().st_mtime_ns} for p in sorted(set(paths))}
def mount_state():
    raw = Path('/proc/self/mountinfo').read_text()
    relevant = []
    for line in raw.splitlines():
        parts = line.split()
        mountpoint = parts[4].replace('\\040',' ')
        if str(module) == mountpoint or str(module).startswith(mountpoint.rstrip('/')+'/'):
            relevant.append(line)
    st = module.stat()
    return {'namespace': os.readlink('/proc/self/ns/mnt'), 'module_mount_chain': relevant,
            'module_inode': st.st_ino, 'module_dev': st.st_dev, 'all_mountinfo_sha256': sha(raw.encode())}
def resolve_command(rule):
    variables = {'ARCHCC_FLAGS':'', 'EDK_TOOLS_PATH':str(repo/'Common/edk2/BaseTools')}
    for line in (module/'GNUmakefile').read_text().splitlines():
        match = re.fullmatch(r'([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*)', line)
        if match:
            variables[match[1]] = match[2]
    def replace(match):
        key = match.group(1)
        if key not in variables:
            raise RuntimeError('unresolved make variable: '+key)
        return variables[key]
    expanded = rule
    for _ in range(20):
        if '$(' not in expanded:
            break
        expanded = re.sub(r'\$\(([^)]+)\)', replace, expanded)
    assert '$' not in expanded and not any(c in expanded for c in ['\n',';','|'])
    return shlex.split(expanded)

def child():
    receipt = {'passed':False, 'commands':[], 'bind_performed':False}
    try:
        request = json.loads((private/'request.json').read_text())
        receipt['namespace'] = os.readlink('/proc/self/ns/mnt')
        receipt['parent_namespace'] = request['parent_namespace']
        assert receipt['namespace'] != receipt['parent_namespace'], 'mount namespace not distinct'
        mountinfo = Path('/proc/self/mountinfo').read_text()
        bad = [l for l in mountinfo.splitlines()
               if any(w.startswith(('shared:','master:','propagate_from:')) for w in l.split()[6:l.split().index('-')])]
        receipt['all_mounts_private_before_bind'] = not bad
        receipt['propagation_evidence'] = mountinfo
        assert not bad, 'child mounts still propagate'
        write(private/'child-receipt.json',receipt)
        bound = subprocess.run(['/usr/bin/mount','--bind',str(copy),str(module)],capture_output=True,text=True)
        receipt['bind_returncode'] = bound.returncode
        receipt['bind_stderr'] = bound.stderr
        assert bound.returncode == 0, 'private bind failed'
        receipt['bind_performed'] = True
        assert module.stat().st_ino == copy.stat().st_ino and module.stat().st_dev == copy.stat().st_dev
        receipt['mountinfo_after_bind'] = Path('/proc/self/mountinfo').read_text()
        env = dict(os.environ, PATH='/usr/bin:/bin', TMPDIR=str(private/'tmp'))
        env.pop('GCC_EXEC_PREFIX',None)
        env.pop('COMPILER_PATH',None)
        env.pop('LIBRARY_PATH',None)
        lines = (module/'GNUmakefile').read_text().splitlines()
        link_rule = next(l.strip() for l in lines if l.startswith('\t"$(DLINK)" -o '))
        genfw_rule = next(l.strip() for l in lines if l.startswith('\t"$(GENFW)" -e '))
        for name, rule in [('link',link_rule),('GenFw',genfw_rule)]:
            argv = resolve_command(rule)
            argv[0] = '/usr/bin/aarch64-linux-gnu-gcc' if name=='link' else str(repo/'Common/edk2/BaseTools/Source/C/bin/GenFw')
            entry = {'stage':name,'original_cached_rule':rule,'argv':argv,'cwd':str(module)}
            receipt['commands'].append(entry)
            write(private/'child-receipt.json',receipt)
            with (private/(name+'.stdout')).open('wb') as stdout, (private/(name+'.stderr')).open('wb') as stderr:
                done = subprocess.run(argv,cwd=module,env=env,stdout=stdout,stderr=stderr,timeout=120)
            entry['returncode'] = done.returncode
            write(private/'child-receipt.json',receipt)
            assert done.returncode == 0, name+' failed'
        receipt['passed'] = True
    except BaseException as exc:
        receipt['error'] = repr(exc)
        receipt['traceback'] = traceback.format_exc()
    finally:
        write(private/'child-receipt.json',receipt)
    return 0 if receipt['passed'] else 1

def parent():
    assert not private.exists(), 'unique baseline directory already exists; do not replay'
    private.mkdir(parents=True)
    (private/'tmp').mkdir()
    paths = [Path(x['path']) for field in ['inputs','libraries','tools','compiler_resources',
             'PlatformBm_compile_dependency_current_hashes'] for x in survey[field]]
    paths += [p for p in module.rglob('*') if p.is_file()]
    paths += [p for p in (repo/'Common/edk2/MdeModulePkg/Universal/BdsDxe').rglob('*') if p.is_file()]
    before, mounts_before = files(paths), mount_state()
    write(private/'parent-before.json',{'files':before,'mount':mounts_before})
    receipt = {'passed':False,'private_directory':str(private),'baseline_only':True,
               'R2_compiled':False,'firmware_packed':False,'device_or_SDK_accessed':False}
    try:
        for field in ['inputs','libraries','tools','compiler_resources','PlatformBm_compile_dependency_current_hashes']:
            for item in survey[field]:
                assert before[item['path']]['sha256'] == item['sha256'], 'survey input changed: '+item['path']
        shutil.copytree(module,copy,copy_function=shutil.copy2)
        assert files([p for p in copy.rglob('*') if p.is_file()])
        assert {str(p.relative_to(module)):sha(p.read_bytes()) for p in module.rglob('*') if p.is_file()} == {
            str(p.relative_to(copy)):sha(p.read_bytes()) for p in copy.rglob('*') if p.is_file()}
        write(private/'request.json',{'parent_namespace':mounts_before['namespace'],'module':str(module),'copy':str(copy)})
        argv = ['/usr/bin/unshare','--mount','--propagation','private','--fork',sys.executable,str(Path(__file__).resolve()),'--child']
        receipt['unshare_argv'] = argv
        with (private/'unshare.stdout').open('wb') as stdout, (private/'unshare.stderr').open('wb') as stderr:
            done = subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=300)
        receipt['unshare_returncode'] = done.returncode
        assert done.returncode == 0, 'child stopped; inspect unshare.stderr / child-receipt.json'
        receipt['child'] = json.loads((private/'child-receipt.json').read_text())
        assert receipt['child']['passed']
        actual = (copy/'OUTPUT/BdsDxe.efi').read_bytes()
        expected = (module/'OUTPUT/BdsDxe.efi').read_bytes()
        receipt['EFI_sha256'] = sha(actual)
        receipt['EFI_bytes'] = len(actual)
        receipt['EFI_equals_cached_and_actual_a30'] = actual == expected and sha(actual) == survey['Bds_EFI_sha256']
        receipt['ELF_equals_original'] = (copy/'DEBUG/BdsDxe.dll').read_bytes() == (module/'DEBUG/BdsDxe.dll').read_bytes()
        receipt['ELF_sha256'] = sha((copy/'DEBUG/BdsDxe.dll').read_bytes())
        assert receipt['EFI_equals_cached_and_actual_a30'], 'any EFI byte difference is failure'
        receipt['passed'] = True
    except BaseException as exc:
        receipt['error'] = repr(exc)
        receipt['traceback'] = traceback.format_exc()
    finally:
        after, mounts_after = files(paths), mount_state()
        write(private/'parent-after.json',{'files':after,'mount':mounts_after})
        receipt['parent_file_count'] = len(before)
        receipt['parent_files_unchanged'] = before == after
        receipt['parent_mount_state_unchanged'] = mounts_before == mounts_after
        receipt['passed'] &= receipt['parent_files_unchanged'] and receipt['parent_mount_state_unchanged']
        receipt['evidence'] = {name:sha((private/name).read_bytes()) for name in
            ['parent-before.json','parent-after.json','request.json','child-receipt.json','unshare.stderr'] if (private/name).exists()}
        write(private/'result.json',receipt)
        write(own/'result.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['child','traceback']},indent=2))
    return 0 if receipt['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(child() if sys.argv[1:] == ['--child'] else parent())
