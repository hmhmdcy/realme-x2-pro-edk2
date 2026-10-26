from pathlib import Path
HERE=Path(__file__).resolve().parent
script=(HERE.parent/'kernel386/check-pixels.py').read_text()
script=script.replace('m2m-runtime-r4-validation.json','dma-runtime-r2-validation.json').replace('collected-r4','collected-r2').replace("stage=386,run='r4'","stage=388,run='r2'")
script=script.replace("b'\\xa5'*(stride-w)","b'\\xa7'*(stride-w)")
script=script.replace('last_full_image_per_case_recomputed_on_host=True,','last_full_image_per_case_recomputed_on_host=True,caller_padding_a7_preserved_instead_of_old_bounce_a5=True,')
script=script.replace('zero_copy_not_claimed=True,libcamera_pipeline_not_yet_integrated=True','native_m2m_direct_dma_without_core_image_copies_verified=True,libcamera387_candidate_integration_separately_checked=True')
exec(compile(script,str(HERE/'check-pixels-generated.py'),'exec'),globals())
