from pydantic import BaseModel


class TopicOut(BaseModel):
    title: str
    logic: str
    dimension: str
    style: str = ""
    audience: str = ""
    format: str = ""
    duration: str = ""
    compliance: str = ""
    core_thesis: str = ""
    common_belief: str = ""
    data_required: str = ""
    reader_hook: str = ""
    logic_model: str = ""
    difficulty: str = ""
    hard_number: str = ""
    news_hook: str = ""
    news_material: str = ""
    insider_knowledge: str = ""
    logic_chain: str = ""
    ai_tool_type: str = ""
    life_analogy: str = ""
    news_summary: str = ""
    news_relevance: str = ""


class TopicLibraryOut(BaseModel):
    skillId: str
    skillName: str
    dimensions: list[str]
    topics: list[TopicOut]


class DimensionAddRequest(BaseModel):
    dimensionName: str
    description: str = ""


class TopicGenerateRequest(BaseModel):
    dimension: str = ""
    newsMaterial: str = ""  # B 模式：新闻驱动
    brainstorm: str = ""   # 头脑风暴模式：大纲内容
    count: int = 5


class TopicAppendRequest(BaseModel):
    skillId: str
    title: str
    logic: str = ""
    dimension: str = ""
    style: str = ""
    audience: str = ""
    format: str = ""
    duration: str = ""
    compliance: str = ""


class TopicRefineRequest(BaseModel):
    skillId: str
    topic: dict  # the existing topic with title, logic, dimension, etc.
    feedback: str  # user's improvement suggestions
