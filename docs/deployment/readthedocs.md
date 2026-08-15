# 文档构建与 ReadTheDocs 发布管线

本文档说明本仓库文档站（MkDocs + Material）的本地构建与 ReadTheDocs 发布方式。站点内容为
`docs/` 下的全部文档（工作簿评估、架构与 API 参考、计算教科书、安装指南），导航结构定义在
仓库根目录的 `mkdocs.yml`。

## 1. 本地构建

前置：Python ≥ 3.11（推荐 3.13）。

```bash
# 安装构建依赖（mkdocs + mkdocs-material）
pip install -r requirements.txt

# 本地预览（http://127.0.0.1:8000，自动重载）
mkdocs serve

# 静态站点构建（输出到 site/）
mkdocs build
```

也可以通过仓库自带的打包脚手架安装（`pip install -e ".[docs]"` 或
`pixi install -e docs`），见 [installation.md](../installation.md)。

## 2. 站点结构

`mkdocs.yml` 的 `nav` 与 `docs/` 目录一一对应：

| 导航分组 | 内容 |
|---|---|
| 首页 | `docs/README.md`（docs清单） |
| 工作簿评估 | `docs/01-workbook-assessment.md`（文档集 01） |
| 架构 | `docs/architecture+api-reference/` 导读 + 01（包与符号清单）+ 08（完整性检查） |
| 计算模型 | `docs/textbook/`（文档集 03，第 1–6 章 + 附录 A） |
| API参考 | `docs/architecture+api-reference/` 02–07（公共基础 / Raumdaten / Gebäude / 版本化与导出 / FastAPI / MCP） |
| 安装 | `docs/installation.md`（pixi / uv / conda / pip） |
| 发布与部署 | 本文档 + [首次上线发布清单](release-checklist.md) |

约定：`docs_dir: docs`（默认），主题 `material`，语言 `zh`，启用搜索与代码复制等特性。

## 3. ReadTheDocs 发布

1. 在 ReadTheDocs 中导入本仓库（Admin → Advanced Settings 可指定构建配置）。
2. 构建配置为 `.readthedocs.yaml`（MkDocs 构建器，Python 3.12，依赖
   `requirements.txt`）。
3. 每次推送到默认分支即触发构建；站点地址：`https://energytools-refactored.readthedocs.io/`
   （`mkdocs.yml` 中 `site_url`，发布前替换为真实域名）。
4. 发布前请将 `mkdocs.yml` 中的 `repo_name` / `repo_url` 替换为真实仓库地址。

## 4. 校验与维护

* 修改文档后运行 `mkdocs build`（或 `mkdocs serve`）验证链接与导航；文档间相对链接与
  锚点校验脚本见 `docs/architecture+api-reference/08-completeness-check.md` §5 及
  `docs-consistency-report.md`。
* 新增文档时同步更新三处：`docs/README.md`（docs清单）、`mkdocs.yml`（`nav`）、必要时
  `docs/architecture+api-reference/08-completeness-check.md` §3（清单状态表）。
