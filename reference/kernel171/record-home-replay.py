from pathlib import Path
import json

ref = Path(__file__).parent
analysis = json.loads((ref / 'dmic0-sd1-home24-analysis.json').read_text())
assert analysis['mixer_restored'] and analysis['amplifiers_off'] and analysis['taint'] == 0
assert all(d['known_tone_detected_with_disabled_amp_control'] for d in analysis['speaker_decisions'])
report = dict(stage=171, kernel_build=168, date='2026-10-14', firmware_dtb_stage=171,
              user_request='我现在回到家了，请你再试一遍。',
              user_reply='两组都听到，来自手机', human_confirms_both_tone_groups_from_phone=True,
              tones_hz=[997,1511], peak_dbfs=-24, same_runtime_boot=True,
              acoustic_analysis='dmic0-sd1-home24-analysis.json',
              active_correlations=[d['active_code_correlation'] for d in analysis['speaker_decisions']],
              active_to_disabled_tone_band_db=[d['active_to_disabled_tone_band_db'] for d in analysis['speaker_decisions']],
              faults_added=analysis['fault_delta'], mixer_restored=True, final_amplifiers_off=True,
              music_voice_quality_headset_and_reliability_not_accepted=True,
              candidate172_not_deployed_during_this_replay=True)
(ref / 'home-listening-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
readme = ref / 'README.md'; s = readme.read_text()
s = s.replace('现场听感、耳机与完整音质/可靠性仍未验收。', '用户随后回家重听并确认两组滴声来自手机；耳机与完整音质/可靠性仍未验收。')
s = s.replace('本轮现场听音问题已提出，尚未收到确认，不能把旧不确定反馈改为新人工通过。',
              '后续回家重放获得用户明确确认，见下段；旧反馈仍属于原SD0时期。')
s += '''
## 用户回家后重放与人工确认

用户要求“我现在回到家了，请你再试一遍。”在同一171 boot/kernel168下重放−24dBFS、997/1511Hz两组编码音，各含对应功放关闭对照。左右相关性0.964/0.955，开关功放频段差18.02/40.80dB，关闭功放时相关性0.179/0.200；无新增WARN、DMA prepare、TX timeout或resume错误，mixer恢复、双功放关闭。用户回复：“两组都听到，来自手机。”由此新增有限的人工出声确认；不把它扩大成音乐/人声音质、耳机或完整可靠性验收。[人工收据](home-listening-validation.json)、[重放分析](dmic0-sd1-home24-analysis.json)

听音时172耳机检测源码仍在构建，手机没有部署该候选。171旧最终收据的13次启停与14条TX停止underflow属于重放前快照，不用于代表重放后的计数。当前可用SD1回退应优先保留完整boot171/logdump171配套原件；boot164/logdump168是更早SD0版本。
'''
readme.write_text(s)
session = ref.parent.parent / 'sessions/171-speaker-sd1-and-acoustic-loop.md'
s = session.read_text()
s += '''

后续同boot回家重放：用户确认“两组都听到，来自手机”。左右编码相关性0.964/0.955，功放开关对照差18.02/40.80dB，新增关键故障0、mixer恢复、功放关闭。首次取得双组测试音的人工来源确认；音乐/人声质量和耳机仍未验。[人工确认](../reference/kernel171/home-listening-validation.json)。听音时172新耳机源码尚未部署；SD1可用回退优先完整boot171/logdump171。
'''
session.write_text(s)
collector = (ref / 'collect-final.py').read_text().replace('k171-final','k171-home-final')
(ref / 'collect-home-final.py').write_text(collector)
print(json.dumps(report,ensure_ascii=False),flush=True)
