from pathlib import Path
import hashlib,json
own=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source')
k=Path('/home/cy122/pmos-samurai-kernel115/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel115')
board=own/'arch/arm64/boot/dts/19781'
records=[]
for p in board.rglob('*'):
    if p.is_file() and 'cam' in p.name.lower():
        text=p.read_text(errors='replace')
        selected=[dict(line=i+1,text=l.strip()) for i,l in enumerate(text.splitlines()) if any(n in l.lower() for n in ['sensor-name','eeprom-name','imx','s5k','ov64','ov48','slave-addr','compatible =','cam_vana','cam_vio','cam_vdig'])]
        records.append(dict(path=str(p.relative_to(own)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),fields=selected))
mainline=(k/'drivers/media/platform/qcom/camss/camss.c').read_text()
dtsi=(k/'arch/arm64/boot/dts/qcom/sm8150.dtsi').read_text()
report=dict(own_board_camera_sources=records,mainline_sm8150_camss_match='qcom,sm8150-camss' in mainline,shared_dtsi_camss_node='camss' in dtsi,physical_camera_not_tested=True,foreign_board_pinmux_not_applied=True,goal_complete=False)
(out/'camera-next-source-inventory.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(own_camera_files=len(records),mainline_sm8150_camss_match=report['mainline_sm8150_camss_match'],shared_dtsi_camss_node=report['shared_dtsi_camss_node']),indent=2))
