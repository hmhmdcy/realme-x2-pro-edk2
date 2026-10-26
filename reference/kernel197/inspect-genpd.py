from pathlib import Path
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');b=k/'drivers/media/platform/qcom/camss'
for name,markers in [('camss.c',['static int camss_configure_pd','static void camss_genpd_cleanup']),('camss-vfe.c',['int vfe_get','static int vfe_set_clock_rates']),('camss-vfe-170.c',['static int vfe_pm_domain_on','static void vfe_pm_domain_off']),('camss-vfe-gen1.c',['int vfe_pm_domain_on','void vfe_pm_domain_off'])]:
 s=(b/name).read_text();print(name)
 for m in markers:
  i=s.find(m);print(s[i:i+7000] if i>=0 else m+' NOT FOUND')
