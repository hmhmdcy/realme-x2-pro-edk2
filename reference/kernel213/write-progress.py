from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel213')
(here/'README.md').write_text('''# 213：IMX471增益和首帧查找表（进行中）

当前仍是212同一干净启动，系统libcamera尚未替换。213已备份程序/IPA/签名及包数据库，建立独立SDK和候选源码，没有刷写或重启。[现场](baseline-validation.json)。

验证了0.7.2源包及原发行版六个补丁，取回官方helper提交e64b507d和属性提交59e7f189。helper模型为1024/(1024-code)，范围0..800；黑位4096来自上游同传感器测量，尚不声称本机暗场校准。属性原上游1400nm与一加官方同款IMX471的1.0µm不符，候选改为1000nm；控制延迟留空，不捏造值。[源与补丁](helper-source-validation.json)、[一加官方规格](https://www.oneplus.com/hk/9/specs)。

首帧黑进一步定位到DebayerCpu查找表：首次参数与默认缓存相等，跳过尚未生成的表。计划先验证仅helper/属性候选，再对同一构建加入查找表有效标记，实际比较首帧，不丢弃首帧来冒充修复。候选尚未完成编译及取流。

首次SDK fetch遇不存在的libglvnd-dev，apk返回0却输出ERROR，原脚本又把零文件当成成功；已保留原始错误和错误报告，修正为检查错误及每个请求包实际存在，随后108份签名APK验证通过。只有必要开发文件进入独立SDK，没有系统包安装。首次Meson配置因缺xorgproto与openssl工具退出，失败日志保留，正在补齐SDK依赖。[fetch失败](sdk-fetch-first-failure-validation.json)、[输入](build-inputs-validation.json)。

所有历史211 GPU告警、212首帧及配置权限失败保持；CPU配置仍为当前兼容路径。后置四摄、完整图像质量、GNSS/蜂窝/蓝牙/传感器/电源及可复现打包目标继续开放。
''')
path=repo/'NEXT-SESSION.md';text=path.read_text();start=text.index('2026-10-15，');end=text.index('\n\n',start)
text=text[:start]+'2026-10-15，阶段213进行中，完整外设goal active。当前212同一启动/产品保持，已备份相机程序/IPA/包数据库并构建独立SDK；已取官方IMX471 helper并修正候选像元尺寸，首帧查找表缺初始化已定位，候选正在编译，尚未安装。无新刷写/重启。[213进展](reference/kernel213/README.md)、[212验收](reference/kernel212/README.md)、[边界](WORKING-BOUNDARIES.md)。'+text[end:]
start=text.index('- 当前运输');end=text.index('\n',start)
text=text[:start]+'- 当前运输reference/kernel213/host.py，当前guard为/var/lib/samurai/k213-baseline/boot-id-private.txt，已验证仍为212启动、taint/fault0、三个DSP running。只有独立SDK/候选构建文件，系统相机库和包数据库未替换，无新切换。212及211所有marker已闭环，不可重放。'+text[end:]
path.write_text(text)
plan=json.loads((private/'current-work-private.json').read_text());plan.update(state='213 fresh baseline clean, camera products/database backed up. Pinned0.7.2+six distro patches and official IMX471 helper/properties prepared; pixel cell corrected1um from manufacturer. Independent SDK ready; first missing SDK dependencies caught,补齐中. No camera product replacement or transition.',next='Resume exact failed Meson configure after SDK extras, observe live build handle. Stage helper-only candidate and finite user capture, then validate initial-LUT cache fix against same build. Full goal active.');(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
print('213 progress checkpoint saved; no deployed camera product replacement or transition claimed.')
