from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126'
for name in ['validate-camss-schema.py','test-endpoint-schema.py','test-iova-reservation-schema.py']:
 s=(r/'reference/kernel125'/name).read_text().replace('kernel125','kernel126').replace('pmos-samurai-rootfs122/camera125','pmos-samurai-build126').replace('reference/kernel122/ensure-rootfs-volume.py','reference/kernel126/ensure-build-volume.py')
 s=s.replace("['disabled']","['okay']").replace("b'disabled\\0'","b'okay\\0'").replace('board-disabled','board-enabled').replace('actual_disabled_camss_node_checked','actual_enabled_camss_node_checked').replace('strict_disabled_node_validation_no_errors','strict_enabled_node_validation_no_errors').replace('cli_suppresses_missing_required_properties_on_disabled_nodes=True','cli_suppresses_missing_required_properties_on_disabled_nodes=False').replace('camss_disabled=True','camss_disabled=False').replace('camss_enabled_only_in_private_synthetic_fixtures=True','camss_actual_enabled_for_internal_tpg=True')
 (ref/name).write_text(s)
for name,target in [('schema-wrapper.py','validate-camss-schema.py'),('endpoint-schema-wrapper.py','test-endpoint-schema.py'),('iova-schema-wrapper.py','test-iova-reservation-schema.py')]:
 s="from pathlib import Path\nimport runpy,os\nr=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel118/ensure-build-volume.py'));runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'))\np='/home/cy122/pmos-samurai-kernel118/camera120/schema-venv/bin/python';os.execv(p,[p,str(r/'reference/kernel126/"+target+"')])\n"
 (ref/name).write_text(s)
print('K126_ACTUAL_ENABLED_DTB_SCHEMA_TESTS_PREPARED')
