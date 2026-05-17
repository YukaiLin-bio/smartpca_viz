# smartpca_viz v2 — PCA可视化工具包

群体遗传学 PCA（smartpca）结果可视化工具。
麻雀原创，持续迭代中。

## 功能

- **交互式 HTML**：SVG 绘图，图例可拖拽，悬停查看样本信息
- **出版级 PDF**：干净的白底图，适合论文投稿
- **PDF 报告**：含参数、样本统计、警告等元信息
- **CSV 导出**：选中样本 / 全部数据的导出
- 🎯 **Target 标记**：星标高亮目标样本
- 🌍 **Modern as background**：现代人群以 group 名称文字标记，低可视度颜色（HSL 降饱和提亮度），图例 `(bg)` 标注
- 🔥 **Density heatmap**：KDE 密度热力图叠加
- 🔍 **Zoom 模式**：框选放大，可连续缩放
- 🎨 **颜色自定义**：color_by group/population，可配置所有参数

## 使用

```bash
python smartpca_viz.py --evec smartpca.evec --eval smartpca.eval --meta poplist.txt --config config.yaml --out output --project MyProject
```

### 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--evec` | ✅ | smartpca 输出的 .evec 文件 |
| `--meta` | ✅ | 元数据（poplist/csv 格式），定义 population→group 映射 |
| `--config` | ❌ | YAML 配置文件 |
| `--targets` | ❌ | 目标样本列表文件 |
| `--eval` | ❌ | .eval 特征值文件（自动查找） |
| `--project` | ❌ | 项目名称（默认 smartpca） |
| `--out` | ❌ | 输出目录（默认 smartpca_viz_output） |

### 元数据格式（poplist）

```
====GroupName====
Population1
Population2
====AnotherGroup====
Population3
```

### 配置文件（config.yaml）

```yaml
modern_background: true
modern_groups:
  - Han
  - Austronesian
  - Austroasiatic
  - Hmong-Mien
  - Japanese-Korean
  - Mongolian
  - Tai-Kadai
  - Tibetan-Burman
modern_background_alpha: 0.35
modern_background_size_multiplier: 3.0
modern_background_show_legend: false
target_groups:
  - Target
color_by: group
point_size: 5.0
pdf_style: sci
```

## 交互式 HTML 操作

| 按钮 | 功能 |
|------|------|
| Focus targets | 聚焦到目标样本 |
| Global view | 重置视图 |
| 🔍 Zoom | 切换放大模式，拖拽框选区域放大 |
| Modern as background | 现代人群切换为背景文字 |
| Density heatmap | 切换 KDE 密度热力图 |
| Color by | 按 group 或 population 着色 |
| Plot size / Point size | 图幅 / 点大小缩放 |
| Labels | 显示样本/群体标签 |
| Export SVG/PNG/PDF | 导出当前布局 |
| 图例拖拽 | 每个图例块可自由拖拽位置 |

## 输出文件

| 文件 | 说明 |
|------|------|
| `*_pca_interactive.html` | 交互式 HTML |
| `*_pca_plot.pdf` | 出版级 PDF 图 |
| `*_pca_report.pdf` | PDF 报告 |
| `*_pca_merged_data.csv` | 合并后的完整数据 |
| `*_config.yaml` | 本次运行配置 |
| `*_README.txt` | 运行说明 |
| `*_run.log` | 运行日志 |

## 依赖

- Python ≥ 3.10
- scipy（可选，用于 KDE 热力图）
- matplotlib（PDF 输出）
- reportlab（报告 PDF）

## 版本

v2 — 2026-05-17
- Modern as background 升级：各 group 独立 muted 颜色，文字标记
- 🔍 Zoom 模式
- Density heatmap
- 框选样本导出
- 图例拖拽 + 导出
