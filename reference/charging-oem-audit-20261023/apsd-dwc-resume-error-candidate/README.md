# DWC resume 返回值的增量候选

实际 `dwc3_resume_common` 在 DEVICE 和 OTG-device 分支丢弃 `dwc3_gadget_resume` 返回值，随后返回0。后者直接返回 soft-connect 的错误，因此控制器/枚举失败可能被上层当作恢复成功。本目录在冻结 DWC R2 之上仅增加这两处错误检查，经共同out清除已有PM gate。`resume-error.patch` 是**叠加在R2上的增量**，不是替代完整R2补丁。

状态：**独立复审判为 changes-required，不可部署。** [实际调用者反例](../../charging-session-20261023/dwc-resume-error-independent-review/README.md)证实“core已初始化、gadget失败”时仅负返回会留下PHY/core初始化，而PM将设备记为suspended；不能把错误传播当作完整恢复修复。已停止另一个扩大终态flag/IRQ深度的未审WIP，不采用其未经验证的回退。该问题也没有被证明是历史r5待机/USB失联的现场原因。

`test-result.json` 先用原完整函数重现gadget timeout被返回0，再直接执行新完整函数的8个定向边界：runtime/system gadget错误、core-init错误、成功DEVICE、PM gate拒绝、OTG-device错误、HOST和自动OTG未改路径。ASan/UBSan/Werror通过；OS/硬件边界为桩，未重跑R2旧套件。

`build-result.json` 仅私有core.o以W=1编译、无诊断，共享source/config未变；未链接Image、未访问手机/SSH/USB或SDK。`prepare.py` 固定R2 core哈希，`build-private.py` 校验并复用现有对象构建器，只改变私有目录和受影响target。
