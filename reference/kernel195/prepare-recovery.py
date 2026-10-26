from pathlib import Path
import hashlib,json,subprocess
ref=Path(__file__).resolve().parent;previous=ref.parent/'kernel194';out=Path('/mnt/e/edk2-samurai-out/kernel195');out.mkdir(exist_ok=True);k=Path('/home/cy122/pmos-samurai-kernel136/kernel');p=k/'drivers/mfd/qcom-pm8008.c';backup=out/'qcom-pm8008-before195-private.c';old=backup.read_text() if backup.exists() else p.read_text()
expected=json.loads((previous/'source-final-validation.json').read_text())['source_sha256'];assert hashlib.sha256(old.encode()).hexdigest()==expected['drivers/mfd/qcom-pm8008.c']
if backup.exists():assert p.read_text()==old or 'failed to reassert reset after address error:' in p.read_text()
else:backup.write_bytes(p.read_bytes())
s=(previous/'pm8008-initial-address.c').read_text();s=s.replace('\tu32 initial;\n\tint ret, write_ret;','\tbool release_attempted = false;\n\tu32 initial;\n\tint ret, write_ret, reset_ret;')
needle='\tret = gpiod_direction_output(reset, 0);\n\tif (ret)\n\t\tgoto out;\n\tusleep_range(10000, 11000);';assert s.count(needle)==1
s=s.replace(needle,'\trelease_attempted = true;\n'+needle)
needle='out:\n\treturn ret;\n}';assert s.count(needle)==1
s=s.replace(needle,'''out:
	if (ret && release_attempted) {
		/* Do not leave an unassigned PMIC awake at the shared address. */
		reset_ret = gpiod_direction_output(reset, 1);
		if (reset_ret)
			dev_err(dev, "failed to reassert reset: %d\\n", reset_ret);
	}
	return ret;
}''')
(ref/'pm8008-initial-address.c').write_text(s);block=s[s.index('#define PM8008_FACTORY_ADDRESS'):];a=old.index('#define PM8008_FACTORY_ADDRESS');b=old.index('static int pm8008_probe(',a);p.write_text(old[:a]+block+'\n'+old[b:])
patch=subprocess.check_output(['git','diff','--','drivers/mfd/qcom-pm8008.c'],cwd=k,text=True);(ref/'pm8008-initial-address.patch').write_text(patch)
check=subprocess.run(['perl',str(k/'scripts/checkpatch.pl'),'--no-tree','--strict','-'],input=patch,capture_output=True,text=True);(out/'pmic-checkpatch-private.log').write_text(check.stdout+check.stderr);assert check.returncode==0,check.stdout
r=dict(stage=195,source_before_sha256=hashlib.sha256(old.encode()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),checkpatch_exit=0,reasserts_reset_after_cold_release_error=True,cleanup_error_preserves_primary_error=True,successful_cold_and_warm_paths_unchanged=True,hardware_deployed=False)
(ref/'pmic-address-source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
# Preserve the earlier harness and add physical reset-state expectations.
s=(previous/'test-pmic-address.py').read_text().replace('kernel194','kernel195').replace('stage=194','stage=195')
s=s.replace('#include <stdint.h>','#include <stdint.h>\n#include <stdbool.h>')
s=s.replace('get_absent,cases;','get_absent,cases,reset_state;')
s=s.replace('gpio_values[gpio_count++]=v;return gpio_count==gpio_fail_call?gpio_error:0;','gpio_values[gpio_count++]=v;if(gpio_count==gpio_fail_call)return gpio_error;reset_state=v;return 0;')
s=s.replace('gpio_error=-EIO;','gpio_error=-EIO;reset_state=0;')
s=s.replace('sleep_count==nsleep);','sleep_count==nsleep);if(expected && ngpio==3 && gpio_fail_call!=3)assert(reset_state==1 && gpio_values[2]==1);')
for old,new in [('finish(-ENODEV,&reset_gpio,2,2)','finish(-ENODEV,&reset_gpio,3,2)'),('finish(-ENXIO,&reset_gpio,2,2)','finish(-ENXIO,&reset_gpio,3,2)'),('finish(-EIO,&reset_gpio,2,2)','finish(-EIO,&reset_gpio,3,2)'),('finish(-ETIMEDOUT,&reset_gpio,2,3)','finish(-ETIMEDOUT,&reset_gpio,3,3)'),('finish(-EIO,&reset_gpio,2,3)','finish(-EIO,&reset_gpio,3,3)'),('finish(-ENODEV,&reset_gpio,2,3)','finish(-ENODEV,&reset_gpio,3,3)'),('finish(-EIO,&reset_gpio,2,1)','finish(-EIO,&reset_gpio,3,1)')]:s=s.replace(old,new)
needle=' printf("%d cases passed\\n",cases);return 0;';assert needle in s
s=s.replace(needle,''' start();gpio_fail_call=3;cold_prefix(-ENXIO);rd(8,2,1);finish(-ENODEV,&reset_gpio,3,2);assert(logs==1 && reset_state==0);
 start();gpio_fail_call=3;cold_prefix(-ENXIO);rd(8,2,0);wr(-ETIMEDOUT);rd(4,-ENXIO,0);finish(-ETIMEDOUT,&reset_gpio,3,3);assert(logs==1 && reset_state==0);
'''+needle).replace('35 cases passed','37 cases passed').replace('cases=35','cases=37')
needle="(ref/'pmic-address-host-validation.json').write_text";position=s.index(needle)
s=s[:position]+'''# The unchanged stage194 helpers must fail the strengthened reset-state test.
legacy=(ref.parent/'kernel194/pm8008-initial-address.c').read_text().split('/* Add this block before pm8008_probe() in drivers/mfd/qcom-pm8008.c. */')[1]
old_c=out/'pm8008-address-before195-host-private.c';old_binary=out/'pm8008-address-before195-host-private';old_c.write_text(stub+legacy+tests)
subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g',str(old_c),'-o',str(old_binary)],check=True)
import resource
def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
failed=subprocess.run([str(old_binary)],capture_output=True,preexec_fn=no_core);(out/'before195-regression-failure-private.log').write_bytes(failed.stdout+failed.stderr)
assert failed.returncode==-6 and b'Assertion' in failed.stderr
report.update(previous_actual_helpers_fail_new_regression=True,primary_error_and_cleanup_error_tested=True,reset_state_checked_on_all_cold_release_failures=True)
'''+s[position:]
(ref/'test-pmic-address.py').write_text(s)
# Keep the same transport and use a fresh, non-overwriting native baseline.
s=(previous/'baseline.py').read_text().replace('k194-baseline','k195-baseline').replace('stage=194','stage=195');s=s.replace("assert not Path('/sys/module/samurai_cci_bringup').exists()", "assert all(not Path('/sys/module/'+n).exists() for n in ['qcom_pm8008','qcom_pm8008_regulator','samurai_pmic_fixture','imx471','v4l2_cci'])\nassert not Path('/sys/module/samurai_cci_bringup').exists()")
(ref/'baseline.py').write_text(s);(ref/'run-native.py').write_bytes((previous/'run-native.py').read_bytes())
