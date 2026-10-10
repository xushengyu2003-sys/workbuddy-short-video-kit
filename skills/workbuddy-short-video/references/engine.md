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
- `burn_subtitles`: true 默认烧录；false 只交付 SRT。PNG 字幕渲染不需要 libass。
- `font`: 本地 TTF/OTF/TTC 文件。
- `narration`: 已生成录音，替换原片声音；时长须与镜头总长相差不超过 0.15 秒，不自动拉速。
- `music`: 本地 BGM 循环并混合；`music_gain` 默认 0.12、上限 0.5，这是相对增益，仍需听感验收。本版没有自动 ducking。
- 图片镜头：`kind: "image"`，start=0/end=展示秒数；静帧，无自动镜头运动。可与视频混用。

render 会逐段统一尺寸、帧率、立体声 48kHz，拼接后对主音轨做单遍 loudnorm，添加可选 BGM/字幕。单遍 loudnorm 是基本音量处理，不声称精确达到目标 LUFS；BGM 混合后有峰值限制器。

成功输出包含 final.mp4、subtitles.srt（有字幕时）、edit-plan.json、quality.json、review/frame-0..2.jpg。quality 完整解码、检查 H.264/AAC，render 额外对照清单尺寸与时长。机器检查不检测黑场/人脸/字幕同步/语义，不等同质量全通过。失败退出 2；机器检查不通过退出 1；诊断与成功退出 0。勿单看 doctor 的退出码判断依赖齐全。
