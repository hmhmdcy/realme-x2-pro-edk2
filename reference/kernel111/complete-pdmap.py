from pathlib import Path
import difflib,hashlib,json,re
out=Path('/mnt/e/edk2-samurai-out/kernel111')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel111')
stage=Path('/home/cy122/pmos-samurai-kernel111')
p=stage/'kernel/drivers/soc/qcom/qcom_pd_mapper.c'
before=p.read_text()
baseline=Path('/home/cy122/pmos-samurai-kernel109/kernel/drivers/soc/qcom/qcom_pd_mapper.c')
assert before==baseline.read_text()
block=re.search(r'static const struct qcom_pdm_domain_data \*sm8150_domains\[\] = \{.*?\n\};',before,re.S)
assert block and '&slpi_root_pd' not in block.group()
old=block.group()
assert old.count('\t&cdsp_root_pd,')==1
new=old.replace('\t&cdsp_root_pd,','\t&cdsp_root_pd,\n\t&slpi_root_pd,\n\t&slpi_sensor_pd,')
for filename,subdomain in [('slpir.jsn','root_pd'),('slpius.jsn','sensor_pd')]:
    data=json.loads((out/'source-files/k111-sensor-sources-readonly/firmware'/filename).read_text())
    assert data['sr_domain']==dict(soc='msm',domain='slpi',subdomain=subdomain,qmi_instance_id=90)
after=before.replace(old,new)
p.write_text(after)
name='drivers/soc/qcom/qcom_pd_mapper.c'
(ref/'qcom_pd_mapper.c.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name)))
changes=json.loads((out/'source-change-manifest.json').read_text())
changes[name]=dict(before=hashlib.sha256(before.encode()).hexdigest(),after=hashlib.sha256(after.encode()).hexdigest())
(out/'source-change-manifest.json').write_text(json.dumps(changes,indent=2)+'\n')
scope=json.loads((ref/'candidate-scope.json').read_text())
scope['source_files_changed']=list(changes)
scope['slpi_pd_maps_match_stock']=True
(ref/'candidate-scope.json').write_text(json.dumps(scope,indent=2)+'\n')
for filename in ['Image-sensors','cpio-sensors','kernel-candidate.sha256']:
    source=out/filename
    target=out/(filename+'.before-pdmap')
    assert source.is_file() and not target.exists()
    source.rename(target)
print('SLPI_STOCK_MATCHED_PD_MAPS_ADDED; first build preserved')
