# md2html 使用说明

一个把 Markdown 文档转成 HTML 的小工具。通过一份 JSON 文件配置输入输出，
支持 4 种图片处理方式，可生成**单文件自包含**的 HTML，也可以生成引用外链资源、
或使用独立 `data.js` 的轻量方案。
```
注：本项目是一个基于deepseek文本交互的的试验型项目，项目全部文档代码均由AI生产（本段落除外），在项目的doc目录下的AI_workflow.md中详细介绍了如何通过14个步骤逐步从需求分析到项目交付的全流程工作流。本项目的意义在于：作为工具，它解决的是小场景；作为学习项目，它串联的是大知识点；作为协作示范，它展示的是完整的“从提问到交付”的路径。
```

**核心特性**

- **JSON 配置驱动**：输入、输出、标题、目录、图片模式都在一个文件里
- **4 种图片模式**：不展示 / 引用 / data.js / Base64 内嵌
- **代码高亮**：基于 Pygments，可选开关
- **目录生成**：自动从标题层级生成 TOC
- **批量模式**：一份配置处理多个 Markdown 文件
- **纯 Python**：无外部二进制依赖

---

> **📌 阅读指引**
>
> 本文档假设你的电脑**已经装好 Python 3.9+ 和项目依赖**。
>
> - 如果**环境已就绪** → 直接从 [一、快速开始](#sec-quickstart) 看起
> - 如果**还没装 Python 或不确定** → 先看 [附录 A：环境准备](#appendix-env)
> - 如果**安装过程报错** → 直接查 [附录 B：安装问题排查](#appendix-install-faq)
> - 如果**不熟悉 Markdown 语法** → 见 [附录 C：语法速查](#appendix-md-syntax)

---

<a id="sec-quickstart"></a>
## 一、快速开始

```bash
# 1. 用默认配置转换 README.md
python md2html.py config.json

# 2. 打开生成的 HTML
# dist/README.html
```

如果这条命令报错，先确认环境是否就绪：

```bash
python md2html.py config.json --help-modes
```

能打印出 `image_mode` 的 4 种说明，就说明一切正常。否则看 [附录 A](#appendix-env)。

## 二、目录结构

```
md2html-project/
├── md2html.py      # 主程序
├── config.json     # 配置文件
├── README.md       # 本说明文档
└── dist/           # 运行后生成
    ├── README.html
    └── data.js     # 模式 3 时才会出现
```

## 三、配置字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `input` | string | 输入的 Markdown 文件路径，相对 JSON 文件所在目录 |
| `output` | string | 输出的 HTML 文件路径，相对 JSON 文件所在目录 |
| `output_dir` | string | 只给目录时，输出文件名取输入文件的同名 `.html` |
| `title` | string | HTML 的 `<title>`，默认取输入文件名 |
| `toc` | bool | 是否在正文前插入目录 |
| `toc_depth` | string | 目录包含的标题层级，如 `"2-4"` |
| `highlight` | bool | 是否启用代码语法高亮 |
| `fragment` | bool | `true` 则只输出正文片段，不套完整页面 |
| `image_mode` | int | 图片处理模式，取值 `1` / `2` / `3` / `4`，详见下节 |
| `image_root` | string | 模式 2 专用，磁盘上图片的根目录 |
| `html_image_base` | string | 模式 2 专用，URL 前缀 |
| `data_js_output` | string | 模式 3 专用，`data.js` 输出路径 |
| `说明` | object | 纯文档字段，程序不读取，仅供人看 |
| `defaults` | object | 批量模式下的公共配置 |
| `jobs` | array | 批量模式下每个文件一项 |

## 四、图片模式详解

`image_mode` 决定了 HTML 里的 `<img>` 标签最终长什么样。
数字不太直观，所以 `config.json` 的 `说明.image_mode` 里写明了每个值的含义，
程序报错时也会自动把对应解释打印出来。

### 模式 1 —— 不展示图片

```json
{ "image_mode": 1 }
```

所有 `<img>` 标签被删除，适合生成纯文字版本，或屏蔽敏感图。

### 模式 2 —— 引用图片

适合把 HTML 和图片资源分开部署，要求图片集中在一个根目录下。

假设目录结构：

```
project/
├── config.json
├── docs/
│   ├── guide.md          # 里面写 ![](images/logo.png)
│   └── images/
│       └── logo.png
└── dist/
    └── guide.html        # 输出目标
```

配置：

```json
{
  "input": "docs/guide.md",
  "output": "dist/guide.html",
  "image_mode": 2,
  "image_root": "docs",
  "html_image_base": "../docs"
}
```

- `image_root`：磁盘上图片根目录，用来校验文件是否存在
- `html_image_base`：从 HTML 出发到 `image_root` 的 URL 相对路径

生成的 `<img>` 会变成 `src="../docs/images/logo.png"`，浏览器打开正常显示。

### 模式 3 —— data.js

把图片全部编码成 Base64 塞进一个独立的 `data.js`，HTML 里只留占位图和一个脚本引用。
适合图片多、又想让 HTML 保持轻量的场景。

```json
{
  "input": "README.md",
  "output": "dist/README.html",
  "image_mode": 3,
  "data_js_output": "dist/data.js"
}
```

结果：

- `dist/README.html`：`<img src="data:image/gif;base64,..." data-md-asset="images/logo.png">`
- `dist/data.js`：`window.__MD_ASSETS__ = { "images/logo.png": "data:image/png;base64,..." }`
- HTML 末尾自动追加 `<script src="data.js"></script>`

页面加载时 JS 用真实图片替换占位图。

> 注意：此模式强依赖 JavaScript。如果用户禁用 JS，图片不会显示。

### 模式 4 —— Base64 内嵌（默认）

```json
{ "image_mode": 4 }
```

所有图片直接内嵌为 `data:` URI，生成的 HTML **单文件自包含**，随便移动、发给别人都能正常打开。

代价是文件体积会膨胀约 33%，图片多时会明显变慢。

## 五、命令行选项

```
python md2html.py <config.json> [选项]

选项:
  --help-modes            打印 image_mode 的说明并退出
  --image-mode MODE       覆盖配置里的 image_mode
  --input FILE            覆盖配置里的 input（仅单任务）
  --output FILE           覆盖配置里的 output（仅单任务）
  --title TITLE           覆盖标题
  --toc                   强制开启目录
  --no-highlight          关闭代码高亮
  --fragment              只输出正文片段
```

## 六、批量模式

`jobs` 是一个数组，每一项独立处理；`defaults` 是公共默认值，可被 job 覆盖。

```json
{
  "defaults": {
    "output_dir": "dist",
    "toc": true,
    "image_mode": 4
  },
  "jobs": [
    { "input": "README.md", "output": "dist/index.html", "title": "首页" },
    { "input": "docs/guide.md", "title": "使用指南" },
    { "input": "docs/api.md", "title": "API 参考", "image_mode": 2,
      "image_root": "docs", "html_image_base": "../docs" }
  ]
}
```

## 七、自举说明

本 README 本身就是一个 Markdown 文档。用项目自带的 `config.json` 转换后，
`dist/README.html` 就是你现在可能正在看的这份说明。这既是使用示例，也是自测方式：

```bash
python md2html.py config.json
```

## 八、常见问题（使用相关）

**Q: 生成的 HTML 图片裂了？**

A: 大概率是相对路径问题。检查 `image_mode`：
- 模式 2：确认 `image_root` 和 `html_image_base` 是否配对
- 模式 3：确认 `data.js` 和 HTML 是否在同一目录或路径正确
- 模式 4：应该不会裂；如果裂了，看程序是否打印了"图片不存在"警告

**Q: 报错 `未知的 image_mode`？**

A: 用 `python md2html.py config.json --help-modes` 看可选值。数字或别名
（`none` / `reference` / `datajs` / `base64`）都可以。

**Q: 输出的 HTML 是片段，我要嵌到别的页面里？**

A: 加 `"fragment": true`，或命令行加 `--fragment`。

**Q: 中文路径 / 中文文件名会有问题吗？**

A: Python 3 原生支持 UTF-8 路径，正常情况没问题。如果 Windows 上报编码错误，
在运行前执行 `chcp 65001` 把终端切到 UTF-8。

**Q: 不想装 `pygments` 可以吗？**

A: 可以。程序检测不到时会自动关闭高亮，只保留基础样式。
用 `--no-highlight` 显式关闭效果相同。

## 九、依赖与许可

**依赖**

- **Python 3.9+**（必需）
- **markdown**（必需）
- **pygments**（可选，用于代码高亮）

**许可**

MIT

---

<a id="appendix-env"></a>
## 附录 A：环境准备

> 本节是**前置条件说明**，仅在电脑上没有 Python 3.9+ 或依赖时阅读。
> 环境已就绪的读者可跳过。

### A.1 检查是否已装 Python

打开终端（Windows 用 PowerShell 或 CMD，macOS/Linux 用 Terminal），执行：

```bash
python --version
```

或（某些系统上 Python 3 叫 `python3`）：

```bash
python3 --version
```

**期望输出**类似 `Python 3.9.x` 或更高。

- 如果**显示了 3.9 以上版本** → 跳到 [A.3 安装依赖](#appendix-env-deps)
- 如果**提示"找不到命令"或版本低于 3.9** → 继续看 A.2

> 为什么要求 3.9+？程序用到了 `dict[str, str]` 这类内置泛型语法，
> 该语法从 Python 3.9 开始支持。3.8 及以下会直接语法报错。

### A.2 安装 Python（没有或版本过低）

#### Windows

1. 打开 <https://www.python.org/downloads/windows/>，下载最新的
   **Windows installer (64-bit)**。
2. 运行安装包，**务必勾选 "Add Python to PATH"**（在第一个界面底部），
   然后点 "Install Now"。
3. 安装完成后**关闭并重新打开 PowerShell**，再执行：

   ```bash
   python --version
   ```

   应该看到版本号。如果仍然找不到，试试：

   ```bash
   py --version
   ```

   `py` 是 Windows 自带的 Python 启动器，即使 PATH 没配好也能用。

4. **记住这个差异**：后面所有命令里的 `python`，如果你的系统只认 `py`，
   就统一换成 `py`。例如 `py md2html.py config.json`。

#### macOS

推荐用 Homebrew 安装（版本更新、更好管理）：

```bash
# 如果还没装 Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Python
brew install python
```

验证：

```bash
python3 --version
```

macOS 上默认没有 `python` 命令，只有 `python3`。后文命令里的 `python`
请自行替换成 `python3`。

#### Linux（Debian/Ubuntu）

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

验证：

```bash
python3 --version
pip3 --version
```

CentOS / Fedora 用 `sudo dnf install python3 python3-pip`。

<a id="appendix-env-deps"></a>
### A.3 安装项目依赖

依赖只有两个：

| 包 | 是否必需 | 用途 |
|---|---|---|
| `markdown` | 必需 | 解析 Markdown 并输出 HTML |
| `pygments` | 可选 | 代码块语法高亮 |

#### 方式 A：使用虚拟环境（推荐）

虚拟环境能避免污染系统 Python，也避免"权限不足"报错。
只需多两条命令：

```bash
# 1. 在项目目录下创建虚拟环境
python -m venv .venv

# 2. 激活它
#    Windows PowerShell:
.venv\Scripts\Activate.ps1
#    Windows CMD:
.venv\Scripts\activate.bat
#    macOS / Linux:
source .venv/bin/activate

# 激活后命令提示符前会出现 (.venv)，说明生效了
# 3. 安装依赖
pip install markdown pygments
```

以后每次打开新终端，都要先执行激活命令，再运行程序。
不想用了直接删掉 `.venv` 目录即可。

#### 方式 B：直接装到全局（简单但有风险）

```bash
pip install markdown pygments
```

如果报 `Permission denied` 或 `Access is denied`，说明没有写系统目录的权限。
两个选择：

- 加 `--user` 装到用户目录：`pip install --user markdown pygments`
- 老老实实回到方式 A 用虚拟环境

#### 国内网络加速

pip 直连官方源可能很慢或超时，换清华镜像：

```bash
pip install markdown pygments -i https://pypi.tuna.tsinghua.edu.cn/simple
```

想永久配置：

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### A.4 验证安装

一条命令搞定：

```bash
python -c "import markdown, pygments; print('依赖正常')"
```

期望输出 `依赖正常`。

再确认程序本身可用：

```bash
python md2html.py config.json --help-modes
```

应该打印出 `image_mode` 的 4 种说明。**看到这个输出，说明环境已经就绪。**

<a id="appendix-install-faq"></a>
## 附录 B：安装问题排查

> 安装过程中遇到报错时查阅。使用过程中的问题见 [八、常见问题](#八常见问题使用相关)。

**Q: 提示 `python: command not found` / `'python' 不是内部或外部命令`？**

A: 分两种情况：
- **Windows**：先试 `py --version`。能用就把后面所有命令的 `python` 换成 `py`。
  如果 `py` 也不行，说明安装时没勾 "Add Python to PATH"，重装一次并勾上。
- **macOS / Linux**：Python 3 通常叫 `python3`，把命令换成 `python3` 和 `pip3`。

**Q: 提示 `No module named markdown`？**

A: 依赖没装，或装到了另一个 Python 环境里。确认：

```bash
# 看当前 pip 属于哪个 Python
pip --version
# 看当前 python 能不能 import
python -c "import markdown"
```

如果 `pip --version` 显示的路径和 `python` 不是一个环境，用
`python -m pip install markdown` 强制绑定到当前解释器。

**Q: 用了虚拟环境，但下次打开终端又提示找不到 markdown？**

A: 虚拟环境不会自动激活。每次新开终端都要先执行
`.venv\Scripts\Activate.ps1`（Windows）或 `source .venv/bin/activate`（macOS/Linux）。
看到提示符前有 `(.venv)` 才是激活成功。

**Q: `pip install` 卡住不动或超时？**

A: 大概率是网络问题，换国内镜像：

```bash
pip install markdown pygments -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**Q: 提示 `pip: command not found`？**

A: 用 `python -m pip` 替代 `pip`，这条命令在任何装好 Python 的环境都能用。
如果连 `python -m pip` 都不行，Linux 上需要额外装：`sudo apt install python3-pip`。

**Q: 虚拟环境激活时提示"禁止运行脚本"（Windows PowerShell）？**

A: PowerShell 默认限制执行脚本。临时放开：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

或者直接用 CMD 激活：`.venv\Scripts\activate.bat`。

<a id="appendix-md-syntax"></a>
## 附录 C：Markdown 常见语法速查

> 仅列出本项目实际支持、且日常最常用的语法。完整规范见
> [CommonMark](https://commonmark.org/help/) 与
> [GitHub Flavored Markdown](https://github.github.com/gfm/)。

### C.1 标题

用 `#` 到 `######` 表示 1 到 6 级标题，`#` 后面要有一个空格。

```markdown
# 一级标题
## 二级标题
### 三级标题
```

> **本项目相关**：`toc: true` 时，`toc_depth` 控制哪些层级的标题进入目录，
> 默认 `"2-4"` 表示只收录 2 到 4 级标题。

### C.2 段落与换行

- **段落**：连续文本之间用**空行**分隔。
- **换行**：行末加**两个空格**，或直接留一个空行另起一段。
- 不建议用 `\` 硬换行，跨平台兼容性差。

```markdown
第一段。

第二段，和上一段之间隔了一个空行。
```

### C.3 强调

| 语法 | 效果 | 说明 |
|------|------|------|
| `*斜体*` | *斜体* | 单个星号 |
| `**粗体**` | **粗体** | 两个星号 |
| `***粗斜体***` | ***粗斜体*** | 三个星号 |
| `~~删除线~~` | ~~删除线~~ | 需要 GFM 扩展 |

> 星号和下划线（`_`）都可用，但**中文场景推荐用星号**，
> 因为下划线容易和变量名混淆。

### C.4 列表

**无序列表**：用 `-`、`*` 或 `+`（同一份文档内保持一致）。

```markdown
- 苹果
- 香蕉
- 橘子
```

**有序列表**：用数字加英文句点。起始数字会自动递增，不用手动编号。

```markdown
1. 第一步
2. 第二步
3. 第三步
```

**嵌套**：子项缩进 2 或 4 个空格。

```markdown
- 前端
  - HTML
  - CSS
- 后端
  - Python
```

> **本项目相关**：`sane_lists` 扩展已启用，混用不同符号或缩进不规范时，
> 会按更严格的标准解析，避免出现意外的嵌套。

### C.5 链接与图片

**链接**：

```markdown
[显示文字](https://example.com)
[带标题的链接](https://example.com "鼠标悬停提示")
```

**图片**：在链接语法前加一个 `!`。

```markdown
![替代文字](images/logo.png)
![带标题](images/logo.png "Logo")
```

> **本项目相关**：`image_mode` 决定图片路径如何处理。写作时**建议用相对路径**
> （如 `images/logo.png`），程序才能定位到磁盘文件。用绝对 URL 的图片会原样保留。

### C.6 代码

**行内代码**：用**单个反引号**包裹。

```markdown
执行 `pip install markdown` 安装依赖。
```

**围栏代码块**：用**三个反引号**包裹，可指定语言以启用高亮。
