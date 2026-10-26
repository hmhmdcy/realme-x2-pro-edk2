#pragma once
#include <gio/gio.h>
G_DECLARE_DERIVABLE_TYPE (PhoshManager, phosh_manager, PHOSH, MANAGER, GObject)
struct _PhoshManagerClass {
  GObjectClass parent_class;
  void (*idle_init) (PhoshManager *manager);
};
#define PHOSH_TYPE_MANAGER (phosh_manager_get_type ())
