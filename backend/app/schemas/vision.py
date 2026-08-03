from pydantic import BaseModel, Field


class VisionAnalyzeRequest(BaseModel):
    prompt: str | None = Field(default=None, max_length=2000)


class VisionQuestionRequest(BaseModel):
    question: str | None = Field(default=None, max_length=2000)


class VisionAnalysisResponse(BaseModel):
    file_id: str
    result: str
