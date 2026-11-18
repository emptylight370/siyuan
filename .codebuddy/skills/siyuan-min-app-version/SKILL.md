---
name: siyuan-min-app-version
description: 确定 SiYuan（思源）插件、脚本或功能的 minAppVersion 要求。通过 git 考古（pickaxe 搜索 + tag --contains）推导内核 API、工作区文件、特性的首个发布版本，合并所有依赖取最大值，并审计基线版本后的 API 变更，判断是否需要提升版本号、是否存在无法用版本号规避的版本窗口限制。当用户询问某 API/文件/特性从哪个版本开始可用、应声明什么 minAppVersion、或后续修改是否影响版本要求时使用。
---

# SiYuan minAppVersion 确认

## 目的

为依赖若干 SiYuan 能力（kernel API、工作区文件、特性）的插件/脚本/功能，确定应声明的 `minAppVersion`，并识别后续 API 变更带来的兼容性风险。

## 核心原则

- **minAppVersion = 所有依赖项"首个发布版本"的最大值**（按语义化版本数值比较，非字符串比较）
- API 契约（`kernel/apicontract/schema.json`）**不含 per-endpoint 的 since/minAppVersion 字段**，必须从 git 历史推导
- 后续变更分两类处理：
  - **收紧类**（安全加固、路径黑名单、参数校验）：不影响旧版本可用性，一般不需要提升版本号，但需确认目标路径/文件不在新黑名单内
  - **移除/封锁类**：导致旧版本可用而新版本不可用，**无法通过提升 minAppVersion 规避**，只能报告"版本窗口"限制
  - **新增必需能力类**：若工作流依赖新参数/新行为，则提升 minAppVersion

## 工作流

### 第 1 步：枚举依赖项

列出工作流用到的每一项能力：API 路由（如 `/api/file/getFile`）、读写的工作区文件（如 `data/.siyuan/indexignore`）、特性（如忽略规则解析）。遗漏依赖项会导致版本号偏低。

### 第 2 步：对每个依赖项做 git 考古，找到引入提交

```bash
# 对 API：pickaxe 搜索路由字符串（大小写不敏感复检一次变体命名）
git log --oneline --reverse -S "/api/file/getFile" -- kernel
# 对文件/特性：搜索代码中的唯一符号或路径常量
git log --oneline --reverse -S "indexignore" -- kernel
# 必要时 -i 大小写不敏感、加 --all 检查所有分支
```

- `--reverse` 取第一条命中即为引入提交；对结果用 `-i` 或不同命名变体（如 Go 驼峰 `SyncIgnore`）复核，避免遗漏更早变体
- 若首个命中是"开源提交"（`完整开源界面和内核`），说明开源时已存在，其发布版本以 tag --contains 为准
- 找到提交后用 `git show <commit> --stat` 确认改动确实引入了该能力（而非恰好包含该字符串）

### 第 3 步：提交 → 首个发布版本

使用脚本（推荐）：

```bash
python <skill目录>/scripts/first_release_tag.py <repo路径> <commit1> [commit2 ...]
```

或手动执行（注意陷阱）：

```bash
git tag --contains <commit> | Where-Object { $_ -match '^v\d+(\.\d+)*$' }
```

陷阱：
- `git tag --contains` 输出**不是按版本排序的**，且混有开发 tag（如 `electron39-dev3.6.0`、`embed-dev1`、`*-alpha*`、`*-dev*`）。必须用 `^v\d+(\.\d+)*$` 过滤正式版本，并按语义化版本数值排序后取最早一个
- 不要用 `git describe --tags --abbrev=0 <commit>` 直接下结论——它给出的是提交前最近的 tag，首个包含该提交的发布版本通常还要看 `tag --contains`

### 第 4 步：交叉核对

- 与 `docs/WORKSPACE.md`（及 zh-CN 版）核对工作区文件的位置与用途：**工作区级**（`data/.siyuan/`）与**笔记本级**（`<notebook>/.siyuan/`）文件受不同的路径守卫约束
- 与 `app/changelogs/` 的变更日志核对版本区间
- 与用户指南（`app/guide/`）核对面向用户的行为描述

### 第 5 步：合并取最大值并给出结论

- 按语义化版本数值比较（major.minor.patch 逐段比较）
- 输出格式：依赖项表格（能力 → 引入提交 → 首个发布版本 → issue 链接）+ 最终 minAppVersion + 取舍说明

### 第 6 步：审计基线版本后的变更

```bash
git log --oneline <基线版本>..HEAD -- kernel/api/file.go        # 对应 API 所在文件
git tag --contains <可疑提交> | Where-Object { $_ -match '^v\d+(\.\d+)*$' }  # 定位变更版本
```

逐项分类（收紧/移除/新增必需），并结合当前代码验证：
- **路径可达性**：检查 `kernel/util/path_guard.go` 的敏感路径黑名单（`IsForbiddenAbsPath` / `IsForbiddenDataRelPath`），确认目标文件未被封锁；注意黑名单区分工作区级与笔记本级
- **API 守卫**：读 handler 当前实现（如 `kernel/api/file.go`），确认 putFile/getFile 的角色、加密 box、插件开发目录等守卫不影响目标路径
- **错误契约**：基线版本与当前版本的错误响应格式（HTTP 状态码 + JSON code）可能不同，作为兼容性建议写进报告，但不据此提升版本号
- **正向修复**（如"写入忽略文件后避免触发同步"）记为可选增强，不算依赖

## 报告规范

1. 结论先行：直接给出 `minAppVersion: "x.y.z"` 及瓶颈来源
2. 依赖项表格 + 版本推导依据（提交 hash、日期、issue 链接）
3. 后续变更审计表：修改 → 版本 → 影响分类（无影响/需容错/版本窗口）
4. 明确报告"通过、未运行、仅静态分析"的验证边界——本结论基于 git 历史与代码阅读，未做跨版本运行时验证

## 详细案例

完整的实战案例（四个忽略文件 + 三个文件 API 的版本推导）见 [references/case-study.md](references/case-study.md)，包含每一步的实际命令与输出解读。
