from pathlib import Path
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
t=(k/'arch/arm64/boot/dts/qcom/sm8150.dtsi').read_text();n=t.index('camcc:');print(t[n:n+1900])
for name in ['drivers/of/samurai-cci-bringup.c','drivers/clk/qcom/camcc-sm8150.c','Documentation/devicetree/bindings/media/i2c/sony,imx471.yaml']:
    lines=(k/name).read_text().splitlines();indexes=set()
    for i,l in enumerate(lines):
        if any(x in l for x in ['pm_runtime_','performance_state','required-opps','power-domains','probe(','qcom_cc_really_probe','dev_pm_domain','additionalProperties','allOf:']):indexes.update(range(max(0,i-3),min(len(lines),i+9)))
    print(name);print('\n'.join(str(i+1)+': '+lines[i] for i in sorted(indexes)))
