# smartpca_viz v2 → v3 代码优化计划

## 现状评估

| 指标 | 数据 |
|------|------|
| 单文件行数 | 1656 行 |
| Python 函数 | 41 个（全部 module-level） |
| 错误处理占比 | ~5%（79/1656） |
| JS 代码 | 全部内联在 HTML_TEMPLATE 字符串中，66 个函数/事件 |
| HTML 模板 | 单行 raw string，JS 压缩在一行 |
| 测试覆盖 | 仅 Python 端 9 个测试 |
| 渲染路径 | SVG（交互）+ Canvas（导出）+ Matplotlib（PDF），三套独立逻辑 |

---

## Phase 1 — 代码结构与模块化（稳定性基础）

**目标**：拆分单文件，建立清晰模块边界

### 1.1 模块拆分

```
smartpca_viz/
├── __init__.py              # 公共导出 + 版本号
├── __main__.py              # CLI 入口（python -m smartpca_viz）
├── cli.py                   # argparse + main() 编排逻辑
├── config.py                # 配置加载、验证、默认值、YAML 写入
├── parser.py                # evec / eval / metadata / targets 解析
├── model.py                 # 数据模型：Sample, Metadata, Config 等 dataclass
├── render_html.py           # HTML + JS 生成（外置 .html 模板）
├── render_pdf.py            # PDF / reportlab 渲染
├── render_matplotlib.py     # matplotlib 渲染（备用 PDF）
├── exporter.py              # CSV 导出、README、log 写入
├── kde_heatmap.py           # KDE 热力图（已有）
├── templates/
│   ├── base.html            # HTML 骨架
│   ├── styles.css           # CSS
│   └── app.js               # 交互 JS（可维护的 .js 文件）
└── tests/
    ├── test_parser.py
    ├── test_config.py
    ├── test_render_html.py
    └── test_integration.py
```

### 1.2 数据模型化

```python
@dataclass
class Sample:
    sample_id: str
    population: str
    group: str
    pcs: list[float]
    is_target: bool = False
    target_label: str = ""
    is_modern_background: bool = False

@dataclass
class PCAConfig:
    modern_background: bool = False
    modern_groups: list[str] = field(default_factory=list)
    modern_background_alpha: float = 0.35
    modern_background_size_multiplier: float = 3.0
    target_groups: list[str] = field(default_factory=lambda: ["Target"])
    color_by: str = "group"
    point_size: float = 5.0
    # ... 所有参数
```

### 1.3 HTML/JS 外置

```python
# render_html.py
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader("templates/"))
template = env.get_template("base.html")
html = template.render(payload=payload, config=config)
```

**原因**：当前 JS 是单行 11KB 字符串，改一个标点要 re-patch 整行。外置后可用 ESLint、Prettier 格式化，浏览器 DevTools source map 可调试。

### 1.4 可复用 API

```python
from smartpca_viz import PCAVisualizer

viz = PCAVisualizer(
    evec="smartpca.evec",
    meta="poplist.txt",
    config="config.yaml",
)
viz.run(output_dir="./output", project="MyProject")
# 或分步调用：
data = viz.parse()
viz.render_html(data)
viz.render_pdf(data)
viz.export_csv(data)
```

---

## Phase 2 — 输入稳定性（生产级健壮）

**目标**：任何异常输入给出明确错误，不崩溃

### 2.1 输入校验清单

| 校验项 | 当前状态 | 改进方案 |
|--------|---------|---------|
| evec 文件不存在 | 直接报错 | 检查路径 + 建议附近文件 |
| evec 空文件 | 崩溃 | 提前校验行数/字段数 |
| evec PC 列数不一致 | 无校验 | 逐行检查 PC 列数一致性 |
| evec 重复 sample_id | 有警告 | 可选去重策略（保留/报错） |
| poplist 格式错误 | 无校验 | 检测 `====` 配对、空 group、空行 |
| poplist population 名不匹配 evec | 标记 Unknown | 报告具体不匹配列表 |
| targets 文件格式错误 | 脆弱 split | CSV/纯文本自动检测 |
| config.yaml 语法错误 | 直接报错 | 给出行号 + 附近上下文 |
| config 缺少必填字段 | 使用默认值 | 同时输出警告 |
| 大文件（>1万样本） | 无处理 | 分段读取 + 进度条 |
| scipy 未安装 + 启用 KDE | 崩溃 | 降级 + 提示安装 |
| matplotlib 未安装 | 崩溃 | 降级跳过 PDF + 提示 |

### 2.2 错误信息改进

```
# 当前
WARNING: Missing metadata for population XXX; assigned group Unknown

# 改进
WARNING [parser.metadata]: Population "XXX" (line 42 of poplist.txt) not found in evec.
  → Check: does poplist.txt entry match the population column in smartpca.evec?
  → Suggestion: "Ming_Dynasty_Monk" in evec vs "monk" in poplist — did you mean "Ming_Dynasty_Monk"?
```

### 2.3 降级策略

```python
# 当前：import 失败直接崩溃
from scipy import stats

# 改进：运行时检测，优雅降级
try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

def compute_kde(...):
    if not HAS_SCIPY:
        logger.warning("scipy not installed, skipping KDE heatmap")
        return None
    ...
```

---

## Phase 3 — HTML 交互深度优化

**目标**：流畅、直觉、可发现

### 3.1 渲染性能

| 优化项 | 当前 | 改进 |
|--------|------|------|
| 渲染引擎 | SVG（纯 DOM） | SVG + Canvas 混合 / WebGL 可选 |
| 大数据集 | 无优化 | 10K+ 点自动降级到 Canvas |
| 缩放时 | 全量重绘 | 缓存已渲染点，仅更新 transform |
| 动画 | 无 | 缩放/切换时平滑过渡（requestAnimationFrame） |

### 3.2 交互增强

```
✅ 已有：
  - 框选样本
  - 图例拖拽
  - 悬停提示
  - Zoom 模式
  - Color by 切换

🆕 待加：
  - 鼠标滚轮缩放（以鼠标位置为中心）
  - 拖拽平移（按住空格或中键）
  - 双击 zoom out
  - Shift+框选 = 添加到选中
  - Ctrl+Z / Cmd+Z 撤销上一次 zoom/select
  - 右键菜单：Copy sample ID、Exclude from view
  - 搜索支持模糊匹配（当前只有精确匹配）
  - 选中样本统计：N、均值、方差
  - 导出选中样本时支持更多格式（BED、PLINK .ped）
```

### 3.3 UI 改进

```
🆕 待加：
  - 状态栏：显示当前 view 范围、选中数、总点数
  - 快捷键面板（按 ? 显示）
  - 颜色主题切换（Light/Dark/High Contrast）
  - 图例搜索/过滤
  - 导出时可选分辨率
  - 手机/平板触控适配（双指缩放）
  - 加载进度条（大文件）
  - Undo/Redo 操作历史
  - 迷你地图（MiniMap）：右上角显示全局视图缩略图，指示当前 zoom 位置
```

### 3.4 JS 代码质量

```
当前问题：
  - 66 个函数全部在全局作用域
  - 所有变量（state, payload, svg 等）都是全局 mutable 状态
  - 没有错误处理（一个异常就白屏）
  - 无法单元测试

改进：
  - 使用 ES6 class：class PCAPlot { constructor(payload) { ... } }
  - 模块化：import { draw, bind, marker } from './renderer.js'
  - 错误边界：try-catch 包裹事件 handler，错误时显示 toast
  - 可在 Node.js 中测试核心逻辑
  - 代码体积：从 ~11KB minified → ~30KB 可读源码 → ~8KB gzipped
```

---

## Phase 4 — 测试与 CI

**目标**：改动不担心 break

### 4.1 Python 测试

| 测试套件 | 用例数 | 覆盖场景 |
|---------|--------|---------|
| 当前测试 | 9 | 基本解析、config |
| 目标 | 50+ | 所有 parser 变体、config 验证、降级路径、大文件、边界值 |

### 4.2 JS 测试

```
- 使用 Vitest 或 Jest
- 测试 draw() 输出 SVG 结构是否正确
- 测试 zoom/invSx/invSy 数学正确性
- 测试 mutedColor HSL 算法
- 测试 legend 构建逻辑
- 在 headless 浏览器中截图对比 (Playwright)
```

### 4.3 集成测试

```
- 端到端测试：输入 evec → 输出 HTML → 打开浏览器验证
- 截图 diff：确保 UI 改动不会意外破坏布局
- GitHub Actions：每次 push 自动跑测试
```

---

## 实施优先级与工作量估算

| 阶段 | 内容 | 预估工时 | 优先级 |
|------|------|---------|--------|
| **P1** | 模块拆分（parser/config/model 分离） | 2-3h | 🔴 高 |
| **P1** | 输入校验强化 + 错误信息改进 | 2h | 🔴 高 |
| **P1** | scipy/matplotlib 降级策略 | 1h | 🔴 高 |
| **P2** | HTML/JS 外置 + 模板化 | 3-4h | 🟡 中 |
| **P2** | JS 类重构 + 错误边界 | 3h | 🟡 中 |
| **P2** | JS 测试框架 + 核心函数测试 | 2h | 🟡 中 |
| **P3** | 滚轮缩放 + 拖拽平移 | 2h | 🟢 低 |
| **P3** | Python API 封装 | 2h | 🟢 低 |
| **P3** | 迷你地图 | 3h | 🟢 低 |
| **P4** | 触控适配 | 2h | ⚪ 可选 |
| **P4** | 快捷键系统 | 1h | ⚪ 可选 |
| **P4** | 颜色主题 | 1h | ⚪ 可选 |

**总计**：约 22-26 小时核心工作，可分布在 2-3 周内完成。

---

## 关键设计决策

### 1. HTML 模板方案

```
推荐：Jinja2 模板引擎（已有依赖因为 reportlab 需 PIL）
备选：string.Template（stdlib，零依赖，但功能弱）
```

### 2. JS 构建方案

```
推荐：无构建工具（No build），直接写 ES6 modules
原因：无需 npm/webpack，浏览器原生支持 import
```

### 3. 大文件策略

```
< 5000 点 → SVG（精确、可交互）
5000-20000 点 → Canvas（流畅，导出时转 SVG）
> 20000 点 → WebGL / Canvas 降采样
```

---

## 下一步

如果你确认方向，我建议从 **P1 模块拆分** 开始，先把 parser/config/model 分离出来，这是所有后续优化的基础。要不要开始做？
