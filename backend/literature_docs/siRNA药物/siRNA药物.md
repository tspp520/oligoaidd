# siRNA 药物

> 来源：知识库内网整理 · 2026-08

## 什么是 siRNA

**小干扰 RNA（small interfering RNA, siRNA）** 是约 **21–23 nt 的双链 RNA**，
利用细胞的 **RNA 干扰（RNAi）** 通路，在 **转录后水平（mRNA）** 高效、序列特异性地沉默目标基因。
siRNA 被誉为"基因沉默的金标准"，具有比 ASO 更高的效力。

## 作用机制

1. **合成双链 siRNA**（guide 链 + passenger 链）进入细胞，被装载到 RNA 诱导沉默复合体 **RISC**。
2. guide 链引导 RISC 与靶 mRNA **完全互补配对**。
3. 核心核酸酶 **AGO2** 切割并降解靶 mRNA，从而阻断蛋白表达。

## 代表药物

| 药物 | 靶点/适应症 | 里程碑 |
|---|---|---|
| **Patisiran (Onpattro)** | hATTR 淀粉样变性（TTR） | 2018 首个获批 siRNA |
| **Givosiran** | 急性肝卟啉症（ALAS1） | 2019 |
| **Lumasiran** | 原发性高草酸尿症（HAO1） | 2020 |
| **Inclisiran (Leqvio)** | 高胆固醇血症（PCSK9） | 2021 长效降脂 |
| **Vutrisiran** | hATTR | 2022 |

## 递送：从脂质体到 GalNAc

- **LNP（脂质纳米颗粒）**：早期 siRNA 采用 LNP 包裹静脉给药（如 Patisiran）。
- **GalNAc（N-乙酰半乳糖胺）偶联**：与肝细胞表面 **ASGPR** 受体结合，实现**肝靶向**高效摄取。
  - 皮下注射、高亲和、低剂量即可起效（Inclisiran 一年两针）。
  - 已成为**肝脏靶点** siRNA/ASO 的主流递送平台。

## 序列设计与 AI（与 OligoLab 的关系）

siRNA 的**反义链（guide）序列设计**直接决定沉默效率与脱靶风险。

- **功效预测**：OligoFormer 等 transformer 模型基于大量实验数据预测 19 nt guide 的沉默效率。
- **脱靶预测**：评估种子区（seed region，第 2–8 位）与转录组中非目标 mRNA 的互补风险。
- **毒性筛选**：结合 GC 含量、连续碱基、免疫刺激基序等规则过滤。
- **化学修饰**：2'-OMe / 2'-F 唾液酸修饰提升稳定性并降低免疫原性。

> 平台对应：OligoLab 平台的「脱靶与靶点预测」模块即调用 OligoFormer 完成上述
> **siRNA 功效 / 脱靶 / 毒性** 一站式评估。

## 成药挑战

1. 递送（尤其肝外组织）。
2. 双链稳定性与体内半衰期。
3. 脱靶沉默、免疫刺激与毒性评估。

> 示意图（见同目录资源）：`![RNAi 机制示意](rnai_mechanism.png)`

---
*知识库内网整理稿，用于内部研发参考。*
