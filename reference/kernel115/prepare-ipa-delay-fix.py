from pathlib import Path
import subprocess,json,hashlib
k=Path('/home/cy122/pmos-samurai-kernel115/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel115')
p=k/'drivers/net/ipa/reg/ipa_reg-v4.1.c'
t=p.read_text()
assert 'ENDP_INIT_CTRL' not in t
out.joinpath('ipa-reg-v4.1-before-delay-fix.c').write_text(t)
needle='static const u32 reg_endp_init_cfg_fmask[] = {'
assert t.count(needle)==1
t=t.replace(needle,'''/* IPA 4.1 still supports TX delay; RX suspend was removed in 4.0. */
static const u32 reg_endp_init_ctrl_fmask[] = {
\t[ENDP_DELAY] = BIT(1),
};

REG_STRIDE_FIELDS(ENDP_INIT_CTRL, endp_init_ctrl, 0x00000800, 0x0070);

'''+needle)
needle='\t[ENDP_INIT_CFG]'
idx=t.index(needle)
t=t[:idx]+'\t[ENDP_INIT_CTRL]\t\t= &reg_endp_init_ctrl,\n'+t[idx:]
p.write_text(t)
subprocess.run(['git','diff','--check','--','drivers/net/ipa/reg/ipa_reg-v4.1.c'],cwd=k,check=True)
out.joinpath('ipa-delay-fix.patch').write_bytes(subprocess.check_output(['diff','-u',str(out/'ipa-reg-v4.1-before-delay-fix.c'),str(p)]) if False else b'')
result=subprocess.run(['diff','-u',str(out/'ipa-reg-v4.1-before-delay-fix.c'),str(p)],capture_output=True)
assert result.returncode==1
out.joinpath('ipa-delay-fix.patch').write_bytes(result.stdout)
print('IPA4_1_TX_DELAY_REGISTER_SOURCE_FIX_READY_NOT_DEPLOYED')
