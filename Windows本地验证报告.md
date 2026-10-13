# Windows 测试版的本地验证

版本：0.2.3-windows-test.3。运行平台：macOS-26.6.2-arm64-arm-64bit。

32 项通过，0 失败、0 错误、0 跳过。包括合成媒体剪辑、字幕与底片复用、原片保护、Windows 路径/字体/编码，以及依赖缺失时阻止剪辑并给下载引导。Mac 上运行的 check_environment.py 实际验证了 FFmpeg 的 H.264/AAC 编码、Pillow 和字体。prepare_model.py 在没有明确 --allow-download 参数时拒绝下载。

Windows PowerShell 启动脚本尚未在 Windows 实机运行；Windows 客户端导入、安装引导、转录模型与真实素材出片仍待验收。SKILL.md 格式、相对文档链接和 ZIP CRC 检查通过。技能包不含视频、字体、模型、运行环境或密钥。
