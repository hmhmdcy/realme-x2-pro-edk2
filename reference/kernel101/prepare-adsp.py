from pathlib import Path
import difflib, hashlib, json, shutil, subprocess

root=Path('/mnt/e/RealmeX2Pro edk2')
ref=root/'reference/kernel101'
out=Path('/mnt/e/edk2-samurai-out/kernel101')
old=out.parent/'kernel100'
k=Path('/home/cy122/x2pro-linux/linux')
init=Path('/home/cy122/x2pro-linux/initramfs')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((out/'preflight-validation.json').read_text())['readonly_preflight_audit_pass']
assert sha(k/'arch/arm64/boot/Image')=='2391f376fc8b8e9eb8de24002c89a8e7645eb00f2bbb2ad3794e45926a0d20be'
assert sha(k/'usr/initramfs_data.cpio')=='77f1c94e6ca7f43cfffd04ac82180cc88c2221b9db087bdaa3d6505f4c0e854e'
assert not (out/'config-before').exists()
paths=[('config-before',k/'.config'),('Image-before',k/'arch/arm64/boot/Image'),
       ('cpio-before',k/'usr/initramfs_data.cpio'),('dtb-before',k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'),
       ('dts-before',k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'),
       ('workspace-dts-mirror-before',root/'linux-port/dts/sm8150-samurai.dts')]
for name,p in paths:shutil.copyfile(p,out/name)
(out/'kernel-source-before.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=k))
before={str(p.relative_to(init)):sha(p) for p in init.rglob('*') if p.is_file() and not p.is_symlink()}
(out/'initramfs-before.json').write_text(json.dumps(before,indent=2)+'\n')
target=init/'usr/sbin/samurai-modem-remoteproc'
assert not target.exists()
shutil.copyfile(ref/'samurai-modem-remoteproc',target); target.chmod(0o755)
for name in ('samurai-wifi','samurai-radio-address'):
    path=init/'usr/sbin'/name
    source=path.read_text()
    (out/(name+'-before')).write_text(source)
    assert '/sys/class/remoteproc/remoteproc0' in source
    if name=='samurai-wifi':
        source=source.replace('prepare()\n{\n','prepare()\n{\n    mpss=$(/usr/sbin/samurai-modem-remoteproc)\n',1)
        source=source.replace('if [ -e /sys/class/remoteproc/remoteproc0/state ] && all_sources_ready; then',
          'if mpss=$(/usr/sbin/samurai-modem-remoteproc) && all_sources_ready; then',1)
    else:
        source=source.replace('    query=$(mktemp', '    mpss=$(/usr/sbin/samurai-modem-remoteproc) || return 1\n    query=$(mktemp',1)
        # Resolve before the state check, rather than after it.
        line='    mpss=$(/usr/sbin/samurai-modem-remoteproc) || return 1\n'
        source=source.replace(line,'').replace('    [ "$(cat /sys/class/remoteproc/remoteproc0/state)"',line+'    [ "$(cat /sys/class/remoteproc/remoteproc0/state)"',1)
    source=source.replace('/sys/class/remoteproc/remoteproc0/','$mpss/')
    assert '/sys/class/remoteproc/remoteproc0' not in source
    path.write_text(source)
    (ref/name).write_text(source)
    original=(out/(name+'-before')).read_text()
    (ref/(name+'-named-mpss.patch')).write_text(''.join(difflib.unified_diff(original.splitlines(True),source.splitlines(True),fromfile='a/usr/sbin/'+name,tofile='b/usr/sbin/'+name)))
fw=init/'lib/firmware/qcom/sm8150/realme/samurai'
# The same directory already contains the verified GPU zap image.
assert not list(fw.glob('adsp*'))
fw.mkdir(parents=True,exist_ok=True)
files=sorted((out/'adsp-firmware').iterdir())
assert len(files)==17 and sum(p.stat().st_size for p in files)==12420754
for p in files:
    assert p.name=='adsp.mdt' or p.name in ('adspr.jsn','adspua.jsn') or (p.name.startswith('adsp.b') and len(p.name)==8 and p.name[-2:].isdigit())
    assert p.is_file() and not p.is_symlink()
    shutil.copyfile(p,fw/p.name)
dts=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
original=dts.read_text()
assert original.count('&remoteproc_adsp {\n\tstatus = "disabled";\n};')==1
after=original.replace('&remoteproc_adsp {\n\tstatus = "disabled";\n};','''&remoteproc_adsp {
	firmware-name = "qcom/sm8150/realme/samurai/adsp.mdt";
	status = "okay";

	glink-edge {
		apr {
			compatible = "qcom,apr-v2";
			qcom,glink-channels = "apr_audio_svc";
			qcom,domain = <4>;
			qcom,intents = <512 20>;
			#address-cells = <1>;
			#size-cells = <0>;

			service@3 {
				compatible = "qcom,q6core";
				reg = <3>;
				qcom,protection-domain = "avs/audio", "msm/adsp/audio_pd";
			};
		};
	};
};''')
dts.write_text(after)
(ref/'samurai-adsp-dts.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),after.splitlines(True),fromfile='a/arch/arm64/boot/dts/qcom/sm8150-samurai.dts',tofile='b/arch/arm64/boot/dts/qcom/sm8150-samurai.dts')))
(ref/'sm8150-samurai.dts.after').write_text(after)
args=['scripts/config']
for name in ('SOUND','SND','SND_SOC','SND_SOC_QCOM','SND_SOC_QDSP6','QCOM_APR'):args+=['--enable',name]
subprocess.run(args,cwd=k,check=True)
(out/'preparation.json').write_text(json.dumps(dict(prepared=True,logical_stage=101,kernel_build=100,
  firmware_private=True,firmware_files=17,firmware_bytes=12420754,firmware_source='installed-handset-modem-readonly',
  added_remoteproc='adsp',apr_services=[3],alsa_card_added=False,codec_or_amp_enabled=False,
  hardware_tested=False,physical_vibration_confirmed=False,physical_vibration_deferred_by_user=True,goal_complete=False),indent=2)+'\n')
print('ADSP_SOURCE_PREPARED')
