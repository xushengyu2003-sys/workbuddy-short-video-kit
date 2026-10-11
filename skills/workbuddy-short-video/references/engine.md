# 执行工具与清单

把 PY 替换为实际 Python 可执行路径、ENGINE 替换为当前技能目录下 scripts/video.py。宿主应负责变量和安全转义，小白只发需求。

```text
PY ENGINE doctor
PY ENGINE probe /素材/口播.mp4
PY ENGINE transcribe /素材/口播.mp4 --out /项目/transcript --model small
PY ENGINE transcribe /素材/口播.mp4 --out /项目/transcript --model small --allow-model-download
PY ENGINE captions /项目/transcript/transcript.json --out /项目/short-source.srt
PY ENGINE silence /素材/口播.mp4 --out /项目/silence.json
PY ENGINE validate /项目/edit-plan.json
PY ENGINE render /项目/edit-plan.json --out /项目/out-v1
PY ENGINE quality /项目/out-v1/final.mp4 --out /项目/review-extra
```

transcribe 默认不联网下载模型，允许下载时才加开关。model 也可为本地 faster-whisper/CTranslate2 模型目录。输出 source.srt 是原片轴，不能直接当剪完后字幕。引擎不自动语义选段，由 WorkBuddy 阅读转录并写清单。

CPU 转录默认 2 线程、beam-size=1 优先降低延迟；需要更精细的候选搜索时传 --beam-size 5，仍需校对。captions 按真实词级时间码、标点和间隔拆短字幕，默认每组最多 16 字；不提供词级时间码时明确拒绝伪造对齐。英语/术语的视觉宽度仍以渲染检查为准。

## 清单 JSON（schema_version=1）

```json
{
  "schema_version": 1,
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "fit": "contain",
  "clips": [
    {"source": "素材/口播.mp4", "start": 10.2, "end": 25.5},
    {"source": "素材/口播.mp4", "start": 28.0, "end": 44.0}
  ],
  "subtitles": "short-source.srt",
  "subtitle_timing": "source",
  "burn_subtitles": true
}
```

所有相对素材路径相对于清单所在目录；不接受 URL。source 视频 start/end 单位秒，按列出顺序拼接，非无损剪辑，重编码为 H.264/AAC。width/height 偶数；默认 1080×1920；fps 默认 30，上限 60。

可选项：

- `fit`: contain 保留完整画面加留边，cover 中央裁切填满；不支持追脸/自定义位置。
- `subtitles`: 本地 SRT；省略则不生成字幕；`subtitle_timing`: output（默认）或 source；source 仅支持单一原片的任意选段序列。
- `burn_subtitles`: true 默认烧录；false 不烧字幕，仍渲染视频并附 SRT；如果用户只要字幕文件，在 editorial captions 后直接交付 SRT，不调用 render。PNG 字幕渲染不需要 libass。
- `font`: 本地 TTF/OTF/TTC 文件。
- `narration`: 已生成录音，替换原片声音；时长须与镜头总长相差不超过 0.15 秒，不自动拉速。
- `music`: 本地 BGM 循环并混合；`music_gain` 默认 0.12、上限 0.5，这是相对增益，仍需听感验收。本版没有自动 ducking。
- 图片镜头：`kind: "image"`，start=0/end=展示秒数；静帧，无自动镜头运动。可与视频混用。

render 会逐段统一尺寸、帧率、立体声 48kHz，拼接后对主音轨做单遍 loudnorm，添加可选 BGM/字幕。单遍 loudnorm 是基本音量处理，不声称精确达到目标 LUFS；BGM 混合后有峰值限制器。

成功输出包含 final.mp4、subtitles.srt（有字幕时）、edit-plan.json、quality.json、review/frame-0..2.jpg。quality 完整解码、检查 H.264/AAC，render 额外对照清单尺寸与时长。机器检查不检测黑场/人脸/字幕同步/语义，不等同质量全通过。失败退出 2；机器检查不通过退出 1；诊断与成功退出 0。勿单看 doctor 的退出码判断依赖齐全。

0.1.1 新增清单 `encoder`：默认 libx264；macOS 可显式使用 h264_videotoolbox（6Mbps，禁用软件回退）。两阶段都使用所选编码器。doctor 可查询编译支持，实际硬件可用性需短片确认。硬件失败请新建输出目录切回 libx264，禁止把未完成 MP4 当成成功。静音检测已排除视频解码。

## 0.2.0 精剪工具

第二个入口为同目录 `scripts/editorial.py`（以下 EDITOR），由宿主负责生成决策，小白只描述希望“紧凑些/保留口语/重点版”。

```text
PY EDITOR analyze /素材/口播.mp4 /项目/transcript/transcript.json --mode tight --silence /项目/silence.json --out /项目/proposals.json
PY EDITOR build /项目/proposals.json /项目/decisions.json --out /项目/compiled-v1
PY EDITOR style-preview /素材/口播.mp4 --at 25 --text 机会还是要自己找 --out /项目/style-v1
PY ENGINE render /项目/compiled-v1/edit-plan.json --out /项目/out-v3
```

旧版 silence.json 无 silences 字段时仍能分析，但候选只具 ASR 空隙证据，标为高风险；需要声学证据时新文件执行一次 `silence --minimum 0.35 --padding 0.12`，不要反复扫描已有相同参数结果。

候选每条含 id/kind/start/end/word_ids/text/context/risk，全部初始 pending。analyze 不改变素材，不生成删词决定。build 核对素材与转录 SHA-256；输出目录必须不存在。

决策例子（编号需来自当前候选，word_id 是零起始，不是时间码）：

```json
{
  "decisions": [
    {"id": "c0001", "action": "keep", "reason": "表达思考，保留"},
    {"id": "c0002", "action": "delete", "reason": "无意义重复起句", "evidence": "读取相邻词及上下文，保留后一句；切口听感待验收"}
  ],
  "manual_cuts": [
    {"word_ids": [12, 13, 14], "reason": "未完成的起句，后文重新完整表达", "evidence": "转录相邻句；原声切口仍待听音"}
  ],
  "semantic_review": {"passes": "重复/改口/口头禅/结构/节奏", "coverage": "全稿", "uncertain": [], "listening": "pending"}
}
```

同一词可能同时作为 filler 和 repetition 候选出现；它们是不同检查视角。一个视角 keep 不会覆盖另一视角 delete，最终以合并后的删除区间为准；理由应注明重复记录，并检查 cut-report 的实际保留词。相邻重复候选仍可能是强调；未写入决定的候选保留，并列入 undecided_kept。build 只编译宿主决定，不认证文字中的证据已被听音核实。连续词组删除可含多个完整词，拒绝切进保留词与零时长词附近。`manual_cuts` 不能用来伪造半个词的时间。输出 edit-plan.json / subtitles.srt / retained-words.json / cut-report.json；拼接点听音范围在报告 joins 中。

## 0.2.0 字幕与术语参数

清单增加 `subtitle_style`，预设可选 classic/readable/accent；旧清单无此字段时保持 classic，精剪编译器默认 readable。

```json
{"subtitle_style": {"preset": "readable", "font_size": 60, "stroke_width": 4, "color": "#FFFFFF", "stroke_color": "#000000", "position_y": 0.78, "max_width": 0.76, "line_spacing": 1.25}}
```

font_size 24–100 和 stroke_width 0–10 的单位为 1080 宽参考像素，其他尺寸同比缩放。position_y 0.15–0.85 为字块中心相对高度；max_width 0.4–0.9 为相对宽度；line_spacing 1–1.8。颜色仅 #RRGGBB。未知字段/预设拒绝，不默默忽略；超过两行要求拆字幕。字幕本身没有逐词高亮、字体粗细开关、动画或平台实时 UI 检测；可选文字标题动画见 extensions.md。

`transcribe --glossary "南通；乙方；C端"` 最多 200 字，仅提示识别，不自动替换事实。新转录保存每个词的 probability；概率也不等于内容正确。本地强制对齐后端尚未接入。

## 0.2.1 精简与复用

- `editorial.py review proposals.json --out review.md`：一次读全文段落及程序生成的词 ID，避免手工重数。
- `editorial.py captions retained-words.json phrases.json --out final.srt`：保留词表必须 timing=output，start/end 已映射；source_start/source_end 是原片时钟。短语首末 ID 必须存在，内部已删词可跨过；全部保留词按顺序覆盖一次。

phrases.json 示例：`{"phrases":[{"first_word_id":32,"last_word_id":41,"text":"吃饭不重要\n重要的是聊的内容"}]}`。宿主负责完整短语与校对，工具负责真实时间、覆盖与短条提示。校对不证明原音准确，记录待确认项。旧版 retained-words 不带 timing，重新 build 即可升级，不重转录。

首次 render 保留 base.mp4（已剪辑/混音，无字幕）和 base.json 校验记录，额外占用约一份成片大小的磁盘空间。仅改字幕可运行：

```text
<PY> <SKILL_DIR>/scripts/video.py restyle out-v1 final-v2.srt --preset accent --font-size 64 --out out-v2
```

它核对底片和原清单指纹，再烧入新字幕、做最终质量检查；不重做剪辑混音。修改剪点/音乐须新 render。0.2.0 旧产物没有无字幕底片，不能从其硬字幕成片逆向复用，需首次重渲染生成底片。每版底片留在项目内，工具不自动删除。timings.json 记录剪辑混音、字幕和检查阶段耗时。

字幕渲染只传输实际有字的透明区域，仍保留 PNG/FFmpeg 可移植链路；未引入 libass、外部运行时或付费服务。
