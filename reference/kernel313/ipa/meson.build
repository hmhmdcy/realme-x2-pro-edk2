# SPDX-License-Identifier: CC0-1.0
ipa_name = 'ipa_camss_vfe'
mod = shared_module(ipa_name, ['camss.cpp', 'parameter_encoder.cpp', 'hardware_agc.cpp', 'hardware_awb.cpp'],
    name_prefix : '',
    include_directories : [ipa_includes],
    dependencies : [libcamera_private, libipa_dep],
    install : true,
    install_dir : ipa_install_dir)
if ipa_sign_module
    custom_target(ipa_name + '.so.sign', input : mod,
        output : ipa_name + '.so.sign',
        command : [ipa_sign, ipa_priv_key, '@INPUT@', '@OUTPUT@'],
        install : false, build_by_default : true)
endif
ipa_names += ipa_name
