"""Prepare a fixed-control diagnostic, retaining all 238 evidence and RAM r14."""
from pathlib import Path
import ast,json

R=Path(__file__).resolve().parent;ROOT=R.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel239')
assert not P.exists();P.mkdir(mode=0o700)
(P/'usb-ipv6-candidates-private.json').write_bytes((P.parent/'kernel238/usb-ipv6-candidates-private.json').read_bytes())
(R/'host.py').write_text((R.parent/'kernel238/host.py').read_text().replace('kernel238','kernel239').replace('usb238','usb239').replace('Authenticated238','Authenticated239'))
archive=ROOT/'archive/NEXT-SESSION-through238-2026-10-16.md';assert not archive.exists();archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(P/'current-work-private.json').write_text(json.dumps(dict(stage=239,state='preparing fixed12-frame RGB diagnostic; fresh baseline pending',guard='/var/lib/samurai/k236-runtime/boot-id-private.txt',active_native_context=None,active_build_session=None,previous_goal_turn_classification='progress',full_peripheral_goal_active=True,next='Fresh boot236/camera idle/r14 payload check; build fixed12 RGB probe, then capture existing actual Debayer DEBUG params. Preserve strict zero-frame failure separately.'),indent=2)+'\n')
(ROOT/'NEXT-SESSION.md').write_text('''# Realme X2 Pro 当前检查点

2026-10-16，239进行中。238为progress，完整r14候选及48帧RAW控制已验证；RGB启动q1全零，严格验收失败未安装，GNSS无fix，goal active。[238归档](archive/NEXT-SESSION-through238-2026-10-16.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前状态

运输reference/kernel239/host.py、私人239/current-work-private.json；仍应为236启动，guard /var/lib/samurai/k236-runtime/boot-id-private.txt，239 fresh baseline待核。旧233及更早不可用。当前默认r13/r8，RAM /run/samurai-camera238-r14，boot235/前摄e49/IMX319176f/CAMSSff9/MFD6021/lab5198/provider2223/FastRPC2abd保持，789清单k237-camss-install/module-inventory-after-private.json。未启动新的手机试验或构建，先核状态。

## 源码、产物与回退依据

238全部完整源/包/签名/失败和原生证据已保留；SDK /home/cy122/x2pro-linux/libcamera214-root，r14 /work/libcamera238-r14-built/src/libcamera-v0.7.2，主机QA prefix /home/cy122/x2pro-linux/libcamera238-r14-qa-prefix。canonical精确after228，旧相机输出不能整刷。原214及r13缓存已恢复/保持，三代理继续已授权只读研究；手机主线程串行操作。

## 续作与已知风险

现有Debayer DEBUG每process均打印实际参数但没有frame号，可在严格12次处理/输出完整FIFO下关联；元数据SensorBlackLevels/Gamma/ColourGains不等于当帧处理参数。固定2ms/1倍先12帧，必要时同request RAW/RGB配对；不能只以全非零验收黑场。start成功后saveIspParams可修首次同步，IPA start还缺combinedMatrix发布；这些不保证暗场非零，不复制猜测BLC。GNSS最小ODM配置来源核验待做，不新增无依据SET/NV动作；S5K3M5离线投影要保留data尾24B section2，append relative须EOF-dataoff，非data_size。其余部署/回退与全机未完成项目详238归档。
''')
text=(R.parent/'kernel238/physical-rgb-control-probe.cpp').read_text().replace('48','12')
def replace(old,new):
 global text
 assert text.count(old)==1,old[:90]
 text=text.replace(old,new)
replace('#include <fstream>','#include <fstream>\n#include <sstream>')
replace('static void manual(ControlList &list, unsigned int phase)','static void manual(ControlList &list, [[maybe_unused]] unsigned int phase)')
replace('list.set(controls::ExposureTime, phase == 0 || phase == 3 ? 2000 : 32000);','list.set(controls::ExposureTime, 2000);')
replace('list.set(controls::AnalogueGain, phase == 2 ? 8.0f : 1.0f);','list.set(controls::AnalogueGain, 1.0f);')
replace('    std::array<double, 8> horizontalMean;','    std::array<double, 8> horizontalMean;\n    std::string ipaMetadataJson;')
replace('                         {}, {}};','                         {}, {}, {}};')
replace('        for (unsigned int index = 0; index < 4; ++index)\n            stats.bayerMean', '''        auto black = request->metadata().get(controls::SensorBlackLevels);
        auto colour = request->metadata().get(controls::ColourGains);
        auto gamma = request->metadata().get(controls::Gamma);
        std::ostringstream extra;
        extra << ",\\\"ipa_sensor_black_levels\\\":";
        if (black) {
            require(black->size() == 4, "four IPA black levels");
            extra << '[';
            for (unsigned int i = 0; i < 4; ++i) { if (i) extra << ','; extra << (*black)[i]; }
            extra << ']';
        } else extra << "null";
        extra << ",\\\"ipa_colour_gains\\\":";
        if (colour) {
            require(colour->size() == 2, "two IPA colour gains");
            extra << '[' << (*colour)[0] << ',' << (*colour)[1] << ']';
        } else extra << "null";
        extra << ",\\\"ipa_gamma\\\":";
        if (gamma) extra << *gamma; else extra << "null";
        stats.ipaMetadataJson = extra.str();
        for (unsigned int index = 0; index < 4; ++index)
            stats.bayerMean''')
replace('                      << ",\\\"quantiles_p10_p50_p90\\\":["', '                      << frame.ipaMetadataJson\n                      << ",\\\"quantiles_p10_p50_p90\\\":["')
(R/'fixed-rgb-probe.cpp').write_text(text)
assert 'nextQueued_ >= 12' in text and 'std::string ipaMetadataJson' in text
runner=(R.parent/'kernel238/native-controlled-rgb-capture-r2.py').read_text()
runner=runner.replace("out=root/'k238-controlled-rear-rgb-r14-r2'","out=root/'k239-fixed-rgb-r14'").replace('stage=238','stage=239').replace('/physical-rgb-control-probe','/fixed-rgb-probe239').replace('k238_rgb_controls_r2','k239_fixed_rgb_controls').replace('len(frames)==48','len(frames)==12').replace("LIBCAMERA_LOG_LEVELS='*:INFO,SimplePipeline:DEBUG'","LIBCAMERA_LOG_LEVELS='*:INFO,SimplePipeline:DEBUG,Debayer:DEBUG,IPASoftBL:DEBUG'")
runner=runner.replace(" report['passed']=success;", " report['diagnostic_capture_completed']=bool(not error and process is not None and process.returncode==0 and len(frames)==12 and not timed and not killed and not restore_errors and report['taint']==0 and not any(faults.values()));report['strict_nonzero_frames_passed']=bool(frames) and all(not f['all_zero'] for f in frames);report['passed']=success;")
assert runner!= (R.parent/'kernel238/native-controlled-rgb-capture-r2.py').read_text()
ast.parse(runner);(R/'native-fixed-rgb.py').write_text(runner)
print('239 prepared: fixed12 RGB/metadata probe, DEBUG parameters; no device action')
