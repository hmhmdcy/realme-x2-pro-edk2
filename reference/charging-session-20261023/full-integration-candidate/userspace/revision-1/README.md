# 用户态兼容候选

2026-10-23。仅独立候选，主目录、设备、SDK及v1八个kernel文件保持不变。实际来源及SHA在[baseline.json](baseline.json)，差异见[userspace.patch](userspace.patch)。

[samurai-charging.py](samurai-charging.py)只容忍与实际sysfs错误相符的安全等待：源预算待定仅限EAGAIN/ENODATA且无旧fault/stop error/timeout；新的TCA等待必须实际errno EAGAIN、明确`gauge_charge_stop=1`、fresh完整保护良好、raw TCA有且无OCA、CHG期望关闭且无旧锁存/stop错误。所有其它IO、参数/权限、保护、旧超时仍抛回原有失败inhibit路径。实际`command(...,'resume')`测试确认安全等待保留AUTO，其它错误会取消并inhibit；没有清fault或放宽budget。

[charging-health.py](charging-health.py)新增`full_holding`健康状态，要求逻辑Full、请求hold及实际hold成功三者一致、会话归零、Full原因已知、CHG期望关闭、保护fresh且无TCA/OCA/timeout。TCA独立显示`waiting_gauge`，不能冒充Full或成功充电验收。audit重新从原始telemetry分类；只接受实际观测到的合格Full边界解释计时归零，非Full倒退仍报错，UNKNOWN/缺采样不能擦除上一有效计时比较基准。正常Full→再充周期不会误报，未观察到的周期不猜测通过。

[69项实际函数测试](test-result.json)通过：21个service request/command场景、22个分类、23个audit、3个解析案例。service使用候选真实AST函数体，health直接运行完整候选模块函数；只在文件系统/telemetry边界fake，不访问任何手机路径。覆盖EIO/ETIMEDOUT/ERANGE/EPERM不能被TCA标签掩盖、保护/旧latch/timeout优先、任意或伪Full计时回退、保存状态标签伪造、跨未知源回退、Full健康状态仍受同boot/taint/限值/相机检查约束。测试需Linux errno环境（WSL root Python），Windows errno缺EREMOTEIO不会误记为通过。

这是配套候选，仍需根会话与模块manifest一起审核打包；没有替代实物终止/再充验收。
