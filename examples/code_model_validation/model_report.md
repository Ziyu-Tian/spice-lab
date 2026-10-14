# ngspice Code Model 加载修复与验证

最终状态：PASS。

## 原因和修复

原 RC 报告的六个加载错误来自 rootless 解包后仍使用 Debian spinit 中的 `/usr/lib/.../ngspice/*.cm`。这些绝对路径属于系统安装布局；实际库位于仓库 `.local/ngspice/usr/lib/.../ngspice/`。

安装脚本保持包内 spinit 不变，生成 `.local/ngspice-runtime/spinit`，重定位 Code Model 路径，并让 wrapper 设置 `SPICE_SCRIPTS` 指向该目录。每次运行 setup 都重新生成配置，即使依赖已安装也可刷新旧快照中的错误 wrapper。APT 签名和哈希、pip 哈希及 TLS 验证保持启用。

官方 [ngspice man page](https://github.com/ngspice/ngspice/blob/master/man/man1/ngspice.1)明确 `SPICE_SCRIPTS` 为 spinit 搜索目录。`codemodel` 在 44.2 中将路径双引号当作文件名字符，因此修复使用无空白的裸绝对路径；安装路径包含空白时脚本明确报错。

## 真实执行结果

| 检查 | 结果 | 证据 |
|---|---|---|
| library_dependencies:spice2poly.cm | PASS | All dependencies resolve |
| library_dependencies:analog.cm | PASS | All dependencies resolve |
| library_dependencies:digital.cm | PASS | All dependencies resolve |
| library_dependencies:xtradev.cm | PASS | All dependencies resolve |
| library_dependencies:xtraevt.cm | PASS | All dependencies resolve |
| library_dependencies:table.cm | PASS | All dependencies resolve |
| original_path_expected_failure | PASS | Expected init failure reproduced for 6/6 libraries; ngspice exit=0 |
| registry_log_clean | PASS | No errors or warnings |
| model_registration:spice2poly.cm | PASS | spice2poly |
| model_registration:analog.cm | PASS | gain |
| model_registration:digital.cm | PASS | d_inverter |
| model_registration:xtradev.cm | PASS | cmeter |
| model_registration:xtraevt.cm | PASS | real_gain |
| model_registration:table.cm | PASS | table2d |
| analog_log_clean | PASS | No errors or warnings |
| analog_gain_numerical | PASS | 41 DC points; max absolute error 4.44089e-16 V |
| digital_log_clean | PASS | No errors or warnings |
| digital_inverter_numerical | PASS | 2101 transient points, 1783 stable samples; max error 0 V |

六库的真实 `ldd` 输出和 sha256 见日志及 `model_libraries.csv`。每个库至少一个独有模型出现在 ngspice `devhelp` 注册表中；这是加载证据，不表示穷尽了该库所有模型的计算功能。

gain Code Model 实际 DC 扫描 -1…+1 V，验证 `Vout = 2.5 Vin + 0.125 V`。数字测试实际使用 ADC bridge、d_inverter 和 DAC bridge，验证 0/3.3 V 输入反相输出；全瞬态保存，数值断言排除输入边沿 100 ns 内的延迟/过渡样本。

OSDI 被 Debian spinit 默认禁用。本测试不加载、也不声称验证 OSDI 外部紧凑模型；标准内建 BJT 与上述 XSPICE Code Model 不依赖 OSDI。

## 警告、失败与重复执行

原始错误再现：6/6 库加载失败，ngspice 返回 0；这是有标签的预期失败，见 `original_path_expected_failure.log`。说明必须检查日志而不能仅看退出码。

修复后的注册表、analog 和 digital 日志中检测到的 error/warning/fatal 数量分别为 0、0、0。XSPICE 会显示 `Reducing trtol to 1 for xspice 'A' devices`，属仿真器正常精度调整提示。

开发时双引号路径导致的首次修复失败保存在 `relocation_quoted_path_failure.log`；后续去除引号重新执行通过。安装刷新和第二次重复执行日志分别见 `setup_refresh.log`、`setup_repeat.log`（历史执行证据，不由本测试程序覆盖）。原 RC 示例文件保持原样。

## 复现命令

```bash
cd /workspace/spice-lab
bash scripts/setup_env.sh
source .local/env.sh
python scripts/test_ngspice_models.py --output-dir results/code_models
```

本次 ngspice、ldd 的确切命令、工作目录和退出码由 `model_report.json` 保存。

## 版本

```text
******
** ngspice-44.2 : Circuit level simulation program
** Compiled with KLU Direct Linear Solver
** The U. C. Berkeley CAD Group
** Copyright 1985-1994, Regents of the University of California.
** Copyright 2001-2024, The ngspice team.
** Please get your ngspice manual from https://ngspice.sourceforge.io/docs.html
** Please file your bug-reports at http://ngspice.sourceforge.net/bugrep.html
** Creation Date: Sun Jan 12 08:19:15 UTC 2025
******
```

- Python: 3.12.14
- numpy: 2.3.5
- scipy: 1.17.0
- matplotlib: 3.10.8
- pandas: 2.2.3
