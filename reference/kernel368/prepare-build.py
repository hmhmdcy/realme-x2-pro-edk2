from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
assert json.loads((HERE/'source-state.json').read_text())['applied']
s=(HERE.parent/'kernel366/build-intree.py').read_text().replace('stage=366','stage=368')
line="(source/relative/'camss-icp-a5-boot-test.c').write_text((HERE/'camss-icp-a5-boot-test.c').read_text())\n"
assert line in s;s=s.replace(line,'')
s=s.replace("modules=['qcom-camss-icp-a5-core','camss-icp-a5-boot-test','camss-icp-a5-memory-test']", "modules=['qcom-camss-icp-a5-core']")
s=s.replace(",'CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_BOOT_TEST=m','CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_MEMORY_TEST=m'",'')
s=s.replace("firmware_region=json.loads((P/'live-overlay-state-private.json').read_text()),", "current_candidate_commit=json.loads((HERE/'source-state.json').read_text())['commit'],")
anchor="build=storage.mounted_build();source=build.parent/'source354';relative=Path('drivers/media/platform/qcom/camss');target=build/relative"
s=s.replace(anchor,anchor+"\nassert 'CONFIG_DEV_COREDUMP=y' in (build/'.config').read_text()\nassert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==json.loads((HERE/'source-state.json').read_text())['commit']\nassert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()")
compile(s,'build-intree.py','exec');(HERE/'build-intree.py').write_text(s)
print('Prepared only A5 core target with real devcoredump support, W1/-Werror, installed k363 release.')
