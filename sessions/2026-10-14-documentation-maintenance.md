# 2026-10-14 文档维护

用途：记录本轮文档结构与工具维护。来源：维护前项目文档、现有reference记录及独立输出目录的既有验收摘要。未新增设备操作、构建、刷写或硬件验收。

## 文档分工

检查点维护最后核对的部署、源码/产物差异、回退依据和续作项；硬件清单维护功能验收范围；WORKING-BOUNDARIES维护当前操作规则。README、旧交接和索引通过链接指向这三份来源。

| 文档 | 原长度 | 整理后长度 |
| --- | --- | --- |
| README | 44,153 bytes | 约11.5 KB |
| HANDOVER-NEXT | 25,907 bytes | 约5.9 KB |
| DOCS-INDEX | 24,185 bytes | 约5.6 KB |
| NEXT-SESSION | 7,427 bytes | 约4.1 KB |
| FLYWHEEL | 31,082 bytes | 约3.1 KB |

18份维护前入口、技术文档及脚本逐字保存到[快照](../archive/docs-before-maintenance-2026-10-14/README.md)，manifest保留SHA256。旧HANDOVER、方案评估和机型说明改为历史入口；README与交接不再累积“当前阶段”。152—165的过程整理到[显示历史](display-handoff-152-165.md)，原始实验与失败结论保留。现有阶段文件和reference目录统一进入[会话索引](INDEX.md)。

## 断链修复

历史全目录链接审计发现162/164的四份JSON摘要只存在独立输出目录。确认它们包含验收结果、计数/时间和哈希，且无原始日志、密钥或设备身份后，逐字补入对应reference目录：

- [162运行验证](../reference/kernel162/runtime-validation.json)
- [162启动时间](../reference/kernel162/boot-timing-validation.json)
- [164首次运行验证](../reference/kernel164/runtime-validation.json)
- [164固件日志验证](../reference/kernel164/firmware-log-validation.json)

内容属于原阶段证据，不构成本次新的验收或对164音频失败的修复证明。

## 维护工具

同步与检查使用[统一清单](../linux-port/scripts/docs-sync-manifest.json)，补入检查点、通用/音频提示词与操作边界。sync-docs-to-repo.sh默认仅同步，显式--publish才提交推送；复制前保存存在差异的仓库镜像原文，暂存范围按清单限定。更新仓库记录采用标记块，删除未经核对的“所有提交已在fork”陈述。

健康检查验证20个当前入口的本地链接、入口体积、索引内容、旧8—30节唯一归属、18份原文SHA256和清单镜像一致性；历史链接审计可选，逐字归档按原路径解释链接。四项行为测试覆盖失效路径/中文锚点、归档篡改、镜像漏项/路径越界、仅同步时暂存区与固件文件保留。

阅读和日常维护命令见[DOCS-INDEX](../DOCS-INDEX.md)。本轮采用仅同步模式，固件源码与Git暂存区保留，未提交或推送。
