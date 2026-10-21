# 项目清单约定（1.0）

普通用户只提交资料即可，AI 整理清单。小册可以用等价表格，不要求为了使用 Skill 写程序。配套 `project-manifest.schema.json` 与检查工具用于需要可重复构建的项目。

## 顶层

- `schema_version`：当前为 `1.0`。
- `phase`：`planning / production / delivery`；用于区分资料策划与最终交付。
- `project`：项目名、类型、阶段、语言和连续量显示精度。
- `sources`：实际输入文件及其权威范围。
- `schemes`：稳定方案 ID 与名称，数量不限；可为空，例如早期场地研究。
- `facts`：原文事实、计算、明确假设和未知。
- `figures`：图版、状态、来源、方案及可选相机。
- `pages`：稳定页 ID、顺序、目的、正文及事实/图版引用。
- `deliverables`：最终文件、哈希及其输入快照。
- `checks`：针对最终文件的核对记录；不能由检查脚本替代人工填写视觉结论。

## 路径与哈希

文件路径相对 `--root` 指定的工作区。默认根目录是项目清单所在目录。禁止越界 `../` 和绝对路径，便于携带。源文件分布在不同位置时，可以在工作区保留只读工作副本及原件哈希，不移动/覆盖原件。检查工具不会复制源文件。

已读取源文件、ready 图版和交付文件使用实际 SHA256。missing/unread 或 planned 图版的哈希可为 null；策划阶段允许，但不等于 ready。不得填全零假哈希。哈希变更表示相关检查须重做，不代表事实必然错误。

## 事实

`quantity_kind` 是 `continuous / count / text`。状态 `source / derived / assumption / unknown`：

- `source`：给出 source ID 与定位，数值不是从生成图估计。
- `derived`：给出公式和输入 fact ID，保存未舍入结果。
- `assumption`：明确假设来源/理由，不能伪称批准。
- `unknown`：value 为 null，locator 解释缺项；影响指定交付时 `blocking_unknown=true`。

公式支持 `sum / difference / product / ratio / percent`，均指向事实 ID。`ratio=a/b`，`percent=a/b×100`；分母为零、循环引用和未知输入不能自动变成 0。这个小工具只核对算术，不核对面积语义或法规适用性。

复杂计算保留在独立可维护脚本/表格，作为数据来源进入清单。不要把复杂分析压缩成一个无法追溯的数字。

## 图版与页面

图版 `kind`：`native / analysis / diagram / generated_visual / reference`。已就绪图版记录文件、哈希、source IDs、方案和图注。相机可记录投影、原生场景、模型哈希、视图组；清单不会验证图里真的保留了几何，仍需视觉/几何检查。

页面的 `claim` 是要解释的判断，`figure_ids / fact_ids / scheme_ids` 是依赖。`order` 是页序，不用它代替稳定 ID。plan 阶段可以保留 planned 图版；交付阶段若被页面引用则必须 ready。

## 交付与检查

每个 deliverable 保存源文件快照 `{source_id, sha256}`。最终 PDF 为主检查目标；若没有 PDF，按约定交付文件检查。content、numeric、visual、delivery 分别记录目标哈希、证据路径/哈希、状态和观察。仅在确实不适用且有说明时使用 `not_applicable`。

`check --release` 验证文件、引用、计算、快照与检查记录是否齐全。它不能证明人工实际看过，也不能证明建筑正确、合法或美观。报告中的 `mechanical_only=true` 必须保留，不能改名成“所有成品验收通过”。
