from pathlib import Path
import json
root=Path('/mnt/e/RealmeX2Pro edk2')
report=json.loads((root/'reference/kernel122/host-volume-validation.json').read_text())
assert report['rootfs122_unmounted'] and all(v['offline_readonly_fsck_exit']==0 for v in report['volumes'])
p=root/'sessions/122-complete-k121-rootfs-and-verified-build-cleanup.md'
t=p.read_text().replace('才进行专项清理；','才完成专项清理；')
t+='\n收尾核验：122新建E构建卷已卸载，离线只读e2fsck退出0；118卷亦未挂载。原WSL VHD没有fsck或扩容。最终C可用约%.2fGiB，E可用约%.2fGiB。已验证清理的E初版raw两份实际占用3,897,139,200字节、重复export实际占用1,887,260,672字节；修正版、失败simg/manifest及回退均保留。\n' % (report['host_c_free_bytes']/1024**3,report['host_e_free_bytes']/1024**3)
p.write_text(t)
p=root/'NEXT-SESSION.md';t=p.read_text()
t=t.replace('C仅约2.4GiB，禁止向C复制大kernel/Mesa树或扩大原VHD。','阶段122清理并观察回收后C约14.35GiB；新kernel/Mesa/rootfs仍优先放E构建卷，不扩大原VHD。')
t=t.replace('完整rootfs121未生成，下一优先从fixed115兼容基线完成匹配121软件rootfs与Image/模块/DTB/启动产物核验，再推进CAMSS DT/C-PHY/DMA/ICC/QoS。','此处原121检查点的rootfs缺口已由122完成匹配121软件rootfs及启动产物核验；下一推进CAMSS DT/C-PHY/DMA/ICC/QoS。')
p.write_text(t)
print('DOCS122_CLOSURE_RECORDED')
