# RC 瞬态仿真测试报告

结果：**通过**

- 测试时间（Asia/Shanghai）：2026-10-14T19:01:52.125657+08:00
- Python：3.12.14
- 系统：Linux-6.18.44-x86_64-with-glibc2.41
- 电路：`rc_transient.cir`，R = 1 kΩ，C = 1 µF，输入 = 1 V。
- 初始条件：电容电压为 0 V；使用 UIC 从 t = 0 开始施加直流电源。
- 理论：τ = R × C = 1 ms；V(t) = 1 − exp(−t / τ)。

ngspice：`ngspice-44.2 : Circuit level simulation program`

依赖版本：NumPy 2.3.5, SciPy 1.17.0, Matplotlib 3.10.8, Pandas 2.2.3

运行命令：

```sh
/workspace/spice-lab/.local/bin/ngspice -b -o ngspice.log /workspace/spice-lab/circuits/rc_transient.cir
```

| 项目 | 测量值 | 验收标准 |
| --- | ---: | --- |
| 理论时间常数 | 1.000000 ms | R × C |
| 非线性拟合时间常数 | 0.999999669 ms | 相对误差 ≤ 1% |
| 拟合相对误差 | 0.000033% | ≤ 1% |
| 63.2121% 电压交点 | 0.999999839 ms | 相对误差 ≤ 1% |
| 交点相对误差 | 0.000016% | ≤ 1% |
| 波形最大绝对误差 | 1.21880161e-07 V | ≤ 0.001 V |
| 波形均方根误差 | 5.846426e-08 V | 记录值 |
| 样本数 | 4014 | ≥ 1000 |
| 最后采样时间 | 8.000000 ms | ≥ 7.9 ms |

拟合使用 SciPy 在 0–6τ 的真实 ngspice 样本上求解单参数 τ；最终电压固定为 1 V。
63.2121% 交点通过相邻样本线性插值独立计算。波形误差按全部原始采样点计算，未补点或平滑。

检查：

- 通过：sample count >= 1000
- 通过：simulation reaches >= 7.9 ms
- 通过：initial capacitor voltage near 0 V
- 通过：capacitor voltage rises monotonically
- 通过：fitted tau relative error <= 1%
- 通过：63.2121% crossing relative error <= 1%
- 通过：waveform maximum absolute error <= 0.001 V

输出文件（所有路径相对于本报告目录）：

- `rc_transient.csv`：时间、电容电压、理论电压与误差。
- `rc_waveform.png`：仿真/理论波形与误差图。
- `rc_transient_ngspice.txt`：ngspice 原始数值输出。
- `ngspice.log`：仿真日志。
- `rc_report.json`：结构化测量值与检查结果。

失败时，尚未生成的输出文件可能不存在；进程以非零状态退出。
