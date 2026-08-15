# 发布清单（ReadTheDocs 首次上线）

> 状态图例：`[ ]` 待办 · `[x]` 已完成
> 本文档面向**首次上线**。之后日常发布只需推送到 GitHub 默认分支，RTD 会自动重建。
> 仓库根目录的 `RELEASE_CHECKLIST.md` 是本文档的入口指针。

---

## 0. 前提：本仓库内容就绪

- [ ] 代码审查通过：`mkdocs.yml`、`.readthedocs.yaml`、`requirements.txt` 已确认
- [ ] 本地构建通过：`mkdocs build` 无错误（见 README「本地构建」）
- [ ] 导航三大板块（架构 / 计算模型 / API参考）的页面均已在 `mkdocs.yml` 的 `nav` 中注册
- [ ] `mkdocs.yml` 中的 `site_url`、`repo_url` 已改为真实地址（见第 1、3 步）

---

## 1. GitHub 仓库（需用户注册/创建）

- [ ] 在 GitHub 创建仓库，例如 `energytools/energytools`
      （公开仓库无需额外授权；私有仓库后续需授予 RTD 读取权限）
- [ ] 将本仓库推送到 GitHub：

      ```bash
      git remote add origin https://github.com/<org>/<repo>.git
      git push -u origin main
      ```

- [ ] 将默认分支设为 `main`（Settings → Branches）
- [ ] 更新 `mkdocs.yml`：`repo_url` → 真实仓库地址
- [ ] 建议：在 GitHub 仓库 About 中开启 **Website** 指向 `https://energytools.readthedocs.io/`

---

## 2. ReadTheDocs 账号（需用户注册）

- [ ] 注册 ReadTheDocs 账号：<https://readthedocs.org/accounts/signup/>
      （推荐直接使用 **GitHub 账号登录**，便于后续绑定与 webhook 管理）
- [ ] 绑定 GitHub：Settings → Connected Services → **Connect GitHub account**
      （用于授权导入仓库；按需选择授予全部仓库或仅指定组织的权限）

---

## 3. 导入项目（账号绑定完成后由用户操作）

- [ ] 登录 RTD → **Import a Project** → 选择 GitHub 仓库
- [ ] RTD 自动识别 `.readthedocs.yaml`（无需手动填写构建配置）
- [ ] 触发首次构建：Projects → `energytools` → **Builds** → Build version: `latest`
- [ ] 构建成功，站点地址：`https://energytools.readthedocs.io/`
- [ ] 更新 `mkdocs.yml`：`site_url` → 实际站点地址（影响搜索与 SEO）

> 若导入时未自动创建集成，需手动检查（见第 4 步）。

---

## 4. Webhook（自动重建，需用户确认）

- [ ] RTD 项目 → **Admin → Integrations**，确认存在
      **GitHub incoming webhook**（导入项目时通常自动创建）
- [ ] 在 GitHub 仓库 **Settings → Webhooks** 中确认该 webhook 存在且最近一次
      **delivery 状态为绿色（成功）**
- [ ] 验证：向 `main` 推送一次提交，确认 RTD 自动触发构建
      （RTD 项目 → Builds 出现新构建记录）

> 若 webhook 缺失：在 RTD 的 Integrations 页手动 **Add integration → GitHub incoming webhook**，
> 并把生成的 URL 粘贴到 GitHub 仓库的 Webhooks 中。

---

## 5. 域名与外观（可选，需用户操作）

- [ ] 自定义域名：RTD 项目 → **Admin → Domains** 添加（如 `docs.energytools.example.com`），
      并按提示在 DNS 处添加 CNAME 记录
- [ ] 本站点不依赖 GitHub Pages，GitHub 仓库无需 Pages 配置

---

## 6. 版本与正式发布（首次发布后维护）

- [ ] 打 release 标签：GitHub → Releases → `v1.0.0`（或按语义化版本规则）
- [ ] RTD 项目 → **Versions** → 将 `v1.0.0` 设为 **Active** 并标记为 **stable**
- [ ] 对外正式链接统一使用 `https://energytools.readthedocs.io/en/stable/`

---

## 7. 收尾核对

- [ ] 站点三大板块可访问：架构 / 计算模型 / API参考
- [ ] 搜索功能正常（Material 主题内置）
- [ ] 提交本清单更新：将已完成的条目打勾后推送

---

## 常见问题

| 现象 | 处理 |
| ---- | ---- |
| 构建失败：`mkdocs not found` | 检查 `requirements.txt` 是否被 `.readthedocs.yaml` 引用且已提交 |
| 构建失败：YAML 语法错误 | 本地 `mkdocs build` 先通过再推送 |
| 推送后不自动构建 | 见第 4 步检查 webhook 与 GitHub 集成授权 |
| 私有仓库无法导入 | 绑定 GitHub 时需授予对应组织/仓库的读取权限 |
| 想改站点子路径 | RTD 项目 → Admin → Advanced settings → `Default branch` 等 |

---

*维护人：项目组 · 生成日期：2025（首次上线时更新）*
