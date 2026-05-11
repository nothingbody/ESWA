# FTV-Logistics 项目数据、流程、结果与分析结论整理

整理日期：2026-05-10

## 1. 项目定位

本项目题目为“借鉴快速思考机制的智慧物流路径优化协同决策架构研究”，英文表述可使用 *A Fast-Think-and-Verify Collaborative Decision Architecture for Smart Logistics Routing Optimization*。当前研究对象不是单一最优求解算法，而是一个可复现、可扩展、可验证的物流路径优化协同决策架构。

项目边界如下：

- 使用公开 benchmark，不使用企业私有订单数据。
- 使用 CPU-only 运行环境，不依赖 GPU 训练。
- 以 VRPTW / PDPTW 的统一建模、约束验证、反馈修复和启发式优化闭环为核心贡献。
- 结果不应表述为刷新 BKS 或最优求解器，应表述为架构验证与启发式优化增强。

## 2. 数据与结果文件台账

### 2.1 数据集范围

| 数据集 | 问题类型 | 当前规模 | 用途 |
| --- | --- | ---: | --- |
| Solomon VRPTW | 带时间窗车辆路径问题 | 56 个 100-customer 实例 | 主实验、算法增强、消融验证 |
| Li & Lim PDPTW | 带时间窗取送货问题 | 56 个 100-task 实例 | 复杂约束与跨问题适配验证 |
| Homberger VRPTW | 大规模带时间窗车辆路径问题 | 12 个 200/400-customer 代表实例 | 扩展性与大规模可运行性验证 |

### 2.2 关键结果文件

| 文件 | 内容 |
| --- | --- |
| `results/tables/solomon_stage1_summary.csv` | Solomon 三种快速构造方法的可行率、车辆数、距离、运行时间 |
| `results/tables/solomon_stage1_gap_summary.csv` | Solomon 快速构造方法相对 BKS 的车辆 gap 和距离 gap |
| `results/tables/solomon_alns_all_gap_summary.csv` | Basic ALNS 增强后的 Solomon gap 汇总 |
| `results/tables/advanced_alns_all_gap_summary.csv` | Advanced ALNS 多启动强化后的 Solomon gap 汇总 |
| `results/tables/li_lim_stage1_all_summary.csv` | Li & Lim 基线与 Pair ALNS 的性能汇总 |
| `results/tables/li_lim_stage1_gap_summary.csv` | Li & Lim 基线与 Pair ALNS 的 BKS gap 汇总 |
| `results/tables/homberger_200_400_summary.csv` | Homberger 代表实例性能汇总 |
| `results/tables/homberger_200_400_gap_summary.csv` | Homberger 代表实例 BKS gap 汇总 |
| `results/tables/solomon_ablation_summary.csv` | FTV 流程消融实验汇总 |
| `results/logs/algorithm_strengthening_20260510_112403.log` | 最近一次算法强化正式重跑日志 |

### 2.3 图表文件

当前已生成的图表位于 `results/figures/`，主要包括：

- `figure_solomon_avg_vehicles.png`
- `figure_solomon_avg_distance.png`
- `figure_solomon_vehicle_gap.png`
- `figure_li_lim_avg_vehicles.png`
- `figure_li_lim_vehicle_gap.png`
- `figure_homberger_avg_vehicles.png`
- `figure_homberger_vehicle_gap.png`
- `figure_ablation_summary.png`

## 3. 总体实验流程

FTV-Logistics 的实验流程可以整理为七步：

1. 公开 benchmark 输入：读取 Solomon、Homberger、Li & Lim 原始实例。
2. 统一任务抽象：解析为统一的 `LogisticsTask`，包含车辆容量、时间窗、服务时间、距离矩阵、取送货配对等信息。
3. 快速思考层：生成初始路径草案，包括 `nearest_neighbor`、`greedy_insertion`、`regret_insertion`，PDPTW 使用 `greedy_pair_insertion`。
4. 约束验证层：统一检查容量、时间窗、服务时间、重复节点、未服务节点、取送货先后关系、同车约束等。
5. 反馈修复与反思优化：使用 `repair_insertion`、`route_merge`、`route_elimination`、局部搜索、Basic ALNS、Advanced ALNS 或 Pair ALNS 改善草案。
6. 多启动择优：Advanced ALNS 和 Pair ALNS 使用固定 seed 池 `42/11/23`，按“可行性、车辆数、距离、违规数”选择最终解。
7. 结果评估：输出可行率、车辆数、距离、运行时间、车辆 gap、距离 gap，并生成汇总表、图表和论文草稿。

可复现入口主要由 `experiments/rerun_full_pipeline.sh` 管理。最近一次正式算法强化重跑已完成，日志显示最终测试为 `17 passed`。

## 4. 主要结果整理

### 4.1 Solomon VRPTW Stage-1 快速构造

| 方法 | 实例数 | 可行率 | 平均车辆数 | 平均距离 | 平均运行时间 |
| --- | ---: | ---: | ---: | ---: | ---: |
| greedy_insertion | 56 | 1.000000 | 8.696429 | 1300.218496 | 8.663579 |
| nearest_neighbor | 56 | 1.000000 | 8.857143 | 1388.953456 | 0.030735 |
| regret_insertion | 56 | 1.000000 | 10.446429 | 2000.435977 | 6.925511 |

Stage-1 中，`greedy_insertion` 是最强构造基线，平均车辆数和平均距离均优于另外两种快速构造方法。`nearest_neighbor` 运行最快，但需要后续修复和优化来弥补解质量不足。

### 4.2 Solomon BKS gap 与 ALNS 强化

| 方法 | 实例数 | 平均车辆 gap | 车辆数匹配率 | 全部距离 gap | 可比较距离实例数 | 可比较距离 gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| greedy_insertion | 56 | 1.464286 | 0.250000 | 28.540275 | 14 | 32.868042 |
| greedy_insertion+basic_alns | 56 | 0.750000 | 0.500000 | 14.048561 | 28 | 17.747329 |
| greedy_insertion+advanced_alns | 56 | 0.446429 | 0.589286 | 2.925030 | 33 | 4.957422 |

关键增量：

- 从 `greedy_insertion` 到 `advanced_alns`，平均车辆 gap 下降 1.017857，约下降 69.51%。
- 从 `basic_alns` 到 `advanced_alns`，平均车辆 gap 下降 0.303571，约下降 40.48%。
- `advanced_alns` 的车辆数匹配率达到 58.9286%，高于 Stage-1 的 25.0000% 和 Basic ALNS 的 50.0000%。
- 多启动选择中，Solomon 56 个实例的 seed 分布为：`42` 选中 28 次，`11` 选中 15 次，`23` 选中 13 次，说明多启动不是形式化操作，而是实际改变了部分算例结果。

### 4.3 Advanced ALNS 参数筛选

| 配置 | 运行数 | 可行率 | 平均车辆数 | 平均距离 | 平均运行时间 |
| --- | ---: | ---: | ---: | ---: | ---: |
| aggressive | 9 | 1.000000 | 14.888889 | 1440.783084 | 20.519654 |
| balanced | 9 | 1.000000 | 14.888889 | 1410.495431 | 20.501997 |
| conservative | 9 | 1.000000 | 15.000000 | 1414.537590 | 20.224351 |

参数筛选结果显示，`balanced` 与 `aggressive` 平均车辆数相同，但 `balanced` 平均距离更低，因此正式 Solomon Advanced ALNS 采用 `balanced` 配置。

### 4.4 Li & Lim PDPTW 结果

| 方法 | 实例数 | 可行率 | 平均初始车辆数 | 平均车辆数 | 平均车辆减少 | 平均距离 | 平均距离改善率 | 平均运行时间 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| greedy_pair_insertion | 56 | 1.000000 | 9.464286 | 8.625000 | 0.839286 | 1344.880537 | 2.800838 | 4.573340 |
| greedy_pair_insertion+pair_alns | 56 | 1.000000 | 8.625000 | 7.660714 | 0.964286 | 1152.123554 | 14.349140 | 68.451542 |

| 方法 | 实例数 | 平均车辆 gap | 车辆数匹配率 | 全部距离 gap | 可比较距离实例数 | 可比较距离 gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| greedy_pair_insertion | 56 | 1.446429 | 0.160714 | 32.157417 | 9 | 16.364800 |
| greedy_pair_insertion+pair_alns | 56 | 0.482143 | 0.571429 | 11.826413 | 32 | 9.441793 |

关键增量：

- Pair ALNS 将 Li & Lim 平均车辆 gap 从 1.446429 降至 0.482143，下降 0.964286，约下降 66.67%。
- 车辆数匹配率从 16.0714% 提升到 57.1429%。
- 平均距离从 1344.880537 降至 1152.123554。
- 多启动选择中，Li & Lim 56 个 Pair ALNS 实例的 seed 分布为：`42` 选中 23 次，`11` 选中 18 次，`23` 选中 15 次。

### 4.5 Homberger 200/400 代表实例

| 方法 | 实例数 | 可行率 | 平均车辆数 | 平均距离 | 平均运行时间 |
| --- | ---: | ---: | ---: | ---: | ---: |
| greedy_insertion | 12 | 1.000000 | 22.166667 | 8633.043284 | 14.988471 |
| nearest_neighbor | 12 | 1.000000 | 30.083333 | 10821.936051 | 0.105924 |
| regret_insertion | 12 | 1.000000 | 31.250000 | 18684.434085 | 15.148746 |

| 方法 | 实例数 | 平均车辆 gap | 车辆数匹配率 | 全部距离 gap | 可比较距离实例数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| greedy_insertion | 12 | 3.750000 | 0.000000 | 54.780391 | 0 |
| nearest_neighbor | 12 | 11.666667 | 0.000000 | 99.644289 | 0 |
| regret_insertion | 12 | 12.833333 | 0.000000 | 265.690152 | 0 |

Homberger 当前结果应解释为扩展性验证，而不是大规模性能最优验证。所有代表实例均能返回可行解，说明统一解析、验证和快速构造流程可扩展到更大规模；但车辆 gap 仍然明显为正，说明大规模优化仍需后续增强。

### 4.6 消融实验

| 生成器 | 变体 | 实例数 | 可行率 | 平均车辆数 | 平均距离 | 平均违规数 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| greedy_insertion | fast_only | 3 | 1.000000 | 17.333333 | 1936.814760 | 0.000000 |
| greedy_insertion | full_ftv | 3 | 1.000000 | 17.000000 | 1663.248156 | 0.000000 |
| nearest_neighbor | fast_only | 3 | 0.333333 | 28.333333 | 2401.745584 | 0.666667 |
| nearest_neighbor | fast_repair_merge | 3 | 0.666667 | 22.333333 | 2274.241156 | 0.333333 |
| nearest_neighbor | full_ftv | 3 | 1.000000 | 20.666667 | 1994.338619 | 0.000000 |
| regret_insertion | fast_only | 3 | 1.000000 | 20.000000 | 2341.050173 | 0.000000 |
| regret_insertion | full_ftv | 3 | 1.000000 | 18.333333 | 1872.203253 | 0.000000 |

消融结果支持 FTV 架构必要性。尤其是 `nearest_neighbor`，从 `fast_only` 到 `full_ftv`，可行率从 0.333333 提升到 1.000000，平均车辆数从 28.333333 降至 20.666667，平均违规数降为 0。这说明验证反馈、修复、合并与优化闭环不是概念包装，而是对弱草案有实质改善。

## 5. 分析结论

### 5.1 已经可以支撑的结论

1. FTV-Logistics 可以在统一抽象下同时处理 VRPTW、较大规模 VRPTW 和 PDPTW。
2. 独立约束验证层有效支撑了容量、时间窗、服务时间、取送货优先关系和同车约束检查。
3. “快速生成、验证反馈、反思修复、再验证选择”的闭环能把弱草案转化为可行且更优的解。
4. Solomon 上，Advanced ALNS 多启动强化显著优于 Stage-1 和 Basic ALNS。
5. Li & Lim 上，Pair ALNS 明显降低车辆 gap，证明该架构不局限于普通 VRPTW。
6. Homberger 代表实例上，系统具备处理 200/400 规模实例的能力，但目前仍是扩展性验证，不是最终大规模最优性能验证。

### 5.2 需要谨慎表述的内容

1. 不能说本项目刷新公开 benchmark BKS。
2. 不能说当前算法是最优路径优化算法。
3. 不能把 Homberger 结果写成大规模竞争性最优结果。
4. 距离 gap 只有在车辆数匹配 BKS 时才严格可比较；车辆 gap 大于 0 时，距离 gap 只能作为辅助诊断。
5. 当前没有 GPU 训练、强化学习训练或企业真实订单验证，不能写成深度学习训练型系统。

### 5.3 推荐论文结论表述

可以使用如下结论口径：

> 实验结果表明，FTV-Logistics 在公开 Solomon、Homberger 和 Li & Lim benchmark 上实现了从快速候选生成、独立约束验证、反馈修复到反思优化选择的完整闭环。Solomon 56 个实例上，强化后的 `greedy_insertion+advanced_alns` 平均车辆 gap 为 0.446429，车辆数匹配率为 58.9286%；Li & Lim 56 个实例上，`greedy_pair_insertion+pair_alns` 平均车辆 gap 为 0.482143，车辆数匹配率为 57.1429%。这些结果说明该架构具备跨 VRPTW 与 PDPTW 的可行性、可复现性和优化增强能力，但当前仍应定位为协同决策架构验证与启发式优化增强，而非公开 benchmark 最优求解器。

## 6. 后续工作建议

| 优先级 | 方向 | 原因 |
| --- | --- | --- |
| 高 | PDPTW 专用 destroy/repair 算子 | Li & Lim 已有明显提升，但平均车辆 gap 仍为 0.482143 |
| 高 | Homberger 大规模局部搜索增强 | 当前 Homberger 是扩展性验证，gap 较大 |
| 中 | 多 seed 统计稳定性报告 | 当前多启动择优有效，但可进一步报告 seed 分布和稳定性 |
| 中 | 图表与论文结果段落统一更新 | 需要让图、表、文字结论完全对应最新 CSV |
| 低 | 更大规模 600/800/1000 实例扩展 | 适合在当前 200/400 代表实例稳定后进行 |

## 7. 当前总判断

当前项目数据、流程和结果已经能够支撑一篇以“协同决策架构”为核心的论文或阶段性研究报告。最有价值的数据证据是：

- Solomon Advanced ALNS 将平均车辆 gap 降至 0.446429。
- Li & Lim Pair ALNS 将平均车辆 gap 降至 0.482143。
- 消融实验显示完整 FTV 流程能显著提升弱构造草案的可行性和解质量。
- 三类公开 benchmark 已覆盖普通 VRPTW、大规模 VRPTW 代表实例和 PDPTW，支撑“跨问题适配”的架构主张。

当前最合适的写作定位是：提出并验证一种借鉴快速思考机制的智慧物流路径优化协同决策架构，强调可复现流程、约束可解释验证、反馈修复闭环和跨问题扩展能力。
