# 显示研究来源与新线索

2026-10-13，实际使用Firecrawl搜索、开发者搜索和页面读取。

1. [Linux workqueue文档](https://docs.kernel.org/core-api/workqueue.html)：cancel_work_sync取消待执行work，并等待正在执行者；保证依赖没有并发入队。152在disable_irq之后调用，宿主IRQ取消是替身，不据此宣称实机取消语义已验证。
2. [Realme官方Android R命令编码器](https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/master/drivers/gpu/drm/msm/sde/sde_encoder_phys_cmd.c)：prepare_commit断开外部TE、关闭autorefresh、轮询在途帧、再接回TE。与本地正常关autorefresh机制一致。单凭顺序相似不能确认启动接管根因。
3. [2026年7月DSI讨论](https://lists.freedesktop.org/archives/dri-devel/2026-July/585026.html)：自动化审阅提出未取消error work和未核查clock enable失败等既有风险。这是自动审阅线索，不是维护者确认或已合入的修复；152的竞态证据来自本地实际函数测试。
4. [Linux 6.17.4官方ChangeLog](https://cdn.kernel.org/pub/linux/kernel/v6.x/ChangeLog-6.17.4)：msm8916/msm8939缺MDSS reset的修复与启动遗留状态相关，机型不同。SM8150阶段135全局reset候选曾失败，不直接套用该DT改变。
5. [保留bootloader面板状态的RFC](https://lkml.org/lkml/2024/10/28/737)：Synaptics面板提案在已初始化场景使用GPIOD_ASIS保持reset状态。是另一面板的RFC，不能视作Realme已验证方案，也不复制其直接设置prepared的做法。

## 新的板级GPIO线索

SOFEF03F probe在mipi_dsi_attach之前用GPIOD_OUT_HIGH申请reset，GPIOD_OUT_LOW申请VCI和VDDD。逻辑reset为active-low，因此这些请求会立即复位并切断面板电源。mipi_dsi_attach进入dsi_host_attach，其dsi_dev_attach调用component_add；随后才进入DPU KMS硬件初始化和本地boot CTL清理。即面板先被关断，仍继承的DSC/autorefresh帧后被清理。

152与回退147均保留了非零在途line、autorefresh启用、out line=0及CTL reset失败。这个源码先后关系是一个可操作的新缺陷线索，但尚未做改变GPIO时机的实机A/B，不能直接写成已证明的黑屏唯一根因。DT默认pinctrl只设置mux/drive/bias，没有output-high/low属性；需要将三个GPIO的方向与初始状态设置延后到prepare，并保留完整原厂供电/复位/DSC序列和失败收尾。probe不应把panel标为prepared，也不应跳过原生初始化。

下一阶段优先验证这一最小板级改动。DSI152同步候选已经归档/撤回，避免把两个改变混在同一首次接管实验。
