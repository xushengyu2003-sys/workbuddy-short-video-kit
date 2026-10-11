# 0.2.0 开源对照与整合记录

## WaytoAGI 社区补充核查

从用户提供的 [中文入口](https://www.waytoagi.com/zh) 查知识库精选，再对照官方项目，核查日期 2026-10-11。精选是编辑推荐线索，不等于投票排名。部分精选读取的是公开索引摘要，没有读到所有飞书原文。

| 社区线索 | 官方核查与优势 | 本包吸收与边界 |
|---|---|---|
| [6月22日：成峰剪辑 Skills](https://www.waytoagi.com/zh/blog/news-20260622) | [官方仓库](https://github.com/Agentchengfeng/chengfeng-videocut-skills)：分类精剪、词 ID、校对与删词记录 | 已落实分类规则、候选与决定分离、删留原因和剪后字幕；未接入其云端 ASR、运行时与动画 |
| [7月15日：BaoCut](https://www.waytoagi.com/zh/blog/news-20260715) | [官方仓库](https://github.com/JimLiu/baocut)：当前 talking-head-cut 按论点列留删表、区分素材与成片时钟、可恢复剪口、短段试听 | 补充全文论点清单与分层验收，已有原片保护、可修改清单与切口表；未实现其桌面时间线、事务撤销与便携工程。文章当时称仅 Mac，当前 README 已列 macOS/Windows |
| [7月23日：ChatCut 操作指南](https://www.waytoagi.com/zh/blog/news-20260723) | [官方 Agent 插件](https://github.com/ChatCut-Inc/agent-plugin)：talking-head-guide 先定口播再字幕/画面，保护完整语义与必要连接词，产品另有剪口微交叉淡化 | 本包剪后重建字幕并重读逻辑；未接入其账户/MCP，未实现其 smooth_audio。公开插件不意味着整个产品开源 |

这些项目最值得学的是先把话剪顺、删留有依据、成片能复核。宣传中的准确率和耗时没有同环境复测，不作为本包指标。已阅读 BaoCut 当前技能入口和 talking-head-cut，以及 ChatCut talking-head-guide；没有安装运行这两款产品，没有上传用户素材。方法独立实现，未复制代码或技能全文。

本包仍是 WorkBuddy 本机文件工作流。BaoCut/ChatCut 的可视化接管和编辑工程更完整；0.2.0 尚不具备同等编辑器体验。

核查日期：2026-10-11。对照 GitHub 官方仓库的 README、技能入口与部分执行代码，未安装或跑完各项目，不能将作者功能声明当成实际效果验证。Star/Fork 为当天 GitHub 公共 API 快照；未获得可比较的下载量，不能编造“高下载量”。Star 只说明关注度，成熟度还需结合维护、实现与测试。

## 逐项比较

| 官方项目 / 当日 Star | 相比本包 0.1.1 的优势 | 0.2.0 如何整合 | 边界 |
|---|---|---|---|
| [auto-editor](https://github.com/WyattBlue/auto-editor) / 5,473 | 现有 Agent Skill 明确支持预览裁切、阈值、前后独立缓冲、最短片段和编辑器导出；适合控制节奏 | 借鉴“先提出候选，再查看切除范围与缓冲”的方法；加入 light/tight/highlight 模式，静音区与词空隙取交集 | 原创 FFmpeg 实现，不安装 auto-editor；尚无 FCP/Premiere 工程导出，缓冲暂为对称；不是完整移植 |
| [chengfeng-videocut-skills](https://github.com/Agentchengfeng/chengfeng-videocut-skills) / 3,049 | 中文精剪方法将修字、重复、残句改口、口头禅分轮处理，使用词 ID 与删词表 | 本包新增分类精剪规则、word_id、删除理由、保留理由、原文指纹和切口表；先修字再判断删词 | 当前上游还要求配套 Runtime，并有版本能力限制与强制云端 ASR 约定，不能直接作为 WorkBuddy 自包含模块；只吸收方法，不复制这些外部约束 |
| [WhisperX](https://github.com/m-bain/whisperX) / 24,455 | 语言相关的强制对齐后端，另有说话人分离；比单纯相信 ASR 词时间更适合精确切口 | 本轮明确区分 ASR 时间与已校准时间；检测重叠、零时长词、切进词的问题 | 尚未接入强制对齐/说话人分离。需额外模型；CPU/Mac 支持不代表轻量或已实测；不能宣称本轮获得 WhisperX 精度 |
| [stable-ts](https://github.com/jianfch/stable-ts) / 2,282 | 音轨静音辅助时间调整、align/refine、按标点与间隔重分组 | 借鉴声学证据与词轴交叉检查、剪后重分组字幕；不把 ASR 空隙等同静音 | 本轮仅做区间交集与时间轴校验，不运行 stable-ts，也不声称修复了原 ASR 时间 |
| [captacity](https://github.com/unconv/captacity) / 139 | 字幕字体、字号、色彩、描边、宽度等参数化，代码另有逐词高亮与阴影 | 同一 PNG 渲染器增加三种预设与可调参数、样式静帧预览；精剪默认更大的 60px 白字黑描边 | 上游维护较久未更新，不列为高星主方案。本轮没有卡拉 OK、阴影或字幕动画，accent 是整条黄字 |
| [auto-edit-video-skill](https://github.com/natyang1234/auto-edit-video-skill) / 1 | 可复核删词建议、字幕校准记录、独立机械/语义状态和本地编辑界面 | 借鉴显式区分未决定、已决定、机器检查、听音待验收；未决定候选保持原声 | 关注度低，不能称成熟高星；未移植 Studio、Ollama、审批体系。源码部分旧 render_cut 已标 legacy，未复制 |
| [video-editor](https://github.com/lainshao/video-editor) / 7 | 中文口播画面、字幕高亮、动画与透明叠加层模块化 | 作为扩展路线参考，本轮聚焦精剪与清晰字幕 | pre-1.0、依赖更多；未引入动画链路或其 node_modules，不把低星技能当成已验证最佳方案 |

上述数字源于官方公共 API，完整快照存于本次任务的研究目录（不随技能包携带第三方全文）。

## 已落实的运行能力

新增 `scripts/editorial.py`：

- analyze：生成有原片时间、上下文、词 ID、风险说明的停顿/填充词/相邻重复候选；全部初始 pending。
- build：消费宿主的删留判断，合并范围、校验素材与转录指纹、拒绝切进词、按保留词重建 output SRT；生成切口听音清单。
- style-preview：同一字体渲染器在真实视频帧上生成 classic/readable/accent 三种样式。

video.py 增加真实静音区间输出、可校验字幕样式、短术语识别提示和词概率保存。原引擎负责编码/解码/合成，WorkBuddy 负责分类阅读、语义删留判断。逻辑整理是宿主工作流改进，不是本地规则脚本具有理解能力。

## 为什么暂不直接换引擎

用户目标是 Mac 上小白能用的 WorkBuddy 技能。直接装配一整个运行时、云端 ASR 或 GPU 对齐栈会增加安装和素材上传成本。先补足本轮确实验证过的精剪数据链路与字幕控制，再独立验证强制对齐。第三方新技能没有实际测试过的特性，不写进本包的已支持清单。

## 来源与许可

本轮阅读了 auto-editor 的 `skills/auto-editor/SKILL.md`，chengfeng 的 `skills/chengfeng-cut/SKILL.md`，captacity 的 Python 字幕实现，以及 auto-edit-video-skill 的部分裁切代码；其余主要核查官方 README。方法与接口独立实现，未复制第三方代码、字体、模型或运行时。因此本包仍采用原 MIT 许可；引用链接用于明确方法来源，不声称第三方背书。

上游仓库许可快照：auto-editor Unlicense；chengfeng Apache-2.0；WhisperX BSD-2-Clause；stable-ts/captacity/两项低星技能 MIT。若以后移植代码或分发模型，必须按实际文件和版本重新核查许可与通知；当前仅调用用户本机已有 FFmpeg/faster-whisper/Pillow。
