"""New text integration boundaries; do not rerun old observer/classifier suites."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'protection-query-observer-candidate'
PRIVATE = Path('/home/cy122/charging-management-20261023/protection-evidence-parser-01')
STUBS = Path('/home/cy122/charging-management-20261023/protection-query-observer-tests-r2')
FIXTURE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/window2/packets-private.bin')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    before = {str(p): sha(p) for p in (OLD / 'gauge-protocol.h', OLD / 'gauge-i2c.h',
              OLD / 'samurai-gauge-protection.c', OLD / 'test-observer.c', STUBS / 'actual-provider.inc', FIXTURE)}
    original = json.loads((OLD / 'test-result.json').read_bytes())
    assert sha(STUBS / 'actual-provider.inc') == original['actual_function_source_sha256']
    assert sha(FIXTURE) == original['old6_packet_fixture_sha256']
    assert sha(OLD / 'gauge-protocol.h') == original['tested_files']['gauge-protocol.h']
    assert sha(OLD / 'samurai-gauge-protection.c') == original['tested_files']['samurai-gauge-protection.c']
    PRIVATE.mkdir(exist_ok=False)
    decoder = PRIVATE / 'frame-decoder'
    compile_decoder = ['gcc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                       str(HERE / 'frame-decoder.c'), '-o', str(decoder)]
    build = subprocess.run(compile_decoder, capture_output=True)
    (PRIVATE / 'decoder-build.log').write_bytes(build.stdout + build.stderr)
    assert build.returncode == 0 and not build.stderr
    prefix = (OLD / 'test-observer.c').read_text().split('int main(int argc,char **argv)')[0]
    source = prefix + r'''
int main(int argc,char **argv)
{
 assert(argc==3);FILE *file=fopen(argv[1],"rb");assert(file);
 for(unsigned i=0;i<6;i++){unsigned char cmd[2];assert(fread(cmd,1,2,file)==2);commands[i]=sm_le16(cmd);assert(fread(packets[i],1,36,file)==36);assert(!sm_mac_validate(packets[i],36,commands[i]));}
 assert(fgetc(file)==EOF);fclose(file);reset();int mode=atoi(argv[2]);assert(mode>=0 && mode<=12);
 if(mode>=1 && mode<=6){fail_cmd=0x50;failure=mode;}
 if(mode==7){fail_cmd=1;failure=7;}
 if(mode==8)word_fail=1;
 if(mode==9)word_fail=2;
 if(mode==10)word_after=0x80;
 if(mode==12)word_after=0xc1;
 if(mode!=11)mac_evidence_capture_store(&dev,NULL,"capture\n",8);
 char data[PAGE_SIZE];unsigned before=io_count;ssize_t n=mac_evidence_show(&dev,NULL,data);
 assert(n>0 && n<PAGE_SIZE && (unsigned)strlen(data)==n && before==io_count);
 assert(fwrite(data,1,n,stdout)==(size_t)n);assert(!pthread_mutex_destroy(&p.lock.native));return 0;
}
'''
    (PRIVATE / 'actual-output-fixture.c').write_text(source)
    fixture_binary = PRIVATE / 'actual-output-fixture'
    compile_fixture = ['gcc', '-std=c11', '-g', '-O1', '-Wall', '-Wextra', '-Werror',
                       '-Wno-unused-parameter', '-Wno-sign-compare', '-Wno-misleading-indentation',
                       '-Wno-unused-function', '-Wno-unused-variable', '-fsanitize=address,undefined',
                       '-fno-omit-frame-pointer', '-pthread', '-I' + str(STUBS / 'stubs'),
                       '-I' + str(OLD), '-I' + str(STUBS), str(PRIVATE / 'actual-output-fixture.c'),
                       '-o', str(fixture_binary)]
    build = subprocess.run(compile_fixture, capture_output=True)
    (PRIVATE / 'fixture-build.log').write_bytes(build.stdout + build.stderr)
    assert build.returncode == 0 and not build.stderr, build.stderr
    spec = importlib.util.spec_from_file_location('saved_parser', HERE / 'parse-evidence.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    decoder_sha = sha(decoder)
    run_cases = []
    outputs = {}
    for mode in range(13):
        run = subprocess.run([str(fixture_binary), str(FIXTURE), str(mode)], capture_output=True)
        (PRIVATE / f'actual-{mode:02d}.txt').write_bytes(run.stdout)
        (PRIVATE / f'actual-{mode:02d}.stderr').write_bytes(run.stderr)
        assert run.returncode == 0 and not run.stderr, (mode, run.stderr)
        result = module.parse_saved(run.stdout, decoder, decoder_sha)
        assert result['sequence_complete'] == (mode in (0, 10, 12))
        assert result['battery_status_mask_stable'] == (False if mode == 10 else True if mode in (0, 12) else None)
        assert result['TCA_classification'] == 'UNVERIFIED'
        assert not any(result[k] for k in ('compatibility_verified', 'freshness_verified',
                       'boot_identity_verified', 'charge_or_recharge_authorized', 'physical_safety_accepted'))
        (PRIVATE / f'analysis-{mode:02d}.json').write_text(json.dumps(result, indent=2) + '\n')
        outputs[mode] = run.stdout
        run_cases.append({'actual_provider_mode': mode, 'passed': True,
                          'input_sha256': hashlib.sha256(run.stdout).hexdigest()})

    def reject(label, data, expected_decoder_sha=decoder_sha):
        try:
            module.parse_saved(data, decoder, expected_decoder_sha)
        except ValueError:
            run_cases.append({'rejection': label, 'passed': True})
        else:
            raise AssertionError(label)

    good = outputs[0]
    reject('missing final newline', good[:-1])
    reject('missing frame', b'\n'.join(good.splitlines()[:-1]) + b'\n')
    reject('oversized', b'x' * 4096)
    reject('duplicate key', good.replace(b'schema=1', b'schema=1 schema=1'))
    reject('unknown schema', good.replace(b'schema=1', b'schema=2'))
    reject('compatibility cannot be asserted', good.replace(b'compatibility_verified=0', b'compatibility_verified=1'))
    reject('wrong frame command', good.replace(b'cmd=0x0050', b'cmd=0x0055'))
    reject('raw contradicts validation', good.replace(b'raw=5000', b'raw=5100'))
    reject('partial claims raw', outputs[3].replace(b'full_read=0 validate_attempted=0', b'full_read=1 validate_attempted=1', 1))
    reject('complete claims no raw', good.replace(b'raw=5000' + good.split(b'raw=5000', 1)[1].split(b'\n', 1)[0], b'raw=unavailable'))
    reject('changed expected size', good.replace(b'cmd=0x0056 attempted=1 expected_size=4', b'cmd=0x0056 attempted=1 expected_size=3'))
    reject('counter disagrees', good.replace(b'frames_attempted=8', b'frames_attempted=7'))
    reject('wrong decoder', good, '0' * 64)
    # The parser's CLI reads a saved regular file and emits the same facts.
    cli = subprocess.run(['python3', '-B', str(HERE / 'parse-evidence.py'), '--input',
                          str(PRIVATE / 'actual-00.txt'), '--decoder', str(decoder),
                          '--decoder-sha256', decoder_sha], capture_output=True)
    assert cli.returncode == 0 and not cli.stderr
    assert json.loads(cli.stdout)['sequence_complete'] is True
    assert before == {p: sha(Path(p)) for p in before}
    result = {'passed': True, 'cases': run_cases, 'new_case_count': len(run_cases), 'cli_returncode': cli.returncode,
              'compile_decoder': compile_decoder, 'compile_fixture': compile_fixture,
              'decoder_sha256': decoder_sha, 'actual_fixture_binary_sha256': sha(fixture_binary),
              'reused_function_source_sha256': sha(STUBS / 'actual-provider.inc'),
              'source_input_sha256': before, 'inputs_unchanged': True,
              'private_output': str(PRIVATE), 'real_packets_reused_only_for_old_six': True,
              'new_three_responses_synthetic': True, 'physical_queries_or_device_access': False,
              'old_suites_rerun': False, 'files': {p.name: sha(p) for p in (HERE / 'parse-evidence.py', HERE / 'frame-decoder.c', HERE / 'test-parser.py')}}
    (HERE / 'test-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'new_case_count': len(run_cases), 'decoder_sha256': decoder_sha}))


if __name__ == '__main__':
    main()
