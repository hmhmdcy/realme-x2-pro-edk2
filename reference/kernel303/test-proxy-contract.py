"""Exercise the generated proxy and real worker under QEMU with mapped FDs."""
from pathlib import Path
import hashlib, json, os, re, shutil, signal, subprocess
import host
HERE = Path(__file__).resolve().parent
SDK = Path('/home/cy122/x2pro-linux/libcamera214-root')
tree = '/work/libcamera299-inline'
stage = SDK / 'private/camss303-contract'
shutil.copyfile(HERE / 'ipa-proxy-contract.cpp', stage / 'proxy-contract.cpp')
q = subprocess.run(['chroot', str(SDK), '/usr/bin/g++', '-std=c++20', '-O0', '-Wall', '-Wextra', '-Werror', '-DLIBCAMERA_BASE_PRIVATE',
 '-I' + tree + '/include', '-I' + tree + '/output/include', '/private/camss303-contract/proxy-contract.cpp',
 '-L' + tree + '/output/src/libcamera', '-L' + tree + '/output/src/libcamera/base', '-Wl,-rpath-link,' + tree + '/output/src/libcamera/base',
 '-lcamera', '-lcamera-base', '-ldl', '-pthread', '-o', '/private/camss303-contract/proxy-contract'], capture_output=True, timeout=180)
(host.PRIVATE / 'proxy-contract-compile-private.log').write_bytes(q.stdout + q.stderr)
assert q.returncode == 0, q.stderr.decode()
results = []
isolated_environment_limited = False
for mode in ['threaded', 'isolated']:
    attempt = 1
    while (host.PRIVATE / f'proxy-{mode}-r{attempt}-private.log').exists(): attempt += 1
    logfile = host.PRIVATE / f'proxy-{mode}-r{attempt}-private.log'
    with logfile.open('xb') as output:
     q = subprocess.Popen(['chroot', str(SDK), '/usr/bin/env',
     'LD_LIBRARY_PATH=' + tree + '/output/src/libcamera:' + tree + '/output/src/libcamera/base',
     'LIBCAMERA_IPA_PROXY_PATH=' + tree + '/output/src/libcamera/proxy/worker',
     '/private/camss303-contract/proxy-contract', tree + '/output/src/ipa/camss-vfe/ipa_camss_vfe.so',
     mode, '/private/camss303-contract/ae.yaml'], stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
     try: q.wait(timeout=60)
     except subprocess.TimeoutExpired:
      os.killpg(q.pid, signal.SIGKILL); q.wait()
    raw = logfile.read_bytes()
    if mode == 'isolated': isolated_environment_limited = b'Failed to fork: Function not implemented' in raw
    print(mode, q.returncode, raw.decode()[-3500:])
    model = re.search(rb'AE_MODEL_PASS frames=(\d+) proposals=(\d+) held=(\d+)', raw)
    results.append(dict(mode=mode, exit_code=q.returncode, ae_model_pass=model is not None,
                        frames=int(model[1]) if model else 0, proposals=int(model[2]) if model else 0))
report = dict(stage=303, hardware_verified=False, actual_generated_proxy_and_worker=results[1]['ae_model_pass'], results=results,
              passed=all(r['exit_code'] == 0 and r['ae_model_pass'] for r in results),
              threaded_passed=results[0]['exit_code'] == 0 and results[0]['ae_model_pass'],
              isolated_worker_started=results[1]['ae_model_pass'],
              isolated_environment_limited=isolated_environment_limited,
              source_sha256=hashlib.sha256((HERE / 'ipa-proxy-contract.cpp').read_bytes()).hexdigest())
(HERE / 'proxy-contract-validation.json').write_text(json.dumps(report, indent=2) + '\n')
assert report['threaded_passed'] and (report['passed'] or report['isolated_environment_limited'])
