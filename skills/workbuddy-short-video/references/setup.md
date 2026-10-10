# macOS 环境检查与新手排错

技能安装不等于底层工具已经安装。先运行 doctor；以下命令由 WorkBuddy 执行，不要求小白使用终端。

1. Python：优先使用宿主可用的 Python 3.9+（本次验证使用 3.13）。如果没有，使用 Python 官方安装包或已有 Homebrew 安装 `python`。不用 sudo 改系统 Python。
2. FFmpeg / ffprobe：已装 Homebrew 时可 `brew install ffmpeg`。没有 Homebrew 时参考 https://ffmpeg.org/download.html 的 macOS 下载入口，让用户选安装方式，不执行来路不明的一键脚本。支持环境变量 `WB_FFMPEG`、`WB_FFPROBE` 指向本地可执行文件。
3. Pillow：烧录字幕需要。用同一 Python 的项目虚拟环境安装 `python -m pip install 'Pillow>=10,<13'`，再用虚拟环境的 Python 跑引擎。不修改其他技能的环境。
4. 转录：可选 `python -m pip install 'faster-whisper>=1.1,<2'`。CPU/int8 默认模型 small；中文人名密集、音频较差时可选 medium 或更大模型。small 首次模型下载数百 MB（实际以模型站点为准），之后可离线使用。安装包也可能需要网络。
5. 字体：macOS 自动尝试 PingFang、STHeiti；不存在时显式传清单 `font`。不随技能再分发系统字体。doctor 发现字体文件不代表所有字都有字形，仍需看抽帧。

doctor 返回中检查 `tools.ffmpeg`、`tools.ffprobe` 是否有 path；`h264_encoder` 是否为 true；字幕要求 `optional.PIL` 和 font；转录要求 `optional.faster_whisper`。doctor 本身为诊断，不会自动下载/安装软件。

## 常见失败

| 提示/现象 | 操作 |
|---|---|
| 找不到 ffmpeg | 检查 PATH，或设置 WB_FFMPEG/WB_FFPROBE；安装后重跑 doctor |
| 没有模型缓存 | 有网且允许首次下载时加 --allow-model-download；否则用本地模型路径/已提供的 SRT |
| 字幕超过两行 | 按 words 时间码拆句，重新写 SRT，不要只缩小字体 |
| 输出已存在 | 指向新的 out-v2/out-v3 目录，保留旧版 |
| 无音轨 | 如需口播，请给含音轨的原片；普通素材混剪可补静音轨或提供配音 |
| 横片切掉人物 | 用 contain，或先在画面上审核后再 cover；没有自动追脸功能 |
| 字幕是方框 | 换包含这些字的本地字体，重跑并查看抽帧 |
| 在线配音无法连接 | 优先使用用户录音；不反复调用服务或默默改付费方案 |

## Windows 后续适配

脚本使用跨平台 Path/subprocess，无 shell 拼接。可用 `py -3`、FFmpeg 官方链接指向的 Windows 构建与微软雅黑字体。第一版未在真实 Windows / WorkBuddy Windows 验收，不标为已兼容。不要给用户 macOS 专属安装命令。
