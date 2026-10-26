# 420：生产IPE请求通道打包集成

完整目标active。本阶段已正式安装419生产驱动与libcamera r31/配置栈r26，逐帧请求通道进入系统默认路径。自动IPA画质参数仍未接入，不能称完整原厂画质完成；第五摄/AF/光学/多模式/同步范围保持。

libcamera r31、配置栈r26，新增0041请求补丁，其余40补丁、完整子包和原IPA接口保留；公共调校数据不变，仅依赖版本pin更新。原厂私有数据仍留设备。初始状态为r30/r25、395核心/393适配器；419临时实验已终态。419生产模块只用正常核心63131与新适配器46f9，禁止用吞ACK测试核心e27。

[源验证](package-source-validation.json)核对418已测试源码摘要并复用其零fuzz补丁证据，不再扩大算法测试矩阵。[构建](package-build-validation.json)产生13包；[包验证](package-artifact-validation.json)检查全部包签名、六IPA签名与包内核心匹配，六IPA二进制均与r30相同。[IPA既有契约](ipa-contract-validation.json)复用原数值证据；包内strip后libcamera核心SHA256 `d8c841d28f65bd1746e240beea71af33b83087f511e6359ba75099ea09c0b05b`，不要与418未strip实验库混淆。

[一次正式安装事务](install-validation.json)为`/var/lib/samurai/k420-install-r1`，worker10893终态，client与collector也终态；只升级七个运行包与两份生产模块，未重启/刷写Image/DT/FW。先停桌面消费者及等待DMA/owner释放，原子替换模块文件、depmod和重载，再离线安装精确版本。安装后正式文件摘要、内核加载notes及包版本一致。旧r30/r25七包、签名索引、world/repo与395/393两模块备份保留；本轮未执行回退，不能声称本轮回退路径已真机验证。准备阶段两次只读查询因apk输出格式及脚本文本转义错误退出，修正后读取安装数据库通过；没有触发设备切换。

[硬件验证](hardware-validation.json)：四摄各12=48帧，主摄RAW+NV12六帧且原IFE SOF保持，RAW-only六对且IPE零帧，隔离IPA27帧/五控制阶段/GammaACK一次，合计81个IPE完成；普通用户PipeWire四节点/广角12帧，WirePlumber映射系统已安装核心。总计93个新IPE任务全部direct成功，取消/失败0，starts/stops7。四摄、双流与隔离IPA日志均明确`requests=1`，证明真实使用新通道；自动参数仍旁路，GammaACK属于既有IFE调校，不冒充非零IPE自动画质。

[最终状态](current-state-validation.json)：PW11073/WP11076各一、uid10000，owner_refs53为正常桌面CAMSS句柄；ICP/CAMSS/双CCI suspended，17相关时钟0，九路相机电源disabled/users0；DMA/CPU/IRQ/PM/map/import均释放，watchdog/protocol/cleanup错误0。无本轮新fault或dump。历史417-r2已修WARN的taint512保留，guard394仍匹配；不声称taint0。数值、恢复证据复用[419](../kernel419/fault-validation.json)，本轮没有重复故障注入。

内核仍维护419提交`07d2ca735f88649587c0e89802febff6dbf2b443`干净，本轮未改驱动/SoC/板级或传感器代码，只完成打包与部署集成。核心419848字节SHA256 `63131c5719526ca796955f4d833380a12c36c62557ccf539e85bd58c0f070632`，适配器132400字节SHA256 `46f91cc8dd024626f05a276e63dd8384bb6a056d15bf441c7d44a91ab4c2e06f`；无测试参数。Image363/DT389/CAMSS389/FW/个体四份配置保持；不以未变组件全量扫描增加本轮耗时。

接续IPA prepare/result与真实统计/曝光/输入域，最终图像成功才commit历史，失败discard；Media Request完成不能单独代表成功。避免重复IFE已有CC/Gamma，复用原厂逆向与数值结果补齐LA/mask/weights/scalars/inverseGamma及非零LTM/LCE。保持[完整验收范围](../kernel363/REMAINING-CAMERA-SCOPE.md)，四摄基础取流不等于原厂完整画质，第五2MP身份/共享mux等仍待完成。原厂数据和完整日志继续私存，本地公共镜像不push。
