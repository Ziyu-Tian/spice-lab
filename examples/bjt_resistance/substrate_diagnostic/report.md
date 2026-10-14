# BJT 默认接地衬底数值支路：补充实际验证

结果：**通过**。时间：2026-10-14T20:02:56.242506+08:00。

本补充设计包含 8 次 OP：极端高压点及名义校准点 × 两个 gmin × 默认/显式接地衬底。
本次实际运行 8 次，得到 8 个有效 OP 样本。
不修改主扫描的 252 个条件、298 次运行或原始数据。

三端写法省略的衬底默认为地；显式四端写法加零伏源独立测量该支路。
正集电极/基极/发射极电流定义进入器件；表内衬底电流为流出器件到地。
故包含衬底的外部残差为三端电流和减去衬底流出电流。
@q1 电流读出自身采用不同的支路记账；其 ic+ib+ie+is 和单独记录，
不把这些读出直接等同于外部零伏测流源。

| 条件 | gmin S | 衬底连接 | 端口 V | 衬底流出 A | 三端和 A | 计入衬底后残差 A | 读出 ic+ib+ie+is A |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| extreme | 1e-12 | implicit_ground | 296801.2891 | 2.96801289e-07 | 2.968265992e-07 | 2.531013142e-11 | -2.964615315e-21 |
| extreme | 1e-12 | explicit_ground | 296801.2891 | 2.96801289e-07 | 2.968265992e-07 | 2.531013142e-11 | -2.964615315e-21 |
| extreme | 1e-14 | implicit_ground | 338626.3965 | 3.386263964e-09 | 3.368610679e-09 | -1.765328473e-11 | 1.564198538e-21 |
| extreme | 1e-14 | explicit_ground | 338626.3965 | 3.386263964e-09 | 3.368610679e-09 | -1.765328473e-11 | 1.564198538e-21 |
| nominal | 1e-12 | implicit_ground | 0.13205 | 1.32e-13 | 1.320156752e-13 | 1.567524706e-17 | -1.749402001e-21 |
| nominal | 1e-12 | explicit_ground | 0.13205 | 1.32e-13 | 1.320156752e-13 | 1.567524706e-17 | -1.749402001e-21 |
| nominal | 1e-14 | implicit_ground | 0.1320499265 | 1.319999265e-15 | 1.328459369e-15 | 8.460104042e-18 | -3.327097067e-21 |
| nominal | 1e-14 | explicit_ground | 0.1320499265 | 1.319999265e-15 | 1.328459369e-15 | 8.460104042e-18 | -3.327097067e-21 |

显式与默认接地得到相同工作点。极端点的大部分三端电流和来自未计入的衬底数值支路；
计入该支路后剩余约 10⁻¹¹ A 的求解残差，验证阈值使用 10⁻⁶ 相对电流及 10⁻¹² A 绝对项。
这不代表真实器件的衬底泄漏、击穿或任何可实现的高压工作点，也不表示电荷守恒被破坏。

## 复现

```bash
source .local/env.sh
python scripts/verify_bjt_substrate.py --output-dir results/bjt_substrate
```

每次执行的 deck、日志、原始 OP 及 SHA-256 见 case 子目录与 run_manifest.jsonl。
主验证使用当前安装 ngspice 44.2 实测；以下官方 GitHub 镜像 master 链接提供实现参照，
不声称该网页快照与 Debian 二进制源码版本完全相同：

- https://github.com/ngspice/ngspice/blob/master/src/spicelib/devices/bjt/bjtload.c#L458
- https://github.com/ngspice/ngspice/blob/master/src/spicelib/devices/bjt/bjtsetup.c#L454
- https://github.com/ngspice/ngspice/blob/master/src/spicelib/devices/bjt/bjtask.c#L239

当前 gdsub 实测等于 gmin，降低 gmin 可改变高压解，但不能补充缺失的击穿或自热模型。

## 软件、执行与检查

```json
{
  "timestamp_utc": "2026-10-14T12:02:56.242506+00:00",
  "passed": true,
  "command": "/workspace/spice-lab/.venv/bin/python /workspace/spice-lab/scripts/verify_bjt_substrate.py --output-dir /workspace/spice-lab/results/bjt_substrate_review_final --ngspice .local/bin/ngspice",
  "python_version": "3.12.14",
  "source_links": [
    "https://github.com/ngspice/ngspice/blob/master/src/spicelib/devices/bjt/bjtload.c#L458",
    "https://github.com/ngspice/ngspice/blob/master/src/spicelib/devices/bjt/bjtsetup.c#L454",
    "https://github.com/ngspice/ngspice/blob/master/src/spicelib/devices/bjt/bjtask.c#L239"
  ],
  "main_scan_is_unchanged": true,
  "source_sha256": {
    "scripts/verify_bjt_substrate.py": "b5526c44a557e3db0622de1cd78cc241cdc5a752eaa77291c1980c4a80a4e292",
    "circuits/bjt_resistance/generic_npn.lib": "84a259c33ae6d1d380d82c932270315f3fbf59fd3a2543d29acc1f6280314422"
  },
  "ngspice_version": "ngspice-44.2 : Circuit level simulation program",
  "checks": {
    "eight_valid_op_runs": true,
    "model_readout_sum_with_is_below_1e-12_a": true,
    "external_kcl_with_substrate_within_solver_tolerance": true,
    "explicit_substrate_sensor_matches_model_is": true,
    "gdsub_equals_gmin": true,
    "implicit_and_explicit_ground_match": true
  },
  "counts": {
    "ngspice_processes": 8,
    "valid_op_samples": 8,
    "warning_runs": 0,
    "failed_runs": 0
  },
  "development_attempt": {
    "ngspice_processes": 16,
    "valid_op_outputs": 8,
    "missing_op_outputs": 8,
    "note": "Initial eight runs requested an unavailable internal-node vector; eight readout retries succeeded. All original evidence is preserved separately."
  },
  "previous_formal_runs": [
    {
      "run": "formal_run_01",
      "timestamp_utc": "2026-10-14T11:59:23.178562+00:00",
      "ngspice_processes": 8,
      "valid_op_samples": 8,
      "artifact": "formal_run_01_summary.json",
      "raw_evidence_retained": false,
      "note": "This summary is transcribed from the actual tool-observed first run. Its generated raw outputs/logs were overwritten by the old script during the second reporting-change repeat. No original raw hash or output is invented."
    },
    {
      "run": "formal_run_02",
      "timestamp_utc": "2026-10-14T12:00:44.686223+00:00",
      "ngspice_processes": 8,
      "valid_op_samples": 8,
      "artifact": "formal_run_02/",
      "raw_evidence_retained": true
    }
  ]
}
```

## 保留的诊断开发记录

development_attempt/ 保留首次临时探测的 16 次运行和原始文件：
其中前 8 次请求不可用内部节点向量而未生成 OP 输出，尽管 ngspice 退出码为零；
后 8 次删除该无效读出后成功。这些运行不计入本补充的 8 次正式验证或主扫描。
当前验证、此前正式复跑与探索合计执行 40 次 ngspice；32 个有效 OP 输出，8 个读出失败。
保存的执行清单为 development_attempt/manifest.json 与 readout_manifest.json；
前者记录首轮命令，读出重试使用相同 ngspice -b -o ngspice.log probe.cir 参数。
本次计数也见 summary.json 的 development_attempt 字段。

此前正式执行的摘要及可用原始证据保存于 run_history/；
其中首次正式执行曾被旧版脚本的重复执行覆盖，只保留实际运行摘要；
第二次正式执行的全部生成文件已在修复拒绝覆盖行为前归档。
