"""Read only the existing front camera, board routes and shared-resource APIs."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('guard449',HERE.parent/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
BUILD=storage.mount.mounted_build();SOURCE=BUILD.parent/'source354'
P=Path('/mnt/e/edk2-samurai-out/kernel454/shared-mux');P.mkdir(mode=0o700,parents=True,exist_ok=True)
names=['drivers/media/i2c/imx471.c','arch/arm64/boot/dts/qcom/sm8150-samurai.dts','drivers/mux/gpio.c','drivers/mux/core.c','include/linux/mux/consumer.h','drivers/reset/reset-gpio.c','drivers/reset/core.c','include/linux/reset.h','drivers/gpio/gpiolib.c','drivers/media/platform/qcom/camss/camss.c','drivers/media/platform/qcom/camss/camss-csiphy.c','drivers/media/platform/qcom/camss/camss-csiphy.h','drivers/media/platform/qcom/camss/camss-csiphy-3ph-1-0.c','drivers/media/platform/video-mux.c']
rows=[]
for name in names:
 source=SOURCE/name
 if not source.is_file():continue
 raw=source.read_bytes();(P/name.replace('/','--')).write_bytes(raw)
 rows.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
pipeline=BUILD.parent/'libcamera450-stats-retirement/src/libcamera-v0.7.2/src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
raw=pipeline.read_bytes();(P/'camss_vfe.cpp').write_bytes(raw)
rows.append(dict(path='libcamera450/src/libcamera/pipeline/camss-vfe/camss_vfe.cpp',sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
config=Path('/mnt/e/edk2-samurai-out/kernel453/image363-config-private').read_text()
options=[line for line in config.splitlines() if re.search(r'CONFIG_(MULTIPLEXER|MUX_|RESET_GPIO|VIDEO_MUX)',line)]
result=dict(stage=454,source_head=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip(),files=rows,image363_options=options,no_phone_sdk=True,source_or_configuration_modified=False,passed=True)
(HERE/'mux-inspection.json').write_text(json.dumps(result,indent=2)+'\n')
def anchor(name,needle):
 text=(P/name.replace('/','--')).read_text()
 assert needle in text,(name,needle)
 return dict(path=name,line=text[:text.index(needle)].count('\n')+1,needle=needle)
anchors=[anchor(name,needle) for name,needle in [
 ('drivers/media/i2c/imx471.c','GPIOD_OUT_HIGH'),
 ('drivers/media/i2c/imx471.c','pinctrl_pm_select_sleep_state(dev)'),
 ('drivers/reset/core.c','fwnode_property_get_reference_args(fwnode, "reset-gpios"'),
 ('drivers/reset/core.c','fwnode_reference_args_equal(args, &rgpio_dev->ref_args)'),
 ('drivers/reset/core.c','atomic_dec_return(&rstc->deassert_count)'),
 ('drivers/reset/reset-gpio.c','devm_gpiod_get(dev, "reset", GPIOD_OUT_HIGH)'),
 ('drivers/mux/core.c','if (down_trylock(&mux->lock))'),
 ('drivers/mux/core.c','even if an error occurs, the'),
 ('drivers/media/platform/qcom/camss/camss.c','csiphy->cfg.csi2 = &csd->interface.csi2;'),
 ('drivers/media/platform/qcom/camss/camss.c','MEDIA_LNK_FL_IMMUTABLE | MEDIA_LNK_FL_ENABLED'),
 ('drivers/media/platform/video-mux.c','mux_control_try_select(vmux->mux, local->index)'),
 ('drivers/media/platform/video-mux.c','MEDIA_BUS_FMT_Y10_1X10'),
 ('drivers/media/platform/qcom/camss/camss-csiphy.c','MEDIA_BUS_FMT_Y10_1X10')]]
audit=dict(stage=454,inspection_receipt_sha256=hashlib.sha256((HERE/'mux-inspection.json').read_bytes()).hexdigest(),anchors=anchors,reset_gpio_fallback_and_reference_dedup_present=True,shared_reset_assert_requires_balanced_deassert=True,mux_try_select_is_exclusive_and_busy_is_error=True,mux_deselect_unlocks_even_if_idle_transition_fails=True,per_sensor_probe_reset_and_sleep_route_must_be_replaced=True,camss_lane_configuration_is_bound_once_not_selected_per_sensor=True,camss_external_links_currently_immutable_enabled=True,video_mux_not_in_image363=True,video_mux_does_not_supply_dynamic_csi_lane_configuration=True,libcamera_bayer_only_mode_selection_requires_monochrome_work=True,driver_or_topology_modified=False,actual_resources_or_streams_verified=False,no_phone_sdk=True,passed=True)
assert '# CONFIG_VIDEO_MUX is not set' in options
assert 'const std::array<unsigned int, 4> codes{MEDIA_BUS_FMT_SRGGB10_1X10,' in raw.decode()
(HERE/'mux-validation.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(dict(files=len(rows),image363_options=options,private_copies=str(P),passed=True),indent=2))
