# Windows WorkBuddy 剪辑技能测试包

版本：0.2.3-windows-test.3，基于已有 0.2.2 剪辑引擎改造。技能名为 workbuddy-short-video-windows，与旧版不同，可并行安装。

## 安装

在 Windows WorkBuddy 的技能管理中上传 workbuddy-short-video-windows-0.2.3-test.3.zip，启用技能。这个 ZIP 的根目录含 SKILL.md。如果导入器要求一层技能文件夹，改用带 -folder 后缀的备用 ZIP。只导入其中一个包；入口名称以当前客户端为准。

如果无法上传 ZIP，可解压 -folder 包，把其中 workbuddy-short-video-windows 文件夹放入该客户端实际支持的本地技能目录；不要猜路径，先让 WorkBuddy 确认目录。

技能包不含 Python、FFmpeg、字体、转录模型，不是免安装的视频软件。首次使用让 WorkBuddy 检查环境。包中无真实用户素材、转录、密钥或个人字体。

第一次安装可先读同包的 `Windows用户安装引导.md`；它根据一台已完成安装的普通 Windows 办公电脑整理，覆盖复用 Workbuddy Python 环境、技能目录内 FFmpeg 和网络镜像备用路径。

## 发给 WorkBuddy

启用后，把同包的「给Windows版WorkBuddy的测试任务.txt」内容粘贴到新聊天，再提供一段 30–120 秒口播。先运行不依赖 Python 的 Windows 环境检测；缺项时 Workbuddy 给出下载与安装指引，复检通过后完成无真人素材的合成测试，再测实际转录和成片。用户只需提供素材与目标，命令由 WorkBuddy 执行。

请把 bootstrap.json、environment.json、selftest.json、doctor.json、tests.txt、真实素材测试报告及报错原文带回来。无需上传私人原视频也能先定位大部分环境问题。

## 当前验证范围

32 项合成媒体和回归检查在 macOS / Python 3.9.6 上通过，包括新增 Windows 路径/字体查找/UTF-8 输出逻辑检查。没有在 Windows 上运行；Windows 客户端导入、依赖安装、转录模型、实际视频与听感均待实测。合成测试不验证转录准确性，也不能证明剪口听感自然。

功能：口播精剪、静音候选、词级删留编译、完整短语字幕、MP4/SRT、画幅适配、缓存底片改字幕；可选本地 BGM、图片/B-roll、简洁文字标题。没有自动追脸、说话人分离、剪映工程导出或自动发布。
