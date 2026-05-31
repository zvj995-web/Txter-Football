# txter-backend — FastAPI 后端

Claude Code 的延伸插件。提供文案生成、选题实验室、音频打磨、公众号文章 4 个 Tab 的后端服务。

## 启动

```bash
cd /home/ubuntu/projects/txter-backend
source venv/bin/activate
python run.py  # http://0.0.0.0:8000
```

单端口模式：FastAPI serve 前端 dist + API。改前端后 `npm run build` 重建。

## Skill 系统（2026-05-28 重建）

两种格式共存：

| 格式 | 目录 | 用途 |
|------|------|------|
| **新格式** `manifest.yaml` + `system_prompt.md` | `skills/{name}/` | Tab 1 文案生成 + Tab 2 选题生成 |
| **旧格式** `SKILL.md` | `~/.hermes/skills/` | Tab 4 公众号文章 (仅 wechat-article 类型) |

新格式 skill 由 Claude Code 从零撰写，不复用 Hermes 旧内容。manifest 支持 `constraints`（严格参考/知识发挥）等元数据。system_prompt.md 使用 `{variable}` 占位符。

当前 skill 清单：
- `yssq-copywriting` — 弈神说球 · Data Sniper 文案
- `persona-copywriting` — 转体世界波 · 纪录片文案
- `yssq-topic-lab` — 弈神说球 · 选题实验室
- `persona-topic-lab` — 转体世界波 · 选题实验室
- `txter-football-yssq-wechat-article` (legacy) — 弈神公众号
- `txter-persona-wechat-article` (legacy) — 转体公众号

## API 端点 (22 total)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/skills?type=` | 技能列表 (copywriting/topic-generation/wechat-article) |
| GET | `/api/reports?keyword=` | 素材文件搜索 |
| GET | `/api/files?keyword=` | 素材文件浏览 |
| GET | `/api/topics` | 所有选题库 |
| GET | `/api/topics/:id` | 单个选题库 |
| GET | `/api/topics/:id/random` | 随机选题 |
| POST | `/api/topics/:id/dimension` | 追加维度 (含备份+去重+回滚) |
| POST | `/api/topics/:id/generate` | AI 生成候选选题 |
| POST | `/api/topics/:id/append` | 选题入库 (含备份+回滚) |
| POST | `/api/generate/copywriting` | 文案生成 (支持 constraint) |
| POST | `/api/generate/wechat` | 公众号 4-node pipeline |
| POST | `/api/generate/wechat/stream` | 公众号 SSE 流式 |
| POST | `/api/polish` | 音频打磨 |
| POST | `/api/polish/iterate` | 迭代打磨 (含 previousResult 上下文) |
| POST | `/api/rag/query` | ChromaDB 语义检索 (chunk 级) |
| POST | `/api/rag/aggregate` | ChromaDB 完整文档检索 |
| GET | `/api/pipelines` | pipeline 列表 (11 个) |
| GET | `/api/brainstorm-outlines` | 大纲文件列表 |
| GET | `/api/brainstorm-outlines/:file` | 大纲文件详情 |
| GET | `/api/references?ip=` | 参考范文列表 |
| GET | `/api/config` | 读取完整配置 |
| POST | `/api/config` | 更新配置 |
| POST | `/api/save` | 保存文件 (sanitize + 元数据头 + 反冲突) |

## 依赖

- `~/.hermes/auth.json` — DeepSeek credential pool
- `~/.hermes/skills/` — wechat-article 旧格式 skill 文件
- `skills/` — 新格式 skill (项目内)
- `txter-workbench/config.json` — managed_paths 等配置
- `txter-workbench/topic_libraries/` — 选题库 markdown 文件
- `football-rag/chroma_db/` — ChromaDB 向量库
- `football-rag/team_map.json` — 队名映射
- `.env` — GEMINI_API_KEY

## 项目结构

```
skills/              # 新格式 skill 定义
  {name}/
    manifest.yaml
    system_prompt.md
app/
  main.py            # FastAPI + CORS + 静态文件 serve
  core/              # config.py, dependencies.py
  models/            # skills, reports, topics, generation, polish, rag, misc
  routers/           # skills, reports, topics, generation, polish, rag, misc
  services/          # skill, topic, report, generation, polish, rag, config,
                     # misc, sensitive_word
```
