"""One private Image363 baseline; no B, modules, DTBs, packaging or device I/O."""
from pathlib import Path
import gzip, hashlib, importlib.util, json, os, shlex, shutil, stat
import subprocess, sys, time, traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
PLAN = REF/'charging-oem-audit-20261023/gauge-image363-integration-plan'
OUT = Path('/home/cy122/charging-management-20261023/gauge-image363-baseline-01')
VOLUME = Path('/mnt/samurai-full282')
BUILD = VOLUME/'build'
SOURCE = VOLUME/'source354'
PAYLOAD = VOLUME/'input-initramfs363'
TEMP = VOLUME/'tmp'
COMMIT = 'ba61a62293e0f6bc5838c06f2e85e033e3d702a8'
EXPECTED = {
 'Image':'15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468',
 'vmlinux':'8e2bc2bd1de55eb53c58915ec03ae25dc77c9401e137d50fccbdcc173ff4dd96',
 'config':'23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed',
 'bq':'5976585aea3504783ea42601c1a9daa94ed6a1ce137a11c182332194dbf7cb7c',
}
GIT_ENV = {**os.environ, 'GIT_OPTIONAL_LOCKS':'0'}

def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def save(p,obj):
    raw = (json.dumps(obj,indent=2)+'\n').encode()
    with Path(p).open('wb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())

def event(stage,**kw):
    print(json.dumps({'stage':stage,'pid':os.getpid(),**kw}),flush=True)

def namespace():
    return os.readlink('/proc/self/ns/mnt')

def mounts(pid='self'):
    return Path(f'/proc/{pid}/mountinfo').read_text().splitlines()

def inventory(root):
    rows = {}
    for current,dirs,files in os.walk(root,followlinks=False):
        if Path(current) == root and '.git' in dirs:
            dirs.remove('.git')
        for name in sorted(dirs+files):
            p = Path(current)/name; s = p.lstat()
            row = {'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid,
                   'mtime_ns':s.st_mtime_ns}
            if stat.S_ISLNK(s.st_mode): row.update(kind='symlink',target=os.readlink(p))
            elif stat.S_ISREG(s.st_mode): row.update(kind='file',bytes=s.st_size,sha256=sha(p))
            elif stat.S_ISDIR(s.st_mode): row.update(kind='directory')
            else: row.update(kind='special',rdev=s.st_rdev)
            rows[str(p.relative_to(root))] = row
    return rows

def inode_set(root):
    return {(p.lstat().st_dev,p.lstat().st_ino) for p in root.rglob('*') if p.is_file() and not p.is_symlink()}

def command(argv,env=None):
    return subprocess.check_output(argv,env=env,text=True).strip()

def closure():
    link = json.loads((PLAN/'link-inputs.json').read_bytes())
    final = json.loads((PLAN/'final-link-inputs.json').read_bytes())
    rows = {name:sha(BUILD/name) for name in link['members']}
    rows.update({name:sha(BUILD/name) for name in final['libstub_members']})
    for group in [final['final_link_extra'],link['link_cache']]:
        for name,r in group.items():
            if not r.get('missing') and (BUILD/name).is_file(): rows[name] = sha(BUILD/name)
    return rows

def build_environment():
    env = dict(os.environ)
    for n in ['KBUILD_EXTMOD','KBUILD_OUTPUT','KCONFIG_CONFIG','SOURCE_DATE_EPOCH','KBUILD_EXTRA_SYMBOLS',
              'KBUILD_BUILD_VERSION','KBUILD_BUILD_USER','KBUILD_BUILD_HOST','KBUILD_BUILD_TIMESTAMP',
              'KCFLAGS','CFLAGS_KERNEL','CFLAGS_MODULE','LDFLAGS','MAKEFLAGS','MFLAGS','LOCALVERSION']:
        env.pop(n,None)
    env.update(PATH='/home/cy122/.rustup/toolchains/nightly-x86_64-unknown-linux-gnu/bin:/home/cy122/.cargo/bin:'+env['PATH'],
        RUSTUP_HOME='/home/cy122/.rustup',KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai',
        KBUILD_BUILD_VERSION='363',KBUILD_BUILD_TIMESTAMP='Tue Oct 20 03:03:47 UTC 2026',TMPDIR=str(TEMP))
    return env

def child(parent_pid,parent_ns,parent_mounts_sha):
    assert os.getuid() == 0 and namespace() != parent_ns
    subprocess.run(['mount','--make-rprivate','/'],check=True)
    private_lines = mounts()
    assert not any(any(t.startswith(('shared:','master:','propagate_from:')) for t in line.split()[6:line.split().index('-')]) for line in private_lines)
    assert hashlib.sha256(('\n'.join(mounts(parent_pid))+'\n').encode()).hexdigest() == parent_mounts_sha
    mapped = []
    for target,name in [(SOURCE,'source354'),(BUILD,'build'),(PAYLOAD,'input-initramfs363'),(TEMP,'tmp')]:
        private = OUT/name
        subprocess.run(['mount','--bind',str(private),str(target)],check=True)
        assert os.path.samefile(private,target)
        mapped.append({'target':str(target),'private':str(private),'stat_device':target.stat().st_dev,'inode':target.stat().st_ino})
    assert hashlib.sha256(('\n'.join(mounts(parent_pid))+'\n').encode()).hexdigest() == parent_mounts_sha
    proof = {'parent_namespace':parent_ns,'child_namespace':namespace(),'recursive_private_verified':True,
             'four_bindings':mapped,'parent_mountinfo_unchanged_while_bound':True,
             'child_mountinfo':mounts()}
    save(OUT/'namespace-proof.json',proof)
    event('namespace-isolated',bindings=4,namespace=namespace())
    env = build_environment()
    expected_config = (OUT/'config363-original').read_bytes()
    assert hashlib.sha256(expected_config).hexdigest() == EXPECTED['config']
    (BUILD/'.config').write_bytes(expected_config)
    original = json.loads((OUT/'closure-original.json').read_bytes())
    bq = BUILD/'drivers/power/supply/bq27xxx_battery.o'
    commands = []
    phases = []
    state = {'worker_pid':os.getpid(),'parent_pid':int(parent_pid),'terminal':False,'private_output':str(OUT)}

    def run(name,argv,cwd=BUILD):
        start = time.monotonic(); log = OUT/(name+'.log')
        commands.append({'phase':name,'argv':argv,'cwd':str(cwd)})
        with log.open('xb') as out:
            proc = subprocess.Popen(argv,cwd=cwd,env=env,stdout=out,stderr=subprocess.STDOUT)
            state.update(phase=name,child_pid=proc.pid,argv=argv)
            save(OUT/'child-state.json',state)
            event(name,child_pid=proc.pid,started=True)
            ret = proc.wait(); out.flush(); os.fsync(out.fileno())
        row = {'phase':name,'returncode':ret,'seconds':round(time.monotonic()-start,2),'log_sha256':sha(log)}
        phases.append(row); save(OUT/'commands.json',commands); save(OUT/'phases.json',phases)
        event(name,returncode=ret,seconds=row['seconds'])
        assert ret == 0,(name,ret)

    try:
        base = ['make','-C',str(SOURCE),'O='+str(BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
                'LOCALVERSION=+','W=1','V=1','-j4']
        run('configure-prepare',base+['olddefconfig','prepare'])
        assert (BUILD/'.config').read_bytes() == expected_config,'Original CONFIG not reproduced'
        assert (BUILD/'include/config/kernel.release').read_text().strip() == '7.3.0-rc6-rmx1931-samurai-k363+'
        cmd = (BUILD/'drivers/power/supply/.bq27xxx_battery.o.cmd').read_text().splitlines()[0]
        assert cmd.startswith('savedcmd_drivers/power/supply/bq27xxx_battery.o := ')
        argv = shlex.split(cmd.split(' := ',1)[1])
        assert argv[0] == 'aarch64-linux-gnu-gcc'
        assert argv[-1] == str(SOURCE/'drivers/power/supply/bq27xxx_battery.c')
        assert argv[argv.index('-o')+1] == 'drivers/power/supply/bq27xxx_battery.o'
        run('original-bq-repeat',argv)
        assert sha(bq) == EXPECTED['bq'],'Original bq object did not reproduce'
        event('bq-byte-exact',sha256=sha(bq))
        run('image-baseline',base+['Image'])
        after = closure()
        leaves = json.loads((PLAN/'link-inputs.json').read_bytes())['members']
        stub = json.loads((PLAN/'final-link-inputs.json').read_bytes())['libstub_members']
        delta = [{'path':n,'before':original.get(n),'after':after.get(n)} for n in sorted(original.keys()|after.keys()) if original.get(n) != after.get(n)]
        leaf_delta = [r for r in delta if r['path'] in leaves or r['path'] in stub]
        save(OUT/'actual-link-input-delta.json',delta)
        save(OUT/'actual-leaf-delta.json',leaf_delta)
        save(OUT/'closure-final.json',after)
        output = {'config':sha(BUILD/'.config'),'bq':sha(bq),'vmlinux':sha(BUILD/'vmlinux'),'Image':sha(BUILD/'arch/arm64/boot/Image')}
        result = {'passed':not leaf_delta and output == EXPECTED,'phases':phases,'outputs':output,
                  'expected':EXPECTED,'leaf_changes':leaf_delta,'link_input_changes':delta,
                  'private_initramfs_unchanged':inventory(PAYLOAD) == json.loads((OUT/'initramfs-before.json').read_bytes()),
                  'B_source_copied':False,'modules_or_dtb_target':False,'device_access':False}
        result['passed'] = result['passed'] and result['private_initramfs_unchanged']
        save(OUT/'baseline-build-result.json',result)
        assert result['passed'],'Baseline outputs or leaf inputs differ; stop without B'
        state.update(terminal=True,phase='passed',returncode=0)
        save(OUT/'child-state.json',state)
        event('baseline-byte-exact',outputs=output)
        return 0
    except BaseException as e:
        state.update(terminal=True,phase='failed',returncode=1,error=repr(e))
        save(OUT/'child-state.json',state)
        save(OUT/'commands.json',commands); save(OUT/'phases.json',phases)
        now = closure()
        save(OUT/'failure-link-input-delta.json',[{'path':n,'before':original.get(n),'after':now.get(n)} for n in sorted(original.keys()|now.keys()) if original.get(n)!=now.get(n)])
        raise

def parent():
    assert os.getuid() == 0 and not OUT.exists(),'Private output already exists; no replay'
    spec = importlib.util.spec_from_file_location('original_storage284',REF/'kernel284/storage.py')
    storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
    assert storage.mounted_build() == BUILD
    original_mounts = mounts(); parent_ns = namespace()
    mount_sha = hashlib.sha256(('\n'.join(original_mounts)+'\n').encode()).hexdigest()
    link = json.loads((PLAN/'link-inputs.json').read_bytes())
    for name,row in link['toolchains'].items():
        if row['path']: assert sha(Path(row['path']).resolve()) == row['sha256'],name
    for row in link['rust_toolchains']: assert sha(row['path']) == row['sha256']
    assert sha(BUILD/'arch/arm64/boot/Image') == EXPECTED['Image']
    assert sha(BUILD/'vmlinux') == EXPECTED['vmlinux']
    assert sha(BUILD/'drivers/power/supply/bq27xxx_battery.o') == EXPECTED['bq']
    assert command(['git','-C',str(SOURCE),'rev-parse',COMMIT],GIT_ENV) == COMMIT
    assert not command(['git','-C',str(SOURCE),'diff','--name-only','HEAD'],GIT_ENV)
    index_path = Path(command(['git','-C',str(SOURCE),'rev-parse','--git-path','index'],GIT_ENV))
    if not index_path.is_absolute(): index_path = SOURCE/index_path
    git_before = {'HEAD':command(['git','-C',str(SOURCE),'rev-parse','HEAD'],GIT_ENV),
                  'index_path':str(index_path),'index_sha256':sha(index_path)}
    OUT.mkdir(parents=True)
    save(OUT/'execution.json',{'worker_pid':os.getpid(),'namespace':parent_ns,'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
         'runner_sha256':sha(__file__),'commit':COMMIT,'no_B':True})
    shared_before = {}; shared_after = {}; ret = None
    try:
        event('snapshot-original-inputs',output=str(OUT))
        for name,path in [('build',BUILD),('source354',SOURCE),('input-initramfs363',PAYLOAD)]:
            shared_before[name] = inventory(path)
            save(OUT/(name+'-shared-before.json'),shared_before[name])
        save(OUT/'mountinfo-parent-before.json',original_mounts)
        raw = (BUILD/'arch/arm64/boot/Image').read_bytes()
        a = raw.index(b'IKCFG_ST')+8; b = raw.index(b'IKCFG_ED',a)
        config = gzip.decompress(raw[a:b]); assert hashlib.sha256(config).hexdigest() == EXPECTED['config']
        (OUT/'config363-original').write_bytes(config)
        expected_closure = closure()
        for n,r in link['members'].items(): assert expected_closure[n] == r['sha256'],n
        save(OUT/'closure-original.json',expected_closure)
        event('copy-private-build')
        subprocess.run(['cp','-a','--reflink=auto',str(BUILD),str(OUT/'build')],check=True)
        assert not (inode_set(BUILD) & inode_set(OUT/'build')),'Hardlinked original output'
        assert inventory(OUT/'build') == shared_before['build']
        subprocess.run(['cp','-a','--reflink=auto',str(PAYLOAD),str(OUT/'input-initramfs363')],check=True)
        assert not (inode_set(PAYLOAD) & inode_set(OUT/'input-initramfs363'))
        assert inventory(OUT/'input-initramfs363') == shared_before['input-initramfs363']
        save(OUT/'initramfs-before.json',shared_before['input-initramfs363'])
        (OUT/'tmp').mkdir(mode=stat.S_IMODE(TEMP.stat().st_mode))
        (OUT/'source354').mkdir()
        event('export-fixed-ba61-source')
        archive = subprocess.Popen(['git','-C',str(SOURCE),'archive','--format=tar',COMMIT],stdout=subprocess.PIPE,stderr=(OUT/'archive-stderr.log').open('xb'),env=GIT_ENV)
        extracted = subprocess.run(['tar','-xf','-','-C',str(OUT/'source354')],stdin=archive.stdout)
        archive.stdout.close(); archive_ret = archive.wait()
        assert extracted.returncode == 0 and archive_ret == 0
        entries = subprocess.check_output(['git','-C',str(SOURCE),'ls-tree','-rz',COMMIT],env=GIT_ENV).split(b'\0')
        same_times = 0; different = []
        for entry in entries:
            if not entry: continue
            meta,name = entry.split(b'\t',1); mode,kind,blob = meta.split()
            assert kind == b'blob'
            relative = os.fsdecode(name); dest = OUT/'source354'/relative
            assert not Path(relative).is_absolute() and '..' not in Path(relative).parts
            data = os.readlink(dest).encode() if mode == b'120000' else dest.read_bytes()
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() == blob.decode(),relative
            row = shared_before['source354'].get(relative)
            same = row and ((row['kind']=='symlink' and mode==b'120000' and row['target'].encode()==data) or
                    (row['kind']=='file' and mode!=b'120000' and row['sha256']==hashlib.sha256(data).hexdigest()))
            if same:
                os.utime(dest,ns=(row['mtime_ns'],row['mtime_ns']),follow_symlinks=False); same_times += 1
            else: different.append(relative)
        # Preserve directory mtimes too; directory creation itself cannot force a build.
        for n,r in shared_before['source354'].items():
            p=OUT/'source354'/n
            if r['kind']=='directory' and p.is_dir(): os.utime(p,ns=(r['mtime_ns'],r['mtime_ns']))
        assert not (OUT/'source354/.git').exists()
        save(OUT/'source-export.json',{'commit':COMMIT,'blob_count':len(entries)-1,'blob_hashes_verified':True,
             'mtime_inherited_only_for_identical_blob_count':same_times,'different_or_missing_paths':different,
             'no_shared_inode':not (inode_set(SOURCE) & inode_set(OUT/'source354'))})
        assert (OUT/'build/source').is_symlink() and os.readlink(OUT/'build/source') == str(SOURCE)
        event('private-copies-ready',source_blobs=len(entries)-1,source_different=len(different))
        argv = ['unshare','--mount','--propagation','private',sys.executable,'-B',str(HERE/'run-baseline.py'),
                '--child',str(os.getpid()),parent_ns,mount_sha]
        save(OUT/'namespace-command.json',argv)
        child_process = subprocess.Popen(argv,cwd=OUT)
        event('namespace-child-started',child_pid=child_process.pid)
        save(OUT/'namespace-child-process.json',{'pid':child_process.pid,'argv':argv,'terminal':False})
        ret = child_process.wait()
        save(OUT/'namespace-child-process.json',{'pid':child_process.pid,'argv':argv,'terminal':True,'returncode':ret})
    finally:
        event('verify-original-inputs-unchanged',child_returncode=ret)
        for name,path in [('build',BUILD),('source354',SOURCE),('input-initramfs363',PAYLOAD)]:
            shared_after[name] = inventory(path)
            save(OUT/(name+'-shared-after.json'),shared_after[name])
        unchanged = {name:shared_before.get(name)==rows for name,rows in shared_after.items()}
        git_after = {'HEAD':command(['git','-C',str(SOURCE),'rev-parse','HEAD'],GIT_ENV),
                     'index_path':str(index_path),'index_sha256':sha(index_path)}
        mount_after = mounts()
        save(OUT/'mountinfo-parent-after.json',mount_after)
        result = {'passed':ret==0 and all(unchanged.values()) and mount_after==original_mounts and git_after==git_before,
                  'child_returncode':ret,'parent_namespace_before':parent_ns,'parent_namespace_after':namespace(),
                  'parent_mounts_unchanged':mount_after==original_mounts,'shared_trees_unchanged':unchanged,
                  'git_metadata_before':git_before,'git_metadata_after':git_after,'git_metadata_unchanged':git_before==git_after,
                  'private_output':str(OUT),'runner_sha256':sha(__file__),'source_commit':COMMIT,
                  'B_source_copied':False,'device_access':False,'SDK_access':False,
                  'modules_dtb_install_packaging':False}
        if (OUT/'baseline-build-result.json').is_file():
            result['baseline'] = json.loads((OUT/'baseline-build-result.json').read_bytes())
        if (OUT/'child-state.json').is_file():
            result['child_state'] = json.loads((OUT/'child-state.json').read_bytes())
        save(OUT/'result.json',result)
        save(HERE/'result.json',result)
        event('finished',passed=result['passed'],child_returncode=ret,shared_unchanged=unchanged,
              mounts_unchanged=mount_after==original_mounts)
    return 0 if result['passed'] else 1

if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--child':
        raise SystemExit(child(*sys.argv[2:]))
    assert sys.argv[1:]==['--execute-baseline'],'Explicit --execute-baseline required'
    raise SystemExit(parent())
