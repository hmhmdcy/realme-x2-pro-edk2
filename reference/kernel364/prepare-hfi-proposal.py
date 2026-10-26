"""Prepare a stricter A5 handshake off-tree while the pinned363 build runs."""
from pathlib import Path
import difflib,json
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel364');P.mkdir(mode=0o700,exist_ok=True)
assert json.loads((HERE.parent/'kernel363/firmware-init-validation.json').read_text())['initialization_success_value']==1
name='drivers/media/platform/qcom/camss/camss-icp-a5-boot.c'
before=(HERE.parent/'kernel356/kernel/camss-icp-a5-boot.c').read_text();s=before
a='value || READ_ONCE(a5->boot_expired), 100, 500000);'
b='value == 1 || value == 2 || READ_ONCE(a5->boot_expired),\n\t\t\t\t 100, 500000);'
assert s.count(a)==1;s=s.replace(a,b)
a='''	/* The retained OEM host rejects 2 and a persistent 0, but continues
	 * after other nonzero responses. This image/hardware reports 3.
	 * Treat that as permission to try SYS_INIT, never as proof of success:
	 * the complete typed response must still acknowledge initialization.
	 */
	if (value != 1 && value != 3) {'''
b='''	/* The retained firmware entry writes 1 only after its host interface
	 * is ready, or 2 on failure. Other values must not shorten the wait
	 * and let SYS_INIT race firmware initialization.
	 */
	if (value != 1) {'''
assert s.count(a)==1;s=s.replace(a,b)
(P/'boot-proposed.c').write_text(s)
(HERE/'exact-hfi-ready.patch').write_text(''.join(difflib.unified_diff(before.splitlines(keepends=True),s.splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name)))
(HERE/'proposal-state.json').write_text(json.dumps(dict(stage=364,off_tree_only=True,active363_source_untouched=True,firmware_evidence='../kernel363/firmware-init-validation.json',applied=False,built_kernel_module=False,installed=False),indent=2)+'\n')
print('Prepared strict HFI-ready proposal off-tree; active363 source unchanged.')
