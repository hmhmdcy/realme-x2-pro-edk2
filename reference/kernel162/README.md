# 162：拒收161后回退原版158

161空RMR候选的新boot出现WCD934x WARN及917条SLIMbus DMA prepare失败，因此未通过软件验收；显示管线本身零错误，但实体白屏未验证。按当前161身份保存失败日志，并在只为停机接受那一个已记录音频WARN的严格守卫下完成全部静默、NV/分区/模块核验和F2FS冻结。单次F1正常进入bootloader，只刷回独立原始158 logdump；没有紧急SysRq。[停机边界](rollback-tools-validation.json)

新boot实际内核158，自动Phoc18.43/Phosh20.24秒，27.47秒运行采样全bootKMS/DSI/DPU/GPU/WARN和音频DMA prepare均0、taint0。原版logdump读回相同，boot/persist、模块132、NV和Mesa149修复保持；不能据这一启动宣称音频问题永久修复。[运行核验](runtime-validation.json)、[启动时间](boot-timing-validation.json)

SMMU161源码改动已恢复，14个158显示文件和其它修改均保持。按原时间重新构建得到#158主Image，SHA256为`1a96e606e35e9f7c69087867e3a8c6e6a502d929eb33c2b708bb5a51ede338cd`，与原始158 Image不相同，未用于本次回退；回退仍使用原始已验证logdump158。后续构建不能拿重建Image假充原始回退包。[重建记录](restored-source-build-validation.json)

用户已去睡觉。160反馈的edk2消失后、首个Linux命令行前白屏花屏仍是开放故障；本轮回退没有实体观察。163正在准备在TLMM就绪后提前保持面板复位，继续保留158正常SMMU流程及首帧背光策略。goal仍active。
