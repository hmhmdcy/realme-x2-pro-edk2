"""Default inert. Exact two-file cold rollback; no module/carrier activation."""
from pathlib import Path,PurePosixPath
from types import SimpleNamespace
import argparse,base64,copy,hashlib,io,json,math,os,re,runpy,stat,struct,sys,tarfile,time,uuid
sys.dont_write_bytecode=True
OLD_FILES={'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko': '7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f', '/usr/share/samurai-charging/manifest.json': '18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5'}
NEW_FILES={'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko': 'd04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037', '/usr/share/samurai-charging/manifest.json': '34ead4cdb98c2d4b812662cdbe4c0964d5e705574b5d4ab85716b37975a8a39b'}
OLD_NOTES={'samurai-usb-input': 'a845cd08aa415ca01ad4791b8c66047a927577e76439e632c73b6b4e2cff8c6d', 'samurai-gauge-protection': 'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec', 'samurai-mp2650': 'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'}
NEW_NOTES={'samurai-usb-input': '08523f9f969b00a278a87ddd5d27ec3b54ac9b53a9c84f6429c4ecf5934c0f3f', 'samurai-gauge-protection': 'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec', 'samurai-mp2650': 'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'}
NEW_MANIFEST={'release': '7.3.0-rc6-rmx1931-samurai-k363+', 'modules': {'samurai-mp2650': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko', 'sha256': '97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd'}, 'samurai-usb-input': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko', 'sha256': 'd04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037'}, 'samurai-gauge-protection': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko', 'sha256': '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044'}}, 'default_input_cap_ua': 900000, 'default_charge_cap_ua': 250000, 'source_budget_enforced': True, 'installed_files': {'/usr/sbin/samurai-charging': '61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4', '/etc/init.d/samurai-charging': 'bfed48ebbcaced5f017110564045eef500a88f12fefe7ebff6d1e74cabfe570a', '/usr/lib/samurai-charging/control-trial.py': 'c33cb2eec24031e72a5f1dda9b94c05607615e0b12a14ba3cecd6db56c820761', '/usr/lib/samurai-charging/live-session.py': '2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko': '97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko': 'd04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko': '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044'}, 'adapter_revision': 'usb-irq-native-pm-budget504-01'}
RELEASE='7.3.0-rc6-rmx1931-samurai-k363+'
VERSION502='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
VERSION504='#504 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
BOOT='eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
LOGDUMP502='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
LOGDUMP504='4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83'
ROOT='/root/charging-management-20261023'
SERVICE='/usr/sbin/samurai-charging'
MANAGER='61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4'
LIVE_SHA='2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b'
STARTUP_SHA='2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a'
LOCK='/run/lock/samurai-charging.lock'
INSTANCE='/sys/devices/platform/samurai-gauge-protection'
MANIFEST='/usr/share/samurai-charging/manifest.json'
USB='/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko'
ORDER=['/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko', '/usr/share/samurai-charging/manifest.json']
ROLLBACK_PAYLOAD='6ff66d182f7b0dc7ac32e3e58ae756e259c246b4edddf85d48878ff561835ab8'
STAGE_WORKER='8e188610e8002c4d23a70a7d3d01572366ebf668c0674ac93ea4f05b23aeb7e8'
STAGE_SUPERVISOR='b29ab985159ecc911571514cdc5fa72a1a44886037e35ff024dfa6fe623440cc'
STAGE_RULES='"""Current cold-stage guards. Definitions have no device side effects."""\nimport base64,fcntl,hashlib,json,os,re,runpy,stat,struct,sys,time,uuid\nfrom pathlib import Path\nROOT=Path(\'/root/charging-management-20261023\')\nSERVICE_LOCK=\'/run/lock/samurai-charging.lock\'\nSTAGE_WORKER=\'8e188610e8002c4d23a70a7d3d01572366ebf668c0674ac93ea4f05b23aeb7e8\'\nSTAGE_SUPERVISOR=\'b29ab985159ecc911571514cdc5fa72a1a44886037e35ff024dfa6fe623440cc\'\nLIVE_PATH=\'/usr/lib/samurai-charging/live-session.py\'\nLIVE_SHA=\'2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b\'\n_SERVICE_FD=None\n_MAC_FD=None\nCAMERA481=\'1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705\'\nSENSOR468_NOTE=\'a52ef87a2388757c542768e5438120d858e785bd334c080b55dec0f532c54d13\'\nFIXED={\'schema\': \'samurai-irq-native-usb-pm-activation-v1\', \'kernel_release\': \'7.3.0-rc6-rmx1931-samurai-k363+\', \'kernel_version\': \'#504 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026\', \'source_kernel_version\': \'#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026\', \'partitions\': [\'logdump\'], \'boot_bytes\': 100663296, \'logdump_bytes\': 67108864, \'image502_sha256\': \'085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955\', \'charging_manifest_sha256\': \'34ead4cdb98c2d4b812662cdbe4c0964d5e705574b5d4ab85716b37975a8a39b\', \'source_manifest_sha256\': \'18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5\', \'cohort_delivery_sha256\': \'89349ffc0adb7e0043505f0250b53eefd78cc917f0b953fb12bb4aeabe25da01\', \'startup500_sha256\': \'2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a\', \'startup500_path\': \'/usr/local/sbin/samurai-usb\', \'max_power_ma\': 500, \'camera481_expected_sha256\': \'1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705\', \'new_disk_files\': {\'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko\': \'d04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037\', \'/usr/share/samurai-charging/manifest.json\': \'34ead4cdb98c2d4b812662cdbe4c0964d5e705574b5d4ab85716b37975a8a39b\'}, \'old_resident_notes\': {\'samurai_usb_input\': \'a845cd08aa415ca01ad4791b8c66047a927577e76439e632c73b6b4e2cff8c6d\', \'samurai_gauge_protection\': \'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec\', \'samurai_mp2650\': \'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016\'}, \'unchanged_boot_sha256\': \'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06\', \'candidate_logdump_sha256\': \'4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83\', \'rollback_logdump_sha256\': \'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1\', \'image504_sha256\': \'f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4\'}\nEXPECTED_MANIFEST={\'release\': \'7.3.0-rc6-rmx1931-samurai-k363+\', \'modules\': {\'samurai-mp2650\': {\'target\': \'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko\', \'sha256\': \'97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd\'}, \'samurai-usb-input\': {\'target\': \'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko\', \'sha256\': \'d04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037\'}, \'samurai-gauge-protection\': {\'target\': \'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko\', \'sha256\': \'7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044\'}}, \'default_input_cap_ua\': 900000, \'default_charge_cap_ua\': 250000, \'source_budget_enforced\': True, \'installed_files\': {\'/usr/sbin/samurai-charging\': \'61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4\', \'/etc/init.d/samurai-charging\': \'bfed48ebbcaced5f017110564045eef500a88f12fefe7ebff6d1e74cabfe570a\', \'/usr/lib/samurai-charging/control-trial.py\': \'c33cb2eec24031e72a5f1dda9b94c05607615e0b12a14ba3cecd6db56c820761\', \'/usr/lib/samurai-charging/live-session.py\': \'2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b\', \'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko\': \'97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd\', \'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko\': \'d04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037\', \'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko\': \'7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044\'}, \'adapter_revision\': \'usb-irq-native-pm-budget504-01\'}\nOLD_MANIFEST={\'release\': \'7.3.0-rc6-rmx1931-samurai-k363+\', \'modules\': {\'samurai-mp2650\': {\'target\': \'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko\', \'sha256\': \'97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd\'}, \'samurai-usb-input\': {\'target\': \'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko\', \'sha256\': \'7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f\'}, \'samurai-gauge-protection\': {\'target\': \'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko\', \'sha256\': \'7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044\'}}, \'default_input_cap_ua\': 900000, \'default_charge_cap_ua\': 250000, \'source_budget_enforced\': True, \'installed_files\': {\'/usr/sbin/samurai-charging\': \'61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4\', \'/etc/init.d/samurai-charging\': \'bfed48ebbcaced5f017110564045eef500a88f12fefe7ebff6d1e74cabfe570a\', \'/usr/lib/samurai-charging/control-trial.py\': \'c33cb2eec24031e72a5f1dda9b94c05607615e0b12a14ba3cecd6db56c820761\', \'/usr/lib/samurai-charging/live-session.py\': \'2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b\', \'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko\': \'97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd\', \'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko\': \'7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f\', \'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko\': \'7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044\'}, \'adapter_revision\': \'usb-irq-protection-observer-01\'}\nRELEASE=\'7.3.0-rc6-rmx1931-samurai-k363+\'\nVERSION=\'#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026\'\nBOOT=\'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06\'\nLOGDUMP=\'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1\'\nOLD=\'18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5\'\nOLD_NOTES={\'samurai-usb-input\': \'a845cd08aa415ca01ad4791b8c66047a927577e76439e632c73b6b4e2cff8c6d\', \'samurai-gauge-protection\': \'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec\', \'samurai-mp2650\': \'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016\'}\nUSB=\'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko\'\nMANIFEST=\'/usr/share/samurai-charging/manifest.json\'\nOLD_FILES={\'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko\': \'7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f\', \'/usr/share/samurai-charging/manifest.json\': \'18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5\'}\nPAYLOAD=\'f1162d2b5614327f0ce78c918cec62fd681d42cca99d8c03819cfa41086230bc\'\nMAC_CACHE_SHA=\'02c98143301bb5db896c6f535f490495428df8b8c6fd6ab3cdc69ca507a545a8\'\n\ndef secure_file(path):\n p=Path(path);assert p.is_file() and not p.is_symlink(),str(p)\n s=p.stat();assert s.st_uid==0 and not s.st_mode&0o022,str(p)\n return p\n\ndef file_sha(path):\n return hashlib.sha256(secure_file(path).read_bytes()).hexdigest()\n\ndef block_sha(path,expected_bytes):\n # This is the existing read-only by-partlabel boundary, with an actual block\n # size check. Never read a writable mapping or use blockdev\'s mutation paths.\n fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC)\n try:\n  assert stat.S_ISBLK(os.fstat(fd).st_mode)\n  assert struct.unpack(\'=Q\',fcntl.ioctl(fd,0x80081272,bytes(8)))[0]==expected_bytes\n  digest=hashlib.sha256();remaining=expected_bytes\n  while remaining:\n   data=os.read(fd,min(1048576,remaining));assert data,\'short partition read\'\n   digest.update(data);remaining-=len(data)\n  return digest.hexdigest()\n finally:os.close(fd)\n\ndef camera481_check(wrapper):\n assert file_sha(wrapper)==CAMERA481\n expected=json.loads(Path(wrapper).read_bytes());assert expected[\'validated\']\n expected=expected[\'expected\'];assert expected[\'kernel_release\']==os.uname().release\n for name,digest in expected[\'installed_files\'].items():assert file_sha(name)==digest,name\n for name,info in expected[\'modules\'].items():\n  assert file_sha(info[\'path\'])==info[\'sha256\']\n  assert hashlib.sha256(Path(\'/sys/module\',name,\'notes/.note.gnu.build-id\').read_bytes()).hexdigest()==info[\'note\']\n  assert Path(\'/sys/module\',name,\'initstate\').read_text().strip()==\'live\'\n assert hashlib.sha256(Path(\'/sys/module/s5k3m5/notes/.note.gnu.build-id\').read_bytes()).hexdigest()==SENSOR468_NOTE\n assert Path(\'/sys/module/s5k3m5/initstate\').read_text().strip()==\'live\'\n versions={}\n for block in Path(\'/lib/apk/db/installed\').read_text().split(\'\\n\\n\'):\n  fields=dict(line.split(\':\',1) for line in block.splitlines() if \':\' in line)\n  if fields.get(\'P\') in expected[\'packages\']:versions[fields[\'P\']]=fields.get(\'V\')\n assert versions==expected[\'packages\']\n\ndef eud_off_check():\n # Firmware keeps COM disabled. No MMIO or driver control is part of this gate.\n node=Path(\'/sys/firmware/devicetree/base/soc@0/serial@88e0000\')\n assert (node/\'compatible\').read_bytes()==b\'qcom,sm8150-eud-com\\0\'\n assert (node/\'status\').read_bytes()==b\'disabled\\0\'\n assert not Path(\'/sys/bus/platform/devices/88e0000.serial/driver\').exists()\n driver=Path(\'/sys/bus/platform/drivers/qcom_eud_com\')\n assert not list(driver.glob(\'*.serial\'))\n assert not list(Path(\'/sys/class/tty\').glob(\'ttyEUD*\'))\n assert not any(\'eud\' in line.lower() for line in Path(\'/proc/consoles\').read_text().splitlines())\n assert not any(t.startswith((\'earlycon=eud\',\'console=eud\')) for t in Path(\'/proc/cmdline\').read_text().split())\n\ndef charging_sample_phase(sample, stopped=False):\n full=(sample[\'logical_full\']==sample[\'hold_requested\']==sample[\'full_holding\']==1 and sample[\'full_cause\'] in (1,2,3) and sample[\'desired_enable\']==0 and sample[\'session_seconds\']==0)\n if stopped:\n  return sample[\'desired_enable\']==sample[\'hold_requested\']==sample[\'full_holding\']==0 and (sample[\'logical_full\']==0 and sample[\'full_cause\']==0 or sample[\'logical_full\']==1 and sample[\'full_cause\'] in (1,2,3) and sample[\'session_seconds\']==0)\n return full if any(sample[k] for k in [\'logical_full\',\'hold_requested\',\'full_holding\',\'full_cause\']) else sample[\'desired_enable\']==1\n\ndef safe_sample(data, now):\n    s = data[\'sample\']\n    need(s.get(\'valid\') == s.get(\'protection_ok\') == s.get(\'online\') == 1 and\n         s.get(\'shadow\') == 0 and 0 <= s.get(\'age_ms\', -1) <= 3000, \'fresh complete online protection sample\')\n    need(all(s.get(k, -1) == 0 for k in [\'error\', \'stop_error\', \'latched\', \'fault\', \'source_inhibit\',\n                                       \'cycle_timeout\', \'thermal_inhibit\', \'gauge_charge_stop\']), \'no fault/timeout/gauge or thermal stop\')\n    need(\'flags\' in s and not s[\'flags\'] & 0xc000 and 0 <= s.get(\'session_seconds\', -1) < 36000, \'safe raw flags/session\')\n    need(all(2000000 <= s.get(key, 0) <= 4600000 for key in [\'cell1_uv\', \'cell2_uv\']) and\n         4000000 <= s.get(\'pack_uv\', 0) <= 9200000 and\n         abs(s[\'cell1_uv\'] + s[\'cell2_uv\'] - s[\'pack_uv\']) <= 200000, \'safe complete pack/cell values\')\n    need(160 <= s.get(\'temp_decic\', -999) < 440 and s.get(\'thermal_band\') == 4, \'known safe NORMAL window\')\n    need(0 <= data[\'read_end\'] - data[\'read_start\'] <= 3 and 0 <= now - data[\'read_end\'] <= 1, \'fresh bounded observation\')\n    p = data[\'protection\']\n    need(data[\'protection_health\'] == \'Good\' and p.get(\'id\') == 0x2719 and p.get(\'error\') == p.get(\'safety\') == p.get(\'pf\') == 0,\n         \'independent fresh protection state\')\n    need(p.get(\'operation\', 0) & 0x300 == 0x300 and not p[\'operation\'] & ((1 << 20) | (1 << 16) | 0x7c00) and\n         p.get(\'manufacturing\', 0) & 0x18 == 0x18 and not p[\'manufacturing\'] & 0x8006, \'sealed autonomous factory protection\')\n    need(data[\'notes\'] == OLD_NOTES and data[\'openrc_started\'] is True, \'old resident modules and service retained\')\n\ndef environment(data):\n    state = data[\'state\']\n    need(state[\'taint\'] == \'0\' and state[\'driver\'] == \'samurai-mp2650\' and\n         len(state[\'camera_pm\']) == 4 and all(v == \'suspended\' for v in state[\'camera_pm\'].values()), \'idle camera and managed charger\')\n    m2m = json.loads(state[\'m2m\'])\n    need(all(m2m.get(k) == 0 for k in [\'users\', \'orphans\', \'jobs\', \'first_error\']) and\n         all(m2m.get(k) is False for k in [\'running\', \'fatal\', \'pinned\']), \'idle camera m2m\')\n    services = state[\'services\']\n    need(len(services) == 4 and {s[\'comm\'] for s in services} == {\'phoc\', \'phosh\', \'pipewire\', \'wireplumber\'} and\n         all(s[\'uid\'] == 10000 and s[\'pid\'] > 0 for s in services), \'actual four session processes\')\n\ndef active(text):\n assert isinstance(text,str),\'unreadable active choice\'\n found=re.findall(r\'\\[([^]]+)\\]\',text)\n return found[0] if len(found)==1 else text.strip() if not found and len(text.split())==1 else None\n\ndef need(value,message):\n if not value:raise ValueError(message)\n\ndef sha(raw):return hashlib.sha256(raw).hexdigest()\n\ndef owned_directory(path):\n p=Path(path);s=p.lstat()\n need(stat.S_ISDIR(s.st_mode) and not p.is_symlink() and s.st_uid==0 and stat.S_IMODE(s.st_mode)==0o700,\'owned directory: \'+str(p))\n return p\n\ndef raw_owned(path,limit=4_000_000):\n p=secure_file(path);s=p.stat()\n need(s.st_size<=limit and stat.S_IMODE(s.st_mode)==0o600,\'bounded private raw: \'+str(p))\n return p.read_bytes()\n\ndef process_observation(receipt):\n pid=receipt[\'pid\'];need(type(pid) is int and pid>0,\'retained positive PID\')\n try:fields=Path(\'/proc\',str(pid),\'stat\').read_text().rsplit(\')\',1)[1].split()\n except FileNotFoundError:return {\'state\':\'absent\',\'pid\':pid}\n except (OSError,ValueError,IndexError):return {\'state\':\'unknown\',\'pid\':pid}\n try:ticks=int(fields[19])\n except (ValueError,IndexError):return {\'state\':\'unknown\',\'pid\':pid}\n if ticks!=receipt[\'start_ticks\']:return {\'state\':\'pid_reused\',\'pid\':pid}\n return {\'state\':\'zombie\' if fields[0]==\'Z\' else \'alive\',\'pid\':pid,\'start_ticks\':ticks}\n\ndef observe_staged():\n need(file_sha(LIVE_PATH)==LIVE_SHA,\'fixed read-only live library\')\n live=runpy.run_path(LIVE_PATH)\n need(file_sha(LIVE_PATH)==LIVE_SHA and live[\'REGS\']==[0,1,2,3,4,5,7,8,9,15,19],\'stable non-destructive register set\')\n start=time.clock_gettime(time.CLOCK_BOOTTIME);state=live[\'state\']()\n ps=Path(\'/sys/class/power_supply\');supply=ps/\'mp2650-input\'\n protection=Path(\'/sys/devices/platform/samurai-gauge-protection/protection_state\').read_text()\n result={\'read_start\':start,\'state\':state,\n  \'sample\':{k:int(v) for k,v in (p.split(\'=\') for p in Path(\'/sys/bus/i2c/devices/0-005c/telemetry\').read_text().split())},\n  \'source\':{k:(ps/\'samurai-usb-input\'/k).read_text().strip() for k in [\'online\',\'usb_type\',\'current_max\',\'input_current_limit\']},\n  \'notes\':{name:sha(Path(\'/sys/module\',name.replace(\'-\',\'_\'),\'notes/.note.gnu.build-id\').read_bytes()) for name in OLD_NOTES},\n  \'openrc_started\':Path(\'/run/openrc/started/samurai-charging\').exists(),\n  \'protection\':{k:int(v,0) for k,v in (p.split(\'=\') for p in protection.split())},\n  \'protection_health\':(ps/\'samurai-gauge-protection/health\').read_text().strip(),\n  \'charge_behaviour\':(supply/\'charge_behaviour\').read_text().strip(),\n  \'limits\':{\'input_ua\':int((supply/\'input_current_limit\').read_text()),\'charge_ua\':int((supply/\'constant_charge_current\').read_text()),\n    \'cv_pack_uv\':int((supply/\'constant_charge_voltage\').read_text())}}\n result[\'read_end\']=time.clock_gettime(time.CLOCK_BOOTTIME)\n return result\n\ndef staged_health(data,now):\n safe_sample(data,now)\n s,r,lim=data[\'sample\'],data[\'state\'][\'registers\'],data[\'limits\']\n need(charging_sample_phase(s,True) and active(data[\'charge_behaviour\'])==\'inhibit-charge\' and r[\'08\']&0x18==8,\'stage INHIBIT still held\')\n source=data[\'source\'];kind=active(source[\'usb_type\'])\n need(source[\'online\']==\'1\',\'actual online source\')\n budget,native=int(source[\'current_max\']),int(source[\'input_current_limit\'])\n need(native==500000 and ((kind==\'SDP\' and budget==500000) or\n  (kind in [\'CDP\',\'DCP\'] and budget==1500000) or (kind==\'C\' and budget in [1500000,3000000])),\'fresh known source/native500 budget\')\n need(s[\'budget_ua\']==budget and lim[\'input_ua\']==min(900000,budget) and lim[\'charge_ua\']==250000,\'fresh source authority/caps\')\n need((r[\'00\']&0x7f)*50000==(r[\'0f\']&0x7f)*50000==lim[\'input_ua\'] and\n  (r[\'02\']&0x7f)*50000==lim[\'charge_ua\'],\'both actual input and charge limits\')\n need(7425000<=lim[\'cv_pack_uv\']<=8725000 and lim[\'cv_pack_uv\']==2*(3712500+((r[\'04\']&0x7e)>>1)*12500),\'inherited CV\')\n state=data[\'state\'];need(state[\'taint\']==\'0\' and state[\'driver\']==\'samurai-mp2650\',\'current untainted provider\')\n need(len(state[\'camera_pm\'])==4 and all(v==\'suspended\' for v in state[\'camera_pm\'].values()),\'idle actual camera\')\n m=json.loads(state[\'m2m\'])\n need(all(m.get(k)==0 for k in [\'users\',\'orphans\',\'jobs\',\'first_error\']) and\n  all(m.get(k) is False for k in [\'running\',\'fatal\',\'pinned\']),\'no active camera work\')\n return {\'stage_INHIBIT_reverified\':True,\'source\':kind,\'budget_ua\':budget,\'hardware_input_ua\':lim[\'input_ua\']}\n\ndef acquire_service_lock():\n global _SERVICE_FD\n need(_SERVICE_FD is None,\'single lock acquisition\')\n fd=os.open(SERVICE_LOCK,os.O_RDWR|os.O_NOFOLLOW)\n try:\n  info=os.fstat(fd);need(stat.S_ISREG(info.st_mode) and info.st_uid==0 and stat.S_IMODE(info.st_mode)==0o600,\'original service lock\')\n  fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)\n except BaseException:os.close(fd);raise\n _SERVICE_FD=fd\n\ndef stage_paths(transaction):\n need(re.fullmatch(r\'irq-native-usb-pm-stage-[a-z0-9-]{8,48}\',transaction),\'current cold stage name\')\n root=ROOT/transaction;out=root/\'device-stage\'\n return {**{k:str(root/v) for k,v in {\n  \'request\':\'request-private.json\',\'worker_launch\':\'worker-launch-receipt-private.json\',\n  \'worker_terminal\':\'worker-terminal-private.json\',\'supervisor_launch\':\'launch-receipt-private.json\',\n  \'supervisor_process\':\'supervisor-process-private.json\',\'supervisor_terminal\':\'supervisor-terminal-private.json\',\n  \'worker_source\':\'stage-worker.py\',\'supervisor_source\':\'stage-supervisor.py\'}.items()},\n  **{k:str(out/v) for k,v in {\'device_request\':\'request-private.json\',\'result\':\'result.json\',\n  \'before\':\'before-private.json\',\'stopped\':\'stopped-private.json\',\'after\':\'after-private.json\',\n  \'worker_process\':\'process-private.json\',\'files_before\':\'files-before-private.json\',\n  \'old_usb\':\'samurai-usb-input.ko.before\',\'old_manifest\':\'manifest.json.before\'}.items()}}\n\ndef validate_stage_receipts(meta,records,processes):\n stage=meta[\'stage\'];tx=stage[\'transaction_id\'];paths=stage_paths(tx)\n need(set(stage)=={\'transaction_id\',\'request_sha256\',\'result_sha256\',\'host_binding_sha256\',\n  \'worker_sha256\',\'supervisor_sha256\',\'evidence\'},\'stage exact fields\')\n need(stage[\'worker_sha256\']==STAGE_WORKER and stage[\'supervisor_sha256\']==STAGE_SUPERVISOR,\'fixed original stage sources\')\n need(set(stage[\'evidence\'])==set(paths),\'stage evidence keys\')\n for key,path in paths.items():\n  item=stage[\'evidence\'][key]\n  need(set(item)=={\'path\',\'sha256\'} and item[\'path\']==path and re.fullmatch(\'[0-9a-f]{64}\',item[\'sha256\']),\'fixed original evidence path/hash\')\n for name in [\'request_sha256\',\'result_sha256\',\'host_binding_sha256\']:\n  need(re.fullmatch(\'[0-9a-f]{64}\',stage[name]),\'actual stage digest: \'+name)\n need(stage[\'evidence\'][\'request\'][\'sha256\']==stage[\'evidence\'][\'device_request\'][\'sha256\']==stage[\'request_sha256\'] and\n  stage[\'evidence\'][\'result\'][\'sha256\']==stage[\'result_sha256\'],\'executed request/result raw binding\')\n need(stage[\'evidence\'][\'worker_source\'][\'sha256\']==STAGE_WORKER and stage[\'evidence\'][\'supervisor_source\'][\'sha256\']==STAGE_SUPERVISOR,\'source evidence hashes\')\n req=records[\'request\'];result=records[\'result\'];w=records[\'worker_process\'];s=records[\'supervisor_process\']\n need(req==records[\'device_request\'] and set(req)=={\'schema\',\'transaction_id\',\'cohort_delivery_sha256\',\'payload_sha256\',\'payload_base64\',\n  \'worker_sha256\',\'identity\',\'adoption\',\'lease_token\'},\'original exact executed request\')\n need(req[\'schema\']==\'samurai-irq-native-usb-pm-stage-request-v1\' and req[\'transaction_id\']==tx and req[\'worker_sha256\']==STAGE_WORKER,\'current stage request\')\n payload=base64.b64decode(req[\'payload_base64\'],validate=True)\n need(req[\'cohort_delivery_sha256\']==FIXED[\'cohort_delivery_sha256\'] and req[\'payload_sha256\']==PAYLOAD and\n  len(payload)==27163 and sha(payload)==PAYLOAD and re.fullmatch(\'[0-9a-f]{48}\',req[\'lease_token\']),\'actual current cohort/payload\')\n identity=dict(boot_id=meta[\'boot_id\'],version=FIXED[\'source_kernel_version\'],serial_sha256=meta[\'soc_serial_sha256\'],\n  compatible_sha256=meta[\'compatible_sha256\'],rootfs_sha256=meta[\'rootfs_release_sha256\'])\n need(req[\'identity\']==identity and req[\'adoption\']==meta[\'adoption\'],\'same actual source boot/guard\')\n need(result[\'schema\']==\'samurai-irq-native-usb-pm-stage-result-v1\' and result[\'transaction_id\']==tx and\n  result[\'request_sha256\']==stage[\'request_sha256\'] and result[\'cohort_delivery_sha256\']==FIXED[\'cohort_delivery_sha256\'] and\n  result[\'payload_sha256\']==PAYLOAD,\'stage result binding\')\n need(result[\'terminal\'] is True and result[\'staged\'] is True and result[\'phase\']==\'staged\' and\n  result[\'status\']==\'staged/runtime_pending\' and result[\'runtime_pending\'] is True and\n  result[\'disk_state\']==\'all_new_fsynced\' and result[\'stop_verified\'] is True,\'complete current stage terminal\')\n need(all(result.get(k) is None for k in [\'primary_error\',\'stop_error\',\'recovery_error\',\'receipt_error\',\'close_error\']) and\n  result.get(\'restored_original_disk\') is not True,\'no failed/restored stage promotion\')\n need(all(result.get(k) is False for k in [\'activation_attempted\',\'new_module_loaded\',\'capture_issued\']),\'no stage activation\')\n need(result[\'old_manifest_sha256\']==FIXED[\'source_manifest_sha256\'] and result[\'new_manifest_sha256\']==FIXED[\'charging_manifest_sha256\'] and\n  result[\'resident_notes\']==OLD_NOTES,\'old live/current disk tuple\')\n need(set(result[\'final_files\'])==set(FIXED[\'new_disk_files\']),\'exact two final disk files\')\n for name,digest in FIXED[\'new_disk_files\'].items():\n  need(result[\'final_files\'][name]==dict(sha256=digest,mode=\'0o600\',classification=\'new\'),\'actual stage final readback\')\n temporary={str(Path(name).with_name(\'.\'+Path(name).name+\'.\'+tx+suffix+\'.next\')) for name in FIXED[\'new_disk_files\'] for suffix in (\'\',\'-restore\')}\n need(set(result[\'temporary_files\'])==temporary and all(v=={\'state\':\'absent\'} for v in result[\'temporary_files\'].values()),\'no unknown/retained atomic temporary\')\n need(sha(records[\'old_usb\'])==OLD_FILES[USB] and sha(records[\'old_manifest\'])==OLD and\n  json.loads(records[\'old_manifest\'])==OLD_MANIFEST,\'actual exact old disk backups\')\n need(records[\'files_before\']=={USB:dict(sha256=OLD_FILES[USB],mode=\'0600\',bytes=len(records[\'old_usb\'])),\n  MANIFEST:dict(sha256=OLD,mode=\'0600\',bytes=len(records[\'old_manifest\']))},\'actual two-file backup metadata\')\n before,paused,after=[records[n] for n in [\'before\',\'stopped\',\'after\']]\n for snapshot in [before,paused,after]:\n  need(snapshot[\'identity\']==dict(identity,guard_sha256=meta[\'adoption\'][\'guard_sha256\']) and snapshot[\'notes\']==OLD_NOTES,\'stage snapshot identity/live tuple\')\n  safe_sample(snapshot,snapshot[\'read_end\'])\n  need(snapshot[\'source\']==before[\'source\'] and snapshot[\'limits\']==before[\'limits\'] and\n   all(snapshot[\'state\'][k]==before[\'state\'][k] for k in [\'boot_id\',\'release\',\'camera_pm\',\'m2m\',\'services\',\'driver\',\'taint\']) and\n   snapshot[\'state\'][\'registers\']==snapshot[\'registers\'],\'stage source/limits/environment retained\')\n  need(snapshot[\'mac_evidence\']==before[\'mac_evidence\'],\'same consumed MAC instance/cache\')\n environment(before)\n need(charging_sample_phase(before[\'sample\']) and before[\'registers\'][\'08\']&0x18==(0 if before[\'sample\'][\'logical_full\'] else 0x10),\'healthy managed or real Full before stop\')\n for previous,current in [(before,paused),(paused,after)]:\n  need(previous[\'read_end\']<=current[\'read_start\'] and charging_sample_phase(current[\'sample\'],True) and\n   current[\'registers\'][\'08\']==(previous[\'registers\'][\'08\']&~0x18)|8 and current[\'registers\'][\'13\']&2,\'ordered synchronous INHIBIT samples\')\n  need(set(previous[\'registers\'])==set(current[\'registers\']) and \'14\' not in current[\'registers\'] and\n   all(current[\'registers\'][k]==v for k,v in previous[\'registers\'].items() if k not in [\'08\',\'13\']),\'retained non-destructive configuration\')\n  if previous[\'sample\'][\'logical_full\']:\n   need(current[\'sample\'][\'logical_full\']==1 and current[\'sample\'][\'full_cause\']==previous[\'sample\'][\'full_cause\'] and current[\'sample\'][\'session_seconds\']==0,\'logical Full/cause retained through stop and stage\')\n need(result[\'logical_full_retained\']==after[\'sample\'][\'logical_full\'] and result[\'full_cause_retained\']==after[\'sample\'][\'full_cause\'],\'final Full result/sample binding\')\n wargv=[\'python3\',\'-B\',str(ROOT/tx/\'stage-worker.py\'),\'--execute-stage\']\n sargv=[\'python3\',\'-B\',str(ROOT/tx/\'stage-supervisor.py\'),\'--execute-supervisor\']\n need(set(w)=={\'transaction_id\',\'boot_id\',\'pid\',\'start_ticks\',\'argv\'},\'actual five-field stage self receipt\')\n for receipt,argv in [(w,wargv),(s,sargv)]:\n  need(type(receipt[\'pid\']) is int and receipt[\'pid\']>0 and type(receipt[\'start_ticks\']) is int and receipt[\'start_ticks\']>0 and\n   receipt[\'transaction_id\']==tx and receipt[\'boot_id\']==meta[\'boot_id\'] and receipt[\'argv\']==argv,\'original process instance\')\n need(s[\'request_sha256\']==stage[\'request_sha256\'],\'supervisor original request\')\n wl,wt,sl,st=[records[k] for k in [\'worker_launch\',\'worker_terminal\',\'supervisor_launch\',\'supervisor_terminal\']]\n for item,pid,argv in [(wl,w[\'pid\'],wargv),(wt,w[\'pid\'],wargv),(sl,s[\'pid\'],sargv),(st,s[\'pid\'],sargv)]:\n  need(item[\'pid\']==pid and item[\'argv\']==argv and item[\'transaction_id\']==tx and item[\'boot_id\']==meta[\'boot_id\'] and\n   item[\'request_sha256\']==stage[\'request_sha256\'],\'same original child/request\')\n need(wl[\'supervisor_pid\']==wt[\'supervisor_pid\']==s[\'pid\'] and wl.get(\'start_ticks\') in [None,w[\'start_ticks\']] and\n  sl.get(\'start_ticks\') in [None,s[\'start_ticks\']] and st[\'start_ticks\']==s[\'start_ticks\'],\'original child ownership/instances\')\n need(wt[\'terminal\'] is True and type(wt[\'returncode\']) is int and wt[\'returncode\']==0 and\n  st[\'terminal\'] is True and type(st[\'returncode\']) is int and st[\'returncode\']==0 and\n  st[\'worker_pid\']==w[\'pid\'] and type(st[\'worker_returncode\']) is int and st[\'worker_returncode\']==0,\'both original Popen wait0\')\n for key,receipt in [(\'worker\',w),(\'supervisor\',s)]:\n  observed=processes[key]\n  need(observed[\'pid\']==receipt[\'pid\'] and observed[\'state\'] in [\'absent\',\'zombie\'],\'original process not alive/unknown/reused\')\n  if observed[\'state\']==\'zombie\':need(observed[\'start_ticks\']==receipt[\'start_ticks\'],\'same zombie instance\')\n return req\n\ndef validate_stage_records(meta,records,processes,claim):\n request=validate_stage_receipts(meta,records,processes)\n tx=meta[\'stage\'][\'transaction_id\'];root=ROOT/tx\n need(claim[\'transaction_id\']==tx and claim[\'boot_id\']==meta[\'boot_id\'] and claim[\'request_sha256\']==meta[\'stage\'][\'request_sha256\'] and\n  claim[\'request_count\']==1 and claim[\'argv\']==[\'python3\',\'-B\',str(root/\'stage-worker.py\'),\'--execute-stage\'] and\n  claim[\'supervisor_argv\']==[\'python3\',\'-B\',str(root/\'stage-supervisor.py\'),\'--execute-supervisor\'] and\n  claim[\'supervisor_sha256\']==STAGE_SUPERVISOR,\'original device launch claim\')\n return request\n\ndef read_stage(meta):\n stage=meta[\'stage\'];root=owned_directory(ROOT/stage[\'transaction_id\']);owned_directory(root/\'device-stage\');records={}\n for key,path in stage_paths(stage[\'transaction_id\']).items():\n  item=stage[\'evidence\'][key];need(item[\'path\']==path,\'original stage path\')\n  raw=raw_owned(path);need(sha(raw)==item[\'sha256\'],\'stage original bytes changed: \'+key)\n  if key not in [\'worker_source\',\'supervisor_source\']:\n   records[key]=raw if key in [\'old_usb\',\'old_manifest\'] else json.loads(raw)\n processes={k:process_observation(records[k+\'_process\']) for k in [\'worker\',\'supervisor\']}\n claim=json.loads(raw_owned(root/\'launch-claim-private.json\'))\n validate_stage_records(meta,records,processes,claim)\n return records\n\ndef verify_consumed_cache(expected):\n global _MAC_FD\n instance=Path(\'/sys/devices/platform/samurai-gauge-protection\');attribute=instance/\'mac_evidence\'\n need((instance/\'driver\').resolve().as_posix()==\'/sys/bus/platform/drivers/samurai-gauge-protection\',\'same bound protection driver\')\n if _MAC_FD is None:_MAC_FD=os.open(attribute,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)\n held,current=os.fstat(_MAC_FD),attribute.stat()\n need((held.st_dev,held.st_ino)==(current.st_dev,current.st_ino)==(expected[\'attribute_dev\'],expected[\'attribute_inode\']) and\n  instance.stat().st_ino==expected[\'instance_inode\'],\'same already-consumed protection instance\')\n os.lseek(_MAC_FD,0,os.SEEK_SET);raw=os.read(_MAC_FD,16384)\n need(0<len(raw)<16384 and raw.endswith(b\'\\n\') and sha(raw)==MAC_CACHE_SHA==expected[\'sha256\'] and\n  base64.b64encode(raw).decode()==expected[\'raw_base64\'],\'same original consumed MAC report bytes\')\n first=dict(x.split(\'=\',1) for x in raw.decode().splitlines()[0].split())\n need(first.get(\'attempted\')==first.get(\'terminal\')==\'1\',\'no new MAC capture\')\n\ndef validate_meta_shape(meta,guard_path):\n need(guard_path.is_absolute() and guard_path.name==\'guard-private.json\',\'private guard path\')\n need(set(meta)==set(FIXED)|{\'transaction_id\',\'token\',\'boot_id\',\'soc_serial_sha256\',\'compatible_sha256\',\n  \'rootfs_release_sha256\',\'adoption\',\'stage\'},\'exact activation fields\')\n need(all(meta.get(k)==v for k,v in FIXED.items()),\'current fixed activation profile\')\n need(re.fullmatch(r\'irq-native-usb-pm-activate-[a-z0-9-]{8,48}\',meta[\'transaction_id\']) and\n  re.fullmatch(\'[0-9a-f]{32,64}\',meta[\'token\']),\'new independent activation\')\n need(guard_path.parent==ROOT/meta[\'transaction_id\'],\'new activation directory\')\n\n\ndef validate_activation_guard(guard_path,allow_inhibit=False):\n need(os.geteuid()==0 and not sys.flags.optimize,\'root non-optimized worker\')\n guard_path=secure_file(guard_path);meta=json.loads(raw_owned(guard_path))\n validate_meta_shape(meta,guard_path)\n owned_directory(guard_path.parent);acquire_service_lock()\n need(str(uuid.UUID(meta[\'boot_id\']))==meta[\'boot_id\'] and meta[\'boot_id\']==Path(\'/proc/sys/kernel/random/boot_id\').read_text().strip(),\'actual original #502 boot\')\n need(os.uname().machine==\'aarch64\' and os.uname().release==FIXED[\'kernel_release\'] and os.uname().version==FIXED[\'source_kernel_version\'],\'exact adopted Image502\')\n need(Path(\'/proc/sys/kernel/tainted\').read_text().strip()==\'0\',\'taint\')\n need(file_sha(\'/etc/samurai-rootfs-release\')==meta[\'rootfs_release_sha256\'],\'rootfs\')\n serial=Path(\'/sys/devices/soc0/serial_number\').read_bytes();compatible=Path(\'/sys/firmware/devicetree/base/compatible\').read_bytes()\n need(serial.strip() and sha(serial)==meta[\'soc_serial_sha256\'] and sha(compatible)==meta[\'compatible_sha256\'] and b\'realme,samurai\' in compatible.split(b\'\\0\'),\'board identity\')\n adoption=meta[\'adoption\'];need(set(adoption)=={\'transaction_id\',\'guard_path\',\'guard_sha256\'},\'actual IRQ adoption fields\')\n need(re.fullmatch(r\'usb-irq-protection-activate-[a-z0-9-]{8,48}\',adoption[\'transaction_id\']) and\n  adoption[\'guard_path\']==\'/var/lib/samurai/\'+adoption[\'transaction_id\']+\'-adopted/boot-id-private.txt\' and\n  re.fullmatch(\'[0-9a-f]{64}\',adoption[\'guard_sha256\']),\'actual source IRQ adopted guard\')\n owned_directory(Path(adoption[\'guard_path\']).parent)\n guard=raw_owned(adoption[\'guard_path\']);need(guard==(meta[\'boot_id\']+\'\\n\').encode() and sha(guard)==adoption[\'guard_sha256\'],\'actual adopted guard bytes\')\n records=read_stage(meta)\n need(block_sha(\'/dev/disk/by-partlabel/boot\',100663296)==FIXED[\'unchanged_boot_sha256\'] and\n  block_sha(\'/dev/disk/by-partlabel/logdump\',67108864)==FIXED[\'rollback_logdump_sha256\'],\'current complete carriers read-only\')\n need(file_sha(\'/usr/share/samurai-charging/manifest.json\')==FIXED[\'charging_manifest_sha256\'],\'new staged disk manifest\')\n manifest=json.loads(Path(\'/usr/share/samurai-charging/manifest.json\').read_bytes())\n need(manifest==EXPECTED_MANIFEST,\'exact new manifest structure\')\n for path,digest in manifest[\'installed_files\'].items():need(file_sha(path)==digest,\'current retained/new file: \'+path)\n for path,digest in FIXED[\'new_disk_files\'].items():need(sha(raw_owned(path))==digest,\'two actual new disk files\')\n for name,digest in FIXED[\'old_resident_notes\'].items():\n  need(sha(Path(\'/sys/module\',name,\'notes/.note.gnu.build-id\').read_bytes())==digest and Path(\'/sys/module\',name,\'initstate\').read_text().strip()==\'live\',\'old live note independent of new disk\')\n need(Path(\'/sys/module/samurai_usb_input/parameters/native_retained\').read_text().strip()==\'Y\' and not Path(\'/sys/module/samurai_usbin_init\').exists(),\'native provider retained/no helper\')\n need(file_sha(FIXED[\'startup500_path\'])==FIXED[\'startup500_sha256\'] and Path(\'/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower\').read_text().strip()==\'500\',\'startup/descriptor500\')\n need(Path(\'/sys/module/bq27xxx_battery/parameters/samurai_instant_current\').read_text().strip()==\'Y\' and\n  [x for x in Path(\'/proc/cmdline\').read_text().split() if x.startswith(\'bq27xxx_battery.samurai_instant_current=\')]==[\'bq27xxx_battery.samurai_instant_current=1\'],\'current gauge opt-in\')\n eud_off_check();camera481_check(guard_path.parent/\'camera481-expected-private.json\')\n verify_consumed_cache(records[\'after\'][\'mac_evidence\'])\n data=observe_staged();staged_health(data,time.clock_gettime(time.CLOCK_BOOTTIME))\n verify_consumed_cache(records[\'after\'][\'mac_evidence\'])\n if not allow_inhibit:environment(data)\n phase=Path(\'/run\')/(meta[\'transaction_id\']+\'-reboot-phase-private.json\');need(not phase.exists(),\'restart already claimed; inspect original only\')\n return meta,Path(\'/var/lib/samurai\')/meta[\'transaction_id\'],phase\n'
STAGE_RULES_SHA='913cbc5e3aefee784cf9cbac49446dc87c8a985875f9d025e23a076db80f784e'

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def detail(error):
    return type(error).__name__ + ': ' + str(error)

def encode(value):
    return (json.dumps(value, indent=2) + '\n').encode()

def read_owned(path, limit=4_000_000):
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        need(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
             'regular root-owned protected file: ' + str(path))
        need(0 <= info.st_size <= limit, 'bounded regular file: ' + str(path))
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        need(len(raw) <= limit, 'growing file bound')
        return raw, stat.S_IMODE(info.st_mode)
    finally:
        os.close(fd)

class AtomicFailure(RuntimeError):
    def __init__(self, message, stage):
        super().__init__(message)
        self.stage = stage

def validate_lease(lease, mode, request, now):
    need(mode == 0o600 and set(lease) == {'transaction_id', 'boot_id', 'token', 'owner', 'exclusive',
         'camera_released', 'bluetooth_released', 'issued_boottime_s', 'expires_boottime_s'}, 'lease exact schema/mode')
    need(lease['transaction_id'] == request['transaction_id'] and lease['boot_id'] == request['identity']['boot_id'] and
         lease['token'] == request['lease_token'] and lease['owner'] == 'charging' and
         lease['exclusive'] is lease['camera_released'] is lease['bluetooth_released'] is True, 'explicit coordinated device window')
    issued, expires = lease['issued_boottime_s'], lease['expires_boottime_s']
    need(all(type(x) in [int, float] and math.isfinite(x) for x in [issued, expires]) and
         issued <= now < expires and 0 < expires - issued <= 120, 'live BOOTTIME lease <=120s')

def atomic_replace(path, raw, transaction, expected_old, record, ops=os, reader=read_owned):
    """Synchronous exclusive temp -> fsync -> replace -> directory fsync. No retry/rollback."""
    path = Path(path)
    temporary = path.with_name('.' + path.name + '.' + transaction + '.next')
    old, mode = reader(path)
    need(mode == 0o600 and sha(old) == expected_old, 'target must still be exact old bytes/mode')
    fd = directory = failure = None
    phase = 'temp-open'
    try:
        record({'step': phase, 'target': str(path), 'temporary': str(temporary)})
        fd = ops.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        phase = 'temp-write'
        offset = 0
        while offset < len(raw):
            count = ops.write(fd, raw[offset:])
            need(type(count) is int and 0 < count <= len(raw) - offset, 'invalid/short regular write')
            offset += count
        ops.fchmod(fd, 0o600)
        phase = 'file-fsync'
        ops.fsync(fd)
        ops.close(fd)
        fd = None
        record({'step': 'temp-fsynced', 'target': str(path), 'new_sha256': sha(raw)})
        phase = 'rename'
        ops.replace(temporary, path)
        record({'step': 'renamed', 'target': str(path), 'new_sha256': sha(raw)})
        phase = 'directory-fsync'
        directory = ops.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        ops.fsync(directory)
        ops.close(directory)
        directory = None
        phase = 'readback'
        actual, mode = reader(path)
        need(actual == raw and mode == 0o600, 'new target exact readback')
        record({'step': 'complete', 'target': str(path), 'new_sha256': sha(actual)})
        return {'sha256': sha(actual), 'mode': '0600', 'file_and_directory_fsynced': True}
    except BaseException as error:
        failure = AtomicFailure(detail(error), phase)
        raise failure from error
    finally:
        cleanup = []
        for descriptor in [fd, directory]:
            if descriptor is not None:
                try:
                    ops.close(descriptor)
                except BaseException as error:
                    cleanup.append(detail(error))
        if cleanup:
            if failure is not None:
                failure.args = (str(failure) + '; cleanup=' + repr(cleanup),)
            else:
                raise AtomicFailure('descriptor cleanup=' + repr(cleanup), 'cleanup')

def active(text):
    if not isinstance(text, str): return None
    values = re.findall(r'\[([^]]+)\]', text)
    return values[0] if len(values) == 1 else text.strip() if not values and len(text.split()) == 1 else None

def safe_electrical(data, now):
    s, r, lim, p = data['sample'], data['state']['registers'], data['limits'], data['protection']
    need(type(data['read_start']) in (int, float) and type(data['read_end']) in (int, float)
         and 0 <= data['read_end'] - data['read_start'] <= 3 and 0 <= now - data['read_end'] <= 1, 'fresh bounded observation')
    need(s.get('valid') == s.get('protection_ok') == 1 and s.get('shadow') == 0
         and type(s.get('age_ms')) is int and 0 <= s['age_ms'] <= 3000, 'fresh complete cell/temperature sample required')
    need(all(type(s.get(key)) is int and 2000000 <= s[key] <= 4600000 for key in ('cell1_uv', 'cell2_uv'))
         and type(s.get('pack_uv')) is int and 4000000 <= s['pack_uv'] <= 9200000
         and abs(s['cell1_uv'] + s['cell2_uv'] - s['pack_uv']) <= 200000, 'safe complete pack/cells')
    need(type(s.get('temp_decic')) is int and 160 <= s['temp_decic'] < 440, 'normal safe temperature')
    need(data['protection_health'] == 'Good' and p.get('id') == 0x2719
         and p.get('error') == p.get('safety') == p.get('pf') == 0, 'fresh independent normal protection')
    need(p.get('operation', 0) & 0x300 == 0x300 and not p['operation'] & ((1 << 20) | (1 << 16) | 0x7c00)
         and p.get('manufacturing', 0) & 0x18 == 0x18 and not p['manufacturing'] & 0x8006, 'sealed autonomous protection')
    need(set(r) == {'00', '01', '02', '03', '04', '05', '07', '08', '09', '0f', '13'}
         and all(type(v) is int and 0 <= v <= 255 for v in r.values()), 'complete nondestructive register set')
    need(type(lim['input_ua']) is type(lim['charge_ua']) is type(lim['cv_pack_uv']) is int
         and 0 <= lim['input_ua'] <= 900000 and 0 <= lim['charge_ua'] <= 250000,
         'actual configured limits within original hard caps')
    need((r['00'] & 0x7f) * 50000 == (r['0f'] & 0x7f) * 50000 == lim['input_ua']
         and (r['02'] & 0x7f) * 50000 == lim['charge_ua'], 'actual register/limit agreement')
    need(7425000 <= lim['cv_pack_uv'] <= 8725000
         and lim['cv_pack_uv'] == 2 * (3712500 + ((r['04'] & 0x7e) >> 1) * 12500), 'bounded inherited CV')
    need(data['state']['driver'] == 'samurai-mp2650' and data['state']['taint'] == '0', 'actual managed untainted charger')
    for name in ('error', 'stop_error', 'latched', 'fault', 'cycle_timeout', 'thermal_inhibit', 'gauge_charge_stop'):
        need(type(s.get(name)) is int, 'known fault history: ' + name)
    need(s['latched'] in (0, 1) and s['cycle_timeout'] in (0, 1), 'known existing latch/timeout')

def safe_stopped(data, now):
    safe_electrical(data, now)
    need(active(data['charge_behaviour']) == 'inhibit-charge'
         and data['state']['registers']['08'] & 0x18 == 8, 'physical INHIBIT required')

def idle(data):
    state = data['state']; need(len(state['camera_pm']) == 4 and all(x == 'suspended' for x in state['camera_pm'].values()), 'camera PM idle')
    value = json.loads(state['m2m'])
    need(not any(value.get(k) for k in ('users', 'running', 'fatal', 'pinned', 'orphans', 'first_error')), 'camera m2m idle')

def legacy_retained(before, after):
    need(before['notes'] == after['notes'] and before['state']['boot_id'] == after['state']['boot_id'], 'resident/boot unchanged')
    need(before['limits'] == after['limits'], 'configuration limits retained')
    for name, value in before['state']['registers'].items():
        if name == '08': need(after['state']['registers'][name] == (value & ~0x18) | 8, 'only INHIBIT configuration change')
        elif name != '13': need(after['state']['registers'][name] == value, 'other configuration unchanged: ' + name)
    for field in ('latched', 'cycle_timeout'):
        need(not before['sample'][field] or after['sample'][field] == 1, 'prior fault/timeout retained: ' + field)

def restore(request, device, execute=False):
    need(execute, 'explicit --execute-rollback required')
    result = dict(schema='samurai-irq-native-usb-pm-cold-rollback-result-v1', transaction_id=request.get('transaction_id'),
        profile=request.get('profile'), terminal=True, restored=False, status='not_staged_original', runtime_pending=True,
        phase='request', stop_verified=False, stop_action=None, primary_error=None, disk_state='not_inspected',
        automatic_replay_or_rollback=False, module_or_carrier_action=False, physical_acceptance=False)
    phase = 'request'
    try:
        files = unpack(request)
        phase = 'begin'; device.begin(request)
        phase = 'source-stage'; result['source_proof'] = device.source_proof(request)
        phase = 'identity'; result['current_profile'] = validate_profile(request, device.current(request))
        phase = 'disk'; backups = {target: device.read_owned(target) for target in ORDER}
        for target, (raw, mode) in backups.items(): need(mode == 0o600 and sha(raw) == NEW_FILES[target], 'exact current new disk: ' + target)
        manager = device.manager(); device.verify_retained(manager)
        phase = 'pre-stop'; before = device.observe(manager)
        safe_electrical(before, device.now()); idle(before)
        need(before['notes'] == expected_profile(request)['notes'], 'actual profile notes before stop')
        device.backup(backups, before)
        phase = 'stop'
        device.check_window(request)
        if active(before['charge_behaviour']) == 'inhibit-charge' and before['state']['registers']['08'] & 0x18 == 8:
            result['stop_action'] = 'already_inhibited'
        else:
            result['stop_action'] = 'manager_stop_once'; device.stop(manager, json.loads(backups[MANIFEST][0]))
        stopped = device.observe(manager); safe_stopped(stopped, device.now()); retained(before, stopped); idle(stopped)
        result['stop_verified'] = True; device.log('stopped-private.json', stopped)
        for target in ORDER:
            phase = 'restore:' + Path(target).name
            device.check_window(request)
            validate_profile(request, device.current(request, carriers=False))
            current = device.observe(manager); safe_stopped(current, device.now()); retained(before, current); idle(current)
            device.replace(target, files[target])
        phase = 'final'
        device.check_window(request); validate_profile(request, device.current(request))
        device.verify_restored(files, manager)
        after = device.observe(manager); safe_stopped(after, device.now()); retained(before, after); idle(after)
        device.log('after-private.json', after)
        result.update(restored=True, phase='staged_original', status='staged_original/runtime_pending',
            disk_state='all_original_fsynced', actual_resident_notes=after['notes'],
            source_budget_observation=after.get('source'), existing_fault_history={key:after['sample'][key]
                for key in ('error','stop_error','latched','fault','cycle_timeout','thermal_inhibit','gauge_charge_stop')},
            old_modules_resident_verified=False, original_full_runtime_accepted=False)
    except BaseException as error:
        result.update(phase='failed',status='failed_preserved_no_replay',primary_error={'phase':phase,'error':detail(error)})
        if isinstance(error, AtomicFailure): result['primary_error']['atomic_stage'] = error.stage
    finally:
        for name, action in [('receipt_error',lambda:device.finish(result)),('close_error',device.close)]:
            try: action()
            except BaseException as error: result.update(restored=False,phase='failed',status='inspect_same_original_worker',**{name:detail(error)})
        try: device.publish(result)
        except BaseException as error: result.update(restored=False,phase='failed',status='inspect_same_original_worker',receipt_error=detail(error))
    return result

class BaseDevice:
    def __init__(self):
        self.out = self.lock = self.journal = None; self.events = []; self.request = None; self.carriers = None

    def now(self): return time.clock_gettime(time.CLOCK_BOOTTIME)

    def read_owned(self, path): return read_owned(path)

    def write_new(self, path, raw):
        with Path(path).open('xb') as file: file.write(raw); file.flush(); os.fsync(file.fileno())

    def log(self, name, value):
        self.write_new(self.out / name, encode(value))

    def event(self, value):
        value = dict(value, boottime_s=self.now()); self.events.append(value)
        self.journal.write(encode(value).replace(b'\n', b' ') + b'\n'); self.journal.flush(); os.fsync(self.journal.fileno())

    def check_window(self, request):
        need(self.identity() == request['identity'], 'current source identity unchanged')
        raw, mode = read_owned('/run/' + request['transaction_id'] + '-window-private.json')
        validate_lease(json.loads(raw), mode, request, self.now())

    def begin(self, request):
        import fcntl
        need(os.geteuid() == 0 and not sys.flags.optimize, 'root/nonoptimized')
        self.request = request; root = Path(ROOT) / request['transaction_id']
        info = root.lstat(); need(stat.S_ISDIR(info.st_mode) and not root.is_symlink() and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o700, 'unique protected transaction directory')
        need(Path(__file__).resolve() == root / 'restore-worker.py' and sha(read_owned(__file__)[0]) == request['worker_sha256'], 'actual worker path/source')
        self.out = root / 'device-rollback'; self.out.mkdir(mode=0o700, exist_ok=False)
        self.journal = (self.out / 'journal-private.jsonl').open('xb')
        fields = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()
        self.log('process-private.json',dict(pid=os.getpid(),start_ticks=int(fields[19]),
            argv=[x.decode() for x in Path('/proc/self/cmdline').read_bytes().split(b'\0') if x],
            boot_id=request['identity']['boot_id'],transaction_id=request['transaction_id'],worker_sha256=request['worker_sha256']))
        self.log('request-private.json',{k:v for k,v in request.items() if k != 'payload_base64'})
        self.check_window(request)
        self.lock = os.open(LOCK, os.O_RDWR | os.O_NOFOLLOW)
        info = os.fstat(self.lock); need(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o600, 'original service lock')
        fcntl.flock(self.lock,fcntl.LOCK_EX | fcntl.LOCK_NB); self.check_window(request)
        client = Path('/sys/bus/i2c/devices/0-005c')
        need((client/'name').read_text().strip() == 'mp2650' and (client/'driver').resolve().name == 'samurai-mp2650'
             and (client/'of_node').resolve().as_posix().endswith('/soc@0/geniqup@8c0000/i2c@884000/charger@5c'), 'existing exact charger owner')

    def block_fact(self, name, length):
        import fcntl
        fd=os.open('/dev/disk/by-partlabel/'+name,os.O_RDONLY|os.O_CLOEXEC)
        try:
            need(stat.S_ISBLK(os.fstat(fd).st_mode) and struct.unpack('=Q',fcntl.ioctl(fd,0x80081272,bytes(8)))[0]==length,'complete read-only carrier')
            digest=hashlib.sha256(); remaining=length
            while remaining:
                raw=os.read(fd,min(1048576,remaining));need(raw,'short carrier');digest.update(raw);remaining-=len(raw)
            return dict(bytes=length,sha256=digest.hexdigest())
        finally: os.close(fd)

    def current(self, request, carriers=True):
        if carriers: self.carriers={name:self.block_fact(name,length) for name,length in [('boot',100663296),('logdump',67108864)]}
        need(self.carriers is not None,'initial complete carrier read required')
        notes={name:sha(Path('/sys/module',name.replace('-','_'),'notes/.note.gnu.build-id').read_bytes()) for name in OLD_NOTES}
        return dict(identity=self.identity(),release=os.uname().release,machine=os.uname().machine,
            taint=Path('/proc/sys/kernel/tainted').read_text().strip(),notes=notes,
            module_states={name:Path('/sys/module',name.replace('-','_'),'initstate').read_text().strip() for name in notes},**self.carriers)

    def manager(self):
        for path,digest in [(SERVICE,MANAGER),('/usr/lib/samurai-charging/live-session.py',LIVE_SHA),('/usr/local/sbin/samurai-usb',STARTUP_SHA)]: need(sha(read_owned(path)[0])==digest,'retained fixed code: '+path)
        value=runpy.run_path(SERVICE); need(sha(read_owned(SERVICE)[0])==MANAGER and value['live'].REGS==[0,1,2,3,4,5,7,8,9,15,19],'stable manager/no REG14')
        return value

    def verify_retained(self, manager):
        manifest=manager['verify'](); need(manifest==NEW_MANIFEST,'exact current new manifest/retained files')

    def observe(self, manager):
        start=self.now(); live=manager['live']; state=live.state()
        def observed(path):
            try:return Path(path).read_text().strip()
            except OSError as error:return {'errno':error.errno}
        supply=live.PSY/'mp2650-input'; source=live.PSY/'samurai-usb-input'
        protection=Path('/sys/devices/platform/samurai-gauge-protection/protection_state').read_text()
        result=dict(read_start=start,state=state,sample=manager['sample'](),
            notes={name:sha(Path('/sys/module',name.replace('-','_'),'notes/.note.gnu.build-id').read_bytes()) for name in OLD_NOTES},
            protection={k:int(v,0) for k,v in (x.split('=') for x in protection.split())},
            protection_health=(live.PSY/'samurai-gauge-protection/health').read_text().strip(),
            charge_behaviour=(supply/'charge_behaviour').read_text().strip(),
            source={key:observed(source/key) for key in ('online','usb_type','current_max','input_current_limit')},
            limits={key:int((supply/file).read_text()) for key,file in [('input_ua','input_current_limit'),('charge_ua','constant_charge_current'),('cv_pack_uv','constant_charge_voltage')]})
        result['read_end']=self.now();return result

    def stop(self, manager, meta):
        need(sha(read_owned(SERVICE)[0])==MANAGER,'exact normal manager stop')
        result=manager['command'](meta,'stop');need(result=={'managed':True,'requested':'inhibit-charge'},'synchronous stop result')

    def backup(self, files, before):
        for path,(raw,mode) in files.items(): self.write_new(self.out/(Path(path).name+'.before'),raw)
        self.log('before-private.json',before)
        self.log('files-before-private.json',{path:dict(sha256=sha(raw),mode=oct(mode),bytes=len(raw)) for path,(raw,mode) in files.items()})

    def replace(self, path, raw):
        need(path in ORDER and sha(raw)==OLD_FILES[path],'only original fixed file')
        return atomic_replace(path,raw,self.request['transaction_id'],NEW_FILES[path],self.event)

    def verify_restored(self, files, manager):
        for path,raw in files.items(): need(read_owned(path)==(raw,0o600),'old readback')
        need(manager['verify']()==json.loads(files[MANIFEST]),'old manifest/retained files reread; no loaded_matches')

    def finish(self, result):
        if self.out is None:return
        final={}; temporaries={}; labels=[]
        for target in ORDER:
            try:
                raw,mode=read_owned(target);digest=sha(raw)
                label='original' if digest==OLD_FILES[target] else 'new' if digest==NEW_FILES[target] else 'unexpected'
                final[target]=dict(sha256=digest,mode=oct(mode),classification=label)
            except BaseException as error:label='unknown';final[target]=dict(classification=label,error=detail(error))
            labels.append(label)
            temporary=Path(target).with_name('.'+Path(target).name+'.'+self.request['transaction_id']+'.next')
            try:raw,mode=read_owned(temporary);temporaries[target]=dict(path=str(temporary),state='retained',sha256=sha(raw),mode=oct(mode))
            except FileNotFoundError:temporaries[target]=dict(path=str(temporary),state='absent')
            except BaseException as error:temporaries[target]=dict(path=str(temporary),state='unknown',error=detail(error))
        result['final_files']=final;result['temporary_files']=temporaries
        result['unknown_write_state']=any(x in ('unknown','unexpected') for x in labels)
        if all(x=='original' for x in labels): result['disk_state']='all_original_fsynced' if result['restored'] else 'all_original_known_durability_or_acceptance_unproved'
        elif all(x=='new' for x in labels):result['disk_state']='all_new'
        elif set(labels)<={'original','new'}:result['disk_state']='partial_known'
        else:result['disk_state']='unknown_inspect_same_worker'
        if result['restored'] and (result['disk_state']!='all_original_fsynced' or any(x['state']!='absent' for x in temporaries.values())):
            result.update(restored=False,phase='failed',status='final_readback_changed_inspect_same_worker')
        self.log('events-private.json',self.events)

    def close(self):
        errors=[]
        for name in ('journal','lock'):
            value=getattr(self,name)
            if value is not None:
                try:value.close() if name=='journal' else os.close(value)
                except BaseException as error:errors.append(detail(error))
                setattr(self,name,None)
        need(not errors,'cleanup: '+repr(errors))

    def publish(self, result):
        if self.out is not None:self.log('result.json',result)

PROFILES=('staged_same_boot_old_resident','booted_504_new_resident','booted_502_new_resident')

def expected_profile(request):
 index=PROFILES.index(request['profile'])
 return {'version':VERSION504 if index==1 else VERSION502,'boot':BOOT,
  'logdump':LOGDUMP504 if index==1 else LOGDUMP502,'notes':OLD_NOTES if index==0 else NEW_NOTES}

def validate_cache(value):
 need(isinstance(value,dict) and set(value)=={'sha256','raw_base64','attribute_dev','attribute_inode','instance_inode'},'actual current cache fields')
 raw=base64.b64decode(value['raw_base64'],validate=True)
 need(0<len(raw)<16384 and raw.endswith(b'\n') and re.fullmatch('[0-9a-f]{64}',value['sha256']) and
  sha(raw)==value['sha256'],'exact current opaque cache bytes')
 first=dict(x.split('=',1) for x in raw.decode().splitlines()[0].split())
 need(first.get('schema')=='1' and (first.get('attempted'),first.get('terminal')) in [('0','0'),('1','1')],
  'fixed7848 cache must be untouched or already terminal; no capture in progress')
 need(type(value['attribute_dev']) is int and value['attribute_dev']>=0 and
  all(type(value[k]) is int and value[k]>0 for k in ['attribute_inode','instance_inode']),'current kernfs instance identity')
 return raw

def unpack(request):
 need(set(request)=={'schema','transaction_id','profile','identity','source_identity','source_stage','source_stage_observations',
  'activation','current_cache','payload_sha256','payload_base64','worker_sha256','lease_token'},'current rollback request fields')
 need(request['schema']=='samurai-irq-native-usb-pm-cold-rollback-request-v1' and
  re.fullmatch(r'irq-native-usb-pm-rollback-[a-z0-9-]{8,48}',request['transaction_id']),'new cold rollback transaction')
 need(request['profile'] in PROFILES,'explicit current profile')
 for identity in [request['identity'],request['source_identity']]:
  need(set(identity)=={'boot_id','version','serial_sha256','compatible_sha256','rootfs_sha256'} and
   str(uuid.UUID(identity['boot_id']))==identity['boot_id'],'complete actual identity')
  for key in ['serial_sha256','compatible_sha256','rootfs_sha256']:need(re.fullmatch('[0-9a-f]{64}',identity[key]),'actual board identity digest')
 need(request['source_identity']['version']==VERSION502 and request['identity']['version']==expected_profile(request)['version'],
  'source502 and actual current profile version')
 need(re.fullmatch('[0-9a-f]{48}',request['lease_token']) and re.fullmatch('[0-9a-f]{64}',request['worker_sha256']),'actual worker/lease')
 validate_cache(request['current_cache'])
 raw=base64.b64decode(request['payload_base64'],validate=True)
 need(request['payload_sha256']==ROLLBACK_PAYLOAD and len(raw)==25858 and sha(raw)==ROLLBACK_PAYLOAD,'actual fixed two-file inverse')
 files={}
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
  members=tar.getmembers();need(len(members)==2,'exact original two files')
  for member in members:
   target='/'+member.name
   need(target in OLD_FILES and target not in files and member.name==target.lstrip('/') and member.isfile() and
    member.mode==0o600 and member.uid==member.gid==member.mtime==0 and member.uname==member.gname=='root' and
    not member.pax_headers,'exact old member metadata')
   data=tar.extractfile(member).read();need(sha(data)==OLD_FILES[target],'actual old member bytes');files[target]=data
 return files

def validate_profile(request,actual):
 current,source=request['identity'],request['source_identity'];profile=expected_profile(request)
 need(actual['identity']==current and all(current[k]==source[k] for k in ['serial_sha256','compatible_sha256','rootfs_sha256']),
  'same actual board/rootfs and exact current identity')
 need(current['version']==profile['version'] and source['version']==VERSION502 and actual['release']==RELEASE and
  actual['machine']=='aarch64' and actual['taint']=='0','actual complete kernel profile')
 need(actual['boot']==dict(bytes=100663296,sha256=profile['boot']) and actual['logdump']==dict(bytes=67108864,sha256=profile['logdump']),
  'complete current bootedd/FAT profile')
 need(actual['notes']==profile['notes'] and set(actual['module_states'])==set(profile['notes']) and
  all(v=='live' for v in actual['module_states'].values()),'actual resident module tuple')
 need(actual['current_cache']==request['current_cache'],'same current held cache instance')
 if request['profile']==PROFILES[0]:
  need(current==source and request['activation'] is None,'same-stage boot/old resident only')
 else:
  need(current['boot_id']!=source['boot_id'],'source boot ended; do not attribute its PIDs now')
  saved=request['activation']
  keys={'schema','activation_transaction_id','context_sha256','guard_sha256','flash_request_sha256','flash_result_sha256',
   'reboot_request_sha256','reboot_result_sha256','flash_claimed_ns','reboot_claimed_ns','boot_sha256','logdump_sha256','action_pair'}
  need(isinstance(saved,dict) and set(saved)==keys and saved['schema']=='samurai-irq-native-usb-pm-saved-activation-v1' and
   re.fullmatch(r'irq-native-usb-pm-activate-[a-z0-9-]{8,48}',saved['activation_transaction_id']),'actual saved original activation binding')
  for key in keys-{'schema','activation_transaction_id','flash_claimed_ns','reboot_claimed_ns','action_pair'}:
   need(re.fullmatch('[0-9a-f]{64}',saved[key]),'saved actual action digest')
  need(saved['boot_sha256']==BOOT and saved['logdump_sha256']==profile['logdump'] and
   type(saved['flash_claimed_ns']) is type(saved['reboot_claimed_ns']) is int and
   0<saved['flash_claimed_ns']<saved['reboot_claimed_ns'],'actual selected carrier and write/reboot order')
  pair=['flash-candidate','reboot-candidate'] if request['profile']==PROFILES[1] else ['rollback-original','reboot-original']
  need(saved['action_pair']==pair,'actual selected action pair')
 return {'profile':request['profile'],'resident_notes':profile['notes'],'boot_sha256':BOOT,
  'logdump_sha256':profile['logdump'],'current_version':profile['version']}

def stage_namespace():
 need(sha(STAGE_RULES.encode())==STAGE_RULES_SHA,'original current stage receipt rules')
 namespace={};exec(compile(STAGE_RULES,'frozen-current-stage-rules','exec'),namespace);return namespace

def source_paths(transaction):
 return stage_namespace()['stage_paths'](transaction)

def verify_source_records(request,raws,processes,claim):
 ns=stage_namespace();projection=request['source_stage'];paths=ns['stage_paths'](projection['transaction_id'])
 need(set(projection['evidence'])==set(paths) and set(raws)==set(paths),'complete actual seventeen source records')
 records={}
 for name,path in paths.items():
  item=projection['evidence'][name]
  need(set(item)=={'path','sha256'} and item['path']==path and item['sha256']==sha(raws[name]),'source original path/bytes: '+name)
  if name not in ['worker_source','supervisor_source']:
   records[name]=raws[name] if name in ['old_usb','old_manifest'] else json.loads(raws[name])
 original=records['request'];need(original['identity']==request['source_identity'],'actual original source identity')
 meta=dict(stage=projection,boot_id=original['identity']['boot_id'],soc_serial_sha256=original['identity']['serial_sha256'],
  compatible_sha256=original['identity']['compatible_sha256'],rootfs_release_sha256=original['identity']['rootfs_sha256'],adoption=original['adoption'])
 # Recheck the authenticated source-frame observations from its actual saved
 # same-boot fetch. These are historical, not new observations of old PIDs.
 captured=request['source_stage_observations'];need(set(captured)=={'worker','supervisor'},'original source-frame processes')
 ns['validate_stage_records'](meta,records,captured,claim)
 if request['identity']['boot_id']==request['source_identity']['boot_id']:
  ns['validate_stage_records'](meta,records,processes,claim)
 else:
  expected=dict(state='source_boot_ended',source_boot_id=request['source_identity']['boot_id'],current_boot_id=request['identity']['boot_id'])
  need(processes=={'worker':expected,'supervisor':expected},'never attribute current PIDs across source boot end')
 need(sha(raws['worker_source'])==STAGE_WORKER and sha(raws['supervisor_source'])==STAGE_SUPERVISOR,'fixed original stage sources')
 return {'source_stage_terminal_verified':True,'source_boot_id':request['source_identity']['boot_id'],
  'source_result_sha256':sha(raws['result']),'source_boot_ended':request['identity']['boot_id']!=request['source_identity']['boot_id'],
  'historical_process_observations_replayed':True,'host_transport_reaudited_here':False}

def retained(before,after):
 legacy_retained(before,after)
 need(before['current_cache']==after['current_cache'],'current protection instance/cache retained')
 b,a=before['sample'],after['sample']
 if b.get('logical_full')==1 and b.get('online')==a.get('online')==1:
  need(a.get('logical_full')==1 and a.get('full_cause')==b.get('full_cause') and a.get('session_seconds')==0,
   'online logical Full/cause retained while stopped')

class Device(BaseDevice):
 def __init__(self):
  super().__init__();self.mac_fd=None
 def identity(self):
  need(self.request is not None,'explicit current request')
  need(os.uname().version==expected_profile(self.request)['version'] and os.uname().release==RELEASE and
   os.uname().machine=='aarch64','exact current profile kernel')
  compatible=Path('/sys/firmware/devicetree/base/compatible').read_bytes()
  need(b'realme,samurai' in compatible.split(b'\0'),'actual board')
  return dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),version=os.uname().version,
   serial_sha256=sha(Path('/sys/devices/soc0/serial_number').read_bytes()),compatible_sha256=sha(compatible),
   rootfs_sha256=sha(read_owned('/etc/samurai-rootfs-release')[0]))
 def begin(self,request):
  super().begin(request)
  p=Path(INSTANCE);need((p/'driver').resolve().as_posix()=='/sys/bus/platform/drivers/samurai-gauge-protection','current protection driver')
  self.mac_fd=os.open(p/'mac_evidence',os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
  need(self.cache_evidence()==request['current_cache'],'fresh current cache matches original-key capture')
 def cache_evidence(self):
  need(self.mac_fd is not None,'held current cache fd')
  p=Path(INSTANCE);held,current=os.fstat(self.mac_fd),(p/'mac_evidence').stat()
  need((held.st_dev,held.st_ino)==(current.st_dev,current.st_ino) and
   (p/'driver').resolve().as_posix()=='/sys/bus/platform/drivers/samurai-gauge-protection','same bound current cache fd')
  os.lseek(self.mac_fd,0,os.SEEK_SET);raw=os.read(self.mac_fd,16384)
  value=dict(sha256=sha(raw),raw_base64=base64.b64encode(raw).decode(),attribute_dev=held.st_dev,
   attribute_inode=held.st_ino,instance_inode=p.stat().st_ino)
  validate_cache(value);need(value==self.request['current_cache'],'current cache/instance continuously retained')
  return value
 def source_proof(self,request):
  paths=source_paths(request['source_stage']['transaction_id']);raws={name:read_owned(path)[0] for name,path in paths.items()}
  original=json.loads(raws['request']);guard,mode=read_owned(original['adoption']['guard_path'])
  need(mode==0o600 and guard==(request['source_identity']['boot_id']+'\n').encode() and
   sha(guard)==original['adoption']['guard_sha256'],'retained actual original IRQ guard')
  different=request['identity']['boot_id']!=request['source_identity']['boot_id'];processes={}
  ns=stage_namespace()
  for role in ['worker','supervisor']:
   processes[role]=dict(state='source_boot_ended',source_boot_id=request['source_identity']['boot_id'],current_boot_id=request['identity']['boot_id']) if different else ns['process_observation'](json.loads(raws[role+'_process']))
  claim=json.loads(read_owned(Path(ROOT)/original['transaction_id']/'launch-claim-private.json')[0])
  result=verify_source_records(request,raws,processes,claim);self.log('source-stage-proof-private.json',result);return result
 def current(self,request,carriers=True):
  value=super().current(request,carriers);value['current_cache']=self.cache_evidence();return value
 def observe(self,manager):
  value=super().observe(manager);value['current_cache']=self.cache_evidence();return value
 def close(self):
  errors=[]
  if self.mac_fd is not None:
   try:os.close(self.mac_fd)
   except BaseException as error:errors.append(detail(error))
   finally:self.mac_fd=None
  try:super().close()
  except BaseException as error:errors.append(detail(error))
  need(not errors,'all owned cache/journal/lock close errors: '+repr(errors))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute-rollback',action='store_true');parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args();need(not(args.execute_rollback and args.check_only),'choose inert check or execution')
    if not args.execute_rollback:
        print(json.dumps(dict(source_only=True,device_accessed=False,runtime_request_generated=False,
            profiles=list(PROFILES),payload_sha256=ROLLBACK_PAYLOAD)));return 0
    need(not sys.flags.optimize,'nonoptimized');os.umask(0o077)
    raw=sys.stdin.buffer.read(100001);need(len(raw)<=100000,'bounded request')
    result=restore(json.loads(raw),Device(),execute=True);print(json.dumps(result),flush=True)
    return 0 if result['restored'] else 1

if __name__=='__main__':raise SystemExit(main())
