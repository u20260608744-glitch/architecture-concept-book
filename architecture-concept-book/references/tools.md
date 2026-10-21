# 配套工具

脚本路径：`scripts/book_tools.py`。Python 3.10+。资料清点只用标准库；清单校验需要 `jsonschema`；PDF 摘要与渲染需要 `pypdfium2`、`Pillow`。可使用环境已提供的 Python 和依赖，缺少时仅安装实际需要的包：

```sh
python -m pip install -r scripts/requirements.txt
```

以下命令从已安装 Skill 或解压的 `architecture-concept-book` 目录运行。`project` 替换成自己的工作区。

## 资料清点

```sh
python scripts/book_tools.py inventory project/inputs --hash --out project/data/inventory.json
```

输出相对路径、类型、大小、修改时间和可选 SHA256；不解释文件内容。不跟随链接，不扫描 `.git`、虚拟环境、node_modules 或 `.env` 文件。关键输入的哈希仍需写入项目清单。输出已存在时默认拒绝覆盖，明确使用 `--overwrite` 才覆盖该输出。

## 清单与算术核对

```sh
python scripts/book_tools.py check project/data/project.json --root project --out project/qa/preflight.json
python scripts/book_tools.py check project/data/project.json --root project --release --out project/qa/release-check.json
```

检查 schema、重复 ID、引用、文件/哈希、方案映射、公式、未知与整数计数。release 模式再查输入快照、被引用图版、交付文件与绑定最终哈希的检查记录。策划模板通过结构校验不代表已做出册子。

用虚构示例试运行：

```sh
python scripts/book_tools.py check assets/example/project.json --root assets/example
```

## 实际 PDF 摘要与逐页渲染

```sh
python scripts/book_tools.py pdf-audit project/output/final.pdf --render-dir project/qa/pdf-render
```

新建渲染目录，输出每页 PNG、分批接触表和 `pdf-audit.json`，记录目标 PDF 哈希、页数、尺寸、文字字符数与首行。它不会改 PDF，不会声称文字准确或版式美观。必须实际查看 PNG，并将观察另记入视觉检查。

目标渲染目录必须不存在，以免新旧页混合。很长的册子以每 24 页一张接触表分批输出。默认长边 1600px；复杂图纸可提高 `--long-edge`。字体授权、嵌入、印刷色彩和 PDF/X 不在这个小工具的自动检查范围。

## 故障与边界

源哈希变化先核实版本，不直接接受新值。路径越界将工作副本或 root 组织正确，不关闭边界检查。缺依赖时使用已有文档工具做等价检查，不声称脚本已执行。脚本没有模型解码器、地图/日照算法、设计自动生成器或 PDF 排版器。

维护者可运行仓库中的 `python -m unittest discover -s tests`。测试使用临时合成文件，不接触原项目。
