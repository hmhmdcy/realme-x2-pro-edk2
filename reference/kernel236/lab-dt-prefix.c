/* Host OF property/refcount model. The actual validator is inserted below. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
#define BIT(n) (1UL<<(n))
#define PM8008_IMX319_LAB_MASK (BIT(0)|BIT(3))
struct property { const char *name;int length;const void *value;struct property *next; };
struct device_node {
 const char *basename,*compatible;bool available;int refs;
 struct property *properties;struct device_node *children,*next;
};
struct device { struct device_node *of_node; };
static struct property *property_find(struct device_node *n,const char *name) {
 for(struct property *p=n->properties;p;p=p->next)if(!strcmp(p->name,name))return p;
 return NULL;
}
static bool of_device_is_compatible(struct device_node *n,const char *s) { return n->compatible&&!strcmp(n->compatible,s); }
static bool of_property_read_bool(struct device_node *n,const char *s) { return property_find(n,s)!=NULL; }
static struct device_node *of_get_child_by_name(struct device_node *n,const char *s) {
 for(struct device_node *c=n->children;c;c=c->next)if(!strcmp(c->basename,s)){c->refs++;return c;}
 return NULL;
}
static void of_node_put(struct device_node *n) { if(n){assert(n->refs>0);n->refs--;} }
static struct device_node *next_child(struct device_node *n,struct device_node *previous) {
 struct device_node *c=previous?previous->next:n->children;
 of_node_put(previous);if(c)c->refs++;return c;
}
#define for_each_child_of_node(p,n) for((n)=next_child((p),NULL);(n);(n)=next_child((p),(n)))
#define for_each_property_of_node(n,p) for((p)=(n)->properties;(p);(p)=(p)->next)
static bool of_device_is_available(struct device_node *n) { return n->available; }
static bool of_node_name_eq(struct device_node *n,const char *s) { return !strcmp(n->basename,s); }
static int of_property_read_u32(struct device_node *n,const char *name,u32 *value) {
 struct property *p=property_find(n,name);if(!p||p->length!=4||!p->value)return -EINVAL;
 const unsigned char *b=p->value;*value=((u32)b[0]<<24)|((u32)b[1]<<16)|((u32)b[2]<<8)|b[3];return 0;
}
