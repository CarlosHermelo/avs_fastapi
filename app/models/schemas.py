# app/models/schemas.py
from pydantic import BaseModel
from typing import Dict, Any, Optional

class QuestionRequest(BaseModel):
    """
    Modelo para las solicitudes de preguntas básicas
    """
    question_input: str
    fecha_desde: str = "2023-01-01"
    fecha_hasta: str = "2024-12-31"
    k: int = 5

class AnswerResponse(BaseModel):
    """
    Modelo para las respuestas básicas
    """
    answer: str

# Nuevos modelos para el endpoint de análisis completo
class CompleteAnalysisRequest(BaseModel):
    """
    Modelo para las solicitudes de análisis completo
    """
    question_input: str
    fecha_desde: Optional[str] = None
    fecha_hasta: Optional[str] = None
    k: Optional[int] = None

class AnalysisMetadata(BaseModel):
    document_count: int
    model: str
    question: str
    fecha_desde: str
    fecha_hasta: str

class CompleteAnalysisResponse(BaseModel):
    """
    Modelo para las respuestas de análisis completo
    """
    answer: str
    metadata: Dict = {}
