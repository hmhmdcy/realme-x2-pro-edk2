# RMX1931 双 PM8008 实验复位契约

这是本地适配候选，尚未进入当前运行系统；没有上游合入或完整供电绑定验收。

`realme,rmx1931-pm8008-resets` 使用一个 reset cell：0 为 P，1 为 Q。`p-reset-gpios` 对应 PM8150L GPIO1、`q-reset-gpios` 对应 GPIO4，两者 active-low。provider 首先取得 P 并保持复位，Q 取得时保持 ASIS；所有后续操作通过独占 reset handle。GPIO hog 同时移除，不能与 provider 分享所有权。

Q 的复位操作要求最近一次 P 方向/输出写成功且保持 asserted，随后再核对 GPIO 逻辑值。SPMI GPIO 的输出读可能来自缓存，不能称物理读回；P 写失败使软件状态失效，后续 Q 操作和 P status 返回错误。provider 不提供自动 pulse/reset 操作。

Q 保留原195的暖启动身份检测、8→4地址迁移、等待和失败重置。P 节点位于同一 I²C adapter、地址8，依赖地址4且 initial-address8 的 Q。编译设备树产物必须证明 P/Q 分别使用同一 provider 的0/1，P的 `qcom,address-setup-supplier` 精确指向 Q；不能仅凭地址8推断它是本板P。

消费者在获取 reset handle 前建立持久 managed provider link；P另建立指向已完整 bound 的 Q 的 managed link。检查位于 supplier device lock 内，同时拒绝 links.status 非 DRIVER_BOUND 的状态，覆盖 driver仍非空但已进入 UNBINDING 的窗口。P检查依赖时不持 address mutex。

实验参数 `experimental_p_address_only` 默认 false、权限0444。对合法P依赖路径，未显式开启时在取得reset和释放P前拒绝 probe。开启后，P在 address mutex 内解除复位并读取0x0100身份；成功后在 secondary dummy、regmap、IRQ及全部MFD children前返回，不注册七路regulator。P卸载/失败清理先移除children，再保持P复位，最后释放reset句柄。Q解绑先等待P退出；provider解绑先等待消费者退出，reset core再排空回调，最后保持P→Q并释放GPIO。

产品候选设备树保持P disabled；实验设备树启用P，只能与显式实验参数成对部署。modprobe配置应写 `options qcom_pm8008 experimental_p_address_only=1`，必须在模块加载前生效。该模式不写P的SID或LDO电压/使能寄存器，不能证明硬件复位默认所有电源轨关闭。未知VIN继续缺省，因此不声称完整PM8008供电schema通过。

原生验收仍需：P身份匹配、P无MFD children/无新增regulator，Q暖路径与前摄回归，P→Q解绑/重绑顺序、provider解绑排空及错误清理。主机模拟不能代替真实Linux设备核心和硬件验证。
