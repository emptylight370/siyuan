# 案例：忽略文件 + 文件 API 的 minAppVersion 推导

本案例是 skill 工作流的完整实战记录，场景为"一个通过 `/api/file/getFile`、`/api/file/putFile` 读写四个忽略文件、失败时用 `/api/notification/pushErrMsg` 提示的插件"。

## 依赖项与推导结果

| 依赖项 | 引入提交 | 日期 | 首个发布版本 | 关联 issue |
|---|---|---|---|---|
| `syncignore` | `f40ed985e1`（开源提交，最早出现在 kernel/model/sync.go） | 2022-05-26 | v2.0.14 | #5013 |
| `indexignore` | `0d89274eb0`（:art: Support ignore index） | 2024-01-06 | v2.12.1 | #9198 |
| `searchignore` | `2ad1662877`（:art: Support ignore search results） | 2024-01-10 | v2.12.2 | #10089 |
| `refsearchignore` | `2ad1662877`（与 searchignore 同一提交） | 2024-01-10 | v2.12.2 | #10089 |
| `/api/file/getFile` | `f40ed985e1`（开源提交） | 2022-05-26 | v2.0.14 | #5013 |
| `/api/file/putFile` | `f40ed985e1`（开源提交） | 2022-05-26 | v2.0.14 | #5013 |
| `/api/notification/pushErrMsg` | `5779dcb151`（:art: 提供消息提示推送 API 接口） | 2022-06-05 | v2.0.17 | #5102 |

**结论：`minAppVersion: "2.12.2"`**。瓶颈是 `searchignore`/`refsearchignore`（v2.12.2），高于 API 侧最晚的 pushErrMsg（v2.0.17）。

## 实际命令序列

### 1. 定位能力代码与文件位置

- 忽略文件的实际存储位置从代码确认：`kernel/sql/upsert.go` 中 `filepath.Join(util.DataDir, ".siyuan", "indexignore")` —— **工作区级** `data/.siyuan/`，而非笔记本级
- 文档交叉核对：`docs/WORKSPACE.zh-CN.md` 的 `data/.siyuan/` 清单

### 2. pickaxe 找引入提交

```bash
git log --oneline --reverse -S "indexignore" -- kernel        # -> 0d89274eb0
git log --oneline --reverse -S "refsearchignore" -- kernel    # -> 2ad1662877（与 searchignore 同提交）
git log --oneline --reverse -i -S "syncignore" -- kernel      # -i 复检，无更早变体 -> f40ed985e1
git log --oneline --reverse -S "pushErrMsg" -- kernel         # -> 5779dcb151
```

### 3. 提交 → 首个发布版本

```bash
git tag --contains 0d89274eb0 | Where-Object { $_ -match '^v\d+(\.\d+)*$' } | Select-Object -First 2
# 输出 v2.12.1、v2.12.2 —— 但输出未排序，必须数值比较后取最早
git tag --contains 2ad1662877 | ...   # -> v2.12.2
git tag --contains 5779dcb151 | ...   # -> v2.0.17
```

注意：`git describe --tags --abbrev=0 0d89274eb0` 返回 `v2.12.1-dev2`（开发 tag），不能直接作为结论。

### 4. 审计 v2.12.2 后的变更

```bash
git log --oneline v2.12.2..HEAD -- kernel/api/file.go
git log --oneline v2.12.2..HEAD -- kernel/api/notification.go
git tag --contains cc2239f969 | ...   # putFile 参数校验 #14658 -> v3.1.29
git tag --contains 5707b825db | ...   # 写入忽略文件后避免同步 #19130 -> v3.8.3
```

分类结果：

| 修改 | 版本 | 分类 | 处理 |
|---|---|---|---|
| putFile 文件名校验 #14658 | v3.1.29 | 收紧 | 忽略文件名合法，无影响 |
| 敏感路径黑名单 `IsForbiddenAbsPath` | 多版本 | 收紧 | 黑名单含笔记本级 `.siyuan/` 与 `data/.siyuan/publishAccess.json`，**不含**工作区级忽略文件，无影响（读 `kernel/util/path_guard.go` 确认） |
| 加密 box / 插件开发目录守卫 | 多版本 | 收紧 | 与 `data/.siyuan/` 无关 |
| getFile symlink 解析防护 | v3.8.2 | 收紧 | 正常路径不受影响 |
| 错误模型/契约迁移 #19378 | 多版本 | 行为变化 | 错误响应格式变化，插件需双容错解析；不构成版本要求 |
| 写入忽略文件后避免同步 #19130 | v3.8.3 | 正向修复 | 记为可选增强 |

**最终判定：无需提升版本号，维持 2.12.2。**

## 可复用的判断要点

1. **依赖方向决定结论方向**：后续"收紧"类修改破坏的是新版本对旧行为的容忍度，无法用 minAppVersion 规避；若未来黑名单波及目标文件，应报告版本窗口限制并建议替代方案（专用 API 或手动编辑）
2. **文件位置决定守卫约束**：同一 `.siyuan` 目录，工作区级 `data/.siyuan/` 与笔记本级 `<notebook>/.siyuan/` 在路径守卫中的待遇完全不同
3. **版本比较必须数值化**：`v3.8.10 < v3.8.3` 按字符串排序是错的
4. **pickaxe 要防变体遗漏**：对命名做大小写不敏感与驼峰变体复检（如 `syncignore` vs `SyncIgnore`）
5. **开源提交是特殊锚点**：命中"完整开源界面和内核"意味着能力在开源时已存在，发布版本以 tag --contains 为准，且该提交可能有更早的私有历史
