"""Inspect retained r30 caller roles; do not infer actual enables from code alone."""
from pathlib import Path
import hashlib,importlib.util,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
root=storage.mounted_build().parent/'libcamera391-ipe-r30-built/src/libcamera-v0.7.2'
checks={
 'src/ipa/camss-vfe/camss.cpp':['configureGammaProfile(tuning["gamma"],&gamma_)','ColourCorrectionProfile::configure(tuning["colour_correction"],&colourCorrection_)','gamma_?&*gamma_:nullptr'],
 'src/ipa/camss-vfe/parameter_encoder.cpp':['if (ccm)','params.block<CamssBlocks::ColorCorrect>()','if (gamma)','params.block<CamssBlocks::IfeGamma>()'],
 'src/ipa/camss-vfe/gamma_profile.cpp':['CAMSS_PARAMS_IFE_GAMMA','V4L2_ISP_PARAMS_FL_BLOCK_ENABLE','encodeGammaCurve'],
 'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp':['ipe_->queue(buffer,output)'],
 'src/libcamera/pipeline/camss-vfe/camss_ipe.cpp':['device_.capture()->queueBuffer(output)','device_.output()->queueBuffer(wrapped)']}
rows=[]
for relative,needles in checks.items():
 p=root/relative;text=p.read_text();lines=text.splitlines();locations=[]
 for needle in needles:
  found=[i+1 for i,line in enumerate(lines) if needle in line];assert found,(relative,needle);locations.append(dict(anchor=needle,lines=found))
 (P/(p.name+'.r30-private')).write_bytes(p.read_bytes());rows.append(dict(path=relative,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),anchors=locations))
ipe=(root/'src/libcamera/pipeline/camss-vfe/camss_ipe.cpp').read_text();assert 'camss_a5_ipe_gamma' not in ipe and 'camss_a5_ipe_colour' not in ipe
report=dict(stage=401,retained_r30_source_inspected=True,files=rows,ife_ccm_and_gamma_have_existing_parameter_emission_paths=True,ife_gamma_uses_separate64_segment_interface=True,ipe_current_userspace_queues_images_without_typed_colour_gamma_metadata=True,current_device_profile_activation_not_inferred_from_source=True,no_phone_access=True,no_source_changes=True,integration_requirement='Keep IFE input transfer function/CCM ownership explicit before enabling IPE tone/colour controls; preserve stock LTM inverse-gamma requirements and avoid duplicate correction.',passed=True)
(HERE/'ife-role-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
