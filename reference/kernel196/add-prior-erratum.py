from pathlib import Path
import hashlib,json
root=Path('/mnt/e/RealmeX2Pro edk2');p=root/'reference/kernel193/README.md';out=Path('/mnt/e/edk2-samurai-out/kernel196');old=p.read_bytes();assert '阶段196勘误' not in old.decode();(out/'kernel193-readme-before-erratum-private.md').write_bytes(old)
needle='只读映射此一个TLMM寄存器用于取得原配置及比较，所有引脚写入经过pinctrl/GPIO接口。';s=old.decode();assert needle in s
s=s.replace(needle,needle+'\n\n阶段196勘误：按当前DT的reg-names与SM8150 group映射，GPIO15的north地址为0x0390f000。193 helper只读的0x0310f000位于west，因此上述整值比较不能证明GPIO15恢复。正常pinctrl/clk/GPIO/CCI路径取得实体ID的证据保留；196另按实际资源核对三处CTL与方向/电平并恢复，见[196报告](../kernel196/README.md)。');p.write_text(s)
print(json.dumps(dict(prior_report_erratum_added=True,original_sha256=hashlib.sha256(old).hexdigest())))
