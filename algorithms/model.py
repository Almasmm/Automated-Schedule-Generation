# model.py ------------------------------------------------------------

from dataclasses import dataclass, field
from typing import List

@dataclass
class Gene:
    group_codes: List[str]
    course_code: str
    course_name: str
    session_type: str  # lecture / practice / lab
    size: int          # total students in session
    slots_needed: int  # number of 50‑min blocks