# Windows 用户安装引导｜Workbuddy 短视频剪辑技能测试版

把本包中的 `workbuddy-short-video-windows-0.2.3-test.3.zip` 上传到 Windows Workbuddy 的技能管理中并启用。若导入器要求 ZIP 内先有一层技能文件夹，改用同包的 `-folder.zip`。导入后，把 `给Windows版Workbuddy的测试任务.txt` 发给 Workbuddy；后续检测、安装和复检由它带你完成。无需先把电脑上的 Python 和 FFmpeg 全部重装一遍。

**第一步：让 Workbuddy 检查现有环境。** 它会先找自己的隔离 Python、FFmpeg、ffprobe 和中文字体，再检查 Pillow、语音转文字包及模型。检测文件是 `bootstrap.json` 和 `environment.json`。看到 `ready=true` 才开始剪辑；缺什么就补什么。请把检测结果和报错交给 Workbuddy，不要凭“软件似乎装过”判断。

**第二步：只安装缺失项。**

- **Python：** 先复用 Workbuddy 找到的 Python 环境。这台电脑用的是 Workbuddy 隔离环境里的 Python 3.13.14；别人的电脑不要求同版本。确实没有可用 Python 时，到 [Python 官方 Windows 下载页](https://www.python.org/downloads/windows/)选择适合电脑的版本。安装后让 Workbuddy 复检。
- **FFmpeg / ffprobe：** 从 [FFmpeg 下载页](https://ffmpeg.org/download.html)进入 Windows 构建下载入口。这台电脑使用了 FFmpeg 9.0.2，并把 `ffmpeg.exe`、`ffprobe.exe` 放在技能的 `bin` 目录，系统 PATH 没有修改。技能目录不可写时，可放用户目录，让 Workbuddy 指定两个文件的路径。复检会实际测试 H.264/AAC 编码。
- **Pillow 和 faster-whisper：** Pillow 用来生成中文字幕；需要自动转录时才安装 faster-whisper。让 Workbuddy 把它们安装到**剪辑任务使用的那个 Python 环境**，然后复检。它们的项目页分别是 [Pillow](https://pypi.org/project/Pillow/) 和 [faster-whisper](https://pypi.org/project/faster-whisper/)。CTranslate2、ONNX Runtime、PyAV、tokenizers、huggingface-hub 通常随 faster-whisper 安装；不必照着这台电脑的版本表逐个下载。
- **中文字体：** 先用 Windows 自带字体；字幕出现方框，再让 Workbuddy 指向本机其他中文字体，并看实际视频画面。
- **转录模型：** 安装 faster-whisper 后还需要模型文件。已有本地模型就复用；没有时，Workbuddy 会先说明下载量和保存位置，征得你同意后下载。截图中的 small 模型约 464 MB，只是这台电脑的记录。

**第三步：网络不顺时选备用入口。** 这台电脑的 pip 直连曾卡住，改用[阿里云 PyPI 镜像](https://developer.aliyun.com/mirror/pypi)完成安装；Hugging Face 直连不可用时，曾在当前终端临时使用 [HF-Mirror](https://hf-mirror.com/)下载模型。镜像是备用渠道，HF-Mirror 是第三方站点。Workbuddy 会先说明来源，再仅对当前安装或下载任务设置镜像，不改系统全局配置。若镜像也失败，就保留错误，改用本地模型或其他可用网络。

**第四步：复检并试剪。** 补齐后重新运行检测，确认 `ready=true`，再做技能自带的合成素材测试。合成测试通过后，用一段 30–120 秒口播试剪，检查成片能播放、中文字幕正确、原视频没有被覆盖，并试听剪辑接缝。请把 `bootstrap.json`、`environment.json`、`selftest.json` 和真实素材测试报告反馈给技能作者；这些报告比“安装成功”的一句话更容易定位问题。

本包仍是 Windows 测试版。这台电脑的安装记录是一个成功案例，其他电脑的 Workbuddy 目录、网络和软件版本可能不同，检测结果以本机实际输出为准。
