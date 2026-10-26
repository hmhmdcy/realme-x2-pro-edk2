"""Keep board metadata and remove the obsolete lab module option in a candidate."""
from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
original=Path('/home/cy122/x2pro-linux/pmos249-build/pmaports')
candidate=Path('/home/cy122/x2pro-linux/pmaports-camera-common269')
G=['git','-c','safe.directory='+str(original),'-C',str(original)]
assert not subprocess.check_output(G+['status','--porcelain']).strip()
assert subprocess.check_output(G+['rev-parse','samurai-userspace'],text=True).strip()=='4aeae3b3035412794b2204e2f8bc104cef082a54'
if not candidate.exists():
 subprocess.run(G+['worktree','add','-b','samurai-camera-common',str(candidate),'samurai-userspace'],check=True,stdout=subprocess.DEVNULL)
else:
 CG=['git','-c','safe.directory='+str(candidate),'-C',str(candidate)]
 assert subprocess.check_output(CG+['rev-parse','HEAD'],text=True).strip()=='4aeae3b3035412794b2204e2f8bc104cef082a54'
 assert not subprocess.check_output(CG+['status','--porcelain']).strip()
pkg=candidate/'device/testing/samurai-platform';recipe=pkg/'APKBUILD';old=recipe.read_text()
obsolete='etc_modprobe.d_samurai-pmic-bringup.conf';new='99-realme-rmx1931-sensors.rules'
assert (pkg/obsolete).read_text().strip()=='options qcom_pm8008 experimental_p_imx319_power=1\nsoftdep qcom_pm8008 pre: reset_realme_rmx1931_pm8008'
text=old.replace('pkgrel=0\n','pkgrel=1\n',1)
text=text.replace(' '+obsolete+' ',' '+new+' ',1)
line=' install -Dm644 "$srcdir"/'+obsolete+' "$pkgdir"/etc/modprobe.d/samurai-pmic-bringup.conf\n'
assert text.count(line)==1
text=text.replace(line,' install -Dm644 "$srcdir"/'+new+' "$pkgdir"/usr/lib/udev/rules.d/'+new+'\n')
text='\n'.join(l for l in text.splitlines() if not l.endswith('  '+obsolete))+'\n'
data=(R/new).read_bytes();digest=hashlib.sha512(data).hexdigest()
assert text.endswith('"\n');text=text[:-2]+digest+'  '+new+'\n"\n'
assert obsolete not in text and 'experimental_p_imx319_power' not in text
(pkg/obsolete).unlink();(pkg/new).write_bytes(data);recipe.write_text(text)
subprocess.run(['sh','-n',str(recipe)],check=True)
namespace=subprocess.check_output(['sh','-c','. "$1"; printf "%s\\n" "$source"; printf "%s\\n" "$sha512sums"','sh',str(recipe)],text=True)
lines=namespace.splitlines();sources=lines[0].split();checks={l.split()[1]:l.split()[0] for l in lines[1:] if l.strip()}
assert set(sources)==set(checks)
for name in sources:assert hashlib.sha512((pkg/name).read_bytes()).hexdigest()==checks[name]
beforefiles={p.name:p.read_bytes() for p in (original/'device/testing/samurai-platform').iterdir() if p.is_file()}
assert all((pkg/n).read_bytes()==b for n,b in beforefiles.items() if n not in ['APKBUILD',obsolete])
mirror=R.parents[1]/'linux-port/packages/samurai-platform';assert not mirror.exists();shutil.copytree(pkg,mirror)
diff=subprocess.check_output(['git','-c','safe.directory='+str(candidate),'-C',str(candidate),'diff','--stat'],text=True)
report=dict(stage=269,package='samurai-platform',candidate_version='5-r1',base_commit='4aeae3b3035412794b2204e2f8bc104cef082a54',
 standard_sensor_rule_sha256=hashlib.sha256(data).hexdigest(),obsolete_experimental_module_option_and_reset_softdep_removed=True,
 all_other_platform_sources_unchanged=True,source_checksums_verified=len(sources),shell_syntax_valid=True,
 packaged_or_installed_apk=False,phone_configuration_installed_separately=True)
(R/'platform-package-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));print(diff)
