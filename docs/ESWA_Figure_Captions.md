# ESWA Figure Captions Draft

## Figure 1. Fast-slow verification-guided routing decision framework

Public benchmark instances are parsed into a unified task abstraction. The fast construction layer generates route drafts. The slow verification layer exposes capacity, time-window, service-time, duplicate-node, unserved-node, precedence, same-vehicle, and vehicle-count violations. Reflection-guided repair, route merge, route elimination, and Tree-of-Routes ALNS selection use this feedback before explanation output.

Source file: `docs/eswa_figures/Figure_1_Framework.png`.

## Figure 2. Constraint verification layer

The verification layer evaluates each candidate solution independently from the construction heuristic. It returns feasibility, vehicle count, total distance, and typed violations. This output forms the common feedback interface for repair and improvement modules.

Source file: `docs/eswa_figures/Figure_2_Verification.png`.

## Figure 3. Solomon vehicle gap comparison

Average vehicle gaps on 56 Solomon instances. Greedy insertion gives the strongest stage-1 baseline. Basic ALNS reduces the average vehicle gap from 1.464286 to 0.750000. Advanced multi-start ALNS further reduces it to 0.446429.

Source file: `docs/eswa_figures/Figure_3_Solomon_Gap.png`.

## Figure 4. Li & Lim vehicle gap comparison

Average vehicle gaps on 56 Li & Lim PDPTW instances. Pair-aware ALNS reduces the average vehicle gap from 1.446429 under greedy pair insertion to 0.482143 while preserving same-vehicle and pickup-before-delivery constraints.

Source file: `docs/eswa_figures/Figure_4_LiLim_Gap.png`.

## Figure 5. Ablation summary

The ablation study compares fast-only construction, repair plus merge, route elimination, and the full verification-guided pipeline on all 56 Solomon instances. The largest effect appears for nearest-neighbor drafts, where feasibility improves from 0.875000 to 1.000000 and average vehicle gap decreases from 8.464286 to 1.625000.

Source file: `docs/eswa_figures/Figure_5_Ablation.png`.
