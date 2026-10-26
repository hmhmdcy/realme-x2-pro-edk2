# 217候选的几何接口审计：尚不能直接部署

218检查实际libcamera 0.7.2消费者后，确认217新增数字裁剪描述还需要修订和验证；编译成功不能作为接口正确的依据。该候选仍未安装。

1. `CameraSensorLegacy::sensorInfo()`只读取`V4L2_SEL_TGT_CROP`，扣除`CROP_DEFAULT`的active-area偏移后写入`analogCrop`；随后直接读取输出格式尺寸。该路径没有读取`COMPOSE`。因此仅在驱动增加一个带数字裁剪偏移的`COMPOSE`，不会自动让现有libcamera正确理解输出视野。
2. libcamera的`sensor_driver_requirements.rst`仍要求`CROP`报告模拟选择区域。不能为了让现有消费者看见数字裁剪，未经模型说明就将其悄悄改成最终有效窗口。
3. [V4L2 subdev处理顺序](https://docs.kernel.org/userspace-api/media/v4l/dev-subdev.html)区分crop、缩放/compose和source crop；纯缩放而不支持合成时compose的左/上偏移应为0。数字裁剪偏移不能直接冒充图像合成位置。
4. [selection targets定义](https://docs.kernel.org/5.17/userspace-api/media/v4l/v4l2-selection-targets.html)不将`COMPOSE_DEFAULT`列为subdev有效目标。217的`get_selection()`同时接受`COMPOSE`和`COMPOSE_DEFAULT`，应在下一版修订，而不是作为已验收接口保留。

当前模式的寄存器几何计算可作为算术交叉检查：

| 模式 | 模拟读取窗口 | bin | 数字裁剪 | 按寄存器推导的输入域有效窗口 |
|---|---|---:|---|---|
| 旧1928×1088 | (8,408) 4640×2644 | 2 | (208,108) 1928×1088 | (424,624) 3856×2176 |
| 原厂2304×1728 | (0,0) 4656×3496 | 2 | (12,10) 2304×1728 | (24,20) 4608×3456 |
| 原厂4608×3456 | (0,0) 4656×3496 | 1 | (24,20) 4608×3456 | (24,20) 4608×3456 |

表中使用寄存器窗口的坐标域，不是已经确认的active pixel array坐标。下一步需明确原点、模拟/数字两段裁剪的表达方式及消费者映射，再测视野和方向。不能根据这个算术表直接覆盖传感器标定或声明镜头校准通过。

本次CPU候选只验证严格相同输入/输出尺寸的像素处理，不声称修复以上几何接口。
