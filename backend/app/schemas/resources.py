from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ResourceName = Annotated[NonEmpty, StringConstraints(max_length=200)]
Description = Annotated[str, StringConstraints(max_length=10_000)]
Category = Annotated[NonEmpty, StringConstraints(max_length=100)]
Condition = Annotated[NonEmpty, StringConstraints(max_length=30)]
Unit = Annotated[NonEmpty, StringConstraints(max_length=50)]
Price = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
TransferType = Literal["donation", "exchange", "sale"]
ListingStatus = Literal["active", "inactive", "depleted"]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResourceCreate(InputModel):
    name: ResourceName
    description: Description | None = None
    category: Category
    condition: Condition
    quantity: int = Field(gt=0)
    unit: Unit
    transfer_type: TransferType
    indicative_price: Price | None = None


class ResourceUpdate(InputModel):
    name: ResourceName | None = None
    description: Description | None = None
    category: Category | None = None
    condition: Condition | None = None
    unit: Unit | None = None
    transfer_type: TransferType | None = None
    indicative_price: Price | None = None

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> "ResourceUpdate":
        for field in ("name", "category", "condition", "unit", "transfer_type"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ResourceStatusUpdate(InputModel):
    status: Literal["active", "inactive"]


class PublicCollegeIdentity(BaseModel):
    id: int
    name: str
    city: str


class MarketplaceResource(BaseModel):
    id: int
    name: str
    description: str | None
    category: str
    condition: str
    quantity_available: int
    unit: str
    transfer_type: TransferType
    indicative_price: Decimal | None
    status: ListingStatus
    image_url: str | None
    college: PublicCollegeIdentity


class ResourceInventoryItem(BaseModel):
    id: int
    name: str
    category: str
    condition: str
    quantity_total: int
    quantity_available: int
    quantity_reserved: int
    unit: str
    status: ListingStatus


class ResourceImageResponse(BaseModel):
    resource_id: int
    image_url: str
    media_type: Literal["image/jpeg", "image/png", "image/webp"]
    size_bytes: int


class ResourceImageEnvelope(BaseModel):
    success: bool
    data: ResourceImageResponse
