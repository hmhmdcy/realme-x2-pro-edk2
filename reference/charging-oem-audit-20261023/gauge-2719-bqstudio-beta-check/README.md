# 2719：TI当前测试版资料核查，未确认新协议语义

2026-10-25。补充此前仅检查稳定版1.3.101文档的范围。[TI稳定版入口](https://www.ti.com/tool/download/BQSTUDIO-STABLE)当前仍列1.3.101.1、2020-05-07，链接的Readme/ReleaseNotes与已有缓存版本一致；不重复下载。[测试版入口](https://www.ti.com/tool/download/BQSTUDIO-TEST)列1.3.130、2026-06-23，是本次新确认的版本资料。

公开[测试版说明](https://software-dl.ti.com/app_bms/bms-bgp/BQSTUDIO-TEST/Common/bqStudioNotes.html)仅说明版本变更在安装目录的ReleaseNotes.txt中，没有精确2719描述。按旧目录形式查询的1.3.130/Readme.txt和ReleaseNotes.txt均返回404；它们不能作为支持列表或“不支持2719”的证据。测试版页面的Windows安装包标为secure/需要审批，未下载、登录、执行或尝试其它安装包路径。化学数据库更新不是设备命令描述，不作为替代输入。

两次宽泛数字搜索命中SDK问题号、蓝牙UUID或其它设备地址，均已排除；对software-dl.ti.com的BQSTUDIO/2719精确查询没有结果。搜索结果不是全软件包内容，本次没有检查安装包内的配置集合，也没有认定TI全部版本缺少2719支持。[现有实物指纹](../gauge-2719-identity-evidence/README.md)仍作为将来描述匹配依据，不重复查询手机。

本轮没有得到可改变TCA、Safety/PF/GaugingStatus位解释的资料，不修改生产协议/白名单、保护、Full、计时、充电参数或诊断状态。精确配置/固件命令语义仍待取得；当前预充实测和508预算验证继续。相关公开页及排除结果存于private `gauge-2719-bqstudio-beta-source-private-01/official-pages.json`，摘要与范围见[result.json](result.json)。
