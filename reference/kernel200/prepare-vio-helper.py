from pathlib import Path
import ast

ref=Path(__file__).resolve().parent;old=ref.parent/'kernel195'
s=(old/'samurai-vio-phandle.c').read_text().replace('inactive, existing camera VIO regulator','existing camera VIO regulator, including RPMH initial state')
s=s.replace('static int supply_microvolts;', 'static int supply_microvolts;\nstatic int supply_enable_state;')
s=s.replace('module_param(supply_microvolts, int, 0444);','module_param(supply_microvolts, int, 0444);\nmodule_param(supply_enable_state, int, 0444);')
s=s.replace('!of_node_name_eq(vio_node, "ldo1"))', '!of_node_name_eq(vio_node, "ldo1") ||\n\t    !of_device_is_compatible(vio_node->parent, "qcom,pm8150l-rpmh-regulators"))')
s=s.replace('ret = supply_microvolts == 1800000 && !regulator_is_enabled(supply) ? 0 : -EINVAL;', '''supply_enable_state = regulator_is_enabled(supply);
		/* RPMH starts with -EINVAL until the first real enable request. */
		if (supply_microvolts != 1800000)
			ret = -EINVAL;
		else if (supply_enable_state == 0 || supply_enable_state == -EINVAL)
			ret = 0;
		else
			ret = supply_enable_state < 0 ? supply_enable_state : -EBUSY;''')
s=s.replace('pr_info("samurai VIO: exact OF lookup found inactive 1.8V supply, phandle %u\\n",\n\t\tassigned_handle);', 'pr_info("samurai VIO: exact 1.8V OF supply, state %d, phandle %u\\n",\n\t\tsupply_enable_state, assigned_handle);')
(ref/'samurai-vio-phandle.c').write_text(s)
s=(old/'build-vio-helper.py').read_text().replace('out/kernel195','out/kernel200').replace('stage=195','stage=200')
s=s.replace("(ref/'pmic-module-build-validation.json')","(ref.parent/'kernel195/pmic-module-build-validation.json')")
s=s.replace('vio-second-compile-source-private.c','vio-helper-before200-private.c').replace('vio-module-build-r3-private.log','vio-module-build-private.log')
s=s.replace(',first_compile_missing_of_private_header_fixed=True,second_modpost_unexported_allnodes_iterator_replaced=True', ',rpmh_unknown_state_accepted_without_power_write=True')
ast.parse(s);(ref/'build-vio-helper.py').write_text(s)
print('K200_READ_ONLY_VIO_HELPER_COLD_RPMH_STATE_GUARD_PREPARED')
