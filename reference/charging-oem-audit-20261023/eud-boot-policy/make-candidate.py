"""Create only a review patch and private DTB copy; no firmware/SDK/build use."""
from pathlib import Path
import difflib,hashlib,json,re,shutil,subprocess
HERE=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-boot-policy-private')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(HERE/'design-evidence.json')=='ca2c28f528bd58f10e6ada8c8e7760eb77f938f929655fda583a4001ba9e5494'
amendment=json.loads((HERE/'design-amendment.json').read_text());assert amendment['known_full_word_values']==[0,1]
old=(HERE/'PlatformBm.c').read_text()
assert sha(HERE/'PlatformBm.c')=='eda995b4a7f50fdd8e792a8989d570fa4be9e3466a5afb946282456fba27198a'
new=old
fragment=(HERE/'eud-handoff-fragment.inc').read_text()
anchor='//\n// SAMURAI: where the mainline Linux kernel lives on a file system.'
assert new.count(anchor)==1;new=new.replace(anchor,fragment+'\n'+anchor)
match=re.search(r'STATIC CHAR16  mSamuraiLinuxCmdLine\[\] =\s*L"([^"]+)";',new)
assert match
original_cmd=match[1];tokens=original_cmd.split()
remove=['earlycon=eud,mmio,0x88e0000','console=eud']
assert all(tokens.count(x)==1 for x in remove)
new_cmd=' '.join(t for t in tokens if t not in remove)
new=new[:match.start(1)]+new_cmd+new[match.end(1):]
before='    Status = SamuraiArmPanelHandoff (&PanelHandoff);'
insert='''#ifdef SAMURAI_ENABLE_EUD
    Status = SamuraiArmEudOffHandoff ();
    if (EFI_ERROR (Status)) {
      Print (L"[SAMURAI-EUD-OFF] not armed: %r; kernel launch refused\\n", Status);
      goto SamuraiKernelBootDone;
    }
#endif
'''
assert new.count(before)==1;new=new.replace(before,insert+before)
after='    SamuraiDisarmPanelHandoff (&PanelHandoff);'
assert new.count(after)==1
new=new.replace(after,after+'''
#ifdef SAMURAI_ENABLE_EUD
    SamuraiDisarmEudOffHandoff ();
SamuraiKernelBootDone:
#endif''')
producer='''  if (Msg == NULL) {
    return;
  }
'''
assert new.count(producer)==1
new=new.replace(producer,producer+'''
#ifdef SAMURAI_LINUX_KERNEL
  // A returned loader/BDS wait must not resume direct FIFO writes after EBS.
  if (mSamuraiEudOffHandoff.Attempted) {
    return;
  }
#endif
''')
target=HERE/'PlatformBm.c.candidate';target.write_text(new)
path='Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c'
patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),'a/'+path,'b/'+path))
(HERE/'boot-policy.patch').write_text(patch)
ns={};legacy=HERE.parents[1]/'kernel93/verify-firmware.py'
exec(legacy.read_text().split('\ndt_audit=')[0],ns)
parse=ns['fdt_nodes']
native=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-boot/samurai-charging-private.dtb')
assert sha(native)=='c559d2c4c9a83e85473b1b24724bb8938f1084bd3efcae9c4b67f37c2a4c4503'
before_dt=parse(native.read_bytes());com='/soc@0/serial@88e0000'
assert before_dt[com]['status']==b'okay\0' and before_dt[com]['compatible']==b'qcom,sm8150-eud-com\0'
assert before_dt['/chosen']['bootargs']==original_cmd.encode()+b'\0'
eud_nodes=[p for p,d in before_dt.items() if any(b'eud' in v for v in d.get('compatible',b'').split(b'\0'))]
assert eud_nodes==[com]
candidate=PRIVATE/'samurai-eud-off-policy-private.dtb';shutil.copyfile(native,candidate)
for node,key,value in [(com,'status','disabled'),('/chosen','bootargs',new_cmd)]:
 subprocess.run(['fdtput','-t','s',str(candidate),node,key,value],check=True)
after_dt=parse(candidate.read_bytes());assert before_dt.keys()==after_dt.keys()
delta=[(p,k) for p in before_dt for k in before_dt[p].keys()|after_dt[p].keys() if before_dt[p].get(k)!=after_dt[p].get(k)]
assert sorted(delta)==sorted([(com,'status'),('/chosen','bootargs')])
result=dict(passed=True,source_sha256=sha(HERE/'PlatformBm.c'),candidate_source_sha256=sha(target),patch_sha256=sha(HERE/'boot-policy.patch'),
 design_sha256=sha(HERE/'design-evidence.json'),design_amendment_sha256=sha(HERE/'design-amendment.json'),
 original_cmdline=original_cmd,candidate_cmdline=new_cmd,removed_tokens=remove,other_tokens_unchanged=True,
 native_base_sha256=sha(native),native_candidate_path=str(candidate),native_candidate_sha256=sha(candidate),
 dt_semantic_changes=[dict(node=p,property=k) for p,k in delta],all_other_dt_properties_byte_exact=True,
 image_preserved_sha256='15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468',
 native_DTB_is_firmware_input=True,source_header_or_kernel_ABI_changed=False,firmware_built=False,
 SDK_invoked=False,shared_tree_modified=False,phone_accessed=False,hardware_CSR_zero_proven=False,
 direct_USB_or_SDP500_proven=False)
(HERE/'candidate-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,patch_sha256=sha(HERE/'boot-policy.patch'),native_candidate_sha256=sha(candidate))))
