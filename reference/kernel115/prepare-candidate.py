from pathlib import Path
import subprocess,json,hashlib
old=Path('/home/cy122/pmos-samurai-kernel114')
stage=Path('/home/cy122/pmos-samurai-kernel115')
out=Path('/mnt/e/edk2-samurai-out/kernel115')
assert not stage.exists()
stage.mkdir()
for name in ['kernel','initramfs']:
    subprocess.run(['cp','-a','--reflink=auto',str(old/name),str(stage/name)],check=True)
k=stage/'kernel'
config=k/'.config'
config.write_text(config.read_text().replace(str(old/'initramfs'),str(stage/'initramfs')))
p=k/'drivers/net/ipa/data/ipa_data-v4.1.c'
t=p.read_text()
assert t.count('0x146a8000')==1
p.write_text(t.replace('0x146a8000','0x146bd000'))
p=k/'arch/arm64/boot/dts/qcom/sm8150.dtsi'
t=p.read_text()
assert t.count('<0 0x01e04000 0 0x2c000>')==1
p.write_text(t.replace('<0 0x01e04000 0 0x2c000>','<0 0x01e04000 0 0x28000>'))
p=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
t=p.read_text()
assert '&ipa {' not in t
p.write_text(t+'\n/* Same-handset stock PIL loader and firmware reservation. */\n&ipa {\n\tstatus = "okay";\n\tqcom,gsi-loader = "self";\n\tmemory-region = <&ipa_fw_mem>;\n\tfirmware-name = "qcom/sm8150/realme/samurai/ipa_fws.mdt";\n};\n')
p=k/'drivers/net/ipa/gsi_trans.c'
t=p.read_text()
start=t.index('void gsi_trans_commit_wait(')
end=t.index('/* Process the completion',start)
part=t[start:end]
assert part.count('wait_for_completion(&trans->completion);')==1
part=part.replace('wait_for_completion(&trans->completion);','''/* Hold our reference until completion or a bounded timeout. The
\t * completion path retains its own reference after we time out.
\t */
\tif (!wait_for_completion_timeout(&trans->completion,
\t\t\t\t\t msecs_to_jiffies(1000)))
\t\tdev_err(trans->gsi->dev,
\t\t\t"channel %u: transaction did not complete in 1000ms\\n",
\t\t\ttrans->channel_id);''')
p.write_text(t[:start]+part+t[end:])
subprocess.run(['git','diff','--check','--','drivers/net/ipa','arch/arm64/boot/dts/qcom/sm8150.dtsi','arch/arm64/boot/dts/qcom/sm8150-samurai.dts'],cwd=k,check=True)
diff=subprocess.run(['git','diff','--','drivers/net/ipa','arch/arm64/boot/dts/qcom/sm8150.dtsi','arch/arm64/boot/dts/qcom/sm8150-samurai.dts'],cwd=k,check=True,capture_output=True).stdout
(out/'candidate-source-diff.patch').write_bytes(diff)
report=dict(build=115,own_register_base_verified=True,own_imem_address='0x146bd000',gsi_register_size='0x28000',gsi_wait_bounded_ms=1000,own_vendor_firmware_verified=True,loader='self',clock_interconnect_values_provisional_reference=True,ipa_board_node_enabled_in_candidate=True,not_deployed=True,goal_complete=False)
(out/'candidate-preparation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
