from pathlib import Path
import difflib, hashlib, json, re, shutil, subprocess

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel104'
old = root / 'reference/kernel103'
out = Path('/mnt/e/edk2-samurai-out/kernel104')
k = Path('/home/cy122/x2pro-linux/linux')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not (out / 'preparation.json').exists()
previous = json.loads((out.parent / 'kernel103/kernel-validation.json').read_text())
for p, key in [('arch/arm64/boot/Image', 'image_sha256'),
               ('arch/arm64/boot/dts/qcom/sm8150-samurai.dtb', 'dtb_sha256'),
               ('usr/initramfs_data.cpio', 'cpio_sha256')]:
    assert sha(k / p) == previous[key], p
baseline = (out / 'baseline-boot-private.txt').read_text().splitlines()
assert baseline[0] == (out.parent / 'kernel103/runtime-boot-id-after-private.txt').read_text().strip()
assert '#102 SMP PREEMPT' in baseline[1] and baseline[3] == '0'
assert sum('id=43' in l and 'global=00' in l and 'failed=0' in l for l in baseline) == 2
assert baseline.count('running') == 2
paths = {'config-before': '.config', 'Image-before': 'arch/arm64/boot/Image',
         'cpio-before': 'usr/initramfs_data.cpio',
         'dtb-before': 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb',
         'dts-before': 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts',
         'q6core-before.c': 'sound/soc/qcom/qdsp6/q6core.c',
         'wcd934x-before.c': 'sound/soc/codecs/wcd934x.c'}
for n, p in paths.items():
    assert not (out / n).exists()
    shutil.copyfile(k / p, out / n)
(out / 'kernel-source-before.patch').write_bytes(subprocess.check_output(['git', 'diff', '--binary'], cwd=k))
init = k.parent / 'initramfs'
(out / 'initramfs-before.json').write_text(json.dumps({str(p.relative_to(init)): sha(p) for p in init.rglob('*') if p.is_file() and not p.is_symlink()}, indent=2) + '\n')
(out / 'untracked-before.json').write_text(json.dumps({str(p.relative_to(k)): sha(p) for n in subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=k, text=True).splitlines() if (p := k / n).is_file()}, indent=2) + '\n')

# Confirm the handset's published topology, without copying private vendor XML.
oem = k.parent / 'refs/19781/arch/arm64/boot/dts/19781/sm8150-oppo-audio-overlay.dtsi'
o = oem.read_text()
for n, bias in [(0, 1), (1, 1), (2, 3)]:
    assert f'"DMIC{n}", "MIC BIAS{bias}"' in o
assert 'qcom,tavil-mclk-clk-freq = <9600000>' in o
card = (old / 'samurai-audio-card.dtsi').read_text()
card = card.replace('"Microphone", "Handset Mic";', '"Microphone", "Handset Mic",\n\t\t\t  "Microphone", "Secondary Mic", "Microphone", "Speaker Mic";')
needle = '"AMIC1", "Handset Mic", "Handset Mic", "MIC BIAS1";'
assert card.count(needle) == 1
card = card.replace(needle, '''/* Native WCD934x uses distinct DMIC input pins and supplies. */
                "DMIC0 Pin", "Handset Mic", "DMIC0", "MIC BIAS1", "DMIC0", "MCLK",
                "DMIC1 Pin", "Secondary Mic", "DMIC1", "MIC BIAS1", "DMIC1", "MCLK",
                "DMIC2 Pin", "Speaker Mic", "DMIC2", "MIC BIAS3", "DMIC2", "MCLK";''')
card = card.replace('"Headphone Jack", "Handset Mic";', '"Headphone Jack", "Handset Mic", "Secondary Mic", "Speaker Mic";')
before = (out / 'dts-before').read_text()
assert before.endswith('\n' + (old / 'samurai-audio-card.dtsi').read_text())
after = before[:-(len((old / 'samurai-audio-card.dtsi').read_text()))] + card
(ref / 'samurai-audio-card.dtsi').write_text(card)
(k / paths['dts-before']).write_text(after)
(ref / 'sm8150-samurai.dts.after').write_text(after)

# APR fills domain/service only. Initialize reserved ports/token explicitly.
p = k / paths['q6core-before.c']
c = p.read_text()
assert c.count('struct apr_pkt pkt;') == 3
c = c.replace('struct apr_pkt pkt;', 'struct apr_pkt pkt = {};')
needle = '\tresult = data->payload;\n\tswitch (hdr->opcode) {'
assert c.count(needle) == 1
c = c.replace(needle, '''\tif (of_machine_is_compatible("realme,samurai"))
\t\tdev_info_ratelimited(&adev->dev,
\t\t\t"samurai core reply opcode=%#x bytes=%d token=%#x ports=%u/%u\\n",
\t\t\thdr->opcode, data->payload_size, hdr->token,
\t\t\thdr->src_port, hdr->dest_port);
\tresult = data->payload;
\tswitch (hdr->opcode) {''')
needle = '\t\tresult = data->payload;\n\t\tswitch (result->opcode) {'
assert c.count(needle) == 1
c = c.replace(needle, '''\t\tresult = data->payload;
\t\tif (of_machine_is_compatible("realme,samurai"))
\t\t\tdev_info_ratelimited(&adev->dev,
\t\t\t\t"samurai core basic command=%#x status=%u\\n",
\t\t\t\tresult->opcode, result->status);
\t\tswitch (result->opcode) {''')
for f in ('fwk', 'svc'):
    needle = f'\t\tcore->{"fwk_version" if f == "fwk" else "svc_version"} = kmemdup(data->payload,'
    assert c.count(needle) == 1
    obj = 'fwk' if f == 'fwk' else 'v'
    c = c.replace(needle, f'''\t\tif (of_machine_is_compatible("realme,samurai"))
\t\t\tdev_info(&adev->dev, "samurai core {f} valid services=%u\\n",
\t\t\t\t {obj}->num_services);
''' + needle)
needle = '\trc = apr_send_pkt(adev, &pkt);'
assert c.count(needle) == 3
c = c.replace(needle, needle + '''
\tif (of_machine_is_compatible("realme,samurai"))
\t\tdev_info_ratelimited(&adev->dev,
\t\t\t"samurai core send opcode=%#x rc=%d ports=%u/%u token=%#x\\n",
\t\t\tpkt.hdr.opcode, rc, pkt.hdr.src_port, pkt.hdr.dest_port,
\t\t\tpkt.hdr.token);''')
p.write_text(c)
(ref / 'q6core.c.after').write_text(c)

# Do not conceal failed transport behind a successful PCM trigger.
p = k / paths['wcd934x-before.c']
c = p.read_text()
start = c.index('static int wcd934x_trigger(')
end = c.index('\nstatic int wcd934x_set_channel_map(', start)
c = c[:start] + '''static int wcd934x_trigger(struct snd_pcm_substream *substream, int cmd,
                          struct snd_soc_dai *dai)
{
\tstruct wcd934x_codec *wcd = snd_soc_component_get_drvdata(dai->component);
\tstruct wcd_slim_codec_dai_data *dai_data = &wcd->dai[dai->id];
\tint ret = 0, cleanup;

\tswitch (cmd) {
\tcase SNDRV_PCM_TRIGGER_START:
\tcase SNDRV_PCM_TRIGGER_RESUME:
\tcase SNDRV_PCM_TRIGGER_PAUSE_RELEASE:
\t\tret = slim_stream_prepare(dai_data->sruntime, &dai_data->sconfig);
\t\tif (ret)
\t\t\tbreak;
\t\tret = slim_stream_enable(dai_data->sruntime);
\t\tif (ret)
\t\t\tslim_stream_unprepare(dai_data->sruntime);
\t\tbreak;
\tcase SNDRV_PCM_TRIGGER_STOP:
\tcase SNDRV_PCM_TRIGGER_SUSPEND:
\tcase SNDRV_PCM_TRIGGER_PAUSE_PUSH:
\t\tret = slim_stream_disable(dai_data->sruntime);
\t\tcleanup = slim_stream_unprepare(dai_data->sruntime);
\t\tif (!ret)
\t\t\tret = cleanup;
\t\tbreak;
\tdefault:
\t\treturn -EINVAL;
\t}
\tif (of_machine_is_compatible("realme,samurai"))
\t\tdev_info(dai->dev, "samurai slim trigger dai=%d command=%d channels=%u rate=%u ret=%d\\n",
\t\t\t dai->id, cmd, dai_data->sconfig.ch_count,
\t\t\t dai_data->sconfig.rate, ret);
\treturn ret;
}
''' + c[end:]
assert '#include <linux/of.h>' in c
p.write_text(c)
(ref / 'wcd934x.c.after').write_text(c)
for n, target in [('dts', paths['dts-before']), ('q6core', paths['q6core-before.c']), ('wcd934x', paths['wcd934x-before.c'])]:
    original = (out / {'dts': 'dts-before', 'q6core': 'q6core-before.c', 'wcd934x': 'wcd934x-before.c'}[n]).read_text()
    changed = (k / target).read_text()
    (ref / (n + '.patch')).write_text(''.join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True), fromfile='a/' + target, tofile='b/' + target)))
(out / 'preparation.json').write_text(json.dumps(dict(stage=104, kernel_build=103, source_prepared=True,
    native_dmic_topology=True, micbias1_microvolts=1800000, dmic_mclk_hz=9600000,
    oem_topology_sha256=sha(oem), initialized_apr_packets=3, actual_reply_diagnostics=True,
    slim_trigger_errors_propagated=True, initramfs_mutated=False, nv_mutated=False,
    bluetooth_pair_or_connect=False, vibration_pulses=False, goal_complete=False), indent=2) + '\n')
print('STAGE104_MIC_CLOCK_BIAS_AND_APR_SOURCE_PREPARED')
