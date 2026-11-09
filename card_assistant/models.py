from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ProductInput(BaseModel):
    name: str
    manufacturer: str = "Данных нет"
    specs: dict[str, str] = Field(default_factory=dict)
    description: str = ""
    offer_id: str = ""
    url: str = ""
    category: str = ""

    @field_validator("name")
    @classmethod
    def name_present(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name не может быть пустым")
        return value.strip()


class MissingData(BaseModel):
    field: str
    reason: str
    severity: Literal["critical", "recommended"]


class KeyCharacteristic(BaseModel):
    name: str
    value: str
    source: Literal["specs", "description"] = "specs"


class CommercialBlock(BaseModel):
    suitable_for: list[str] = Field(default_factory=list)
    tasks_solved: list[str] = Field(default_factory=list)
    manager_notes: str = ""


class Validation(BaseModel):
    title_length: int = 0
    description_length: int = 0
    prompt_version: str = "v2"
    warnings: list[str] = Field(default_factory=list)


class Card(BaseModel):
    product_name: str
    source: dict[str, str]
    status: Literal["ok", "needs_clarification"]
    missing_data: list[MissingData]
    seo_title: str
    seo_description: str
    key_characteristics: list[KeyCharacteristic]
    search_queries: list[str]
    commercial_block: CommercialBlock
    validation: Validation = Field(default_factory=Validation)
