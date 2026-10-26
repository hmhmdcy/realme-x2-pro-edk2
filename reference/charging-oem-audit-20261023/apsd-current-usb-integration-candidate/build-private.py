"""Only current-input object changes; reuse frozen owner/PD/PHY objects."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1];PRIOR=HERE.parent/'apsd-final-transfer-candidate';CURRENT=HERE.parent/'usb-input-irq-wake-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['pm-test-result.json','transfer-test-result.json']:
    result=json.loads((HERE/name).read_bytes());assert result['passed'] and all(sha(HERE/n)==h for n,h in result['files'].items())
original=(CURRENT/'samurai-usb-input.c').read_text();source=(HERE/'samurai-usb-input.c').read_text()
def function(text,name):
    match=re.search(r'(?m)^static [\w\s*]+?\b'+name+r'\([^;]*?\)\s*\{',text);assert match,name
    end=match.end();depth=1
    while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[match.start():end]
names=re.findall(r'(?m)^static [\w *]+?\b(samurai_usb_\w+)\(',original)
unchanged=[name for name in names if name not in ['samurai_usb_stop','samurai_usb_prepare','samurai_usb_complete','samurai_usb_probe']]
assert all(function(original,name)==function(source,name) for name in unchanged)
helper=REF/'kernel284/storage.py';assert sha(helper)=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
s=importlib.util.spec_from_file_location('original_guard_current_APSD_input',helper);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.mounted_build()
old=json.loads((PRIOR/'build-result.json').read_bytes());interface=json.loads((PRIOR/'interface-result.json').read_bytes());assert old['passed'] and interface['passed']
OUT=Path('/home/cy122/charging-management-20261023/apsd-current-usb-input-objects-01');assert not OUT.exists()
paths=[Path(p) for p in old['shared_after']]+[CURRENT/'samurai-usb-input.c',CURRENT/'samurai-usb-input-decode.h']
before={str(p):sha(p) for p in paths};OUT.mkdir();(OUT/'tmp').mkdir();include=OUT/'include';include.mkdir()
(include/'linux/usb').mkdir(parents=True);(include/'linux/usb/samurai-apsd-backend.h').write_bytes((HERE/'samurai-apsd-backend.h').read_bytes())
argv=list(old['commands'][-1]);argv[-1]=str(HERE/'samurai-usb-input.c');argv[argv.index('-o')+1]=str(OUT/'input.o')
argv=[('-Wp,-MMD,'+str(OUT/'input.d')) if word.startswith('-Wp,-MMD,') else word for word in argv]
argv=[('-I'+str(include)) if word=='-I'+old['private_output']+'/include' else word for word in argv]
cwd=Path('/home/cy122/charging-management-20261023/source-float-candidate/kbuild')
child=subprocess.Popen(argv,cwd=cwd,env={**os.environ,'TMPDIR':str(OUT/'tmp')},stdout=subprocess.PIPE,stderr=subprocess.PIPE)
stdout,stderr=child.communicate();child.wait();(OUT/'stdout').write_bytes(stdout);(OUT/'stderr').write_bytes(stderr)
assert child.returncode==0 and not stderr,(child.returncode,stderr.decode())
objects=[Path(old['private_output'])/'owner-future-builtin.o',OUT/'input.o']
for path,digest in interface['input_objects'].items():
    if Path(path).name not in ['owner-future-builtin.o','input.o']:objects.append(Path(path));assert sha(Path(path))==digest
assert sha(objects[0])==old['objects'][objects[0].name]
target=OUT/'private-interface-only.o';link=['aarch64-linux-gnu-ld','-r','--fatal-warnings','-o',str(target),*[str(p) for p in objects]]
linked=subprocess.run(link,capture_output=True,text=True);assert linked.returncode==0 and not linked.stderr,(linked.returncode,linked.stderr)
undefined=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(target)],text=True).splitlines()
internal=[line for line in undefined if any(prefix in line for prefix in ['qcom_snps_hsphy_window_','qcom_pmic_typec_5v_','samurai_pd5v_','samurai_apsd_bus_'])]
assert not internal,internal
after={str(p):sha(p) for p in paths};assert before==after
result=dict(passed=True,private_output=str(OUT),command=argv,original_child_pid=child.pid,original_child_terminal=True,returncode=child.returncode,
    diagnostic_bytes=len(stderr),input_object_sha256=sha(OUT/'input.o'),current_unchanged_functions=unchanged,
    link_command=link,link_returncode=linked.returncode,relocatable_interface_only=True,input_objects={str(p):sha(p) for p in objects},
    internal_unresolved=internal,partial_link_sha256=sha(target),shared_before=before,shared_after=after,shared_unchanged=before==after,
    actual_shared_TYPEC='m',future_builtin_command_view_only=True,Image_or_module_linked=False,phone_accessed=False,SDK_invoked=False,
    files={name:sha(HERE/name) for name in ['samurai-usb-input.c','samurai-apsd-input.inc','samurai-apsd-backend.h','samurai-usb-input-decode.h']})
with (HERE/'build-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,compiled_objects=1,unchanged_current_functions=len(unchanged),unresolved_internal=0,shared_unchanged=True)))
