"""Check exact paired producer deltas and apply their patch without fuzz."""
from pathlib import Path
import hashlib,json,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=json.loads((HERE/'source-result.json').read_bytes())['files']
def bodies(text):
    # Preserve offsets while ignoring comments, strings and character literals.
    scrub=re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',lambda m:' '*len(m[0]),text,flags=re.S)
    out={}
    for match in re.finditer(r'^([A-Za-z_][\w \t*]*?)\b(\w+)\s*\([^;{}]*\)\s*\{',scrub,re.M):
        name=match[2];start=scrub.index('{',match.start());depth=1;end=start+1
        while depth:
            depth+=(scrub[end]=='{')-(scrub[end]=='}');end+=1
        assert name not in out,name;out[name]=text[match.start():end]
    return out
expected={'eud.c':{'eud_probe_locked'},'qcom_eud.c':{'eud_probe'},'eud_earlycon.c':{'eud_setup'}}
review={}
with tempfile.TemporaryDirectory(prefix='samurai-eud-paired-source-review-') as temporary:
    root=Path(temporary)
    for name,row in record.items():
        original=Path(row['original']);assert sha(original)==row['original_sha256'] and sha(HERE/name)==row['sha256']
        target=root/row['target'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(original.read_bytes())
        old,new=bodies(original.read_text()),bodies((HERE/name).read_text())
        removed=set(old)-set(new);added=set(new)-set(old);changed={key for key in set(old)&set(new) if old[key]!=new[key]}
        assert removed==({'eud_wait_tx'} if name=='eud_earlycon.c' else set()) and not added,(name,removed,added)
        assert changed==expected[name],(name,changed)
        body=new[next(iter(expected[name]))]
        claim='samurai_eud_earlycon_claim' if name=='eud_earlycon.c' else 'samurai_eud_producer_claim'
        marker={'eud.c':'devm_platform_get_and_ioremap_resource','qcom_eud.c':'devm_platform_ioremap_resource','eud_earlycon.c':'early_ioremap'}[name]
        assert body.index(claim)<body.index(marker),(name,claim,marker)
        if name!='eud_earlycon.c':assert body.index('devm_add_action_or_reset')<body.index(marker)
        review[name]=dict(changed_functions=sorted(changed),unchanged_functions=len(set(old)&set(new))-len(changed),removed_uncalled_functions=sorted(removed),claim_before_first_hardware_operation=True)
    child=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(HERE/'producer-entry.patch')],cwd=root,capture_output=True,text=True)
    assert child.returncode==0 and 'fuzz' not in child.stdout.lower() and 'offset' not in child.stdout.lower(),(child.returncode,child.stdout,child.stderr)
    assert all(sha(root/row['target'])==row['sha256'] for row in record.values())
core=(HERE/'samurai-eud-route.c').read_text();header=(HERE/'samurai-eud-route.h').read_text()
assert 'request_mem_region' not in core and 'insert_resource' not in core
assert 'producer_ever_granted = true' in core and not re.search(r'producer_ever_granted\s*=\s*false',core)
assert 'atomic_set(&boot_evidence_retired, 1)' in core and not re.search(r'atomic_set\(&boot_evidence_retired, 0\)',core)
assert '*token = NULL' in header and 'return -EOPNOTSUPP' in header
result=dict(passed=True,paired_producers=review,producer_patch_fuzz=0,patch_outputs_exact=True,
    real_resource_tree_is_not_an_authority=True,shared_arbiter_precedes_all_paired_live_producers=True,
    boot_history_retained=True,PM_route_retention_proved=False,full_DWC_consumer_connected=False,
    phone_accessed=False,APSD_gate_enabled=False,
    files={name:sha(HERE/name) for name in ['samurai-eud-route.c','samurai-eud-route.h','eud.c','qcom_eud.c','eud_earlycon.c','producer-entry.patch']})
with (HERE/'source-review.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,functions=review,patch_fuzz=0)))
