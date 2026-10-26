"""Offline R2: only add the twice-observed whole CSR literal to R1's predicate."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
R1=HERE.parent/'eud-boot-policy'
REF=HERE.parents[1]
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def save(name,raw):
    p=HERE/name
    if p.exists():assert p.read_bytes()==raw,'new bytes require another revision: '+name
    else:p.write_bytes(raw)
def jsonraw(data):return (json.dumps(data,indent=2)+'\n').encode()
def function(text,name):
    at=text.index(name+'(') if name+'(' in text else text.index(name+' (')
    start=text.rfind('\n',0,at)+1
    assert text[start:at].startswith('static '),name
    opening=text.index('{',at);i=opening+1;depth=1
    while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[start:i]

def main():
    r1=json.loads((R1/'result.json').read_bytes());assert r1['passed']
    for name,digest in r1['files'].items():assert sha((R1/name).read_bytes())==digest,name
    old=(R1/'PlatformBm.c').read_text();r1c=(R1/'PlatformBm.c.candidate').read_text()
    prior='  // Do not mask away unknown bits or accept an unproven replicated word.\n  return (Value == 0U) || (Value == 1U);'
    changed='  // Match full words only; 0x01010101 was read twice on this board.\n  return (Value == 0U) || (Value == 1U) || (Value == 0x01010101U);'
    assert r1c.count(prior)==1
    new=r1c.replace(prior,changed);save('PlatformBm.c.candidate',new.encode())
    frag=(R1/'eud-handoff-fragment.inc').read_text();assert frag.count(prior)==1
    save('eud-handoff-fragment.inc',frag.replace(prior,changed).encode())
    # This identity proves all panel, cmdline, callback, event and failure bytes stay R1.
    assert new.replace(changed,prior)==r1c
    path='Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c'
    full=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),'a/'+path,'b/'+path))
    delta=''.join(difflib.unified_diff(r1c.splitlines(True),new.splitlines(True),'a/'+path,'b/'+path))
    save('boot-policy.patch',full.encode());save('r1-to-r2.patch',delta.encode())
    # Check full and delta patches independently against their exact complete base.
    patch_results=[]
    for name,base in [('boot-policy.patch',old),('r1-to-r2.patch',r1c)]:
        with tempfile.TemporaryDirectory(prefix='eud-boot-r2-') as tmp:
            target=Path(tmp)/path;target.parent.mkdir(parents=True);target.write_text(base)
            command=['patch','--batch','--fuzz=0','-p1','-d',tmp,'-i',str(HERE/name)]
            dry=subprocess.run(command+['--dry-run'],capture_output=True,text=True);assert dry.returncode==0,dry.stdout+dry.stderr
            apply=subprocess.run(command,capture_output=True,text=True);assert apply.returncode==0,apply.stdout+apply.stderr
            assert target.read_bytes()==new.encode()
            patch_results.append({'patch':name,'dry_run':0,'apply':0,'candidate_bytes_equal':True,'fuzz':0})
    observation_path=REF/'charging-management-20261023/eud-csr-r8-result.json'
    observed=json.loads(observation_path.read_bytes())
    assert observed['passed'] and observed['hardware_writes']==0 and observed['csr_equal']
    assert observed['csr_address']=='0x088e1014' and observed['csr_width_bits']==32 and observed['explicit_mmio_bytes_read']==8
    assert len(observed['csr'])==2 and all(row['value']==0x01010101 and row['hex']=='0x01010101' for row in observed['csr'])
    assert observed['device_source_sha256']=='810e220c03fab3f00fd88f2ddb742ee2c78ea5b7de09a84bf32997ef71bba6d8'
    assert observed['eud_driver']=='qcom_eud_com' and observed['taint']==0 and observed['helper_absent']
    polls=[int(dict(field.split('=') for field in observed[key].split())['polls']) for key in ['eud_rx_stats_before','eud_rx_stats_live','eud_rx_stats_after']]
    assert polls[0]<polls[1]<polls[2]
    eud=(R1/'drivers--tty--serial--eud.c').read_text()
    probe=function(eud,'eud_probe');retire=function(eud,'eud_reboot_cmd')
    assert 'writel_relaxed(1, port->membase + EUD_REG_CSR_EUD_EN)' in probe
    assert 'writel(0, up->port.membase + EUD_REG_CSR_EUD_EN);\n\treadl(up->port.membase + EUD_REG_CSR_EUD_EN)' in retire
    assert retire.index('synchronize_irq')<retire.index('writel(0,') and retire.index('unregister_console')<retire.index('writel(0,') and retire.index('tx_stopping = true')<retire.index('writel(0,')<retire.index('kernel_restart')
    assert '#define EUD_REG_CSR_EUD_EN     0x1014' in eud
    save('existing-eud-functions.inc',(probe+'\n\n'+retire+'\n').encode())
    evidence={'schema':'eud-boot-known-whole-word-r2','observation_receipt':'charging-management-20261023/eud-csr-r8-result.json',
        'observation_receipt_sha256':sha(observation_path.read_bytes()),'executed_readonly_source_sha256':observed['device_source_sha256'],
        'observed_address':'0x088e1014','observed_width_bits':32,'observed_full_words':[0x01010101,0x01010101],
        'observed_existing_rx_polls_advanced':True,'observation_hardware_writes':0,
        'source':'eud-boot-policy/drivers--tty--serial--eud.c','source_sha256':sha(eud.encode()),
        'functions':{name:{'sha256':sha(body.encode()),'line':eud[:eud.index(body)].count('\n')+1} for name,body in [('eud_probe',probe),('eud_reboot_cmd',retire)]},
        'supports':'existing Linux code uses literal1 to enable and literal0 plus read to retire under its own producer-stop/restart sequence',
        'does_not_prove':['datasheet replication or alias semantics','online CSR write safety','CSR zero achieved','post-EBS producers/route state','USB hub or SDP500 causality']}
    save('source-evidence.json',jsonraw(evidence))
    dt=Path(r1['native_candidate_path']);assert sha(dt.read_bytes())==r1['native_candidate_sha256']=='9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358'
    independent=REF/'charging-session-20261023/eud-boot-policy-independent-review/review-result.json'
    reviewed=json.loads(independent.read_bytes());assert reviewed['native_candidate_sha256']==r1['native_candidate_sha256'] and reviewed['all_other_dtb_values_nodes_reserved_map_preserved']
    result={'passed':True,'revision':2,'only_changed_function':'SamuraiEudCsrKnown','r1_result_sha256':sha((R1/'result.json').read_bytes()),
        'original_source_sha256':sha(old.encode()),'r1_candidate_source_sha256':sha(r1c.encode()),'candidate_source_sha256':sha(new.encode()),
        'known_full_words':[0,1,0x01010101],'write_target_full_word':0,'low_byte_mask':False,
        'all_other_r1_source_bytes_unchanged':True,'panel_cmdline_lifecycle_failure_bytes_unchanged':True,
        'patches':{n:sha((HERE/n).read_bytes()) for n in ['boot-policy.patch','r1-to-r2.patch']},'patch_checks':patch_results,
        'source_evidence_sha256':sha((HERE/'source-evidence.json').read_bytes()),'native_candidate_sha256':r1['native_candidate_sha256'],
        'native_DTB_reused_without_generation':True,'r1_12_case_receipt_sha256':r1['files']['test-result.json'],
        'r1_independent_FDT_review_sha256':sha(independent.read_bytes()),'r1_files_unchanged':True,
        'firmware_built':False,'SDK_invoked':False,'device_accessed':False,'shared_tree_modified':False,'hardware_CSR_zero_proven':False,'USB500_cause_proven':False}
    save('candidate-result.json',jsonraw(result));print(json.dumps({'passed':True,'candidate_source_sha256':result['candidate_source_sha256'],'native_DTB_reused':True}))

if __name__=='__main__':main()
