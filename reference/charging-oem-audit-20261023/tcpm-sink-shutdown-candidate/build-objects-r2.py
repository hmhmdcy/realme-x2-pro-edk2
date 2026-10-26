"""Compile the affected port object in a private overlay of adopted Image506."""
from pathlib import Path
import hashlib, importlib.util, json, os, re, subprocess, sys, time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('adopted506_build', HERE.parent / 'eud-route-pm-candidate/build-image-r2.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
p, base = m.p, m.base
OUT = Path('/home/cy122/charging-management-20261023/tcpm-sink-shutdown-objects-02')
LAYERS = [OUT.parent/'tcpm-sink-image507-01', OUT.parent/'tcpm-sink-port-object-01', m.OUT, m.PREVIOUS, m.LOWER]
PREFIX = 'drivers/usb/typec/tcpm/qcom/'
CHANGED = json.loads((HERE/'source.json').read_bytes())['sources']
OBJECTS = [PREFIX+n+'.o' for n in ['qcom_pmic_typec', 'qcom_pmic_typec_port', 'qcom_pmic_typec_pdphy', 'qcom_pmic_typec_pdphy_stub', 'qcom_pmic_typec_5v']]

def lower(name, relative):
    for layer in LAYERS:
        q = layer / (name + '-upper') / relative
        if q.exists():
            return q
    return m.BASE / name / relative

def child(parent, ns, mounts):
    assert os.geteuid() == 0 and base.namespace() != ns
    subprocess.run(['mount', '--make-rprivate', '/'], check=True)
    for name, target in [('source354', base.SOURCE), ('build', base.BUILD)]:
        layers = [str(x / (name + '-upper')) for x in LAYERS] + [str(m.BASE / name)]
        options = 'lowerdir=' + ':'.join(layers) + ',upperdir=' + str(OUT / (name + '-upper')) + ',workdir=' + str(OUT / (name + '-work'))
        subprocess.run(['mount', '-t', 'overlay', 'overlay', '-o', options, str(OUT / (name + '-merged'))], check=True)
        subprocess.run(['mount', '--bind', str(OUT / (name + '-merged')), str(target)], check=True)
    subprocess.run(['mount', '--bind', str(m.BASE / 'input-initramfs363'), str(base.PAYLOAD)], check=True)
    subprocess.run(['mount', '-o', 'remount,bind,ro', str(base.PAYLOAD)], check=True)
    subprocess.run(['mount', '--bind', str(OUT / 'tmp'), str(base.TEMP)], check=True)
    assert p.mount_hash(parent) == mounts
    for name, row in CHANGED.items():
        target = base.SOURCE / PREFIX / name
        assert m.sha(target) == row['baseline_sha256']
        target.write_bytes((HERE/name).read_bytes())
        assert m.sha(target) == row['candidate_sha256']
    env = base.build_environment()
    env['KBUILD_BUILD_VERSION'] = '507'
    argv = ['make', '-C', str(base.SOURCE), 'O=' + str(base.BUILD), 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-', 'LOCALVERSION=+', 'W=1', '-j4'] + OBJECTS
    start = time.monotonic()
    with (OUT / 'object.log').open('xb') as log:
        proc = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
        m.save(OUT / 'process.json', dict(process=p.pid_info(proc.pid), argv=argv))
        code = proc.wait()
    diagnostics = [line for line in (OUT / 'object.log').read_text().splitlines() if re.search(r'\b(warning:|error:|undefined reference)', line, re.I)]
    assert code == 0 and not diagnostics, (code, diagnostics)
    m.save(OUT / 'child-result.json', dict(passed=True, returncode=code, seconds=time.monotonic()-start, objects={n:m.sha(base.BUILD/n) for n in OBJECTS}, sources={n:m.sha(base.SOURCE/PREFIX/n) for n in CHANGED}, diagnostics=diagnostics))

def main():
    assert not OUT.exists() and not (HERE / 'build-r2-result.json').exists()
    assert json.loads((m.HERE / 'image-build-r2-result.json').read_bytes())['passed']
    helper = p.load('sink_port_original_storage', ROOT / 'reference/kernel284/storage.py')
    helper.mounted_build()
    assert os.statvfs('/home/cy122').f_bavail * os.statvfs('/home/cy122').f_frsize > 2 * 1024**3
    tracked = [lower('source354', PREFIX+n) for n in CHANGED] + [lower('build', x) for x in ['.config', 'arch/arm64/boot/Image', 'vmlinux.symvers', 'modules.builtin', 'modules.builtin.modinfo']]
    before = {str(q): m.sha(q) for q in tracked}
    ns, mounts = base.namespace(), p.mount_hash()
    OUT.mkdir()
    for name in ['source354-upper', 'source354-work', 'source354-merged', 'build-upper', 'build-work', 'build-merged', 'tmp']:
        (OUT / name).mkdir()
    argv = ['unshare', '--mount', '--propagation', 'private', '--fork', sys.executable, '-B', str(Path(__file__).resolve()), '--child', str(os.getpid()), ns, mounts]
    with (OUT / 'owner.stdout').open('xb') as stdout, (OUT / 'owner.stderr').open('xb') as stderr:
        proc = subprocess.Popen(argv, stdout=stdout, stderr=stderr)
        m.save(OUT / 'owner.json', dict(process=p.pid_info(proc.pid), argv=argv))
        code = proc.wait()
    after = {str(q): m.sha(q) for q in tracked}
    result = dict(passed=code == 0 and before == after and ns == base.namespace() and mounts == p.mount_hash(), returncode=code, parent_inputs_unchanged=before == after, parent_mounts_unchanged=mounts == p.mount_hash(), private_output=str(OUT), phone_accessed=False, installed=False)
    if code == 0:
        result['build'] = json.loads((OUT / 'child-result.json').read_bytes())
    m.save(OUT / 'terminal.json', dict(terminal=True, returncode=code))
    m.save(HERE / 'build-r2-result.json', result)
    print(json.dumps(result), flush=True)
    if code:
        print((OUT / 'owner.stderr').read_text()[-3000:])
    raise SystemExit(0 if result['passed'] else 1)

if __name__ == '__main__':
    if sys.argv[1:2] == ['--child']:
        child(int(sys.argv[2]), sys.argv[3], sys.argv[4])
    else:
        main()
