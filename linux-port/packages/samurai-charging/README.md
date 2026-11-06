# samurai-charging 0.1.0-r2 (legacy experiment)

这是 `7.3.0-rc6-rmx1931-samurai-k363+` 的历史充电实验包，不属于
Linux v7.3.1 标准 ARM64 平台组合。标准内核使用 DTS 中的
`mps,mp2650` 绑定、主线 `power_supply` 类和板级极薄驱动，不加载本包
的三个私有 KO，也不由用户态强制重新绑定驱动。

包内模块只适用于上述旧 release 的 aarch64 内核。安装钩子不会自动把
服务加入 runlevel，也不会自动启动；必须同时满足旧 release，并显式
设置 `SAMURAI_ENABLE_LEGACY_CHARGING=1` 才会启用。新系统只应把它当作
可回滚、可审计的实验输入。

当前策略：

- TCPM 在线但未取得显式 PD 电流合约时，内核回退到输入 provider 的
  `CURRENT_MAX` / `INPUT_CURRENT_LIMIT`，不再把零合约误判成 0A；
- 用户态同样接受该回退，不再要求 TCPM `current_max >= 50mA`；
- 用户态只设置板级 2A 输入、1.1A 充电上限，内核按实时来源和电芯
  电压收敛，5V/2A 来源留有 15% 转换余量；
- SDP 仍按输入 provider 上限，DCP/CDP 按 BC1.2 1.5A，PD/Type-C
  来源最高 2A；
- 保持原有温度区间、电芯过压、Full、故障锁存和 10 小时保护。

实机当前结果：

```text
budget_ua=500000 valid=1 error=0
MP2650 status=Charging
battery status=Charging
net current +146..+163mA
```

源文件 SHA-256：

```text
f96922737dcb3700a931a9b8801d12462137b2c712bc146dcdc464f1218b26ae  samurai-mp2650.ko
22604106772b89758ea745531e99dd70a6ab696b7740705107a767599e9a6529  samurai-usb-input.ko
f6bef8a239d5101dbb710f1dd5da9642bdc7ac5e4e568e2e1193de6233a31d7e  samurai-gauge-protection.ko
f0342f2e9c97daf4fae2e4f1fac9ed0f5f8c75c42720a7e0e9bbb222435df675  samurai-charging
```

`installed-manifest.json` 的 installed_files 必须与包内文件逐字一致。
安装由签名 APK 仓库完成，不使用 `--allow-untrusted`。
