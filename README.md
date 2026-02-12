# Rabbit Translator
<img width="1086" height="633" alt="image" src="https://github.com/user-attachments/assets/26493ef7-d77f-4258-9fb1-53d7a066704c" />

基于浏览器 **Web Speech API** 的实时语音转写 + VRChat OSC 发送工具。  
**无需付费 API**、**不需要翻墙**、启动快，并且是目前识别速度最快的！！无言势亲身体会！！而且可以设置好玩的前缀后缀，好多玩法等你发现~~ 
**体积小**、**设置简单**，只有不到10M体积！无需安装，开箱即用。


## 功能亮点
- 实时流式语音识别（目前体感语音识别最快的！针对长句子进行特别优化，不会让你再丢句）
- 语音触发识别（可以根据自己麦克风的状况调节激活阈值，和VRC一样）
- 静音自动结束会话，结束时间到了之后，自动清空聊天框（可以设定气泡的停留时间）
- VRChat 输入气泡 + “正在输入”提示 + 输入完成后的提示音（他人听到的）
- 转换中文本的即时输出（长句子，多句话都可以正常拼接发送）
- 可以自定义的前缀 / 后缀（支持多个随机选择 用逗号分隔）
- 违禁词拦截（命中即停止发送）
- 关键词替换（比如说我设置了 姜茶=>笨蛋 那么当你说姜茶的时候就会自动替换为“笨蛋”啦！）
- 会话提示音（开始/结束）
- 多语言 UI（简体/繁体/英/日/韩）


<img width="1086" height="633" alt="image" src="https://github.com/user-attachments/assets/a9990294-55b8-4b11-94d9-9de5329928a3" />

## 系统要求
- Windows 10/11
- 已安装 Chrome 或 Edge（用于 Web Speech API）
- VRChat 已开启 OSC

## 快速开始
1. [下载Release版本Zip](https://github.com/chiooone/Rabbit-Translator/releases)

2. 解压并运行 RabbitTranslator.exe （如果有杀毒软件可能会有警报）

3. 在RabbitTranslator中点击 **开始** 并且 **允许麦克风访问权限**

4. 在VRC中开启OSC功能

## 重要说明
- 本工具依赖浏览器 Web Speech API，**不需要付费 API**，也**不需要翻墙**。
- 识别窗口在后台/被遮挡时，浏览器可能降低识别能力；建议保持窗口可见（小窗也可以）。
- OSC 默认发送到 `127.0.0.1:9000`，如 VRChat 在同机运行无需修改。

## 常见问题
**1. VRChat 没显示文本？**  
确认 VRChat 已开启 OSC，并允许控制聊天框。

**2. WebSocket 断开？**  
请确认 `config.json` 中端口未被占用，必要时更换端口并重启。

如需更多功能或自定义，欢迎提交 Issue 或 PR。
