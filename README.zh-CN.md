# Reviewed Git Publish

> 让 AI Agent 像一位谨慎的代码审查者一样整理 Git 变更，并且只提交你真正批准的内容。

<p align="right">
  <a href="./README.md">English</a> |
  <a href="./README.zh-CN.md">简体中文</a>
</p>

Reviewed Git Publish 是一个可复用的 Agent Skill，面向已经在本地开发完成、
希望让 Agent 帮忙检查改动、生成高质量 Git 历史并正常推送的开发者。

你可以直接说：

> 检查一下当前改动，按功能合理拆分 Commit；展示文件清单和提交说明，我确认后再推送。

Agent 负责理解代码差异、组织提交和解释原因；本 Skill 自带的 Python
执行器负责冻结具体 Git 状态、校验用户批准的计划，并按**精确文件范围**执行。
这里的批准是本地开发流程中的显式确认，**不是独立认证的人类签名**。

## 快速安装

在目标项目目录使用 [Skills CLI](https://github.com/vercel-labs/skills) 安装（需要 Node.js 22.20+）：

```bash
npx skills add Homeuh/reviewed-git-publish
```

也可以**直接让编程 Agent** 从
[GitHub](https://github.com/Homeuh/reviewed-git-publish)
安装，要求它先检查脚本、确认目标安装路径。

指定 Agent、全局安装、ZIP 安装及版本更新请参阅下方的
[安装与使用](#安装与使用)或[安装指南](references/installation.md)。

## 能做什么

| 能力 | 表现 |
|---|---|
| **Git 改动审核** | 审阅已暂存、未暂存、未跟踪文件，识别敏感或无关改动 |
| **文件级原子提交** | 按功能把完整文件组织成一笔或多笔有意义的提交；不追求拆得越碎越好 |
| **高质量 Commit** | Conventional Commits 英文 Subject，复杂改动补充 Body / Footer，并提供中文审阅说明 |
| **精确包含与排除** | 展示每一笔提交的完整文件路径和不应提交的变更；保护工作区中的其他文件 |
| **冻结计划与审批** | 固定 HEAD、变更内容、Git index、远端目标、完整消息等信息并计算 SHA-256 |
| **Git Hook 兼容预检查** | 按每笔候选提交依次执行提交前 Hook，整轮结束后统一验证 |
| **需要时重新审批** | Hook 产生可接受的格式化变更时停止，要求重新审核与新的审批指纹，绝不静默重试 |
| **正常推送和核实** | 使用用户批准的目标执行普通 push，保留 `pre-push`，核对最终远端 OID |
| **故障诊断** | 通过只读 `reconcile` 观察部分成功、远端差异和不确定状态 |

## 如何工作

```text
开发者自然语言请求
      │
      ▼
Agent 读取 Git 状态和代码 Diff
      │
      ▼
按功能提出提交分组、完整 Commit Message、排除文件
      │
      ▼
执行器冻结准确文件范围、index、分支、远端 → SHA-256
      │
      ▼
等待开发者审核批准（WAITING_FOR_USER）
      │
      ├─ 不批准 / 计划有误 → 修改计划并重新冻结
      │
      ▼
漂移检查与约定的代码验证
      │
      ▼
隔离候选 Git Tree + 每笔 Commit 的 Hook 预检查
      │
      ├─ Hook 失败或产生新内容 → 停止；必要时重新冻结与审批
      │
      ▼
一次更新本地分支，创建已批准的提交链
      │
      ▼
如果批准了 push：正常推送 + 远端 OID 确认
```

这个过程将两种工作分开：**Agent 的语义判断**决定什么内容应该组成一笔提交，
**Git 执行器的确定性校验**决定实际允许提交什么。阅读
[整体架构](references/architecture.md) 和
[完整工作流](references/workflow.md) 可以了解每个阶段的职责。

## 提交计划是什么样的

一次改动可以被整理为：

```text
Commit 1
  feat(web): improve workspace navigation

  Consolidate route-selection logic without changing public behavior.

  文件：src/navigation.ts
  中文说明：整理导航逻辑，保持现有路由行为

Commit 2
  fix(api): handle expired sessions

  Return a controlled error for requests with an expired session.

  文件：src/api.ts
  中文说明：修复会话过期时的接口处理

排除：.env.local（包含本地环境配置，不应提交）
目标：origin/main
状态：WAITING_FOR_USER
指纹：<真正冻结计划中的 64 位 SHA-256>
```

对很简单的修改，一行 Commit Subject 就足够，不强制写 Body。
同一个文件中不同 Hunk 的自动拆分不在支持范围内：有意义的说明和可追踪的
Git 历史比过度拆分更重要。

## 安装与使用

**Skill 运行环境：** Python 3.9+、支持 `--pathspec-from-file` 的 Git。
无需第三方 Python 依赖，也不依赖特定前端或后端框架。

### 推荐：使用 Skills CLI 安装

此安装方式需要 Node.js 22.20+。在**目标项目目录**执行：

```bash
npx skills add Homeuh/reviewed-git-publish
```

按提示选择 Agent 和安装范围，也可以指定 Agent 或全局安装：

```bash
npx skills add Homeuh/reviewed-git-publish -a codex
npx skills add Homeuh/reviewed-git-publish -a antigravity
npx skills add Homeuh/reviewed-git-publish -g
```

安装前仅查看可发现的 Skill：

```bash
npx skills add Homeuh/reviewed-git-publish --list
```

Skills CLI 从 GitHub 仓库分支获取内容，**不是**从 GitHub Release
附件安装；请先检查源码和目标安装路径。后续可使用
`npx skills check`、`npx skills update` 检查和更新。

### 直接让编程 Agent 帮你安装

把这段话发给拥有终端权限的 Agent：

> 请从 https://github.com/Homeuh/reviewed-git-publish
> 将 `reviewed-git-publish` Skill 安装到当前项目。
> 安装前先检查 `SKILL.md` 和可执行脚本。
> 如果有 Node.js，优先使用
> `npx skills add Homeuh/reviewed-git-publish --skill reviewed-git-publish`；
> 否则按仓库的 Release ZIP/Python 安装说明操作。
> 确认安装目录；如果已安装同名 Skill，覆盖前先征求我的同意。
> 安装过程中不要执行 Git 发布器、提交或推送。

这种方式要求 Agent 能操作终端，且用户允许安装软件；
仅粘贴 GitHub 地址并不代表 Skill 已自动安装。

### 备用：通过 Release ZIP 安装

下载官方 Release ZIP，解压后进入 `reviewed-git-publish/` 目录：

```bash
python3 -B scripts/manage_skill.py install \
  --target /path/to/your-repo/.agents/skills

python3 -B scripts/manage_skill.py status \
  --target /path/to/your-repo/.agents/skills
```

更新到新版 ZIP：

```bash
python3 -B scripts/manage_skill.py update \
  --target /path/to/your-repo/.agents/skills \
  --source /path/to/new-reviewed-git-publish.zip
```

Python 安装器不会自动暂存、提交或推送 Git 变更，升级时会保留旧版本备份。

### 安装完成后

在支持该 Skill 的 Agent 中发起代码审核。Agent 应展示真正的
SHA-256 计划指纹；**审核清楚提交内容之后**，再明确发送：

```text
COMMIT PLAN APPROVED <实际显示的 64 位指纹>
```

详见 [安装与维护](references/installation.md)。

## Skill 内部如何组织

```text
reviewed-git-publish/
├── SKILL.md                       Agent 必须遵守的行为和审批边界
├── README.md                      默认英文产品介绍
├── README.zh-CN.md                简体中文产品介绍
├── LICENSE                        MIT 开源许可证
├── agents/openai.yaml             Agent 元信息
├── references/                    当前有效的按领域划分的文档
│   ├── workflow.md
│   ├── commit-conventions.md
│   ├── hooks.md
│   ├── safety.md
│   ├── architecture.md
│   ├── installation.md
│   └── troubleshooting.md
├── scripts/
│   ├── reviewed_git_publish.py    inspect / freeze / verify / execute / reconcile
│   ├── manage_skill.py            install / update / status
│   └── rpg/                       Git 状态、计划、审批、验证、Hook 和执行模块
├── schemas/                       计划及可选策略的 JSON 输入规范
└── assets/                        通用策略示例
```

分发 Skill 只包含**正常使用必需的材料**。开发仓库另行保存自动化测试、
Agent 评估、打包工具、研发过程归档和实验性发布原型，不与用户安装包混合。
模块接口和数据边界见 [架构说明](references/architecture.md)。

## 安全边界与已知限制

- `inspect`、`freeze`、`verify` 在审批前只读；计划必须放在目标
  Git 工作区以外。未经批准不暂存、提交或推送。
- 审批覆盖完整计划而非只覆盖 Commit 标题。任何内容或远端目标漂移，
  都必须停止并重新获取批准。
- 同一文件既暂存又存在额外未暂存改动、Git 冲突、submodule、
  detached HEAD 等特殊状态暂不支持自动发布。
- Git Hook 在**临时检出目录**进行兼容性预检查，不能保证所有依赖
  `node_modules`、Husky 或自定义环境的 Hook 都能原样运行；
  `post-commit` 不执行，`pre-push` 正常执行。
- SHA-256 保护的是**获批计划与待执行状态的一致性**；Agent 若拥有无约束的
  shell 和 Git 凭证，仍可能绕过这个本地工具。因此不能把本地批准当成
  独立身份认证或生产级权限隔离。
- 不进行自动 retry、force push、reset、amend、rebase 或历史重写；
  异常状态由使用者查看后重新发起计划。

完整限制见 [安全说明](references/safety.md) 与
[故障排查](references/troubleshooting.md)。

## 开源许可证

本项目使用 [MIT License](LICENSE) 开源，版权归属 Copyright (c) 2026 Homeuh。

## 文档导航

- [工作流与命令](references/workflow.md)
- [Commit 规范](references/commit-conventions.md)
- [Git Hook 与重新审批](references/hooks.md)
- [安全约束](references/safety.md)
- [架构与目录职责](references/architecture.md)
- [安装与更新](references/installation.md)
- [故障排查](references/troubleshooting.md)
