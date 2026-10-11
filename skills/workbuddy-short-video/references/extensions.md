# 可选扩展：文章/PPT 解说、生成素材与技能协作

第一版主线是已有口播/访谈自动剪短、字幕。以下扩展需要额外输入/服务，不宣传成默认一键能力。

## 图片或幻灯片 + 已录配音

先从用户文章提炼文案或读取 PPT；已有宿主文档能力时导出每页为 PNG。引擎不直接解析 PPT/PDF。按已录配音时间轴安排 kind=image 镜头，生成 output SRT；narration 设置为配音文件。用配音实际时长校正清单再渲染。普通图文视频可执行，但第一版不含自动找素材、图片生成或 PPT 解析。

## 在线配音

用户愿意把文案发送到 Microsoft Edge 在线语音服务后，可在独立环境安装 edge-tts，使用其官方 CLI 或 Python API生成 MP3/SRT；命令见官方项目 https://github.com/rany2/edge-tts 。服务不需要 API Key，但依赖网络和服务可用性；不是本地 TTS，也不保证永久免费/商用条款。使用服务返回的时间码，不按字数猜时间轴。其他服务按宿主实际可用连接器及用户授权处理，不虚构 API。

## 与 WorkBuddy 已安装技能/专家协作

仅当宿主列出已启用且可调用的相应能力时使用；安装目录中有文件不代表当前会话已启用。名称也可能变更，优先核实实际功能：

| 可寻找能力 | 协作任务 | 对本包的接口 |
|---|---|---|
| 短视频脚本/内容专家 | 梳理目标、标题、讲稿 | brief.md 和内容稿 |
| 本地 Whisper | 提供转录和时间轴 | 校验 SRT 或 transcript.json |
| 视频抽帧 | 检查人脸/字幕 | 本地 JPG/PNG |
| AI 图片/视频/配音连接器 | 用户明确需要的补充素材 | 有授权的本地文件及来源记录 |

本机调研时发现 short-video-script、philosophy-short-video、video-frames、openai-whisper。philosophy-short-video 有个人外部脚本/字体/音色路径，不能作为他人必装依赖。本包不复制这些技能，也不沿用个人偏好/账号凭据。

如专家/技能不存在，本包仍可自行写剪辑清单、执行导出，不把多个模型/子代理当作依赖，也不自动安装市场包。若服务生成任务只返回 URL/任务状态，下载并 probe 验证本地素材后才能合成。

## B-roll 与简洁 MG 标题（可选，本地）

用户确认需要后，使用 scripts/extras.py。先普通 render 得到带 base.json 校验的无字幕底片，再把选择映射到 decorations.json，执行：

```
python "$SKILL_DIR/scripts/extras.py" 项目/out 项目/decorations.json --out 项目/out-decorated
```

该阶段复用剪点和混音，B-roll覆盖所选时段的画面，保留原声音轨，再重新烧录字幕。标题是透明文字的淡入、短距离上移、淡出，不含复杂3D动画/自动动效模板。只在用户选中时跑，会增加一次视觉编码和字幕编码；普通口播默认关闭。后续仅改字幕可对 out-decorated 使用 restyle。

计划样例（start/end为成片时间，source_start为B-roll原素材起点）：

```json
{"items":[
  {"kind":"broll","media":"video","source":"补充画面.mp4","source_start":0,"start":10,"end":13},
  {"kind":"title","text":"机会要主动争取","start":2,"end":5}
]}
```

图片B-roll设置media=image、source为本地PNG/JPG。默认contain保全画面；覆盖期间人物会被补充镜头遮住，先确认使用场景，不用无关画面伪造事实。记录素材路径、来源与用户授权。没有已有素材则询问用户选不加还是提供素材；外部检索/生成需先明确来源、服务及是否上传内容。字幕在装饰之后烧录，B-roll不会盖住字幕。抽看插入起止、文字遮挡与切回镜头；解码通过不等于听感通过。
