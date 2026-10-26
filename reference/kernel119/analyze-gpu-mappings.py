from pathlib import Path
import re,json,hashlib
out=Path('/mnt/e/edk2-samurai-out/kernel119/gpu-coredump')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel119')
raw=(out/'devcd2-private.data').read_text(errors='replace')
decoded=(out/'decoded-summary-private.txt').read_text(errors='replace')
fault=re.search(r'^fault-info:\n(.*?)(?=^[a-z])',raw,re.S|re.M).group(1)
iova=int(re.search(r'iova=(?:0x)?([0-9a-fA-F]+)',fault).group(1),16)
pg=re.search(r'^pgtable-fault-info:\n(.*?)(?=^[a-z])',raw,re.S|re.M).group(1)
ptes=[int(x,16) for x in re.search(r'ptes: (.*)',pg).group(1).split()]
fault_ttbr=int(re.search(r'ttbr0=(?:0x)?([0-9a-fA-F]+)',fault).group(1),16)
pg_ttbr=int(re.search(r'ttbr0: (?:0x)?([0-9a-fA-F]+)',pg).group(1),16)
assert fault_ttbr==pg_ttbr
bos_section=re.search(r'^bos:\n(.*?)(?=^[a-z])',raw,re.S|re.M).group(1)
bos=[]
for match in re.finditer(r'  - iova: ((?:0x)?[0-9a-fA-F]+)\n    size: ([0-9]+)',bos_section):
    base=int(match[1],16);size=int(match[2]);bos.append((base,size))
assert bos
contained=[dict(bo_index=n,bo_size=size,offset_bytes=iova-base) for n,(base,size) in enumerate(bos) if base<=iova<base+size]
nearest=sorted([(min(abs(iova-base),abs(iova-(base+size))),n,base,size) for n,(base,size) in enumerate(bos)])[:2]
nearest_summary=[dict(bo_index=n,bo_size=size,distance_to_edge_bytes=distance,fault_position='after' if iova>=base+size else ('before' if iova<base else 'inside')) for distance,n,base,size in nearest]
lines=decoded.splitlines();idx=next(i for i,line in enumerate(lines) if 'ESTIMATED CRASH LOCATION' in line)
tokens=lambda line:list(dict.fromkeys(re.findall(r'\bCP_[A-Z0-9_]+\b',line)))
before=[name for line in lines[max(0,idx-10):idx] for name in tokens(line)]
after=[name for line in lines[idx+1:idx+10] for name in tokens(line)]
report=dict(core_owner='glmark2',fault_direction='READ',fault_type='TRANSLATION',fault_source='CCU',captured_buffer_objects=len(bos),fault_in_listed_bo=bool(contained),containing_bo_details=contained,nearest_bo_edges=nearest_summary,page_table_descriptor_levels=len(ptes),zero_page_table_descriptors=sum(x==0 for x in ptes),estimated_stop_preceding_commands=before,estimated_stop_following_commands=after,estimated_stop_is_not_proven_trigger=True,raw_addresses_private=True,no_phone_changes=True,no_root_cause_proven=True,decoded_output_sha256=hashlib.sha256((out/'decoded-summary-private.txt').read_bytes()).hexdigest())
report.update(fault_and_page_table_ttbr_match=True,vm_history_present=bool(re.search(r'^vm-log:',raw,re.M)),bo_list_is_not_proven_complete_address_space=True)
for p in [out/'mapping-analysis.json',ref/'mapping-analysis.json']:p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
