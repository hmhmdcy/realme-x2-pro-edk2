from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel244');root=R.parents[1]
for p in R.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
lock=dict(stage=244,local_sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.iterdir()) if p.suffix in ['.py','.ps1','.initd']},
 upstream_diag_commit='23c12c167e93215853af4e59c021551767f6fec8',android_diag_commit='bf51f920fdef2acb189f5c2e282148279a1f12c9',
 protocol_sources=json.loads((P/'protocol-source/manifest-private.json').read_text()),gnss_layout_sources=json.loads((P/'gnss-layouts/manifest-private.json').read_text()),
 log_code_header={k:v for k,v in json.loads((P/'protocol-source/log-code-hits-private.json').read_text()).items() if k!='matches'})
(R/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
obs=json.loads((P/'observe-nextboot-private.json').read_text());transition=json.loads((P/'normal-reboot-request-private.json').read_text());transition.update(transition_pending=False,new_boot_confirmed=True,new_boot=obs['private']['boot']);(P/'normal-reboot-completion-private.json').write_text(json.dumps(transition,indent=2)+'\n')
health=json.loads((R/'final-health-validation.json').read_text());(P/'current-checkpoint-private.json').write_text(json.dumps(dict(stage=244,goal_active=True,gnss_fix_verified=False,guard='/var/lib/samurai/k244-runtime/boot-id-private.txt',health=health,all_workers_terminal=True,boot_hook_removed=True,archive_members=44),indent=2)+'\n')
p=root/'NEXT-SESSION.md';old=p.read_bytes();archive=root/'archive/NEXT-SESSION-through243-2026-10-16.md'
if not archive.exists():archive.write_bytes(old)
lines=old.decode('utf-8-sig').splitlines();lines[2]='2026-10-16 GNSS244：保持Linux，普通重启后首次DIAG握手/两ID分配成功，90秒取得GPS/GLO/Gal各90份测量日志，均NumValidReports0；同期QMI89事件缺SV列表，不能计零CNR。仍无fix，goal active。[244](reference/kernel244/README.md)。临时hook已移除，三DSP/Wi-Fi正常、taint0；其它验收沿用240。'
for i,line in enumerate(lines):
 if line.startswith('236启动/boot235，guard'):
  lines[i]='244启动/boot235/Image183（普通重启、未刷写），guard `/var/lib/samurai/k244-runtime/boot-id-private.txt`，236及更早无效。运输`reference/kernel244/host.py`，私有端点/当前状态`E:/edk2-samurai-out/kernel244`，严格原SSH密钥。244全部worker退出，44项原生归档核验，DIAG端点及临时启动项清理，切换已确认。'
 if line.startswith('最后核对：'):lines[i]='240核对（244未重做全机验收）：'+line[len('最后核对：'):]
 if line.startswith('GNSS见[243]') or line.startswith('GNSS见[244]'):
  lines[i]='GNSS见[244](reference/kernel244/README.md)：真实测量均无有效SV，缺字段不算0；前41 GPS周65535、后49周2440，UTC并非全程准备。首次启动DIAG可采，关闭后重连仍失败。下一轮保持端点、先准备时间，增加Clock1478、PRX147e/DRX147f等日志；未据此猜GPIO/NV。原[243](reference/kernel243/README.md)开窗/WLAN零CNR和UFS归因保留。goal继续定位可用；其它待办保持。'
s='\n'.join(lines)+'\n';assert len(s.encode())<=6500,len(s.encode());p.write_text(s)
p=root/'linux-port/docs/HARDWARE-STATUS.md';s=p.read_text(encoding='utf-8-sig').replace('243于2026-10-16继续GNSS专项','244于2026-10-16继续GNSS专项').replace('[243开窗/PDC/DIAG采集](../../reference/kernel243/README.md)','[244真实DIAG测量](../../reference/kernel244/README.md)');lines=s.splitlines()
for i,line in enumerate(lines):
 if line.startswith('| GNSS定位 |'):
  lines[i]='| GNSS定位 | 244普通Linux重启、未刷写；在modem首次启动前完成DIAG feature/两个ID协商。90秒GPS/GLO/Gal各90份真实测量，全部NumValidReports0、无CNo字段；QMI89事件缺SV列表。时间周从65535变2440。正常Stop/release/close，发送日志mask清零/实时模式释放，44项归档核验，临时hook清理；三DSP/Wi-Fi正常，新boot fault0/taint0。243开窗/WLAN零CNR及UFS归因保持 | 定位仍不可用，goal active。测量条目为空不能计零CNR；首次启动DIAG可用但重连未修。须加入Clock/RF HW状态日志并核版本，先确认UTC准备。AP clk/genpd及ldo10事件不能直接证明LNA状态；不猜GPIO或写NV。当前Linux guard为k244-runtime，236失效；其他功能未全机重验 |'
p.write_text('\n'.join(lines)+'\n')
p=root/'DOCS-INDEX.md';s=p.read_text(encoding='utf-8-sig').replace('| GNSS标准链路、相关机型与modem文件服务 | [243','| GNSS标准链路、相关机型与modem文件服务 | [244首次启动DIAG与真实测量](reference/kernel244/README.md)、[243');p.write_text(s)
print(json.dumps(dict(stage=244,locked_sources=len(lock['local_sources']),new_boot_checkpoint_written=True,goal_active=True,checkpoint_bytes=len((root/'NEXT-SESSION.md').read_bytes()))))
