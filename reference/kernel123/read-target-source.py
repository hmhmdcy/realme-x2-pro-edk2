from pathlib import Path
import runpy
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
k=Path('/home/cy122/pmos-samurai-kernel118/camera121/kernel')
for name in ['drivers/media/platform/qcom/camss/camss.c','drivers/media/platform/qcom/camss/camss-csiphy-3ph-1-0.c']:
    t=(k/name).read_text();print('SOURCE',name)
    if name.endswith('camss.c'):
        for marker,end in [('static const struct camss_subdev_resources csiphy_res_8150', 'static const struct camss_subdev_resources csiphy_res_8250'),('static const struct camss_resources sm8150_resources','static const struct camss_resources sm8250_resources')]:
            if marker not in t:print('MISSING',marker);continue
            start=t.index(marker);stop=t.find(end,start)
            print(t[start:stop if stop!=-1 else start+17000])
        for line in t.splitlines():
            if 'dma_set' in line or 'dma_mask' in line or 'sm8150' in line:print(line)
    else:
        for marker,end in [('static void csiphy_gen2_config_lanes','static void csiphy_lanes_enable'),('static void csiphy_lanes_enable','static void csiphy_lanes_disable')]:
            if marker in t:
                a=t.index(marker);b=t.find(end,a+len(marker));print(t[a:b if b!=-1 else a+4500])
