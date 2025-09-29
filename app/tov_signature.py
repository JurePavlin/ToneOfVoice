from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

class AddressPolicy(BaseModel):
    allowed: List[str] = []
    banned: List[str] = []

class ToneOfVoiceSignature(BaseModel):
    brand: str
    languages: List[str]
    tone: List[str]
    language_style: List[str]
    formality_level: str = Field(pattern="^(informal|neutral|formal)$")
    address_forms: Dict[str, AddressPolicy]
    emotional_appeal: Dict[str, float]

JSON_SCHEMA = ToneOfVoiceSignature.model_json_schema()
