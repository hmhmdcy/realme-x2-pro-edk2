struct ui_device {
	struct regmap *map;
	struct mutex lock;
	struct delayed_work work;
	struct ui_state state;
	struct ui_ops io;
	u64 instance;
	bool held_ref, paused, joining;
};
