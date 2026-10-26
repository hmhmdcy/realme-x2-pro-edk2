"""Preserve the previous checkpoint and update GNSS pointers only."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[2];p=root/'NEXT-SESSION.md';old=p.read_bytes();archive=root/'archive/NEXT-SESSION-through242-2026-10-16.md'
if archive.exists():assert archive.read_bytes()==old or 'reference/kernel243/README.md' in old.decode('utf-8-sig')
else:archive.write_bytes(old)
s=old.decode('utf-8-sig');lines=s.splitlines()
lines[2]='2026-10-16 GNSS243：保持Linux/236启动，开窗及关闭Wi-Fi各90秒，1722有效SNR全0/SEARCH。idle两次ldo10栈属UFS。active PDC与207相同，7项init匹配ROM；DIAG仅首次VERSION成功，无GNSS诊断测量。根因未定。[243](reference/kernel243/README.md)、[相关修复](reference/kernel243/RELATED-LINUX-GNSS.md)。Wi-Fi已恢复连接，三DSP/taint0/新增故障0；其它沿用240。'
for i,line in enumerate(lines):
 if line.startswith(('GNSS见[242]','GNSS见[243]')):
  lines[i]='GNSS见[243](reference/kernel243/README.md)：两轮仍0；ldo10的UFS调用栈/live DT吻合，不能认LNA；RF指标/AP clk/genpd不足定因。DIAG原control peer断开/重连失败，无GNSS mask或NV写入。MM/辅助worker idle，探针/trace均收尾，Wi-Fi恢复连接。保持Linux，无Android运行报文。[242原检查点](archive/NEXT-SESSION-through242-2026-10-16.md)保留。其它待办保持。'
s='\n'.join(lines)+'\n'
s=s.replace('当前没有安排新手机操作。','当前探针已收尾。').replace('当前MM/辅助worker idle，所有探针/trace已收尾。','MM/辅助worker idle，探针/trace已收尾。')
assert len(s.encode())<=6500,(len(s.encode()),6500);p.write_text(s)
p=root/'linux-port/docs/HARDWARE-STATUS.md';s=p.read_text(encoding='utf-8-sig')
s=s.replace('242于2026-10-16继续GNSS专项','243于2026-10-16继续GNSS专项').replace('[242文件一致性与时钟关联采集](../../reference/kernel242/README.md)','[243开窗/PDC/DIAG采集](../../reference/kernel243/README.md)')
lines=s.splitlines()
for i,line in enumerate(lines):
 if line.startswith('| GNSS定位 |'):
  lines[i]='| GNSS定位 | 243保持Linux开窗/关闭Wi-Fi各90秒，862+860有效SNR全0/SEARCH，121事件缺列表；无TRACK/fix。idle35秒两次ldo10栈属UFS，live DT vcc引用ldo10。active PDC与207相同，7项vendor init匹配ROM；DIAG仅首次VERSION55字节成功，control peer断开/重连失败，未发GNSS mask。110项归档核验，探针/trace/端点收尾，Wi-Fi恢复连接，三DSP/taint0/新增故障0；242文件一致性保持 | 根因未定。关闭Wi-Fi未恢复不等于排除全部干扰；RF指标/AP clk/genpd非LNA/物理时钟诊断，idle栈未逐条归因此前28条事件。无modem GNSS DIAG测量/Android运行报文。用户室内开窗/无SIM，报告其它手机可接收；保持Linux、不刷Android，不猜LNA接线、盲持RF票或写NV。其它手机修复及范围见243研究 |'
p.write_text('\n'.join(lines)+'\n')
p=root/'DOCS-INDEX.md';s=p.read_text(encoding='utf-8-sig');s=s.replace('| GNSS标准链路、相关机型与modem文件服务 | [242','| GNSS标准链路、相关机型与modem文件服务 | [243开窗/PDC/DIAG与其它手机修复](reference/kernel243/README.md)、[242');p.write_text(s)
print(json.dumps(dict(stage=243,checkpoint_characters=len((root/'NEXT-SESSION.md').read_text()),previous_checkpoint_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),entrypoints_updated=3)))
