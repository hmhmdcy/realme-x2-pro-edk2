from pathlib import Path
import runpy,re
root=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(root/'reference/kernel122/ensure-rootfs-volume.py'))
k=Path('/home/cy122/pmos-samurai-rootfs122/camera124/kernel')
def function(text,name):
    m=re.search(r'^.*\b'+re.escape(name)+r'\([^;]*?\)\s*\{',text,re.M|re.S)
    if not m: return 'MISSING '+name
    start=text.rfind('\n',0,text.index(name,m.start()))+1
    while start and text[start-1]=='\n' and text[start:text.index(name,m.start())].strip()=='':start=text.rfind('\n',0,start-1)+1
    brace=text.index('{',text.index(name,m.start()));depth=1;i=brace+1
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[start:i]
for name,funcs in {'camss.c':['camss_get_link_freq','camss_parse_endpoint_node'],'camss-csiphy.c':['csiphy_set_power','csiphy_stream_on','csiphy_get_lane_mask','msm_csiphy_subdev_init'],'camss-csiphy-3ph-1-0.c':['csiphy_settle_cnt_calc','csiphy_gen2_config_lanes','csiphy_init'],'camss-csid.c':['csid_link_setup'],'camss-csid-gen2.c':['__csid_configure_rx']}.items():
    text=(k/'drivers/media/platform/qcom/camss'/name).read_text()
    for f in funcs:print('FILE',name,'FUNCTION',f,'\n',function(text,f))
for name in ['camss-csiphy.h','camss-csid.h']:
    text=(k/'drivers/media/platform/qcom/camss'/name).read_text();print('HEADER',name,'\n',text[:6500])
text=(k/'drivers/media/platform/qcom/camss/camss.c').read_text()
for label in ['csiphy_res_8150','csid_res_8150']:
    start=text.index('static const struct camss_subdev_resources '+label);end=text.index('\n};',start)+3;print('RESOURCES',text[start:end])
for name in ['drivers/media/v4l2-core/v4l2-common.c']:
    text=(k/name).read_text();print('CORE_HELPER',function(text,'v4l2_get_link_freq'))
native=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/drivers/media/platform/msm/camera_8150/cam_sensor_module/cam_csiphy/cam_csiphy_core.c').read_text()
for f in ['cam_csiphy_cphy_data_rate_config','cam_csiphy_cphy_irq_config']:print('NATIVE_EXTRA',function(native,f))
for p in (k/'drivers/media/platform/qcom/camss').glob('*.[ch]'):
    for i,line in enumerate(p.read_text().splitlines()):
        if 'camss_get_link_freq(' in line or 'PHY_TYPE_SEL' in line:print('CALL',p.name,i+1,line)
