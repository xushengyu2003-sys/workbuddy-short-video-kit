# WorkBuddy 小白短视频剪辑技能包

macOS 优先，把已有口播/访谈素材剪短、添加中文硬字幕并导出 MP4。WorkBuddy 判断内容，随包脚本执行剪辑；核心出片使用本地 FFmpeg，不需要另买剪辑软件或视频 API。

**状态：0.1.0 验证版。** 执行引擎已在 macOS 验证；真实 WorkBuddy 对话执行和用户真人口播验收需以验证报告为准。Windows 尚未实机验收。没有自动追脸、剪映工程导出、说话人分离或自动发布。

## 小白安装和使用

1. 获取 [技能安装 ZIP](dist/workbuddy-short-video-0.1.0.zip)。这是技能安装包，不是整个源码包。
2. WorkBuddy 左侧「专家 · 技能 · 连接器」→「技能」→「添加技能」→「上传技能」，选择该 ZIP 并启用。入口名称可能随版本变化。
3. 安装列表中名称为 `workbuddy-short-video`，可以输入 `/` 后搜索该名称。把视频发给 WorkBuddy，再发送下面这句话。首次使用，WorkBuddy 应先检查本机工具；依赖缺失就按技能说明处理。

> 使用 workbuddy-short-video 技能，把这个口播剪成约一分钟，保留完整观点，删掉多余停顿，加中文字幕，给我可播放的 MP4。先检查环境；原文件不要覆盖。

长访谈可以说：

> 从这段访谈里挑出最适合讲给新手的一段，剪成 60–90 秒，保留提问背景、完整观点和关键例子，加中文字幕。横版不要切掉人物。

如果导入器不接受根目录 SKILL.md 的 ZIP，用备用 `workbuddy-short-video-0.1.0-folder.zip`（多一层技能文件夹）。不要导入整个源码 ZIP。

## 分享给评论者

私信发 [小白领取包](dist/workbuddy-short-video-beginner-0.1.0.zip) 即可：里面有技能安装 ZIP、备用版 ZIP 和使用说明。无需发送你的环境、私人视频、API Key 或字体库。该包本身体积很小；Python/FFmpeg/转录模型是另行安装的工具。只发 ZIP 并不能保证每个人机器已具备依赖。

## Fork 和改造

Fork 此仓库后，修改 `skills/workbuddy-short-video/SKILL.md` 的默认风格或 references/ 中的选段方法；修改 scripts/video.py 的执行功能。保留 source/output 字幕时间轴、原素材保护和错误报告。修改后运行：

```sh
python3 -m unittest discover -s tests -v
python3 build_release.py
```

测试需要 FFmpeg、ffprobe、Pillow 和中文字体。`tests/create_demo.py` 使用 macOS 本地合成语音生成演示输入，随后可使用转录/剪辑命令检验真实链路。生成媒体在 demo/，默认不进入源码分享。

## 文件

- `skills/workbuddy-short-video/`：完整可移植技能及执行引擎。
- `小白使用说明.md`：分发时附给用户。
- `RESEARCH.md`：WorkBuddy 市场、本地技能与开源工具选型记录。
- `VALIDATION.md`：测试与尚未验收事项。
- `LICENSE`：本项目原创代码/说明的 MIT 授权。外部工具各自遵循许可证，本包未包含它们的源码或二进制。

官方格式和安装入口：[技能开发文档](https://open.workbuddy.cn/en/docs/skill)、[技能使用说明](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)。
