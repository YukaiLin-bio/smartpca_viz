# smartpca_viz

群体遗传学 PCA（smartpca）结果可视化工具。生成 **Nature 出版级 PDF** + **交互式 HTML**。

![example](examples/warring-states/pca_plot.pdf)

## 快速开始

```bash
cd 你的数据目录
git clone https://github.com/YukaiLin-bio/smartpca_viz.git
cd smartpca_viz

# 一行命令，自动检测 evec/eval/poplist
python3 -m smartpca_viz \
  --modern-poplist modern.poplist \
  --ancient-poplist ancient.poplist \
  --project my_pca \
  --out output
```

### 数据文件准备

```
项目文件夹/
├── smartpca.evec       # smartpca 输出的特征向量（自动检测）
├── smartpca.eval       # 特征值（自动检测）
├── modern.poplist      # 现代人群（====Group==== 格式）
└── ancient.poplist     # 古代人群（====Group==== 格式）
```

poplist 格式：
```
====GroupName====
Population1
Population2
====AnotherGroup====
Population3
```

### 完整命令

```bash
python3 -m smartpca_viz \
  --evec smartpca.evec \
  --eval smartpca.eval \
  --modern-poplist modern.poplist \
  --ancient-poplist ancient.poplist \
  --project 项目名 \
  --out output
```

### 现代人群文字标签版

```bash
echo 'modern_background_labels: true' > nature.yaml
python3 -m smartpca_viz \
  --modern-poplist modern.poplist \
  --ancient-poplist ancient.poplist \
  --project my_pca \
  --config nature.yaml \
  --out output
```

## 输出

| 文件 | 说明 |
|------|------|
| `*_pca_plot.pdf` | **出版级 PDF** — Nature 风格，正方形主图 3.5"，右侧图例 |
| `*_pca_interactive.html` | **交互式 SVG 图** — 悬停查看样本、框选导出、缩放、图例拖拽 |
| `*_pca_report.pdf` | 报告（含参数、样本统计） |
| `*_pca_merged_data.csv` | 合并后的完整数据 |
| `*_run.log` | 运行日志 |

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--evec` | smartpca 输出的 .evec 文件 | `smartpca.evec` |
| `--eval` | .eval 特征值文件 | `smartpca.eval` |
| `--modern-poplist` | 现代人群 poplist（推荐） | — |
| `--ancient-poplist` | 古代人群 poplist（推荐） | — |
| `--meta` | 元数据文件 | 自动合并 poplists |
| `--config` | YAML 配置文件 | Nature 出版级默认值 |
| `--targets` | 目标样本 CSV | — |
| `--project` | 项目名称 | smartpca |
| `--out` | 输出目录 | `output` |

> `--evec`/`--eval` 默认在当前目录查找。`--meta` 省略时自动合并 `modern.poplist` + `ancient.poplist`。`--config` 省略时使用 Nature 出版级默认配置。

## 交互式 HTML 操作

| 按钮 / 控件 | 功能 |
|------|------|
| Focus targets | 聚焦到目标样本 |
| Global view | 重置视图 |
| 🔍 Zoom | 框选放大 |
| Modern as background | 现代人群切换背景文字 |
| Density heatmap | KDE 密度热力图开关 |
| 🏷 Target labels | Target 标签显示开关 |
| Target size | Target 星标大小滑块 |
| Color by | 按 group / population 着色 |
| Legend size / Point size | 图例 / 点大小缩放 |
| Labels | 显示样本/群体标签 |
| Export SVG/PNG/PDF | 导出当前布局 |
| 图例拖拽 | 每个图例块可自由拖拽 |

## 配置（config.yaml）

完整默认配置见 `output/*_config.yaml`。主要可调参数：

```yaml
# 出图风格
pdf_style: nature                    # nature / sci
pdf_nature_col_width: 3.5            # 主图宽度（英寸）

# Target
target_size_multiplier: 1.2          # 星标大小
target_color: "#D81B60"              # 星标颜色
target_outline_color: "#222222"      # 星标描边
label_targets: false                 # PDF 中显示标签

# 点
point_size: 4.5                      # 古代人群点大小

# 现代背景
modern_background_color: "#B0B8C4"
modern_background_alpha: 0.45
modern_background_labels: false      # true = 文字标签模式
```

## 依赖

```bash
pip install matplotlib scipy adjustText reportlab
```

- Python ≥ 3.10
- matplotlib（PDF 输出）
- scipy（KDE 热力图，可选）
- adjustText（标签避让，可选）
- reportlab（报告 PDF，可选）

## 示例

输出预览见 [`examples/warring-states/`](examples/warring-states/)：

- [PCA 出版级 PDF](examples/warring-states/pca_plot.pdf)
- [交互式 HTML](examples/warring-states/pca_interactive.html)
- [报告 PDF](examples/warring-states/pca_report.pdf)
