from pathlib import Path
import difflib,hashlib,json
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel105';out=Path('/mnt/e/edk2-samurai-out/kernel105')
p=Path('/home/cy122/x2pro-linux/linux/drivers/remoteproc/qcom_q6v5.c')
old=p.read_text()
assert old==(ref/'q6v5.c.after').read_text()
assert not (out/'q6v5-global-only.c').exists()
(out/'q6v5-global-only.c').write_text(old)
needle='\telse\n\t\tdev_err(q6v5->dev, "%s without message\\n", event);\n}'
assert old.count(needle)==1
new=old.replace(needle,'''\telse
\t\tdev_err(q6v5->dev, "%s without message\\n", event);
\t/* Host ANY resolves global SMEM, not the APPS/MODEM private partition. */
\tif (!text_len && q6v5->crash_reason == 421 &&
\t    of_machine_is_compatible("realme,samurai")) {
\t\tlen = 0;
\t\tmsg = qcom_smem_get(1, q6v5->crash_reason, &len);
\t\ttext_len = !IS_ERR(msg) && len ?
\t\t\tstrnlen(msg, min_t(size_t, len, 4096)) : 0;
\t\tdev_err(q6v5->dev,
\t\t\t"samurai crash SMEM modem-host=1 item=421 error=%ld bytes=%zu text=%zu\\n",
\t\t\tIS_ERR(msg) ? PTR_ERR(msg) : 0, len, text_len);
\t\tif (text_len)
\t\t\tdev_err(q6v5->dev, "modem partition reason: %.*s\\n",
\t\t\t\t(int)text_len, msg);
\t}
}''')
p.write_text(new);(ref/'q6v5.c.after').write_text(new)
before=(out/'q6v5-before.c').read_text()
(ref/'q6v5.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),new.splitlines(True),fromfile='a/drivers/remoteproc/qcom_q6v5.c',tofile='b/drivers/remoteproc/qcom_q6v5.c')))
for n in ['target-build.log','kernel-build.log','kernel-validation.json']:
    source=out/n;target=out/(n+'.global-only')
    assert source.exists() and not target.exists();source.rename(target)
print('READONLY_MODEM_PRIVATE_SMEM_DIAGNOSTIC_ADDED')
