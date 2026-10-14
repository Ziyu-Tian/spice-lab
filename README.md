# spice-lab

在 Linux 云端运行 ngspice，并通过 Python 检查 RC 电路瞬态响应。

## 安装与运行

已验证环境：Debian 13（trixie，x86_64）、Python 3.12.14、ngspice 44.2。
Python 要求 **3.11 或更新版本**。云端提供的 Python 3 可直接使用。

在现有仓库检出目录运行：

```bash
cd /workspace/spice-lab
bash scripts/setup_env.sh
source .local/env.sh
python scripts/test_rc.py --output-dir results/rc
```

安装脚本和测试均可重复执行。每个云端任务已经隔离，使用现有检出目录，
无需创建 Git worktree。其他检出路径中，脚本会自动定位仓库根目录。

Debian 13 下安装脚本使用 Debian 官方签名 APT 仓库下载固定版本的
ngspice（`44.2+ds-1`）及缺失依赖，解包到 `.local/ngspice`；无需 sudo。
APT 保留签名和包哈希检查，不修改系统包、源配置或仓库中的受版本控制文件。
它依赖已有的 APT、dpkg、dpkg-architecture、Debian 官方 keyring 与 HTTPS 信任证书。
其他 Debian/Ubuntu 版本若尚无 ngspice，会使用系统 APT 安装，需要 root
或无需交互的 sudo；这些平台尚未验证，ngspice 版本由该发行版决定。
若没有 Python，脚本会尝试通过系统 APT 安装 `python3`、`python3-venv`；
已有 Python 应支持 `python3 -m venv`。

Python 包安装到 `.venv`，全部直接及间接依赖都在
`requirements.lock` 中固定版本并记录 SHA-256。
安装使用 `pip --require-hashes --only-binary=:all:`，保留 TLS 验证。
直接依赖为 NumPy 2.3.5、SciPy 1.17.0、Matplotlib 3.10.8、Pandas 2.2.3。
安装、重复安装和 `pip check` 已在当前云端执行验证。

网络需要 `deb.debian.org`、`pypi.org`、`files.pythonhosted.org`；
GitHub 同步使用平台已有的 Git 认证，无需在脚本内放置令牌。

## RC 验证

电路文件：`circuits/rc_transient.cir`。
R = 1 kΩ、C = 1 µF、输入电压 1 V，电容从 0 V 开始充电。
使用 `UIC` 与直流源模拟从零初始电荷开始的阶跃，避免有限上升沿改变测量值。

理论时间常数 `τ = RC = 1 ms`，理论波形为：

```text
V(t) = 1 - exp(-t / τ)
```

ngspice 执行 0–8 ms 瞬态计算，最大时间步长 2 µs。
测试程序使用真实 ngspice 原始样本进行检查，包含：

- SciPy 非线性拟合得到 τ，相对理论值误差不得超过 1%。
- 对达到 `1 - exp(-1)`（约 63.2121%）电压的时间插值，误差不得超过 1%。
- 全波形最大绝对误差不得超过 1 mV。
- 检查时间递增、有限数值、样本数、仿真时长、初始电压及单调充电。

任何检查失败都会以非零退出码结束并写入报告，失败不得视为环境验证通过。
图形使用 Matplotlib Agg 后端，无需显示服务器或后台服务。
也可用 `--ngspice /absolute/path/to/ngspice` 指定程序。

输出目录包含：

| 文件 | 内容 |
| --- | --- |
| `rc_transient.csv` | 时间、电容电压、理论电压、误差 |
| `rc_waveform.png` | 仿真与理论波形，以及误差曲线 |
| `rc_report.md` | 可读测试报告、阈值、测量值与结果 |
| `rc_report.json` | 结构化结果和工具版本 |
| `rc_transient_ngspice.txt` | ngspice 原始数值输出 |
| `ngspice.log` / `ngspice_console.log` | 仿真日志 |

本次验证结果保存在 [`examples/rc_validation/rc_report.md`](examples/rc_validation/rc_report.md)，
CSV 和 PNG 同在该目录。常规重复运行请输出到被 Git 忽略的 `results/rc`，
避免修改已提交的示例结果。

## 新建云端任务

首次或需刷新依赖时执行 `bash scripts/setup_env.sh`。
每次新 shell 执行 `source .local/env.sh` 后运行测试即可；已安装文件可以保留，
虚拟环境激活和环境变量需在新进程中重新设置。
云端配置中的安装脚本、启动指引也保存了这组命令；配置保存与环境发布是两个独立步骤。

如需更新依赖，在独立编码任务中编辑 `requirements.in`，重新生成锁文件并复验。
本锁文件使用以下命令生成（需要 uv）：

```bash
uv pip compile requirements.in --generate-hashes --python-version 3.11 --universal \
  --default-index https://pypi.org/simple --no-header --output-file requirements.lock
```

普通安装无需 uv，脚本不改动锁文件。安装缓存、虚拟环境和运行结果均不提交到 Git。
