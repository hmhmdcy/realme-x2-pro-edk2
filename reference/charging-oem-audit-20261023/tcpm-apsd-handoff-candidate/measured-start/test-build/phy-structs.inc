struct pmic_typec_pdphy_irq_data {
	int				virq;
	int				irq;
	struct pmic_typec_pdphy		*pmic_typec_pdphy;
};
struct pmic_typec_pdphy {
	struct device			*dev;
	struct tcpm_port		*tcpm_port;
	struct regmap			*regmap;
	u32				base;

	unsigned int			nr_irqs;
	struct pmic_typec_pdphy_irq_data	*irq_data;

	struct work_struct		reset_work;
	struct work_struct		receive_work;
	struct regulator		*vdd_pdphy;
	bool			supply_held;
	bool			handoff_powered; /* actual untransferred regulator reference */
	bool			irqs_started;
	spinlock_t			lock;		/* Register atomicity */
};
