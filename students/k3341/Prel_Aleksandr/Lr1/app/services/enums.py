from enum import Enum

from fastapi import HTTPException, status


def parse_enum(enum_class: type[Enum], value: str, field_name: str):
    try:
        return enum_class(value)
    except ValueError:
        allowed = ", ".join(item.value for item in enum_class)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be one of: {allowed}",
        )
