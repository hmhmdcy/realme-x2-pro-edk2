# 软件Full候选v2：人为INHIBIT门控

后续部署状态：根会话已将本目录冻结源码构建的模块作为r6安装，[更新](../../charging-management-20261023/r6-update-result.json)与[INHIBIT/AUTO](../../charging-management-20261023/r6-smoke-result.json)通过；实体Full/再充仍待验。下文保留本候选制作时的范围与离线证据，不将安装读回当完整循环验收。

2026-10-23。独立复制已冻结v1八个内核文件，原件指纹见[baseline.json](baseline.json)。未修改v1源码/receipt/patch、主生产r5、设备、SDK或共享kernel。相对于v1的[小补丁](full-integration.patch)仅改变C调用门、Full helper新增skip、cycle准确注释；完整候选八文件可供根会话私有增量编译。

`auto_requested=false`时调用`sm_oem_full_skip()`：保留已建立的logical Full/cause，清SW/HW电压/recharge未完成streak，不建立新Full、不产生recharge/entered事件、不请求正常converter hold，也不把人为停止伪装成ENODATA或真实detach。真实采样、源核对、保护和故障锁存仍每秒执行；实际写门继续保留用户双抑制意图。重新AUTO后从fresh合格首份证据起计，旧五份SW或三份再充不能借用为第六份。

这项门控是根据[原厂MMI调用链审查](../../charging-oem-audit-20261023/manual-inhibit-audit/README.md)有意收敛原厂缺口，不声称原厂已有同样上层门。计时仍是本适配的BOOTTIME连接周期加合格Full重置，**不新增“只累计实际充电时间”语义**；人为INHIBIT本身不暂停timer或抹掉既有超时。原始REG13硬件Full仍可作为真实遥测和原有健康硬件计时边界，但INHIBIT期间不创建新的logical Full。AUTO下非5秒tick的真实硬件Full仍立即转正常Full保持，避免限值变化路径短暂使能CHG。

[离线结果](test-result.json)全部ASan/UBSan通过：实际候选step现26条序列/223断言，新增INHIBIT高电压/非充入11份不成Full、五份SW后暂停不借第六、已有Full时停止并保留事实、三份再充后停止打断、重新AUTO需全新六份、停止期间真实fault/timeout/source未知保留。原v1的真实detach、36000秒新Full边界、旧timeout优先、硬件Full非tick预算下降等继续通过；Full事务14/97、真实gauge7/20、组件16/251、OEM差分52及原core6016/113/8均保持。

结果逐个核对冻结v1八文件和主生产七文件仍原SHA。根会话已完成[私有真实k363 in-tree W=1编译](../../charging-management-20261023/oem-full-v2-build-result.json)，ko为fac827cf…89cb6，无warning/有效CONFIG变化；编译收据绑定上述源码和测试hash。未部署，仍需协调窗口实测。配套用户态使用v1目录下的[userspace revision2](../full-integration-candidate/userspace/README.md)，103项实际函数测试通过；它将已Full人为停止精确归为inhibited，既不误报unavailable，也不当正常充电通过或新周期边界。
