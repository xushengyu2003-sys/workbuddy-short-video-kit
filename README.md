# WorkBuddy 小白短视频剪辑技能包

macOS 优先，把已有口播/访谈素材剪短、添加中文硬字幕并导出 MP4。WorkBuddy 判断内容，随包脚本执行剪辑；核心出片使用本地 FFmpeg，不需要另买剪辑软件或视频 API。

**状态：本地 0.2.2 验证版。** 执行引擎与真实 WorkBuddy 口播流程已在 macOS 验证；具体版本和测试范围见验证报告。Windows 尚未实机验收。没有自动追脸、剪映工程导出、说话人分离或自动发布。

## 小白安装和使用

1. 获取 [技能安装 ZIP](dist/workbuddy-short-video-0.2.2.zip)。这是技能安装包，不是整个源码包。
2. WorkBuddy 左侧「专家 · 技能 · 连接器」→「技能」→「添加技能」→「上传技能」，选择该 ZIP 并启用。入口名称可能随版本变化。
3. 安装列表中名称为 `workbuddy-short-video`，可以输入 `/` 后搜索该名称。把视频发给 WorkBuddy，再发送下面这句话。首次使用，WorkBuddy 应先检查本机工具；依赖缺失就按技能说明处理。

> 使用 workbuddy-short-video 技能，把这个口播剪成约一分钟，保留完整观点，删掉多余停顿，加中文字幕，给我可播放的 MP4。先检查环境；原文件不要覆盖。

长访谈可以说：

> 从这段访谈里挑出最适合讲给新手的一段，剪成 60–90 秒，保留提问背景、完整观点和关键例子，加中文字幕。横版不要切掉人物。

如果导入器不接受根目录 SKILL.md 的 ZIP，用备用 `workbuddy-short-video-0.2.2-folder.zip`（多一层技能文件夹）。不要导入整个源码 ZIP。

## 分享给评论者

私信发 [小白领取包](dist/workbuddy-short-video-beginner-0.2.2.zip) 即可：里面有一个技能安装 ZIP、三步安装文本、开始提示词和可离线阅读的领取页面。备用 folder 包在 dist 中单独提供。无需发送你的环境、私人视频、API Key 或字体库。该包本身体积很小；Python/FFmpeg/转录模型是另行安装的工具。只发 ZIP 并不能保证每个人机器已具备依赖。

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

## 当前功能与选择入口

精剪、轻剪或按重点切片；单条或多条；原比例、竖屏、横屏或方形；三种可调字幕、独立SRT；已有本地轻音乐；已有图片/视频B-roll；简洁文字标题动画。WorkBuddy 一次最多询问三个缺失选项，已经明确的偏好直接复用。B-roll/MG进一步按需要确认素材和位置，默认关闭。没有自动找素材、复杂MG或自动音乐生成。

执行工具包括全文阅读表、删留编译、完整短语字幕校验、全片导出、缓存底片改字幕和可选装饰合成。字幕只处理有字的区域；Mac 可选已验证的硬件编码。底片额外占一份视频空间，但后续修改字幕可省去重剪和混音。只要SRT可跳过视频渲染。

[开源方法比较](UPGRADE-RESEARCH.md)、[实测范围](VALIDATION.md)、[速度与限制](SPEED-NOTES.md)。本包是独立实现，没有将 WhisperX、stable-ts 或第三方 Studio 打包进去。机器解码不能证明字幕准确或听感自然。

本次发布版本为0.2.2；面向小白的领取页在 index.html，页面内嵌安装包，下载不需要读取GitHub源码。分享仅包含技能、说明和测试，不包含真人素材、字幕、成片、音乐、字体、模型或密钥。
