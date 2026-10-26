from pathlib import Path
import hashlib,json
here=Path(__file__).resolve().parent;root=Path('/home/cy122/x2pro-linux/libcamera214-root');build=root/'work/libcamera239-r15-built/src/libcamera-v0.7.2/output';targets=json.loads((build/'meson-info/intro-targets.json').read_text());names=sorted({p['name'] for p in targets});config=(build/'config.h').read_text()
required=['cam','lc-compliance','qcam','gstlibcamera','v4l2-compat','_libcamera','ipa_mali_c55','ipa_rkisp1','ipa_rpi_pisp','ipa_rpi_vc4','ipa_soft_simple']
found={name:(any(value.startswith('_libcamera.cpython-314-aarch64-linux-musl') for value in names) if name=='_libcamera' else name in names) for name in required}
report=dict(stage=239,configure_completed=True,required_original_feature_targets=found,all_required_feature_targets_found=all(found.values()),python_target_abi='cpython-314-aarch64-linux-musl',gpu_isp_still_compiled='#define HAVE_DEBAYER_EGL 1' in config,ipa_signing_public_key_enabled='#define HAVE_IPA_PUBKEY 1' in config,compiled_binary_package_not_yet_accepted=True,all_target_names=names)
(here/'r15-full-feature-configuration-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
