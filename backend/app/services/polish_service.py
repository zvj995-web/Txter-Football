
from app.core.dependencies import get_ds_client

AUDIO_POLISH_SYSTEM_PROMPT = """
你是一位资深的 AI 配音文案校对师。任务：把一段为短视频 / 播客准备的中文文案，改写成适合主流中文 TTS 引擎（豆包 / 即梦 / MiniMax / 腾讯智影 等）直接朗读的版本。

【必守规则 —— 视觉符号去除】
1. 删除所有 emoji、markdown 装饰符（**、##、-、1.、[]、()等）和分隔线；保留纯文字。
2. 破折号「——」和省略号「……」常被 TTS 忽略或读乱，改用标点控制停顿（逗号 / 句号 / 分号）。
3. 书名号、引号若只是视觉强调而非真引用，可去掉；若是真引用务必保留。

【必守规则 —— 读音规范化】
4. 阿拉伯数字统一改中文：2023 → 二零二三；100 → 一百；2.5 → 二点五；90% → 百分之九十；¥1000 → 一千元。
5. 英文缩写按语境处理：AI → 人工智能；VS → 对阵；NBA → 可保留字母但用空格隔开 N B A；首次出现给中文解释。
6. 单位符号汉化：$ / ¥ / ℃ / km → 美元 / 元 / 摄氏度 / 公里。
7. 同音歧义主动替换，如「他 / 她 / 它」若难分辨，写成「这位男士 / 这位女士 / 这件事」。
8. 生僻字、异体字换成常用字或拼音写法。

【必守规则 —— 节奏控制】
9. 单句不超过 30 字；超长句子按语义切成短句，用句号 / 分号断开。
10. 段落间保留空行，让 TTS 识别成大停顿；句内用逗号控制小停顿。
11. 语气助词（吧、吗、呢、啊、哦、呀、嘛）是 TTS 情感曲线的关键，保留 / 增加。

【必守规则 —— 合规】
12. 博彩类敏感词按语境中性化：赔率 → 数字 / 特定数字组合；赌博 → 博弈 / 决策；买球 → 参与。
13. 不添加任何原文没有的观点或事实。

【输出要求】
- 直接输出完整改写后的文案，一个字都不要解释。
- 保留原文的段落结构、叙事顺序、情绪基调。
- 改动幅度以「能被 AI 语音流畅朗读」为底线，不做风格重写。

【用户的额外指令】（优先级最高，与上述规则冲突时听用户的）
{user_instruction}

【待打磨原文】
{source_text}
""".strip()


async def polish_text(text: str, instruction: str = "") -> str:
    client = await get_ds_client()
    if not client:
        return "Error: DeepSeek client not available"
    prompt = AUDIO_POLISH_SYSTEM_PROMPT.format(
        user_instruction=instruction or "（无额外指令，严格按默认规则改写即可）",
        source_text=text,
    )
    resp = await client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    return resp.choices[0].message.content.strip()


async def polish_iterate(text: str, instruction: str, previous_result: str = "") -> str:
    client = await get_ds_client()
    if not client:
        return "Error: DeepSeek client not available"

    history = ""
    if previous_result:
        history = f"\n【上一轮打磨结果】\n{previous_result}\n"

    prompt = AUDIO_POLISH_SYSTEM_PROMPT.format(
        user_instruction=instruction or "（无额外指令，在上一轮基础上继续优化）",
        source_text=text,
    )
    prompt += f"""
{history}
【注意】这是迭代打磨。你已经看过上一轮的结果，请在上一轮基础上，重点响应用户的新指令，不要退回原始版本。
"""
    resp = await client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    return resp.choices[0].message.content.strip()
