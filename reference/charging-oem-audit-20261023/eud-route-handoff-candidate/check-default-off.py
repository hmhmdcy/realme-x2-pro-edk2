"""The always-present EFI include must compile with the real option absent."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((HERE/'build-result.json').read_bytes());latest=json.loads((HERE/'build-r2-result.json').read_bytes());assert old['passed'] and latest['passed']
helper=REF/'kernel284/storage.py';assert sha(helper)=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
s=importlib.util.spec_from_file_location('original_guard_EFI_default_off',helper);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);BUILD=m.mounted_build()
assert 'CONFIG_QCOM_SAMURAI_EUD_HANDOFF=' not in (BUILD/'.config').read_text()
OUT=Path('/home/cy122/charging-management-20261023/eud-route-handoff-default-off-01');assert not OUT.exists();OUT.mkdir();(OUT/'tmp').mkdir()
argv=list(old['commands'][1]);assert argv.count('-DCONFIG_QCOM_SAMURAI_EUD_HANDOFF=1')==1;argv.remove('-DCONFIG_QCOM_SAMURAI_EUD_HANDOFF=1')
argv[argv.index('-o')+1]=str(OUT/'efi.o');argv=[('-Wp,-MMD,'+str(OUT/'efi.d')) if word.startswith('-Wp,-MMD,') else word for word in argv]
paths=[BUILD/'.config',BUILD/'include/generated/autoconf.h',HERE/'efi.c',HERE/'samurai-eud-handoff.h',HERE/'samurai-eud-handoff-wire.h'];before={str(p):sha(p) for p in paths}
child=subprocess.Popen(argv,cwd=BUILD,env={**os.environ,'TMPDIR':str(OUT/'tmp')},stdout=subprocess.PIPE,stderr=subprocess.PIPE)
stdout,stderr=child.communicate();child.wait();(OUT/'stdout').write_bytes(stdout);(OUT/'stderr').write_bytes(stderr)
assert child.returncode==0 and not stderr,(child.returncode,stderr.decode())
undefined=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(OUT/'efi.o')],text=True).splitlines();assert not any('samurai_eud_handoff_' in line for line in undefined)
after={str(p):sha(p) for p in paths};assert before==after
result=dict(passed=True,private_output=str(OUT),command=argv,original_child_pid=child.pid,original_child_terminal=True,returncode=child.returncode,
    diagnostic_bytes=len(stderr),actual_shared_option_absent=True,no_handoff_imports=True,object_sha256=sha(OUT/'efi.o'),
    before=before,after=after,shared_inputs_unchanged=True,phone_accessed=False,route_authorization=False)
with (HERE/'default-off-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,actual_default_off=True,no_handoff_imports=True,shared_inputs_unchanged=True)))
