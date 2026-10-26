from pathlib import Path
import json
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel119'
source=json.loads((ref/'mesa-source-validation.json').read_text())
build=json.loads((ref/'crashdec-build-validation.json').read_text())
decode=json.loads((ref/'decode-validation.json').read_text())
mapping=json.loads((ref/'mapping-analysis.json').read_text())
assert decode['decoder_exit']==0 and decode['estimated_location_found'] and mapping['fault_and_page_table_ttbr_match']
marker='## 离线Mesa解码完成，保留根因边界'
session=root/'sessions/119-k118-deployment-and-real-gpu-pixel-failure.md'
text=session.read_text();assert marker not in text
text+=f'''\n{marker}\n\n[官方Mesa 26.2.4归档](https://archive.mesa3d.org/mesa-26.2.4.tar.xz)通过HTTPS下载，SHA256 {source['archive_sha256']}；未声称GPG签名认证。源码解压到118的E盘ext4隔离卷mesa-offline，版本文件26.2.4。初次tar路径守卫不接受顶层目录无斜杠，未解压；修正为Path.parts首段精确匹配及无父路径，data过滤后解压。WSL闲置卸载导致第一次挂载守卫拒绝，fetch/build/decode均增加同进程ensure-build-volume。电脑Ubuntu官方源新增Meson/Ninja/pkg-config/Mako/XML/DRM/Lua/archive开发依赖，约30MiB安装，不改手机APK。\n\n初次配置缺Lua，虽Meson返回0但没有crashdec目标；保留日志，补依赖后clearcache/reconfigure成功。一次构建提前于配置完成，Meson锁拒绝，未绕过锁；等待配置进程退出后继续。只请求src/freedreno/decode/crashdec及其依赖272目标，不编译/部署Mesa图形驱动，不执行replay。原始编译警告保留。x86_64解码器SHA256 {build['binary_sha256']}，私有副本gpu-coredump/crashdec-mesa26.2.4-x86_64。\n\n私有devcd2原hash先核验；crashdec -s -f、RNN_PATH指定同版本寄存器XML，CPU40秒/墙钟50秒/地址空间1GiB/文件32MiB/无自身core限制。实际{decode['wall_seconds']}秒、exit0、输出{decode['output_bytes']}字节、无缺失寄存器数据库，找到ESTIMATED CRASH LOCATION；完整输出只在gpu-coredump/decoded-summary-private.txt，SHA256 {mapping['decoded_output_sha256']}。解码不接触手机，不上传dump。\n\n转储comm精确glmark2，fault READ/TRANSLATION/CCU；fault-info与pgtable-fault-info TTBR一致。51个BO中没有包含fault IOVA，最近BO边界相距36864/40960字节，四级页表描述符有1个0。估算停止前CP_WAIT_FOR_ME、CP_SET_MODE，后CP_SET_BIN_DATA5、CP_SET_VISIBILITY_OVERRIDE。没有vm-log历史，不能证明use-after-free/错误buffer基址/CCU cache状态哪项是原因。当前内核msm_gpu.c crashstate_get_bos的非VM_BIND分支只枚举submit->bos，VM_BIND分支枚举VM映射；BO列表不是完整地址空间的无条件证明。Mesa文档明确流水线导致停止位置可能晚于触发状态，不能直接修改CP_SET_BIN_DATA5。mapping-analysis.json公开只保留计数/相对边界/命令名称，不公开地址或shader/raw buffers。\n\n后续优先继续旧glmark resize/FBO静态复现及RB/CCU render-target映射分析，再设计小负载的单场景验收；禁止重跑整套33负载、重放或全桌面debug开关。此轮GPU离线分析已得到边界，暂转摄像头CCI/CAMCC/C-PHY/DMA/ICC资源核对，符合长難项留档后换项。最终SSH复核#118/taint0/Phosh3492/Phoc3190/DPU2/GPU1/PCM双closed/SLPI offline，无追加GPU故障。\n'''
session.write_text(text)
note='Mesa26.2.4官方源码离线crashdec已成功：51 BO不包含fault IOVA、TTBR一致、1个零页表项，估算停止在CP_WAIT_FOR_ME/CP_SET_BIN_DATA5附近；无VM历史，根因未证明，先转摄像头资源核对。'
for name in ['README.md','FLYWHEEL.md','linux-port/docs/HARDWARE-STATUS.md']:
    p=root/name;text=p.read_text();anchor='NV6/source4/vendor/persist/GPT及音频空闲保持，goal继续active。'
    assert anchor in text
    p.write_text(text.replace(anchor,anchor+' '+note,1))
p=root/'NEXT-SESSION.md';text=p.read_text()
text=text.replace('按Mesa官方Freedreno文档离线crashdec，读固定源码/SQE反汇编；',note+' 固定源码及解码器已在E盘118卷mesa-offline，公开计数见reference/kernel119/decode-validation.json/mapping-analysis.json；进一步可查RB/CCU基址及SQE反汇编；')
text=text.replace('下一可继续CCI/CAMCC/C-PHY/DMA/ICC/QoS与本机19781资源。','下一优先继续CCI/CAMCC/C-PHY/DMA/ICC/QoS与本机19781资源。')
p.write_text(text)
print('DECODE_COMPLETE_WITH_ROOT_CAUSE_BOUNDARY_DOCUMENTED')
