from pathlib import Path
import json,re
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel217')
records=json.loads((private/'factory-imx471-modes-private.json').read_text())['modes'];keys=[0x0301,0x0303,0x0305,0x0306,0x0307,0x0309,0x030b,0x030d,0x030e,0x030f,0x0310,0x0820,0x0821,0x0822,0x0823,0x0900,0x0901,0x0902]
print(json.dumps([dict(index=r['index'],registers={hex(k):next((x['value'] for x in r['registers'] if x['address']==k),None) for k in keys}) for r in records]))
kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');source=(kernel/'drivers/media/i2c/imx471.c').read_text();start=source.index('static const struct cci_reg_sequence mode_1928x1088_regs');end=source.index('\n};',start)+3
(private/'current-mode-register-source-private.txt').write_text(source[start:end]);print(source[start:end])
lines=(kernel/'drivers/clk/qcom/camcc-sm8150.c').read_text().splitlines();chosen=set()
for i,line in enumerate(lines):
    if 'ftbl_cam_cc_mclk' in line or 'ftbl_cam_cc_csi' in line or 'ftbl_cam_cc_ife' in line:chosen.update(range(max(0,i-2),min(len(lines),i+20)))
(private/'camcc-rate-context-private.json').write_text(json.dumps({str(i+1):lines[i] for i in sorted(chosen)},indent=2)+'\n')
