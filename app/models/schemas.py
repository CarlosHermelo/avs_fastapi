# app/models/schemas.py
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class QuestionRequest(BaseModel):
    """
    Modelo para las solicitudes de preguntas básicas
    """
    question_input: str
    fecha_desde: Optional[str] = Field(None, description="Fecha de inicio para filtrar documentos")
    fecha_hasta: Optional[str] = Field(None, description="Fecha fin para filtrar documentos")
    k: Optional[int] = Field(5, description="Número de documentos a recuperar")

class AnswerResponse(BaseModel):
    """
    Modelo para las respuestas básicas
    """
    answer: str
    metadata: Dict[str, Any] = Field(
        default={},
        description="Metadatos sobre la respuesta"
    )

# Nuevos modelos para el endpoint de análisis completo
class CompleteAnalysisRequest(BaseModel):
    """
    Modelo para las solicitudes de análisis completo
    """
    question_input: str = Field(..., description="Pregunta del usuario")
    id_usuario: Optional[int] = Field(None, description="ID del usuario que realiza la consulta")
    ugel_origen: Optional[str] = Field(None, description="UGL de origen del usuario")

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
    answer: str = Field(..., description="Respuesta generada")
    metadata: Dict[str, Any] = Field(
        default={},
        description="Metadatos sobre la respuesta"
    )
