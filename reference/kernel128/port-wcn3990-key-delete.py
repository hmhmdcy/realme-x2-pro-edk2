from pathlib import Path
import difflib,hashlib,json,subprocess
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128';k=Path('/home/cy122/pmos-samurai-kernel128/kernel')
assert json.loads((ref/'key-delete-baseline-validation.json').read_text())['narrow_wcn3990_snoc_patch_justified']
assert (ref/'candidate-source-validation.json').is_file() and not (ref/'wcn3990-snoc-key-delete.patch').exists()
relative='drivers/net/wireless/ath/ath10k/mac.c';p=k/relative;old=p.read_text()
start=old.index('static int ath10k_install_key(');end=old.index('\n}',start)+2;part=old[start:end]
needle='\ttime_left = wait_for_completion_timeout(&ar->install_key_done, 3 * HZ);'
assert part.count(needle)==1
newpart=part.replace(needle,'''\t/* WCN3990/SNOC sends no security indication for cipher-none pairwise
\t * deletion. The WMI send above must still succeed. Group deletion
\t * installs a random replacement key and keeps its completion wait.
\t */
\tif (cmd == DISABLE_KEY && !(flags & WMI_KEY_GROUP) &&
\t    ar->hw_rev == ATH10K_HW_WCN3990 &&
\t    ar->hif.bus == ATH10K_BUS_SNOC)
\t\treturn 0;

'''+needle)
new=old[:start]+newpart+old[end:]
assert old[:start]==new[:start] and old[end:]==new[start+len(newpart):]
p.write_text(new)
patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative))
(ref/'wcn3990-snoc-key-delete.patch').write_text(patch)
subprocess.run(['git','diff','--check','--',relative],cwd=k,check=True)
report=dict(candidate=128,base=126,changed_files=[relative],
 only_wcn3990_snoc_pairwise_disable_skips_absent_completion=True,
 send_error_propagation_preserved=True,set_key_group_delete_other_bus_other_hardware_wait_preserved=True,
 nohwcrypt_unchanged=True,send_key_random_group_replacement_unchanged=True,
 no_struct_or_exported_api_change=True,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
 firmware_calibration_regulatory_nv_unchanged=True,not_deployed=True)
(ref/'key-delete-port-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
