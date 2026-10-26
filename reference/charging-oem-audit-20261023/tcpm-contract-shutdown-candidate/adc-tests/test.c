
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define EPROBE_DEFER 517
#define ADC5_USB_IN_V_16 8
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define ERR_PTR(n) ((void *)(intptr_t)(n))
enum iio_chan_type {IIO_VOLTAGE,IIO_CURRENT};
struct device_node {bool compatible;struct device_node *parent;unsigned int reg;};
typedef uint32_t u32;
struct device {struct device_node *of_node;struct device *parent;bool property;};
struct iio_dev {struct device dev;};
struct iio_chan_spec {int channel;};
struct iio_channel {struct iio_dev *indio_dev;struct iio_chan_spec *channel;};
struct pmic_typec_port {struct iio_channel *vbus_adc;};
struct pmic_typec {struct pmic_typec_port *pmic_typec_port;int (*read_vbus_uv)(void *,int *);};
static struct iio_channel *result;
static enum iio_chan_type type;
static int type_error,processed_error,processed_uv,reads;
static bool device_property_present(struct device *d,const char *s){assert(!strcmp(s,"io-channels"));return d->property;}
static struct iio_channel *devm_iio_channel_get(struct device *d,const char *s){assert(d->property&&!strcmp(s,"vbus"));return result;}
static int iio_get_channel_type(struct iio_channel *c,enum iio_chan_type *t){assert(c==result);*t=type;return type_error;}
static bool of_device_is_compatible(struct device_node *n,const char *s){assert(!strcmp(s,"qcom,spmi-adc5"));return n&&n->compatible;}
static struct device_node *of_get_parent(struct device_node *n){return n?n->parent:NULL;}
static void of_node_put(struct device_node *n){(void)n;}
static int of_property_read_u32(struct device_node *n,const char *s,u32 *r){assert(!strcmp(s,"reg"));*r=n->reg;return 0;}
static int iio_read_channel_processed(struct iio_channel *c,int *uv){assert(c==result);reads++;*uv=processed_uv;return processed_error;}
static int qcom_pmic_typec_port_get_vbus_voltage(void *context, int *uv)
{
	struct pmic_typec *tcpm = context;
	int ret;

	ret = iio_read_channel_processed(tcpm->pmic_typec_port->vbus_adc, uv);
	if (ret)
		return ret;
	return *uv < 0 ? -ERANGE : 0;
}
static int qcom_pmic_typec_port_get_vbus_adc(struct device *dev,
					 struct pmic_typec *tcpm)
{
	struct iio_channel *adc;
	struct device_node *provider, *pmic, *adc_pmic;
	u32 reg;
	enum iio_chan_type type;
	int ret;

	if (!device_property_present(dev, "io-channels"))
		return 0;
	adc = devm_iio_channel_get(dev, "vbus");
	if (IS_ERR(adc))
		return PTR_ERR(adc);
	provider = adc->indio_dev->dev.of_node;
	if (!provider && adc->indio_dev->dev.parent)
		provider = adc->indio_dev->dev.parent->of_node;
	ret = iio_get_channel_type(adc, &type);
	if (ret)
		return ret;
	/* Channel 8 is ADC5_USB_IN_V_16 in this exact local provider. */
	if (!of_device_is_compatible(provider, "qcom,spmi-adc5") ||
	    type != IIO_VOLTAGE || adc->channel->channel != ADC5_USB_IN_V_16)
		return -EINVAL;
	/* Match the actual ADC block within this Type-C controller's PMIC. */
	pmic = of_get_parent(dev->of_node);
	adc_pmic = of_get_parent(provider);
	ret = pmic && pmic == adc_pmic &&
	      !of_property_read_u32(provider, "reg", &reg) && reg == 0x3100 ? 0 : -EINVAL;
	of_node_put(adc_pmic);
	of_node_put(pmic);
	if (ret)
		return ret;
	tcpm->pmic_typec_port->vbus_adc = adc;
	tcpm->read_vbus_uv = qcom_pmic_typec_port_get_vbus_voltage;
	return 0;
}

int main(void){
 struct device_node pmic={0},wrong_pmic={0},tcpc_node={.parent=&pmic};
 struct device_node node={.compatible=true,.parent=&pmic,.reg=0x3100};struct device provider={.of_node=&node};
 struct iio_dev indio={.dev={.of_node=&node,.parent=&provider}};
 struct iio_chan_spec spec={.channel=8};struct iio_channel channel={.indio_dev=&indio,.channel=&spec};
 struct device consumer={.of_node=&tcpc_node};struct pmic_typec_port port={0};struct pmic_typec pm={.pmic_typec_port=&port};
 result=&channel;type=IIO_VOLTAGE;
 assert(!qcom_pmic_typec_port_get_vbus_adc(&consumer,&pm)&&!pm.read_vbus_uv&&!port.vbus_adc);
 consumer.property=true;
 result=ERR_PTR(-EPROBE_DEFER);assert(qcom_pmic_typec_port_get_vbus_adc(&consumer,&pm)==-EPROBE_DEFER);
 result=&channel;type_error=-EIO;assert(qcom_pmic_typec_port_get_vbus_adc(&consumer,&pm)==-EIO);type_error=0;
 node.compatible=false;assert(qcom_pmic_typec_port_get_vbus_adc(&consumer,&pm)==-EINVAL);node.compatible=true;
 type=IIO_CURRENT;assert(qcom_pmic_typec_port_get_vbus_adc(&consumer,&pm)==-EINVAL);type=IIO_VOLTAGE;
 spec.channel=6;assert(qcom_pmic_typec_port_get_vbus_adc(&consumer,&pm)==-EINVAL);spec.channel=8;
 node.parent=&wrong_pmic;assert(qcom_pmic_typec_port_get_vbus_adc(&consumer,&pm)==-EINVAL);node.parent=&pmic;
 node.reg=0x3200;assert(qcom_pmic_typec_port_get_vbus_adc(&consumer,&pm)==-EINVAL);node.reg=0x3100;
 assert(!pm.read_vbus_uv&&!port.vbus_adc);
 indio.dev.of_node=NULL;assert(!qcom_pmic_typec_port_get_vbus_adc(&consumer,&pm));
 assert(pm.read_vbus_uv&&port.vbus_adc==&channel);
 int uv;processed_uv=9000000;assert(!pm.read_vbus_uv(&pm,&uv)&&uv==9000000&&reads==1);
 processed_uv=5000000;assert(!pm.read_vbus_uv(&pm,&uv)&&uv==5000000&&reads==2);
 processed_error=-ETIMEDOUT;assert(pm.read_vbus_uv(&pm,&uv)==-ETIMEDOUT);processed_error=0;
 processed_uv=-1;assert(pm.read_vbus_uv(&pm,&uv)==-ERANGE);
 puts("ADC provider/channel/type/absence/error gates and exact microvolt forwarding passed");return 0;
}
