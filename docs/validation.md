# v1.0.0 验证范围

## 已实际执行

- Skill Creator 的结构与 frontmatter 校验。
- Python 语法编译。
- 14 个隔离的行为测试：单方案与多方案、模板不冒充成品、未知不变零、整数计数、算式与零分母、循环引用、重复 ID、缺失引用、路径边界、源哈希变化、表现图不作计量依据、最终文件及输入快照/视觉证据失效、清点与拒绝覆盖。
- 合成项目清单核对：1 方案、7 事实、2 个派生公式、1 图版、2 页；停车保持 unknown。
- 实际长册 PDF 的只读摘要与逐页渲染：37 页，原文件哈希前后不变。实际项目 PDF 和渲染图仅用于本地核对，不随仓库公开。
- Markdown 相对链接、包内文件、未完成脚手架和机器路径/敏感素材扫描。

## 检查的边界

这些检查说明说明书结构与辅助脚本能处理所列场景，不表示已经自动生成所有类型项目的高质量册子。没有声称完成所有 CAD/BIM 格式的解析、法定面积审批、所有司法地区的法规适用性、所有字体/印刷规范或所有平台的软件兼容性测试。

本次脚本行为测试在 Windows / Python 3.13 执行；macOS、Linux 和其他 Python 版本未实机验证。缺少依赖时按工具说明安装，不依赖维护者机器上的私有路径。

脚本不能证明人已看过图片，也不能自动验收设计品质。最终册子仍要按 Skill 的流程实际查看，记录真实观察。

## 复现

从仓库根目录执行，依赖可以安装在虚拟环境：

```sh
python -m pip install -r architecture-concept-book/scripts/requirements.txt
python -m unittest discover -s tests -v
python architecture-concept-book/scripts/book_tools.py check architecture-concept-book/assets/example/project.json --root architecture-concept-book/assets/example
```

PDF 渲染命令见 [工具说明](../architecture-concept-book/references/tools.md)。仓库没有附带实际客户资料；可用自己有权使用的 PDF 验证渲染功能。


## v1.1.0 增量验证

新增按类型的详细输入指南、REF读取/转译与参考提交表、场地Skill交接流程，以及两张原创PNG预览和对应SVG图源。已重跑上述14项行为测试、合成清单核对及Skill结构校验；脚本行为未改动。

两张预览已实际打开检查字体、对齐、主图与说明；它们是虚构排版/流程演示，不是GIGIRI原件。发布前核对新增本地链接、JSON、UTF-8/LF与素材范围，并从提交生成ZIP、全新解压复核。公开仓库、预览和下载包另做匿名访问及字节一致性验证。

新场地Skill的独立验证边界见其公开仓库，不因配合使用而自动宣称已经完成真实测绘、模型或原生软件格式测试。原有37页PDF的只读验证属于v1.0.0编写记录，本次没有把历史检查当作任何新项目成品验收。
