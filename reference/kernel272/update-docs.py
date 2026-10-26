from pathlib import Path
R=Path(__file__).resolve().parent;W=R.parents[1]
p=W/'NEXT-SESSION.md';text=p.read_text()
marker='## 当前部署与启动身份'
assert text.count(marker)==1 and '[272 GW1' not in text
text=text.replace(marker,'[272 GW1主摄候选](reference/kernel272/README.md)：标准driver/静态DT/binding、匹配Image183模块和libcamera helper已编译/主机验证；未安装、未上电或刷写，主摄与Spectra仍未完成。当前部署仍为下述271组合。\n\n'+marker)
old='维护WSL `/home/cy122/x2pro-linux/camera270-kernel`，当前分支`samurai-camera-gain271`，提交`ac7ccc2da924b44aa6dff5d1be24356253890ee8`清洁；270及camera-common分支保留，未推送。'
new='维护WSL `/home/cy122/x2pro-linux/camera270-kernel` 当前为未部署开发分支`samurai-main-camera272`，提交`3184c56b7f206ab000ab79bc99eb83d35c3e1d65`清洁；部署对应的271/ac7ccc2及270、camera-common分支保留，均未推送。272源锁仅锁候选，产品camera源锁/部署锁仍为真实271。'
assert text.count(old)==1;text=text.replace(old,new)
old='GW1主摄Sunny/Qtech各10模式及含11条WRITE_BURST的初始化已做独立解析/双schema交叉核对，仍未上电或建立主摄driver/C-PHY/AF。'
new='GW1主摄两家10模式与初始化已重核，272新增driver/C-PHY静态描述候选及helper；物理chip-ID、C-PHY出帧/时序、曝光与AF仍待验。'
assert text.count(old)==1;text=text.replace(old,new)
assert len(text.encode())<=6500;p.write_text(text)
p=W/'HANDOVER-NEXT.md';text=p.read_text();marker='当前细分增益与AE实景见[271]'
assert text.count(marker)==1;text=text.replace(marker,'未部署GW1驱动/DT/helper候选及验证见[272](reference/kernel272/README.md)，'+marker);p.write_text(text)
for relative in ['linux-port/camera/README.md','linux-port/camera/kernel/README.md']:
 p=W/relative;text=p.read_text();link='../../reference/kernel272/README.md' if relative.endswith('camera/README.md') else '../../../reference/kernel272/README.md'
 intro='272未部署候选：新增GW1标准驱动、静态DT/binding和libcamera helper，编译/主机故障注入通过；现机仍为下述271，主摄出帧/AF/Spectra未完成。[候选与证据]('+link+')。\n\n'
 assert not text.startswith('272未部署候选');p.write_text(intro+text)
print('272 candidate linked; actual deployment locks preserved; NEXT bytes',len((W/'NEXT-SESSION.md').read_bytes()))
