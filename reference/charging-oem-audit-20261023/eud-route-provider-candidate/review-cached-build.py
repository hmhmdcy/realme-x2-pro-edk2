"""Finish the failed export-name audit using its existing compiler artifacts."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1];HANDOFF=HERE.parent/'eud-route-handoff-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((HERE/'build-result.json').read_bytes());assert not old['passed'] and old['shared_unchanged']
helper=REF/'kernel284/storage.py';assert sha(helper)=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
s=importlib.util.spec_from_file_location('original_guard_cached_route_export_review',helper);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.mounted_build()
out=Path('/home/cy122/charging-management-20261023/eud-route-provider-earlycon-r2-01');oldout=Path(old['private_output'])
original=HERE/'history/build-earlycon-r2-before-export-review.py.inc'
text=original.read_text();assert '__ksymtab_samurai_eud_producer_claim' in text and 'child.returncode==0 and not stderr' in text
assert 'compile-terminal-private.json' not in text
objects={name:oldout/(name+'.o') for name in ['provider','COM-on','COM-off','qcom-EUD-on','qcom-EUD-off']}
for name,path in objects.items():
    assert next(row for row in old['phases'] if row['name']==name)['returncode']==0
    assert sha(path)==old['objects'][path.name]
objects.update({name:out/(name+'.o') for name in ['earlycon-on','earlycon-off']})
assert all(sha(HERE/name)==old['files'][name] for name in ['samurai-eud-route.c','samurai-eud-route.h','eud.c','qcom_eud.c'])
sources=json.loads((HERE/'source-result.json').read_bytes())['files']
assert all(sha(HERE/name)==row['sha256'] for name,row in sources.items())
assert all(not (out/(name+'.stdout')).read_bytes() and not (out/(name+'.stderr')).read_bytes() for name in ['earlycon-on','earlycon-off'])
warning=(out/'baseline-warning.stderr').read_bytes();assert b'eud_wait_tx' in warning and b'unused-function' in warning
assert all(sha(Path(name))==digest for name,digest in old['after'].items())
default_off={name:subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(objects[name])],text=True).splitlines() for name in ['COM-off','earlycon-off','qcom-EUD-off']}
assert not any('samurai_eud_' in line for rows in default_off.values() for line in rows)
definitions=subprocess.check_output(['aarch64-linux-gnu-nm','--defined-only',str(objects['provider'])],text=True)
exports=['__export_symbol_samurai_eud_producer_claim','__export_symbol_samurai_eud_producer_release']
assert all(any(line.split()[-1]==symbol for line in definitions.splitlines()) for symbol in exports)
h=json.loads((HANDOFF/'build-r2-result.json').read_bytes());receiver=Path(h['private_output'])/'samurai-eud-handoff.o'
assert h['passed'] and sha(receiver)==h['receiver_sha256']
target=out/'private-interface-only.o';assert target.is_file()
undefined=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(target)],text=True).splitlines()
assert not any('samurai_eud_' in line for line in undefined)
result=dict(passed=True,private_output=str(out),cached_artifact_review=True,compiler_or_linker_replayed=False,
    original_postprocessor_failure='Expected legacy __ksymtab_* names; actual kernel7.3 emits __export_symbol_* metadata',
    original_executed_script_sha256=sha(original),
    original_r2_compile=dict(baseline_returncode_observed=1,earlycon_on_returncode_observed=0,earlycon_off_returncode_observed=0,
      original_child_pids=None,original_child_pids_persisted=False,
      completion_evidence='Original executed script joined each child, asserted expected status and empty diagnostics, linked and checked internal symbols, then failed at the export-name assertion. Review uses those retained artifacts; it does not synthesize child receipts.'),
    original_baseline_same_unused_warning_verified=True,reused_five_objects=True,
    objects={name:dict(path=str(path),sha256=sha(path)) for name,path in objects.items()},
    default_off_new_imports_absent=True,producer_exports_present=True,export_symbols=exports,
    partial_interface_sha256=sha(target),unresolved_internal=[],handoff_receiver_reused=dict(path=str(receiver),sha256=sha(receiver)),
    shared_unchanged=True,shared_inputs=old['after'],
    files={name:sha(HERE/name) for name in ['samurai-eud-route.c','samurai-eud-route.h','eud.c','eud_earlycon.c','qcom_eud.c']},
    Image_or_module_linked=False,phone_accessed=False,APSD_gate_enabled=False)
with (HERE/'build-r2-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,compiler_replayed=False,reused_objects=5,default_off_new_imports=0,unresolved_internal=0)))
