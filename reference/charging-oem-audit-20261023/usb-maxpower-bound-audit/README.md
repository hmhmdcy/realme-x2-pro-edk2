# 已绑定时写 MaxPower 的精确语义

**允许写，但不能保证 native100 一直保持到下一次物理重接。** 本叶只读既有 Image363 关联源码和 startup 原件，没有设备、USB、SSH、构建或任何现役修改。

已冻结的 `dwc-r2-independent-review/callback-source-manifest.json` 将这两份完整源与原 Image source commit `ba61a62293e0f6bc5838c06f2e85e033e3d702a8` 比较相等：configfs SHA `9b692e34…17947`，composite SHA `01eefa9a…819e1`。完整路径/pins 见 [result.json](result.json)。

- `drivers/usb/gadget/configfs.c::gadget_config_desc_MaxPower_store:532–545` 只做 u16 解析、`DIV_ROUND_UP(val,8)<=0xff` 范围校验和 `cfg->c.MaxPower=val`，返回写入长度。500合法。没有 bound 检查、UDC reset/unregister 或 `usb_gadget_vbus_draw()`，所以单次 store 本身不会立即通知 native 预算，也不会主动重枚举。
- 但这不是独立的“下次生效描述符缓存”。`composite.c::encode_bMaxPower:529–548` 动态从同一个 MaxPower 生成描述符；`set_config:1038–1059` 也从它取值并调用 vbus_draw。
- 更直接的反例是 `composite_resume:2609–2652`：已有 config 时在 **2632** 读取当前 `cdev->config->MaxPower`，在 **2645** 调用 `usb_gadget_vbus_draw(gadget,maxpower)`；无 config 分支2649才限制100。因而 bound/configured100→在线写500→一次普通USB suspend/resume，就可能回调500，无需物理拔插或新描述符 fetch。这里没有要求用户现场再复现实验，只是实际代码路径的结论。

当前可离线绑定的已恢复 startup 缓存是 `usb-hotplug-r2/usb-services-before-private.json`，与 `usb-startup-rollback-result.json` 的原恢复哈希一致；本次未再次读取手机。`/usr/local/sbin/samurai-usb` 为 `fcfd5052…1ad3e`，`/usr/sbin/samurai-usb` 为 `0f623986…906a`。两份的唯一 MaxPower echo 均在 gadget **不存在时的创建分支**内，准确行号见 result。单改该 echo 不会迁移 initramfs 已创建的 gadget。

仓库 `linux-port/scripts/samurai-usb.sh` 全文 SHA 与缓存 `/usr/sbin` 原件相同；其中 echo 行对应 `/usr/local` 的同一原创建行。`linux-port/packages/samurai-platform/usr_sbin_samurai-usb` 全文为 `46db0d9d…01b3`，包含不同 machine-id/身份逻辑，与实际 `/usr/local` 不是全文同源，不能整份替换来冒认一行改动。

最小不 rebind 路径可以是先只持久改已核的创建行（不执行 startup），但 volatile MaxPower500 应等明确的真实断源窗口再单写，随后由下一物理 attach 重新读取描述符/SetConfiguration并取得真实 native500。store 本身确实不要求 UDC unbind；**在线 store 后再承诺始终 native100，源码不支持**。若 initramfs仍先创建100，持久创建行本身也不足以覆盖每次启动，需另说明其真实启动顺序/受控迁移。
