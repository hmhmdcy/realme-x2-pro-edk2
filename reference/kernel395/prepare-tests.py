from pathlib import Path
import ast,shutil
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel394'
script=(OLD/'check-hook.py').read_text().replace('stage=394','stage=395').replace('camss-icp-a5-boot.c.before','camss-icp-a5-boot.c.normal');(HERE/'check-hook.py').write_text(script)
shutil.copyfile(OLD/'ack-loss-client-tail.c',HERE/'ack-loss-client-tail.c');script=(OLD/'build-client.py').read_text().replace('stage=394','stage=395');(HERE/'build-client.py').write_text(script)
script=(HERE/'build-intree.py').read_text().replace('intree-build','test-intree-build').replace("'-intree-r'","'-test-intree-r'")
script=script.replace("'KCFLAGS=-Werror'","'KCFLAGS=-Werror -DCAMSS_A5_TEST_DROP_FRAME_ACK'")
anchor="try:\n subprocess.run([str(source/'scripts/config')";assert script.count(anchor)==1
script=script.replace(anchor,"path=source/'drivers/media/platform/qcom/camss/camss-icp-a5-boot.c'\nassert path.read_bytes()==(P/'camss-icp-a5-boot.c.normal').read_bytes()\ntry:\n path.write_bytes((P/'camss-icp-a5-boot.c.test').read_bytes())\n subprocess.run([str(source/'scripts/config')",1)
script=script.replace('finally:\n for relative',"finally:\n path.write_bytes((P/'camss-icp-a5-boot.c.normal').read_bytes())\n for relative",1)
script=script.replace('report=dict(stage=395',"assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()\nreport=dict(stage=395",1)
script=script.replace('only_core_changed_adapter_abi_unchanged=True','temporary_ack_loss_core=True,source_restored_to_normal395=True')
ast.parse(script);(HERE/'build-test-core.py').write_text(script)
print('Prepared the unchanged lost-ACK client/hook against the pulse candidate.')
