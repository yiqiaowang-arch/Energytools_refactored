# 发布清单入口

Energytools 文档站（ReadTheDocs 首次上线）的**完整发布清单**位于：

👉 [docs/deployment/release-checklist.md](docs/deployment/release-checklist.md)

该清单涵盖用户需注册/操作的事项：

- **GitHub**：创建仓库、推送、默认分支、`repo_url` 更新
- **ReadTheDocs**：注册账号、绑定 GitHub、导入项目、首次构建
- **Webhook**：确认自动重建集成、验证推送触发构建
- 域名、版本（latest/stable）、收尾核对与常见问题

站点上线后，也可在「发布与部署」板块直接访问该清单页面。

## 本地验证状态（2026-08-15）

- ✅ `pip install -r requirements.txt`（mkdocs 1.6.1 + mkdocs-material 9.7.7，Python 3.12）—— 亦已验证 pixi 环境等价
- ✅ `mkdocs build` 通过：0 错误、0 警告（`--strict` 复验通过）
- ✅ 导航三大板块（架构 / 计算模型 / API参考）+ 附录（对拍复核报告、一致性报告、发布前置清单）已注册并渲染
- ✅ `mkdocs.yml` 的 `site_url` / `repo_url` 已替换为真实地址（`energytools-refactored.readthedocs.io` / `yiqiaowang-arch/Energytools_refactored`）
- ⬜ 待办：用户在 ReadTheDocs 网页导入项目（https://readthedocs.org/dashboard/import/ ）
