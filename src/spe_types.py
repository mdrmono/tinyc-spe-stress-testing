# Skeletal Program Enumeration Term Project
# Authors: Rashed Hadi (rmh7), Kavi Godden (kgodden), Manuel Delfin(mda99)

from dataclasses import dataclass
from typing import List, Dict, Any

# file to store the types for the SPE

@dataclass
class Variable:
    name: str
    type_info: str
    scope: str
    is_pointer: bool = False
    is_array: bool = False


@dataclass
class Hole:
    start: int
    end: int
    type_info: str
    scope: str


@dataclass
class ParseResult:
    variables: List[Variable]
    holes: List[Hole]
    skeleton_structure: Dict[str, Any]
    scopes: List[str]
    global_hole_indices: List[int]


__all__ = ["Variable", "Hole", "ParseResult"]


