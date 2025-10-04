"""
CPU core implementation for W65C02S emulator.

This module provides the complete W65C02S CPU implementation including:
- CPU registers management
- Processor flags handling
- Addressing modes calculation
- Instruction decoding and execution
"""

from .registers import CPURegisters
from .flags import ProcessorFlags
from .addressing import AddressingModes, AddressingMode, AddressingResult

__all__ = [
    "CPURegisters",
    "ProcessorFlags", 
    "AddressingModes",
    "AddressingMode",
    "AddressingResult",
]
