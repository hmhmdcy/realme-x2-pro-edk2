# USB IRQ 唤醒配置：实际装机与一次待机恢复

2026-10-24。唯一根会话执行，无子代理；相机保持暂停。源码与差异见[候选说明](../../charging-oem-audit-20261023/usb-input-irq-wake-candidate/README.md)。

当前实际组合是 Image504/Y、bootedd/载体4453、USB13f41、charger97c、保护f6bef、服务83469、manifest5ef4；新 boot 为 `4e325db2-7579-461d-9e90-cf41662e4cf1`。两文件冷暂存原 worker 终态0、停充保持已核；正常重启后只发出 fastboot reboot，未刷写载体。新模块 note 与磁盘文件一致，启动12项检查通过，随后新鲜采用。

[本组合 RTC 结果](../../charging-management-20261023/usb-irq-wake-rtc001-result.json)：单次 mem 写入，实际驻留15.019404秒，success+1/fail0；前后12项检查通过，原密钥 NCM 自动恢复，源/native/硬件输入500mA、CC250mA/CV8.725V保持，保护Good，无新增fault。过滤 trace 记录 USB suspend/resume 回调返回0；现有 PSY wake 开关 enabled。结合实际候选代码和已注册 IRQ，可推断两次启用/释放调用成功；未直接测 wake-depth。所有8CPU trace 无丢失，入睡期无 USB 软件自唤醒，通知在complete发布；本次 alarm、trace 已清理。

前一 boot 的[2719八帧完整查询](../../charging-management-20261023/protection-profile-live001-result.json)仍有效于其记录范围，不移记到新 boot。新保护实例 schema2/profile1 缓存未捕获0/0，保持只读，未重arm或重新查询。

精确逆向包 `0c6a609778833a66d1a631582884f9f94577897997749ad5406b9440d673ed4e` 仅恢复 USBebfcb/manifest8c5b7，须正常冷启动；保护f6/服务834/charger97c/Image504保持。不能用旧三文件保护回退或旧整套 PM 回退冒充此范围。

`physical.py prepare` 已离线生成一次真实 USB 唤醒窗口，尚未 launch/start；用户已回复暂时不方便，继续离线，因此不启动。它复用原单次 PM primitive 和同 child supervisor，等待现场就绪后才启动；使用60秒 RTC 回退、一个 mem 写入和独占 trace。返回后保留 wake IRQ、真实中断、源状态及重连证据。RTC 成功不等于物理 USB 唤醒通过。

[新增跟踪清理的三项离线检查](physical-trace-test-result.json)通过：正常启动关闭、写入IRQ过滤器后失败、启用IRQ事件后失败，均关闭自身事件并删除自身instance。只执行实际新trace类和模型文件接口，没有手机访问或PM请求；原PM primitive按哈希逐字复用。

私有实际证据：`E:/edk2-samurai-out/charging-management-20261023/usb-irq-wake-update-live-20261024-01/`。`cohort-result.json` 保持生成时的准备状态；实际装机/采用/PM以该目录原终态、postboot和公开RTC结果为准。已结束 stage、restart、adopt、PM 事务不得重放。

现场延期后继续离线完成[确认停充时暂停累计计时的R2](../charge-timer-hold-r2-candidate/README.md)：旧实际函数复现误累计，新实际函数9组76断言通过。此候选尚未安装，不改变上面的手机组合或RTC证据。
