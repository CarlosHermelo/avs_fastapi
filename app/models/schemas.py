# app/models/schemas.py
from pydantic import BaseModel
from typing import Dict, Any, Optional

class QuestionRequest(BaseModel):
    question_input: str
    fecha_desde: str
    fecha_hasta: str
    k: int

class AnswerResponse(BaseModel):
    answer: str

# Nuevos modelos para el endpoint de análisis completo
class CompleteAnalysisRequest(BaseModel):
    question_input: str
    fecha_desde: str
    fecha_hasta: str
    k: Optional[int] = 4

class AnalysisMetadata(BaseModel):
    document_count: int
    model: str
    question: str
    fecha_desde: str
    fecha_hasta: str

class CompleteAnalysisResponse(BaseModel):
    answer: str
    metadata: AnalysisMetadata
