"""Extract only changed scheduler integration; run six new userspace C groups."""
from pathlib import Path
import hashlib, json, re, subprocess, sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
BASE = HERE.parent / 'thermal-bands-candidate'
OUT = Path('E:/edk2-samurai-out/charging-session-20261023/charger-reattach-observation-tests-02')
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def function(text, name):
    start = re.search(r'^static (?:void|int) ' + re.escape(name) + r'\(', text, re.M).start()
    opening = text.index('{', start); depth = 1; end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}'); end += 1
    return text[start:end] + '\n'


def linux(path):
    text = str(path.resolve()).replace('\\', '/')
    if re.match(r'^[A-Za-z]:/', text): return '/mnt/' + text[0].lower() + text[2:]
    return text


def main():
    base = (BASE / 'samurai-mp2650.c').read_bytes()
    current = (HERE / 'samurai-mp2650.c').read_bytes()
    reuse = json.loads((HERE / 'source-reuse.json').read_bytes())
    assert sha(base) == reuse['base_sha256'] == 'ed2e1d4d96ea4f2d55b514288b0e8da1d731864d385944d02a105d41b03a144c'
    assert sha(current) == reuse['candidate_sha256']
    reverse = current.decode()
    for change in reversed(reuse['changes']):
        assert reverse.count(change['new']) == 1
        reverse = reverse.replace(change['new'], change['old'])
    assert reverse.encode() == base
    text = current.decode().replace('\r\n', '\n')
    for name, output in [('sm_poll', 'actual-poll.inc'), ('sm_supply_changed', 'actual-notifier.inc')]:
        (HERE / output).write_bytes(function(text, name).encode())
    source = re.search(r'\tsource = c->sample.online[^\n]*\n\tsm_reattach_source[^\n]*\n', text)
    assert source
    (HERE / 'actual-source.inc').write_bytes(source[0].encode())
    oldtext = base.decode().replace('\r\n', '\n')
    names = re.findall(r'^static (?:void|int) ([a-zA-Z_][a-zA-Z_0-9]*)\(', oldtext, re.M)
    unchanged = {name: sha(function(oldtext, name).encode()) for name in names
                 if name not in ('sm_step_locked', 'sm_poll') and function(oldtext, name) == function(text, name)}
    assert all(name in unchanged for name in ['sm_supply_changed', 'sm_cleanup', 'sm_suspend', 'sm_resume'])
    assert not OUT.exists(), 'one unique offline fixture output already exists; inspect original only'
    OUT.mkdir(parents=True)
    tested = ['reattach-observation.h', 'samurai-mp2650.c', 'source-reuse.json', 'test-observation.c',
              'test-observation.py', 'actual-poll.inc', 'actual-source.inc', 'actual-notifier.inc']
    result = {'passed': False, 'scope': 'six new actual helper/poll/source/notifier/timing groups; fake OS and IO boundaries',
              'tested_files': {name: sha((HERE / name).read_bytes()) for name in tested},
              'reused_headers': {name: sha((BASE / name).read_bytes()) for name in ['oem-full-cycle.h', 'charge-cycle.h']},
              'unchanged_actual_functions': unchanged,
              'exact_base_recovered_by_four_reverse_replacements': True,
              'device_SDK_storageguard_kernel_module_build': False, 'old_suites_rerun': False, 'children': []}
    try:
        binary = OUT / 'test-observation'
        commands = [
            ['wsl.exe', '-d', 'Ubuntu', '-u', 'root', '--', 'gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
             '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', linux(HERE / 'test-observation.c'), '-o', linux(binary)],
            ['wsl.exe', '-d', 'Ubuntu', '-u', 'root', '--', linux(binary)]]
        for index, argv in enumerate(commands):
            child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = child.communicate()
            row = {'argv': argv, 'owned_host_pid': child.pid, 'terminal': True, 'returncode': child.returncode,
                   'stdout': stdout.decode(errors='replace'), 'stderr': stderr.decode(errors='replace')}
            result['children'].append(row)
            (OUT / ('compile' if index == 0 else 'run')).with_suffix('.stdout.inc').write_bytes(stdout)
            (OUT / ('compile' if index == 0 else 'run')).with_suffix('.stderr.inc').write_bytes(stderr)
            assert child.returncode == 0, 'original offline fixture child failed'
        result['groups_passed'] = result['children'][1]['stdout'].count('ok ')
        assert result['groups_passed'] == 6
        result['passed'] = True
    finally:
        (HERE / 'test-result.json').write_text(json.dumps(result, indent=2) + '\n')
        (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'groups': 6,
                      'original_child_pids': [c['owned_host_pid'] for c in result['children']],
                      'returncodes': [c['returncode'] for c in result['children']],
                      'actual_device_or_kernel_build': False}))


if __name__ == '__main__': main()
