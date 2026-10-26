from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel213')
report=dict(condition_source='direct human message',room_lights_off=True,phone_previously_confirmed_indoors_by_window=True,all_zero_processed_rgb_alone_does_not_prove_bug=True,dark_raw_tests=['active RAW10 pixels excluding stride padding','histogram and noise variance','Bayer channel statistics','frame-to-frame changes'],positive_control_required_for_isp_first_frame=['known nonblack synthetic RAW or sensor internal test pattern'],raw_scene_images_private=True)
(here/'dark-room-conditions.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
path=repo/'NEXT-SESSION.md';text=path.read_text();marker='## 续作与已知风险\n';assert marker in text
text=text.replace(marker,marker+'\n用户最新明确房间关灯，后续按暗场判断。必须用去除stride填充的RAW10直方图/噪声方差、Bayer分通道及帧间变化区分正常暗噪声与全零数据；RGB黑位扣除后全零本身不能证明bug。首帧ISP验收应加已知非黑合成RAW或sensor内部图案对照；原始场景仍私下保存。\n',1);path.write_text(text)
plan=json.loads((private/'current-work-private.json').read_text());plan.update(current_scene='User explicitly turned room lights off. Distinguish active RAW10 dark noise from all-zero faults; processed RGB zero alone is not a bug proof.',next='Finish isolated SDK runtime dependency closure/link; live build failed at link and is terminal. Then helper candidate, synthetic/test-pattern ISP positive control and physical RAW dark statistics. Keep full peripheral goal active.');(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
failure=private/'transport-last-failure-private.log'
if failure.exists():(private/'sdk-readelf-first-failure-private.log').write_bytes(failure.read_bytes())
print('User lights-off condition and required dark-noise/positive-control distinction recorded.')
