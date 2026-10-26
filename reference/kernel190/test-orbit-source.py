from pathlib import Path
import hashlib,json,os,shlex,subprocess
ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel190/mm-host-tests');out.mkdir(exist_ok=True)
source=Path('/mnt/e/edk2-samurai-out/kernel190/mm-build/ModemManager-7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a/src/mm-shared-qmi.c').read_text()
def callbacks(s):
    start=s.index('typedef struct {',s.index('/* Location: load supported assistance data */'))
    middle=s.index('/*****************************************************************************/\n/* Location: Inject UTC time */',start)
    last=s.index('static void\nloc_location_get_predicted_orbits_data_source_indication_cb (',middle)
    end=s.index('/*****************************************************************************/\n/* Location: inject assistance data */',last)
    return s[start:middle]+s[last:end]
code=(ref/'orbit-source-harness.c').read_text().replace('/* BUILD_PRODUCTION_CALLBACKS */',callbacks(source))
path=out/'orbit-source-harness.c';path.write_text(code)
flags=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','gio-2.0'],text=True))
binary=out/'orbit-source-harness'
command=['gcc','-g','-O1','-fno-omit-frame-pointer','-fsanitize=address,undefined','-Wall','-Wextra','-Wno-unused-parameter',str(path),'-o',str(binary)]+flags
subprocess.run(command,check=True,capture_output=True)
env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
result=subprocess.run([str(binary)],check=True,capture_output=True,text=True,env=env)
print(result.stdout)
# A deliberately regressed ACK gate must be rejected at runtime, not by text matching.
mutant=code.replace('if (!ctx->response_received) {','if (TRUE) {',1)
mutantpath=out/'mutant.c';mutantpath.write_text(mutant)
subprocess.run([arg if arg!=str(path) and arg!=str(binary) else str(mutantpath) if arg==str(path) else str(out/'mutant') for arg in command],check=True,capture_output=True)
m=subprocess.run([str(out/'mutant')],capture_output=True,env=env)
assert m.returncode!=0
original=Path('/mnt/e/edk2-samurai-out/kernel190/location-sources/src/mm-shared-qmi.c').read_text()
baseline=(ref/'orbit-source-harness.c').read_text().replace('/* BUILD_PRODUCTION_CALLBACKS */',callbacks(original))
baselinepath=out/'baseline.c';baselinepath.write_text(baseline)
subprocess.run([arg if arg!=str(path) and arg!=str(binary) else str(baselinepath) if arg==str(path) else str(out/'baseline') for arg in command],check=True,capture_output=True)
b=subprocess.run([str(out/'baseline')],capture_output=True,env=env)
assert b.returncode!=0 and b'scenario IA expected 1 got -9' in b.stderr
(out/'baseline-failure-private.log').write_bytes(b.stdout+b.stderr)
report=dict(production_callbacks_sha256=hashlib.sha256(callbacks(source).encode()).hexdigest(),cases=23,address_sanitizer=True,undefined_behavior_sanitizer=True,leak_detection=True,regression_mutant_rejected=True,pinned_original_fails_early_indication=True,stdout=result.stdout.strip())
(ref/'mm-orbit-source-host-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
