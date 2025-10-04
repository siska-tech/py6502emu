"""
Disassembler for W65C02S emulator debugging.

This module implements PU016: Disassembler functionality including:
- Memory range disassembly
- W65C02S mnemonic conversion
- Operand formatting
- Symbolic label display
- Address to source code mapping
"""

from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum, auto
import re

from ..memory.memory_controller import MemoryController


class AddressingMode(Enum):
    """W65C02S addressing modes."""
    IMPLIED = auto()           # BRK
    ACCUMULATOR = auto()       # ASL A
    IMMEDIATE = auto()         # LDA #$12
    ZERO_PAGE = auto()         # LDA $12
    ZERO_PAGE_X = auto()       # LDA $12,X
    ZERO_PAGE_Y = auto()       # LDA $12,Y
    ABSOLUTE = auto()          # LDA $1234
    ABSOLUTE_X = auto()        # LDA $1234,X
    ABSOLUTE_Y = auto()        # LDA $1234,Y
    INDIRECT = auto()          # JMP ($1234)
    INDEXED_INDIRECT = auto()  # LDA ($12,X)
    INDIRECT_INDEXED = auto()  # LDA ($12),Y
    RELATIVE = auto()          # BNE $1234
    ABSOLUTE_INDEXED_INDIRECT = auto()  # JMP ($1234,X) - W65C02S only
    ZERO_PAGE_INDIRECT = auto()         # LDA ($12) - W65C02S only


@dataclass
class InstructionInfo:
    """Information about a W65C02S instruction."""
    opcode: int
    mnemonic: str
    addressing_mode: AddressingMode
    length: int
    cycles: int
    description: str = ""


@dataclass
class DisassembledInstruction:
    """A disassembled instruction with all formatting information."""
    address: int
    opcode: int
    operand_bytes: List[int]
    mnemonic: str
    operand_text: str
    full_text: str
    length: int
    cycles: int
    addressing_mode: AddressingMode
    target_address: Optional[int] = None  # For branches/jumps
    symbol: Optional[str] = None


class InstructionFormatter:
    """Formats disassembled instructions for display."""
    
    def __init__(self):
        self._address_width = 4  # Default to 4 hex digits
        self._show_bytes = True
        self._show_cycles = False
        self._uppercase = True
    
    def set_options(self, address_width: int = 4, show_bytes: bool = True,
                   show_cycles: bool = False, uppercase: bool = True) -> None:
        """Set formatting options."""
        self._address_width = address_width
        self._show_bytes = show_bytes
        self._show_cycles = show_cycles
        self._uppercase = uppercase
    
    def format_instruction(self, instruction: DisassembledInstruction) -> str:
        """Format a single instruction for display."""
        parts = []
        
        # Address
        addr_format = f"{{:0{self._address_width}X}}"
        parts.append(addr_format.format(instruction.address))
        
        if self._show_bytes:
            # Instruction bytes
            byte_strs = [f"{instruction.opcode:02X}"]
            byte_strs.extend(f"{b:02X}" for b in instruction.operand_bytes)
            
            # Pad to consistent width (3 bytes max for W65C02S)
            while len(byte_strs) < 3:
                byte_strs.append("  ")
            
            parts.append(" ".join(byte_strs))
        
        # Instruction text
        instr_text = instruction.full_text
        if self._uppercase:
            instr_text = instr_text.upper()
        else:
            instr_text = instr_text.lower()
        
        parts.append(instr_text)
        
        if self._show_cycles:
            parts.append(f"[{instruction.cycles}]")
        
        return "  ".join(parts)
    
    def format_instruction_list(self, instructions: List[DisassembledInstruction]) -> List[str]:
        """Format a list of instructions."""
        return [self.format_instruction(instr) for instr in instructions]


class SymbolResolver:
    """Resolves addresses to symbolic names."""
    
    def __init__(self):
        self._symbols: Dict[int, str] = {}
        self._reverse_symbols: Dict[str, int] = {}
    
    def add_symbol(self, address: int, name: str) -> None:
        """Add a symbol at the given address."""
        self._symbols[address] = name
        self._reverse_symbols[name] = address
    
    def remove_symbol(self, address: int) -> bool:
        """Remove symbol at address."""
        if address in self._symbols:
            name = self._symbols[address]
            del self._symbols[address]
            del self._reverse_symbols[name]
            return True
        return False
    
    def get_symbol(self, address: int) -> Optional[str]:
        """Get symbol name for address."""
        return self._symbols.get(address)
    
    def get_address(self, symbol: str) -> Optional[int]:
        """Get address for symbol name."""
        return self._reverse_symbols.get(symbol)
    
    def load_symbols_from_map(self, map_data: str) -> int:
        """Load symbols from linker map format. Returns count loaded."""
        count = 0
        lines = map_data.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith(';'):
                continue
            
            # Parse format: "symbol_name = $address"
            match = re.match(r'(\w+)\s*=\s*\$([0-9A-Fa-f]+)', line)
            if match:
                symbol_name = match.group(1)
                address = int(match.group(2), 16)
                self.add_symbol(address, symbol_name)
                count += 1
        
        return count
    
    def get_all_symbols(self) -> Dict[int, str]:
        """Get all symbols."""
        return self._symbols.copy()


class SourceMapper:
    """Maps addresses to source code locations."""
    
    def __init__(self):
        self._address_to_source: Dict[int, Tuple[str, int]] = {}  # address -> (file, line)
        self._source_to_address: Dict[Tuple[str, int], int] = {}  # (file, line) -> address
    
    def add_mapping(self, address: int, source_file: str, line_number: int) -> None:
        """Add address to source mapping."""
        self._address_to_source[address] = (source_file, line_number)
        self._source_to_address[(source_file, line_number)] = address
    
    def get_source_location(self, address: int) -> Optional[Tuple[str, int]]:
        """Get source location for address."""
        return self._address_to_source.get(address)
    
    def get_address_for_source(self, source_file: str, line_number: int) -> Optional[int]:
        """Get address for source location."""
        return self._source_to_address.get((source_file, line_number))
    
    def load_from_listing(self, listing_data: str) -> int:
        """Load mappings from assembler listing format. Returns count loaded."""
        count = 0
        lines = listing_data.strip().split('\n')
        current_file = "unknown"
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for file directive
            if line.startswith(';') and 'file:' in line.lower():
                match = re.search(r'file:\s*(.+)', line, re.IGNORECASE)
                if match:
                    current_file = match.group(1).strip()
                continue
            
            # Parse listing line: "line_num address bytes instruction"
            match = re.match(r'(\d+)\s+([0-9A-Fa-f]{4})\s+', line)
            if match:
                line_number = int(match.group(1))
                address = int(match.group(2), 16)
                self.add_mapping(address, current_file, line_number)
                count += 1
        
        return count


class Disassembler:
    """
    W65C02S disassembler with full instruction set support.
    
    Provides disassembly of memory ranges with proper W65C02S mnemonic
    conversion, operand formatting, and optional symbolic representation.
    """
    
    def __init__(self, memory_controller: MemoryController):
        self._memory = memory_controller
        self._formatter = InstructionFormatter()
        self._symbol_resolver = SymbolResolver()
        self._source_mapper = SourceMapper()
        
        # Initialize instruction table
        self._instruction_table = self._build_instruction_table()
    
    def _build_instruction_table(self) -> Dict[int, InstructionInfo]:
        """Build the W65C02S instruction decode table."""
        table = {}
        
        # Define instruction information
        # Format: opcode -> (mnemonic, addressing_mode, length, cycles)
        instructions = [
            # ADC - Add with Carry
            (0x69, "ADC", AddressingMode.IMMEDIATE, 2, 2),
            (0x65, "ADC", AddressingMode.ZERO_PAGE, 2, 3),
            (0x75, "ADC", AddressingMode.ZERO_PAGE_X, 2, 4),
            (0x6D, "ADC", AddressingMode.ABSOLUTE, 3, 4),
            (0x7D, "ADC", AddressingMode.ABSOLUTE_X, 3, 4),
            (0x79, "ADC", AddressingMode.ABSOLUTE_Y, 3, 4),
            (0x61, "ADC", AddressingMode.INDEXED_INDIRECT, 2, 6),
            (0x71, "ADC", AddressingMode.INDIRECT_INDEXED, 2, 5),
            (0x72, "ADC", AddressingMode.ZERO_PAGE_INDIRECT, 2, 5),  # W65C02S
            
            # AND - Logical AND
            (0x29, "AND", AddressingMode.IMMEDIATE, 2, 2),
            (0x25, "AND", AddressingMode.ZERO_PAGE, 2, 3),
            (0x35, "AND", AddressingMode.ZERO_PAGE_X, 2, 4),
            (0x2D, "AND", AddressingMode.ABSOLUTE, 3, 4),
            (0x3D, "AND", AddressingMode.ABSOLUTE_X, 3, 4),
            (0x39, "AND", AddressingMode.ABSOLUTE_Y, 3, 4),
            (0x21, "AND", AddressingMode.INDEXED_INDIRECT, 2, 6),
            (0x31, "AND", AddressingMode.INDIRECT_INDEXED, 2, 5),
            (0x32, "AND", AddressingMode.ZERO_PAGE_INDIRECT, 2, 5),  # W65C02S
            
            # ASL - Arithmetic Shift Left
            (0x0A, "ASL", AddressingMode.ACCUMULATOR, 1, 2),
            (0x06, "ASL", AddressingMode.ZERO_PAGE, 2, 5),
            (0x16, "ASL", AddressingMode.ZERO_PAGE_X, 2, 6),
            (0x0E, "ASL", AddressingMode.ABSOLUTE, 3, 6),
            (0x1E, "ASL", AddressingMode.ABSOLUTE_X, 3, 7),
            
            # Branch Instructions
            (0x90, "BCC", AddressingMode.RELATIVE, 2, 2),
            (0xB0, "BCS", AddressingMode.RELATIVE, 2, 2),
            (0xF0, "BEQ", AddressingMode.RELATIVE, 2, 2),
            (0x30, "BMI", AddressingMode.RELATIVE, 2, 2),
            (0xD0, "BNE", AddressingMode.RELATIVE, 2, 2),
            (0x10, "BPL", AddressingMode.RELATIVE, 2, 2),
            (0x50, "BVC", AddressingMode.RELATIVE, 2, 2),
            (0x70, "BVS", AddressingMode.RELATIVE, 2, 2),
            (0x80, "BRA", AddressingMode.RELATIVE, 2, 3),  # W65C02S
            
            # BIT - Bit Test
            (0x24, "BIT", AddressingMode.ZERO_PAGE, 2, 3),
            (0x2C, "BIT", AddressingMode.ABSOLUTE, 3, 4),
            (0x89, "BIT", AddressingMode.IMMEDIATE, 2, 2),  # W65C02S
            (0x34, "BIT", AddressingMode.ZERO_PAGE_X, 2, 4),  # W65C02S
            (0x3C, "BIT", AddressingMode.ABSOLUTE_X, 3, 4),  # W65C02S
            
            # BRK - Break
            (0x00, "BRK", AddressingMode.IMPLIED, 1, 7),
            
            # Clear/Set Flag Instructions
            (0x18, "CLC", AddressingMode.IMPLIED, 1, 2),
            (0xD8, "CLD", AddressingMode.IMPLIED, 1, 2),
            (0x58, "CLI", AddressingMode.IMPLIED, 1, 2),
            (0xB8, "CLV", AddressingMode.IMPLIED, 1, 2),
            (0x38, "SEC", AddressingMode.IMPLIED, 1, 2),
            (0xF8, "SED", AddressingMode.IMPLIED, 1, 2),
            (0x78, "SEI", AddressingMode.IMPLIED, 1, 2),
            
            # Compare Instructions
            (0xC9, "CMP", AddressingMode.IMMEDIATE, 2, 2),
            (0xC5, "CMP", AddressingMode.ZERO_PAGE, 2, 3),
            (0xD5, "CMP", AddressingMode.ZERO_PAGE_X, 2, 4),
            (0xCD, "CMP", AddressingMode.ABSOLUTE, 3, 4),
            (0xDD, "CMP", AddressingMode.ABSOLUTE_X, 3, 4),
            (0xD9, "CMP", AddressingMode.ABSOLUTE_Y, 3, 4),
            (0xC1, "CMP", AddressingMode.INDEXED_INDIRECT, 2, 6),
            (0xD1, "CMP", AddressingMode.INDIRECT_INDEXED, 2, 5),
            (0xD2, "CMP", AddressingMode.ZERO_PAGE_INDIRECT, 2, 5),  # W65C02S
            
            (0xE0, "CPX", AddressingMode.IMMEDIATE, 2, 2),
            (0xE4, "CPX", AddressingMode.ZERO_PAGE, 2, 3),
            (0xEC, "CPX", AddressingMode.ABSOLUTE, 3, 4),
            
            (0xC0, "CPY", AddressingMode.IMMEDIATE, 2, 2),
            (0xC4, "CPY", AddressingMode.ZERO_PAGE, 2, 3),
            (0xCC, "CPY", AddressingMode.ABSOLUTE, 3, 4),
            
            # Decrement Instructions
            (0xC6, "DEC", AddressingMode.ZERO_PAGE, 2, 5),
            (0xD6, "DEC", AddressingMode.ZERO_PAGE_X, 2, 6),
            (0xCE, "DEC", AddressingMode.ABSOLUTE, 3, 6),
            (0xDE, "DEC", AddressingMode.ABSOLUTE_X, 3, 7),
            (0x3A, "DEC", AddressingMode.ACCUMULATOR, 1, 2),  # W65C02S
            
            (0xCA, "DEX", AddressingMode.IMPLIED, 1, 2),
            (0x88, "DEY", AddressingMode.IMPLIED, 1, 2),
            
            # EOR - Exclusive OR
            (0x49, "EOR", AddressingMode.IMMEDIATE, 2, 2),
            (0x45, "EOR", AddressingMode.ZERO_PAGE, 2, 3),
            (0x55, "EOR", AddressingMode.ZERO_PAGE_X, 2, 4),
            (0x4D, "EOR", AddressingMode.ABSOLUTE, 3, 4),
            (0x5D, "EOR", AddressingMode.ABSOLUTE_X, 3, 4),
            (0x59, "EOR", AddressingMode.ABSOLUTE_Y, 3, 4),
            (0x41, "EOR", AddressingMode.INDEXED_INDIRECT, 2, 6),
            (0x51, "EOR", AddressingMode.INDIRECT_INDEXED, 2, 5),
            (0x52, "EOR", AddressingMode.ZERO_PAGE_INDIRECT, 2, 5),  # W65C02S
            
            # Increment Instructions
            (0xE6, "INC", AddressingMode.ZERO_PAGE, 2, 5),
            (0xF6, "INC", AddressingMode.ZERO_PAGE_X, 2, 6),
            (0xEE, "INC", AddressingMode.ABSOLUTE, 3, 6),
            (0xFE, "INC", AddressingMode.ABSOLUTE_X, 3, 7),
            (0x1A, "INC", AddressingMode.ACCUMULATOR, 1, 2),  # W65C02S
            
            (0xE8, "INX", AddressingMode.IMPLIED, 1, 2),
            (0xC8, "INY", AddressingMode.IMPLIED, 1, 2),
            
            # Jump Instructions
            (0x4C, "JMP", AddressingMode.ABSOLUTE, 3, 3),
            (0x6C, "JMP", AddressingMode.INDIRECT, 3, 5),
            (0x7C, "JMP", AddressingMode.ABSOLUTE_INDEXED_INDIRECT, 3, 6),  # W65C02S
            
            (0x20, "JSR", AddressingMode.ABSOLUTE, 3, 6),
            
            # Load Instructions
            (0xA9, "LDA", AddressingMode.IMMEDIATE, 2, 2),
            (0xA5, "LDA", AddressingMode.ZERO_PAGE, 2, 3),
            (0xB5, "LDA", AddressingMode.ZERO_PAGE_X, 2, 4),
            (0xAD, "LDA", AddressingMode.ABSOLUTE, 3, 4),
            (0xBD, "LDA", AddressingMode.ABSOLUTE_X, 3, 4),
            (0xB9, "LDA", AddressingMode.ABSOLUTE_Y, 3, 4),
            (0xA1, "LDA", AddressingMode.INDEXED_INDIRECT, 2, 6),
            (0xB1, "LDA", AddressingMode.INDIRECT_INDEXED, 2, 5),
            (0xB2, "LDA", AddressingMode.ZERO_PAGE_INDIRECT, 2, 5),  # W65C02S
            
            (0xA2, "LDX", AddressingMode.IMMEDIATE, 2, 2),
            (0xA6, "LDX", AddressingMode.ZERO_PAGE, 2, 3),
            (0xB6, "LDX", AddressingMode.ZERO_PAGE_Y, 2, 4),
            (0xAE, "LDX", AddressingMode.ABSOLUTE, 3, 4),
            (0xBE, "LDX", AddressingMode.ABSOLUTE_Y, 3, 4),
            
            (0xA0, "LDY", AddressingMode.IMMEDIATE, 2, 2),
            (0xA4, "LDY", AddressingMode.ZERO_PAGE, 2, 3),
            (0xB4, "LDY", AddressingMode.ZERO_PAGE_X, 2, 4),
            (0xAC, "LDY", AddressingMode.ABSOLUTE, 3, 4),
            (0xBC, "LDY", AddressingMode.ABSOLUTE_X, 3, 4),
            
            # Logical Shift Right
            (0x4A, "LSR", AddressingMode.ACCUMULATOR, 1, 2),
            (0x46, "LSR", AddressingMode.ZERO_PAGE, 2, 5),
            (0x56, "LSR", AddressingMode.ZERO_PAGE_X, 2, 6),
            (0x4E, "LSR", AddressingMode.ABSOLUTE, 3, 6),
            (0x5E, "LSR", AddressingMode.ABSOLUTE_X, 3, 7),
            
            # NOP - No Operation
            (0xEA, "NOP", AddressingMode.IMPLIED, 1, 2),
            
            # OR - Logical OR
            (0x09, "ORA", AddressingMode.IMMEDIATE, 2, 2),
            (0x05, "ORA", AddressingMode.ZERO_PAGE, 2, 3),
            (0x15, "ORA", AddressingMode.ZERO_PAGE_X, 2, 4),
            (0x0D, "ORA", AddressingMode.ABSOLUTE, 3, 4),
            (0x1D, "ORA", AddressingMode.ABSOLUTE_X, 3, 4),
            (0x19, "ORA", AddressingMode.ABSOLUTE_Y, 3, 4),
            (0x01, "ORA", AddressingMode.INDEXED_INDIRECT, 2, 6),
            (0x11, "ORA", AddressingMode.INDIRECT_INDEXED, 2, 5),
            (0x12, "ORA", AddressingMode.ZERO_PAGE_INDIRECT, 2, 5),  # W65C02S
            
            # Stack Instructions
            (0x48, "PHA", AddressingMode.IMPLIED, 1, 3),
            (0x08, "PHP", AddressingMode.IMPLIED, 1, 3),
            (0xDA, "PHX", AddressingMode.IMPLIED, 1, 3),  # W65C02S
            (0x5A, "PHY", AddressingMode.IMPLIED, 1, 3),  # W65C02S
            (0x68, "PLA", AddressingMode.IMPLIED, 1, 4),
            (0x28, "PLP", AddressingMode.IMPLIED, 1, 4),
            (0xFA, "PLX", AddressingMode.IMPLIED, 1, 4),  # W65C02S
            (0x7A, "PLY", AddressingMode.IMPLIED, 1, 4),  # W65C02S
            
            # Rotate Instructions
            (0x2A, "ROL", AddressingMode.ACCUMULATOR, 1, 2),
            (0x26, "ROL", AddressingMode.ZERO_PAGE, 2, 5),
            (0x36, "ROL", AddressingMode.ZERO_PAGE_X, 2, 6),
            (0x2E, "ROL", AddressingMode.ABSOLUTE, 3, 6),
            (0x3E, "ROL", AddressingMode.ABSOLUTE_X, 3, 7),
            
            (0x6A, "ROR", AddressingMode.ACCUMULATOR, 1, 2),
            (0x66, "ROR", AddressingMode.ZERO_PAGE, 2, 5),
            (0x76, "ROR", AddressingMode.ZERO_PAGE_X, 2, 6),
            (0x6E, "ROR", AddressingMode.ABSOLUTE, 3, 6),
            (0x7E, "ROR", AddressingMode.ABSOLUTE_X, 3, 7),
            
            # Return Instructions
            (0x40, "RTI", AddressingMode.IMPLIED, 1, 6),
            (0x60, "RTS", AddressingMode.IMPLIED, 1, 6),
            
            # Subtract with Carry
            (0xE9, "SBC", AddressingMode.IMMEDIATE, 2, 2),
            (0xE5, "SBC", AddressingMode.ZERO_PAGE, 2, 3),
            (0xF5, "SBC", AddressingMode.ZERO_PAGE_X, 2, 4),
            (0xED, "SBC", AddressingMode.ABSOLUTE, 3, 4),
            (0xFD, "SBC", AddressingMode.ABSOLUTE_X, 3, 4),
            (0xF9, "SBC", AddressingMode.ABSOLUTE_Y, 3, 4),
            (0xE1, "SBC", AddressingMode.INDEXED_INDIRECT, 2, 6),
            (0xF1, "SBC", AddressingMode.INDIRECT_INDEXED, 2, 5),
            (0xF2, "SBC", AddressingMode.ZERO_PAGE_INDIRECT, 2, 5),  # W65C02S
            
            # Store Instructions
            (0x85, "STA", AddressingMode.ZERO_PAGE, 2, 3),
            (0x95, "STA", AddressingMode.ZERO_PAGE_X, 2, 4),
            (0x8D, "STA", AddressingMode.ABSOLUTE, 3, 4),
            (0x9D, "STA", AddressingMode.ABSOLUTE_X, 3, 5),
            (0x99, "STA", AddressingMode.ABSOLUTE_Y, 3, 5),
            (0x81, "STA", AddressingMode.INDEXED_INDIRECT, 2, 6),
            (0x91, "STA", AddressingMode.INDIRECT_INDEXED, 2, 6),
            (0x92, "STA", AddressingMode.ZERO_PAGE_INDIRECT, 2, 5),  # W65C02S
            
            (0x86, "STX", AddressingMode.ZERO_PAGE, 2, 3),
            (0x96, "STX", AddressingMode.ZERO_PAGE_Y, 2, 4),
            (0x8E, "STX", AddressingMode.ABSOLUTE, 3, 4),
            
            (0x84, "STY", AddressingMode.ZERO_PAGE, 2, 3),
            (0x94, "STY", AddressingMode.ZERO_PAGE_X, 2, 4),
            (0x8C, "STY", AddressingMode.ABSOLUTE, 3, 4),
            
            (0x64, "STZ", AddressingMode.ZERO_PAGE, 2, 3),  # W65C02S
            (0x74, "STZ", AddressingMode.ZERO_PAGE_X, 2, 4),  # W65C02S
            (0x9C, "STZ", AddressingMode.ABSOLUTE, 3, 4),  # W65C02S
            (0x9E, "STZ", AddressingMode.ABSOLUTE_X, 3, 5),  # W65C02S
            
            # Transfer Instructions
            (0xAA, "TAX", AddressingMode.IMPLIED, 1, 2),
            (0xA8, "TAY", AddressingMode.IMPLIED, 1, 2),
            (0xBA, "TSX", AddressingMode.IMPLIED, 1, 2),
            (0x8A, "TXA", AddressingMode.IMPLIED, 1, 2),
            (0x9A, "TXS", AddressingMode.IMPLIED, 1, 2),
            (0x98, "TYA", AddressingMode.IMPLIED, 1, 2),
            
            # Test and Reset/Set Bit Instructions (W65C02S)
            (0x14, "TRB", AddressingMode.ZERO_PAGE, 2, 5),
            (0x1C, "TRB", AddressingMode.ABSOLUTE, 3, 6),
            (0x04, "TSB", AddressingMode.ZERO_PAGE, 2, 5),
            (0x0C, "TSB", AddressingMode.ABSOLUTE, 3, 6),
        ]
        
        # Build the table
        for opcode, mnemonic, mode, length, cycles in instructions:
            table[opcode] = InstructionInfo(opcode, mnemonic, mode, length, cycles)
        
        return table
    
    def disassemble_instruction(self, address: int) -> DisassembledInstruction:
        """Disassemble a single instruction at the given address."""
        try:
            opcode = self._memory.read_byte(address)
        except Exception:
            # Handle inaccessible memory
            return DisassembledInstruction(
                address=address,
                opcode=0,
                operand_bytes=[],
                mnemonic="???",
                operand_text="",
                full_text="???",
                length=1,
                cycles=0,
                addressing_mode=AddressingMode.IMPLIED
            )
        
        # Look up instruction info
        if opcode not in self._instruction_table:
            # Unknown instruction
            return DisassembledInstruction(
                address=address,
                opcode=opcode,
                operand_bytes=[],
                mnemonic="???",
                operand_text=f"${opcode:02X}",
                full_text=f"??? ${opcode:02X}",
                length=1,
                cycles=0,
                addressing_mode=AddressingMode.IMPLIED
            )
        
        info = self._instruction_table[opcode]
        
        # Read operand bytes
        operand_bytes = []
        for i in range(1, info.length):
            try:
                operand_bytes.append(self._memory.read_byte(address + i))
            except Exception:
                operand_bytes.append(0)  # Use 0 for inaccessible bytes
        
        # Format operand
        operand_text, target_address = self._format_operand(info.addressing_mode, operand_bytes, address)
        
        # Check for symbol
        symbol = None
        if target_address is not None:
            symbol = self._symbol_resolver.get_symbol(target_address)
            if symbol:
                operand_text = symbol
        
        # Build full instruction text
        if operand_text:
            full_text = f"{info.mnemonic} {operand_text}"
        else:
            full_text = info.mnemonic
        
        return DisassembledInstruction(
            address=address,
            opcode=opcode,
            operand_bytes=operand_bytes,
            mnemonic=info.mnemonic,
            operand_text=operand_text,
            full_text=full_text,
            length=info.length,
            cycles=info.cycles,
            addressing_mode=info.addressing_mode,
            target_address=target_address,
            symbol=symbol
        )
    
    def _format_operand(self, mode: AddressingMode, operand_bytes: List[int], 
                       instruction_address: int) -> Tuple[str, Optional[int]]:
        """Format operand based on addressing mode. Returns (text, target_address)."""
        target_address = None
        
        if mode == AddressingMode.IMPLIED:
            return "", None
        
        elif mode == AddressingMode.ACCUMULATOR:
            return "A", None
        
        elif mode == AddressingMode.IMMEDIATE:
            if operand_bytes:
                return f"#${operand_bytes[0]:02X}", None
            return "#$00", None
        
        elif mode == AddressingMode.ZERO_PAGE:
            if operand_bytes:
                target_address = operand_bytes[0]
                return f"${operand_bytes[0]:02X}", target_address
            return "$00", 0
        
        elif mode == AddressingMode.ZERO_PAGE_X:
            if operand_bytes:
                target_address = operand_bytes[0]
                return f"${operand_bytes[0]:02X},X", target_address
            return "$00,X", 0
        
        elif mode == AddressingMode.ZERO_PAGE_Y:
            if operand_bytes:
                target_address = operand_bytes[0]
                return f"${operand_bytes[0]:02X},Y", target_address
            return "$00,Y", 0
        
        elif mode == AddressingMode.ABSOLUTE:
            if len(operand_bytes) >= 2:
                target_address = operand_bytes[0] | (operand_bytes[1] << 8)
                return f"${target_address:04X}", target_address
            return "$0000", 0
        
        elif mode == AddressingMode.ABSOLUTE_X:
            if len(operand_bytes) >= 2:
                target_address = operand_bytes[0] | (operand_bytes[1] << 8)
                return f"${target_address:04X},X", target_address
            return "$0000,X", 0
        
        elif mode == AddressingMode.ABSOLUTE_Y:
            if len(operand_bytes) >= 2:
                target_address = operand_bytes[0] | (operand_bytes[1] << 8)
                return f"${target_address:04X},Y", target_address
            return "$0000,Y", 0
        
        elif mode == AddressingMode.INDIRECT:
            if len(operand_bytes) >= 2:
                addr = operand_bytes[0] | (operand_bytes[1] << 8)
                return f"(${addr:04X})", addr
            return "($0000)", 0
        
        elif mode == AddressingMode.INDEXED_INDIRECT:
            if operand_bytes:
                return f"(${operand_bytes[0]:02X},X)", operand_bytes[0]
            return "($00,X)", 0
        
        elif mode == AddressingMode.INDIRECT_INDEXED:
            if operand_bytes:
                return f"(${operand_bytes[0]:02X}),Y", operand_bytes[0]
            return "($00),Y", 0
        
        elif mode == AddressingMode.RELATIVE:
            if operand_bytes:
                # Calculate branch target
                offset = operand_bytes[0]
                if offset >= 128:
                    offset -= 256  # Convert to signed
                target_address = instruction_address + 2 + offset
                return f"${target_address:04X}", target_address
            return "$0000", instruction_address + 2
        
        elif mode == AddressingMode.ABSOLUTE_INDEXED_INDIRECT:
            if len(operand_bytes) >= 2:
                addr = operand_bytes[0] | (operand_bytes[1] << 8)
                return f"(${addr:04X},X)", addr
            return "($0000,X)", 0
        
        elif mode == AddressingMode.ZERO_PAGE_INDIRECT:
            if operand_bytes:
                return f"(${operand_bytes[0]:02X})", operand_bytes[0]
            return "($00)", 0
        
        return "", None
    
    def disassemble_range(self, start_address: int, end_address: int) -> List[DisassembledInstruction]:
        """Disassemble a range of memory addresses."""
        instructions = []
        address = start_address
        
        while address <= end_address:
            instruction = self.disassemble_instruction(address)
            instructions.append(instruction)
            address += instruction.length
            
            # Safety check to prevent infinite loops
            if len(instructions) > 10000:
                break
        
        return instructions
    
    def disassemble_count(self, start_address: int, count: int) -> List[DisassembledInstruction]:
        """Disassemble a specific number of instructions."""
        instructions = []
        address = start_address
        
        for _ in range(count):
            instruction = self.disassemble_instruction(address)
            instructions.append(instruction)
            address += instruction.length
        
        return instructions
    
    def get_formatter(self) -> InstructionFormatter:
        """Get the instruction formatter."""
        return self._formatter
    
    def get_symbol_resolver(self) -> SymbolResolver:
        """Get the symbol resolver."""
        return self._symbol_resolver
    
    def get_source_mapper(self) -> SourceMapper:
        """Get the source mapper."""
        return self._source_mapper
    
    def format_disassembly(self, instructions: List[DisassembledInstruction]) -> List[str]:
        """Format a list of instructions for display."""
        return self._formatter.format_instruction_list(instructions)
