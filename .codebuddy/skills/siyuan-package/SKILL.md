---
name: siyuan-package
description: SiYuan项目构建和打包流程。当用户需要构建SiYuan内核、前端或打包安装包时使用此skill。支持Windows、Linux和macOS平台的构建。此skill应被用于以下场景：构建桌面内核、打包发布版本、完整构建流程。
---

# SiYuan 打包流程 Skill

此skill提供SiYuan项目的完整构建和打包流程，包括前端构建、内核编译和安装包生成。

## 前置条件

在开始构建前，确保满足以下条件：

1. **工具链已安装**：
   - Go (版本见 `kernel/go.mod` 中的 `go` 指令)
   - Node.js + pnpm (版本见 `app/package.json` 中的 `packageManager` 字段)
   - mise (可选，用于任务管理)

2. **环境变量**：
   - `CGO_ENABLED=1` (必需，用于CGO支持)
   - `GO111MODULE=on` (必需，启用Go模块)

3. **中国区域镜像配置** (可选，仅限中国用户)：
   - 运行 `mise run set_mirror` 配置下载镜像

## 构建流程

### 1. 完整构建和打包

按顺序执行以下步骤完成完整构建：

```bash
# 步骤1: 安装依赖并构建前端 (在 app/ 目录下)
cd app
pnpm install     # 安装pnpm依赖
pnpm run build   # 构建所有前端包 (app, mobile, desktop, export)

# 步骤2: 构建桌面内核 (在 kernel/ 目录下)
cd ../kernel
# Windows:
go build -tags "fts5" -o "../app/kernel/SiYuan-Kernel.exe"
# Linux/macOS:
go build -tags "fts5" -o "../app/kernel/SiYuan-Kernel"

# 步骤3: 打包发布版本 (在 app/ 目录下)
cd ../app
pnpm run dist  # Windows
# pnpm run dist-darwin  # macOS
# pnpm run dist-linux    # Linux
```

### 2. 使用 mise 简化构建

如果已安装mise，可以使用预配置的任务简化构建流程：

```bash
# 构建桌面内核 (自动包含前端构建)
mise run build_desktop

# 打包发布版本 (Windows x64)
mise run package_release
```

**可用的mise任务**：
- `build_desktop` - 构建桌面内核（自动先构建前端）
- `build_frontend` - 仅构建前端
- `package_release` - 打包发布版本
- `clean` - 清理构建缓存
- `set_mirror` - 配置中国区域镜像

### 3. 各平台打包命令

根据目标平台选择相应的打包命令：

**Windows**:
```bash
cd app
pnpm run dist
```

**macOS**:
```bash
cd app
pnpm run dist-darwin
```

**Linux**:
```bash
cd app
pnpm run dist-linux
```

## 构建输出

构建完成后，输出文件位于：

- **内核**: `app/kernel/SiYuan-Kernel` (或 `.exe`)
- **安装包**: `app/build/siyuan-<version>-<platform>.exe` (Windows) 或相应格式

## 常见问题

### 1. Go模块下载失败

**解决方案**:
- 配置Go代理: `go env -w GOPROXY=https://goproxy.cn,direct`
- 中国区域用户可设置环境变量: `SET GOPROXY=https://goproxy.cn,direct` (Windows)

### 2. Electron下载失败

**解决方案**:
- 设置Electron镜像: `SET ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/` (Windows)
- 或在package.json中配置electron镜像

### 3. CGO编译错误

**解决方案**:
- 确保 `CGO_ENABLED=1` 已设置
- Windows: 安装TDM-GCC或MinGW-w64
- Linux: 安装gcc
- macOS: 安装Xcode Command Line Tools

### 4. 签名错误 (Windows)

**解决方案**:
- 如果没有代码签名证书，可以在 `app/electron-builder.yml` 中禁用签名
- 设置 `win: sign: null`

## 清理构建

如需清理构建缓存：

```bash
# 使用mise清理
mise run clean

# 或手动清理
rm -r app/kernel
rm -r app/build
cd kernel && go clean -cache
```

如仅清理构建输出：

```bash
# 使用mise清理
mise run clean --skip-deps

# 或手动清理
rm -r app/kernel
rm -r app/build
```

## 验证构建

构建完成后，验证安装包：

1. **检查文件存在**: 确认 `app/build/` 目录下生成了安装包
2. **测试安装**: 运行安装包，确认安装成功
3. **启动测试**: 启动SiYuan，确认功能正常

## 注意事项

1. **不要编辑的文件**:
   - `app/stage/protyle/js/lute/lute.min.js` (从上游lute项目构建)
   - `app/stage/build/**` (构建输出)
   - `app/kernel/SiYuan-Kernel*` (构建输出)

2. **版本管理**:
   - 版本号在 `app/package.json` 的 `version` 字段
   - 修改版本号后重新构建

3. **交叉编译**:
   - 当前配置仅支持本机平台构建
   - 交叉编译需要额外配置 (参见各平台构建指南)
