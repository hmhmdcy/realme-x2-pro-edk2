# 485：恢复 libcamera 的安装路径识别

离线修复候选通过；未安装或访问手机，正式 r33/r28 继续保留。484 的 `libcamera is not installed, //src/ipa` 来源已定位：473 的 `source_paths.cpp:40` 按 ELF 是否含 RPATH/RUNPATH 判断安装状态，`meson.build:187` 明确将 `/` 当作构建标志，由 Meson 安装阶段移除。475 为保留已测 ELF 字节而直接组包，core 中仍有 `$ORIGIN/base:/`，放在 `/usr/lib` 后被当成构建树。

[normalize-core.py](normalize-core.py)复用主机 Meson 的 `depfixer.fix_rpath()`，只操作经预期 SHA256 核对的新 core 副本，不修改生产源码或原 core。原 ARM64 `a21fcedd…97b` → 候选 `24a29a5c…6294`，大小仍为 51,259,496 字节。完整比较证明只移除动态表中的 RUNPATH 项并将原路径字符串填为 Meson 的 `X`；其它动态项的顺序/值、所有其余字节（代码、数据、公钥、符号、调试信息和 ELF 头）相同。原 core、IPA6、签名、proxy 和 base 均未更改。

[validate-local.py](validate-local.py)先调用 461 的卷检查，再用主机 g++ 直接编译未修改的实际 `source_paths.cpp`，`dirname()` 函数从原源码原样提取，只加两个 C 查询入口。三个 DSO 分别在独立进程加载：真实构建目录返回构建/源码路径；直接复制且保留 RUNPATH 的库仍被误判为构建；经过 Meson 处理的副本返回两个空路径。该有限原码验证与 ARM64 ELF 静态比较见 [local-validation.json](local-validation.json)。未使用 SDK、没有重建生产库。

这项修复恢复现有查找分支，不绕过日志或重写安装判断。`ipa_manager.cpp` 在构建路径非空时额外搜索 `src/ipa`；`ipa_proxy.cpp` 也依赖该判断选择源码配置和代理工作程序。实际 ARM64 loader、系统 IPA/配置/worker 查找及原 IPA 签名验证仍待新候选运行检查；本机 native 路径验证不能代替这些结果。IPA/proxy 自身没有因此归一化或重签名。

484 的 `/root/.config` 错误是独立的启动器环境问题，由 [486](../kernel486/README.md)处理。原 `global_configuration.cpp` 对权限错误停止回退的规则保持，不能通过忽略 EACCES 来掩盖错误环境。本轮不改变调校系数、PD10 打包、双遍时序或 LTM 数学；441/442/469/474 的相关历史验证保留原适用范围。

复现需要新的私有输出目录，避免覆盖原件：

```text
python3 -B reference/kernel485/validate-local.py --private PRIVATE_NEW_DIRECTORY --receipt NEW_RECEIPT.json
```

原件和生成的 native/ARM64 候选留在私有485目录，公开目录只保留工具、说明与脱敏回执。

独立只读复审确认上述原码 oracle 和当前固定 SHA 物料的差异约束成立；另查当前 core/oracle 的 GNU version 名称均不与路径字符串重叠，未发现 CONFIG/AUDIT/DEPAUDIT 动态项。本工具面向已核对的 libcamera 构建输入，不声称覆盖任意 ELF 的全部字符串别名。
