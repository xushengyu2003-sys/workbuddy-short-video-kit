# 选型与来源记录

调研日期：2026-10-11（中国时间）。高 Star 用作社区规模的参考；不把 Star 当下载量、质量或安全保证。下面的数值是 GitHub 页面本次读取的约数，并非永久排名；没有统一可比的真实安装量/下载量，因此不标“下载量最高”。

## 主线工具

| 工具/来源 | 页面 Star 约数 | 本包采用方式 | 取舍与许可 |
|---|---:|---|---|
| [FFmpeg](https://github.com/FFmpeg/FFmpeg) / [滤镜文档](https://ffmpeg.org/ffmpeg-filters.html) | 64.9k | 调用用户本地可执行程序完成裁切、拼接、音频和编码 | 成熟的执行底座；LGPL/GPL 取决于构建，本包不分发二进制 |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 25.8k | 可选本地 CPU/int8 转录，导出词级时间码 | MIT；模型另行下载，模型条款另查；本包不分发模型 |
| [Auto-Editor](https://github.com/WyattBlue/auto-editor) | 5.5k | 借鉴按音频活跃区间压缩停顿的工作方式；用 FFmpeg silencedetect 原创实现候选区间 | 本包不依赖该软件，不复制代码；它不是语义选段器 |
| [LosslessCut](https://github.com/mifi/lossless-cut) | 44.4k | 可作为高级用户手动审片/无损粗剪备选 | GPL-2.0；不打包源码或应用。本包有字幕/画幅处理，走重编码 |
| [edge-tts](https://github.com/rany2/edge-tts) | 12.2k | 只列为文章/PPT 解说的可选配音扩展 | 在线服务会发送文案；不是本地 TTS。没有合并进默认执行链 |

未将 MoneyPrinterV2 选为核心：它覆盖更多生成/发布任务，对已有口播剪短不需要这么多外部能力。第一版也没有自动下载网络素材、自动营销分发或自动收费调用。

## WorkBuddy 调研

- [官方技能开发格式](https://open.workbuddy.cn/en/docs/skill)：采用 SKILL.md、references/、scripts/、templates/；包使用官方说明中的必需描述字段、version 和 author。
- [官方安装使用入口](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)：支持本地技能包导入和启用/停用。ZIP 的根目录版和单层文件夹备用版均提供，具体以客户端导入结果为准。
- 本机只读查看到 short-video-script、philosophy-short-video、video-frames、openai-whisper。现有文字转视频方案依赖个人共享脚本、字体/音色配置；不复制到公共包，也不作为硬依赖。
- 本机已安装专家目录以 PPT/设计等为主，未据此声称已安装视频剪辑专家。另检索[公开市场归档](https://github.com/infometa/workbuddyskills)中的抖音策略/内容专家条目；归档不是官方实时市场，且再分发权限不能默认推定。
- [WorkBuddy 专家团队社区项目](https://github.com/darker2016/workbuddy-skill-groups)有视频制作/宣传片工作流，但本次优先原创自包含主线，避免小白先装一组互相依赖的技能。

## 用户飞书参考：实际读到什么

来源：[codex 的部分应用场景](https://my.feishu.cn/wiki/UhPzwxxBiilLV1khGlKcQBPZnXc)。网页抓取失败后，使用浏览器现有窗口读到正文并打开视频播放器，查看关键画面；未下载视频，未做完整音频转录。

- 第一支约 1:07 视频的教程画面出现 **Agent TARS**；其视频宣称的 Star 数为历史宣传值，不作为当前数据。[官方仓库 UI-TARS-desktop](https://github.com/bytedance/UI-TARS-desktop)确认 Agent TARS 是通用多模态电脑/浏览器工具栈，不是视频剪辑执行引擎。
- 第二支约 1:01 视频画面出现 **AiToEarn** 和自动发自媒体/MCP 的介绍；[官方仓库](https://github.com/yikart/AiToEarn)本次页面约 26.4k Star，提供内容创作和分发能力。第一版留作可选后续发布集成，默认不安装、不配置账号。
- 页面链接 [2395.mp4](https://my.feishu.cn/file/IHHmbrFS0oCrQYxHsZUchr0tnHe) 的演示画面出现**开拍/网感剪辑**和 kaipai.com，属于视频中使用的网站；未发现足够证据称它是高 Star 开源剪辑工具，不纳入开源依赖。

结论：视频提供了电脑操作和内容分发的补充思路；对于“已有口播/访谈剪短+字幕”，本地确定性引擎更适合作为首版底座。以后要把“剪→用户验收→发布”连起来，可以单独建立发布技能，不把平台登录和发帖绑进剪辑包。

## 原创与再分发

本包脚本和技能说明为原创，MIT 授权。只引用工具功能/API，不复制市场专家包、私有账号配置、个人音色、系统字体或第三方二进制。外部工具及模型遵循各自许可证/服务条款。适合 Fork、修改和私信分发本包；用户素材并不自动获得再分发许可。
