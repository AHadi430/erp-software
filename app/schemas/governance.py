from datetime import date
from pydantic import BaseModel, Field, model_validator


class AccountingPeriodCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    is_closed: bool = False

    @model_validator(mode="after")
    def valid_range(self):
        if self.end_date < self.start_date:
            raise ValueError("End date must be on or after start date")
        return self
