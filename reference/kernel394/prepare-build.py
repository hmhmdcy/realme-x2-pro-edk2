from pathlib import Path
import ast,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'hook-validation.json').read_text())['passed']
base=json.loads((HERE.parent/'kernel393/source-state.json').read_text())
(HERE/'source-state.json').write_text(json.dumps(dict(stage=394,commit=base['commit'],branch=base['branch'],permanent_source_unchanged=True,only_private_test_variant_built=True),indent=2)+'\n')
script=(HERE.parent/'kernel393/build-intree.py').read_text().replace('stage=393','stage=394')
a=script.index('modules=[camss/');b=script.index('\ncommand=',a)
script=script[:a]+"modules=[camss/'qcom-camss-icp-a5-core.ko']\nruntime_modules=set(modules)"+script[b:]
script=script.replace("'KCFLAGS=-Werror'","'KCFLAGS=-Werror -DCAMSS_A5_TEST_DROP_FRAME_ACK'")
script=script.replace('only_changed_core_adapter_pair_selected_for_deployment=True','temporary_test_core_only=True,production_module_files_not_changed=True')
anchor="try:\n subprocess.run([str(source/'scripts/config')"
assert script.count(anchor)==1
script=script.replace(anchor,"path=source/'drivers/media/platform/qcom/camss/camss-icp-a5-boot.c'\nassert path.read_bytes()==(P/'camss-icp-a5-boot.c.before').read_bytes()\ntry:\n path.write_bytes((P/'camss-icp-a5-boot.c.test').read_bytes())\n subprocess.run([str(source/'scripts/config')",1)
script=script.replace('finally:\n for relative','finally:\n path.write_bytes((P/\'camss-icp-a5-boot.c.before\').read_bytes())\n for relative',1)
script=script.replace('report=dict(stage=394',"assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()\nreport=dict(stage=394",1)
ast.parse(script);(HERE/'build-test-core.py').write_text(script)
print('Prepared isolated test-core build with permanent source restoration.')
