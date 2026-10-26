from pathlib import Path
import re,subprocess,difflib,json
k=Path('/home/cy122/pmos-samurai-kernel116/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel116')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel116')
source=Path('/mnt/e/edk2-samurai-out/kernel115/camera-reference/aports/device/testing/linux-oneplus-hotdog-mainline616/0055-media-camss-add-sm8150-support.patch')
patch=source.read_text()
added='\n'.join(l[1:] for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))+'\n'
start=added.index('static const struct camss_subdev_resources csiphy_res_8150[]')
end=added.index('static const struct camss_resources sm8150_resources')
tables=added[start:end]
resources=added[end:added.index('\t{ .compatible = "qcom,sm8150-camss"')]
# camss_link_entities moved out of the SoC resources in 7.3.
assert resources.count('\t.link_entities = camss_link_entities\n')==1
resources=resources.replace('\t.link_entities = camss_link_entities\n','')
p=k/'drivers/media/platform/qcom/camss/camss.c'
before=p.read_text();assert 'csiphy_res_8150' not in before
marker='static const struct camss_subdev_resources csiphy_res_8250[] = {'
assert before.count(marker)==1
t=before.replace(marker,tables+marker)
marker='static const struct camss_resources sm8250_resources = {'
assert t.count(marker)==1;t=t.replace(marker,resources+marker)
marker='\t{ .compatible = "qcom,sm8250-camss", .data = &sm8250_resources },'
assert t.count(marker)==1
t=t.replace(marker,'\t{ .compatible = "qcom,sm8150-camss", .data = &sm8150_resources },\n'+marker)
(out/'camss-base-before.c').write_text(before);p.write_text(t)
diff=''.join(difflib.unified_diff(before.splitlines(True),t.splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/camss.c',tofile='b/drivers/media/platform/qcom/camss/camss.c'))
(ref/'camss-base-7.3.patch').write_text(diff)
subprocess.run(['git','diff','--check','--','drivers/media/platform/qcom/camss'],cwd=k,check=True)
report=dict(kernel_candidate=116,base_sm8150_resource_tables_added=True,new_kernel_api_adapted=True,
 csiphy_generation_still_845_pending=True,cphy_not_ported=True,board_camera_nodes_not_enabled=True,
 not_deployed=True,goal_complete=False)
for folder in [out,ref]: (folder/'camss-base-port-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
