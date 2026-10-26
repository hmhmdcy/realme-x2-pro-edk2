from pathlib import Path
import difflib
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel105';out=Path('/mnt/e/edk2-samurai-out/kernel105')
p=Path('/home/cy122/x2pro-linux/linux/drivers/soc/qcom/apr.c')
old=p.read_text();assert old==(ref/'apr.c.after').read_text()
needle='cleanup_srcu:\n\tcleanup_srcu_struct(&apr->apr_srcu);\nhandle_release:'
assert old.count(needle)==1
new=old.replace(needle,'cleanup_srcu:\n\tpdr_handle_release(apr->pdr);\n\tdestroy_workqueue(apr->rxwq);\n\tcleanup_srcu_struct(&apr->apr_srcu);\n\treturn ret;\nhandle_release:')
p.write_text(new);(ref/'apr.c.after').write_text(new)
before=(out/'apr-before.c').read_text()
(ref/'apr.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),new.splitlines(True),fromfile='a/drivers/soc/qcom/apr.c',tofile='b/drivers/soc/qcom/apr.c')))
for n in ['target-build.log','kernel-build.log','kernel-validation.json']:
    source=out/n;target=out/(n+'.before-srcu-cleanup')
    assert source.exists() and not target.exists();source.rename(target)
print('SRCU_ERROR_PATH_DRAINS_WORK_BEFORE_CLEANUP')
