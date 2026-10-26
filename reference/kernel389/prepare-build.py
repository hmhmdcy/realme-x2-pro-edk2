from pathlib import Path
import ast,json
import host
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel388/build-intree.py').read_text().replace('stage=388','stage=389')
s=s.replace("modules=[camss/'qcom-camss-icp-a5-core.ko'", "modules=[camss/'qcom-camss.ko',camss/'qcom-camss-icp-a5-core.ko'")
s=s.replace("modules += [vb2/", "modules += [v4l2/'v4l2-isp.ko']\nmodules += [vb2/")
anchor="try:\n with log.open('xb') as stream:"
setup="""try:
 subprocess.run([str(source/'scripts/config'),'--file',str(build/'.config'),'--enable','VIDEO_QCOM_CAMSS_ICP','--module','VIDEO_QCOM_CAMSS_ICP_A5_BOOT_TEST'],check=True)
 config=subprocess.run(['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','olddefconfig'],env=env,capture_output=True)
 (P/('olddefconfig-r'+str(attempt)+'.log')).write_bytes(config.stdout+config.stderr);config.check_returncode()
 selected=[line for line in (build/'.config').read_text().splitlines() if line.startswith(('CONFIG_VIDEO_QCOM_CAMSS=','CONFIG_VIDEO_QCOM_CAMSS_ICP','CONFIG_V4L2_MEM2MEM_DEV='))]
 assert 'CONFIG_VIDEO_QCOM_CAMSS_ICP=y' in selected
 assert 'CONFIG_VIDEO_QCOM_CAMSS=m' in selected and 'CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_CORE=m' in selected and 'CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_M2M=m' in selected,selected
 with log.open('xb') as stream:"""
assert s.count(anchor)==1;s=s.replace(anchor,setup)
s=s.replace("'CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_CORE=m'", "'CONFIG_VIDEO_QCOM_CAMSS_ICP=y','CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_CORE=m'",1)
s=s.replace("firmware_region=json.loads((P/'live-overlay-state-private.json').read_text()),", "selected_config=selected,normal_camss_and_icp_same_module_owner=True,")
ast.parse(s);(HERE/'build-intree.py').write_text(s)
print('Normal CAMSS/ICP build with real Kconfig selection and output restoration prepared.')
