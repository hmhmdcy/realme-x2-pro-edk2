from pathlib import Path
import json
root=Path('/mnt/e/RealmeX2Pro edk2'); ref=root / 'reference/kernel147'
v=json.loads((ref / 'gpu-regression-validation.json').read_text())
c=json.loads((ref / 'closeout-validation.json').read_text())
assert v['device_fix_accepted'] and c['gpu_faults']==0 and c['source_integrity_pass']
session='''# A640 GMEM 迟发 CCU fault 修复（阶段147，2026-10-13）

本次GPU目标完成：已修复并实机验收此前固定800×600 glmark2成功退出后出现的CCU READ TRANSLATION故障。手机当前#147/software132，boot132、logdump147、770模块132。仅刷logdump。

修复为A640内核管理私有GPU VM的IOVA起点采用64KiB对齐；默认及其他GPU仍按PAGE_SIZE，用户管理VM_BIND地址由用户态选择。BO大小、实际映射范围保持，虚拟地址空隙不映射物理内存。#146无效的CCU事件顺序实验已撤销。独立补丁在[reference/kernel147/a640-managed-iova-alignment.patch](../reference/kernel147/a640-managed-iova-alignment.patch)，其他原有源码差异已核对保留。

证据链包括原#145默认GMEM失败、#146多个隔离对照、#147实际RD中BO起点对齐确认。原版转储30条BO记录全部不满足64KiB对齐，#147对应30条全部对齐；它们各有18个不同BO、3次提交。该实验指向本机GMEM resolve地址对齐问题，尚不等同于证明所有Adreno的硬件规范。固定提交的原厂KGSL也提高大导入缓冲区对齐，来源见reference/kernel147/oem-alignment-source-validation.json。

同一#147启动通过20次800×600像素验证：带RD默认build8、无RD默认build4、不用VBO2、最近邻纹理3、线性纹理3；又通过6次1080×2259连续绘制：build、线性纹理、Phong各2次，每轮2秒。默认Mesa策略保持，未强制sysmem或关闭UBWC/binning。每次退出观察35、40或90秒，总26次退出无GPU fault，taint0，警告、DPU timeout、DSI error、DMA prepare计数均为0，桌面进程身份保持。每组提交追踪没有丢事件，所有归档和内部文件SHA256已验证。

连续绘制实际使用1080×2259，首个控制脚本误要求800×600而中断；修正尺寸断言后复核原始结果并继续剩余场景，未重复已经完成的GPU负载。两个分辨率分别记录，未把benchmark当作像素验证。

W=1 MSM与完整Image/modules/DTB编译无警告；config与DTB保持，770模块逐字节等同132。刷写前重新核验#146实际身份、静止状态、分区和来源；唯一F1收据后确认fastboot身份/产品/几何再刷logdump。实机logdump读回匹配，boot与persist哈希保持。结束时NV、原厂来源、模块校验通过，没有遗留临时GPU追踪或待取core。源代码验收后只改了一行说明注释，不改变已部署机器码的行为。

当前验收范围是本机A640旧式内核管理私有VM的GLES默认GMEM路径。Vulkan用户管理VM_BIND、其他GPU型号未验收。显示启动偶发问题、音频、充电和其他整机适配问题仍是独立待办，本次干净窗口不代表它们已修复。

实机与校验报告见reference/kernel147/gpu-regression-validation.json、closeout-validation.json、build-package-validation.json、rd-alignment-validation.json。原始core/RD、BO地址、启动身份及刷写收据只在E:/edk2-samurai-out/kernel146和kernel147。原#145回退镜像保留；再次切换必须确认当前#147状态，不能重用部署前#146收据。
'''
(root / 'sessions/147-a640-gmem-alignment-fix.md').write_text(session)
nexttext='''# Realme X2 Pro继续检查点（阶段147，2026-10-13）

当前操作边界仅以[WORKING-BOUNDARIES](WORKING-BOUNDARIES.md)为准。

本次GPU目标已完成：A640内核管理私有VM的IOVA起点改为64KiB对齐，撤销无效的146 CCU事件顺序改动。原145的固定800×600像素成功后迟发CCU READ TRANSLATION已不再复现。#147同一启动通过20次像素验证和6次1080×2259持续绘制，逐次退出后35–90秒观察无fault，taint0、GPU/WARN/DPU/DSI/DMA prepare均为0，桌面保持；默认Mesa GMEM策略，未采用sysmem全局绕过。

当前手机#147/software132：boot132/logdump147/modules132/rootfs132，仅刷logdump。完整源码/Image在WSL /home/cy122/pmos-samurai-kernel136/kernel（目录136不代表版本），Image和可刷logdump在私有E:/edk2-samurai-out/kernel147。770模块与132逐字节相同，config/DTB保持；结束时boot/persist/NV/来源/模块核验通过，临时GPU实例清除，没有待取core。

详见[147修复与验收](sessions/147-a640-gmem-alignment-fix.md)、[146隔离实验](sessions/146-gpu-gmem-isolation.md)和[147补丁与报告](reference/kernel147/README.md)。私有当前启动身份为E:/edk2-samurai-out/kernel147/embedded-boot-id-private.txt和手机/var/lib/samurai/k147-closeout/boot-id-private.txt。再次刷写或重启必须重新检查实际状态，不重用146启动身份及147部署收据。

本次范围：A640旧式内核管理私有VM/GLES GMEM；Vulkan用户管理VM_BIND与其他型号未验收。整机显示启动偶发问题、音频、充电等仍未解决，不把本次干净窗口当作整机适配完成。

原145回退镜像仍保留。旧118诊断构建卷从封存恢复到E:/edk2-samurai-out/kernel118/build-volume.ext4，原压缩备份保持；使用它前在同一WSL调用中确认挂载。解压时检查Windows实际卷空间，不能只看WSL虚拟容量。C盘本轮不完整解压文件已移除，临时腾挪的原下载文件已复原并核验。
'''
(root / 'NEXT-SESSION.md').write_text(nexttext)
(root / 'NEXT-SESSION-PROMPT.md').write_text('''# 下一会话短提示词

继续Realme X2 Pro postmarketOS适配，当前规则见WORKING-BOUNDARIES.md。最新手机#147/software132，仅刷logdump；A640旧式VM/GLES GMEM迟发CCU fault已用64KiB IOVA对齐修复，20次像素验证+6次持续绘制和退出35–90秒观察全部无fault，taint0，显示/警告/DMA错误计数0。详见NEXT-SESSION.md及sessions/147-a640-gmem-alignment-fix.md。

源码/Image仍在WSL kernel136目录，实际版本147。147补丁和报告在reference/kernel147；私有产物、启动身份、刷写与原始RD/core在E:/edk2-samurai-out/kernel147。再次切换先查当前状态，不复用146身份与旧收据。Vulkan用户管理VM_BIND、其他GPU型号未验收；显示启动偶发问题、音频、充电等整机待办保持。
''')
readme=root / 'README.md'; text=readme.read_text(); anchor='当前阶段145收尾：'
at=text.index(anchor)
intro='''当前阶段147：A640旧式内核管理GPU VM采用64KiB IOVA起点对齐，已修复复现的GMEM迟发CCU fault。只刷logdump部署#147/software132；20次800×600像素验证和6次1080×2259连续绘制，逐次退出35–90秒观察无fault，taint0，GPU/WARN/DPU/DSI/DMA错误计数均0。770模块、config/DTB与原厂来源保持；当前GPU范围验收通过，Vulkan用户管理VM_BIND和整机其他适配问题未验收。

详见[147修复与验收](sessions/147-a640-gmem-alignment-fix.md)与[补丁和报告](reference/kernel147/README.md)。下方为历史记录，不能作为当前状态依据。

'''
readme.write_text(text[:at]+intro+text[at:])
summary=ref / 'README.md'; text=summary.read_text()
text=text.replace('a640-managed-iova-alignment-diagnostic.patch','a640-managed-iova-alignment.patch')
start=text.index('#147转储实际BO地址'); end=text.index('\n\n相关证据',start)
text=text[:start]+'#147真实转储已确认BO起点全部64KiB对齐。完整回归通过20次800×600像素验证和6次1080×2259持续绘制，26次退出后观察35–90秒均无fault、taint0，GPU/警告/显示/DMA错误计数为0。验收见gpu-regression-validation.json及closeout-validation.json；默认GMEM策略保持。'+text[end:]
summary.write_text(text)
print('K147_SOURCE_BACKED_CHECKPOINT_AND_GPU_CLOSEOUT_WRITTEN')
