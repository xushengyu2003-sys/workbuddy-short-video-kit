---
name: workbuddy-short-video
display_name: 小白短视频剪辑工作流
description: 把已有中文口播、访谈、课程或产品素材剪成短视频并添加字幕；从素材检查、转录选段到本地 MP4 导出和质量检查。用户说剪短、剪口播、访谈切片、删停顿、加字幕、一句话出片时使用。
description_zh: 给素材、说目标，自动检查环境、选段、剪辑、加字幕并交付可播放视频。
description_en: Edit existing talking-head or interview footage into short clips with local transcription, captions, MP4 rendering and quality checks.
version: 0.2.2
author: WorkBuddy Short Video Kit Contributors
---

# 小白短视频剪辑工作流

使用随包本地工具完成已有口播/访谈的精剪与字幕。WorkBuddy 做内容判断，脚本处理真实时间轴和导出。默认 tight 精剪、保留原声与核心观点、按原片显示比例适配输出/30fps、readable 白字字幕；用户的时长与样式要求覆盖默认值。

## 用户选择

先读 [options.md](references/options.md)，把用户明确的要求填入 brief；只询问仍缺失且会影响结果的选项，一次最多三个问题。用户可说“按推荐来”，也可随后只改字幕、画幅或配乐。不要默认启用所有扩展。

## 快速执行

先确定本技能目录 `SKILL_DIR` 和可用 Python（优先宿主虚拟环境）；工具为 `scripts/video.py`、`scripts/editorial.py`。新素材通常用新的 WorkBuddy 任务，避免带入无关历史；同一项目改字幕复用现有产物。每个新任务开始先用候选 Python 运行 doctor，确认 Pillow、FFmpeg、字体满足本次任务，在 brief 中记录 runtime_python，后续所有命令复用这一个解释器，不先试系统裸 Python；再执行任务。环境诊断使用 doctor，缺依赖见 [setup.md](references/setup.md)。普通口播只读 [editing.md](references/editing.md)；参数需要时查 [engine.md](references/engine.md)，不用反复读全部源码。

1. 新建项目，原片只读。按 proposals 的原片路径与哈希核对再复用同一素材已有转录/静音报告，不能只凭文件夹名选缓存；没有词级转录才 transcribe。先看素材方向与人脸。
2. editorial analyze → review 生成全文阅读表和程序编号。一次读全文，按论点列留删表；重复、改口、口头禅、结构、节奏在同一轮判断中检查。以文件保存决定，不在回复中逐词重数或长篇推演每个候选。编号、覆盖与时长交给工具。
3. build 编译删减。`retained-words.json` 明确 timing=output：start/end 已是成片时间，source_start/source_end 才是原片时间，不能二次映射。默认自动字幕只是初稿。
4. 校对文字并按完整短语选首末 word_id，写 phrases.json；editorial captions 生成最终 output SRT、检查覆盖和短闪条。先看完整字幕与样式静帧，需要时做短样片；确认后再全片导出，减少返工。
5. validate → render。Mac 已通过短样片硬件编码时用 encoder=h264_videotoolbox；否则 libx264。后台等待真实 final.mp4 与 machine_pass=true。读取 timings.json 定位耗时，不重复做已通过的全片 quality。
6. 抽看开头、中段、结尾及两行字幕，试听切口清单。未听项 pending；交付可播放 MP4、SRT、删留理由与质量状态。

仅改字幕文字/字号/颜色时使用 video restyle，复用上版带校验记录的 base.mp4，不重剪重混音；剪点/配乐变化才重新 render。底片会增加项目磁盘占用，详见 engine.md。不要把已烧字幕 final.mp4 当无字幕底片。

## 内容与边界

- 删无意义重复、残句与口头禅，保留限定词、否定、论据和必要过渡。时长取舍基于完整观点；不机械截前一分钟，不编第三点或新因果。
- ASR 空隙不等于静音；结合音轨证据。零时长/重叠词不能猜音节时间，需对齐或保留。字幕修字不能替代声音剪辑。
- 字幕按完整短语，每条最多两行；不要为固定字数拆“主动的人/信息/团队”。字体使用本机文件，不随分享包携带个人字体。默认位置需结合人脸和平台按钮检查。
- BGM 可混入用户提供或有依据的本地音频，低音量不盖原声。没有合适音乐就省略，不自动发素材到在线服务或调用付费服务。
- 本地新版本输出不覆盖原片。失败保留诊断，针对明确问题最多修复两次；未出片不能宣称完成。原意、字幕准确与听感不由解码检查证明。

清单与命令：[engine.md](references/engine.md)。文章/图片/配音扩展按需读 [extensions.md](references/extensions.md)。分享仅带技能文件，不带真人素材、转录、成片、字体、模型或密钥。
