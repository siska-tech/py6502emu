"""
State inspection functionality for W65C02S emulator debugging.

This module implements PU015: StateInspector functionality including:
- CPU register state display (A, X, Y, PC, S, P)
- Processor flag mnemonic representation
- Memory range hex dump display
- ASCII representation with memory dump
- Device state inspection functionality
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum, auto
import string

from ..cpu.registers import CPURegisters
from ..cpu.flags import ProcessorFlags
from ..memory.memory_controller import MemoryController
from ..core.device import Device


class DisplayFormat(Enum):
    """Display format options for different data types."""
    HEXADECIMAL = auto()
    DECIMAL = auto()
    BINARY = auto()
    ASCII = auto()
    MIXED = auto()


@dataclass
class RegisterState:
    """Snapshot of CPU register state."""
    a: int
    x: int
    y: int
    pc: int
    s: int
    p: int
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary format."""
        return {
            'A': self.a,
            'X': self.x,
            'Y': self.y,
            'PC': self.pc,
            'S': self.s,
            'P': self.p
        }


@dataclass
class FlagState:
    """Snapshot of processor flag state."""
    negative: bool
    overflow: bool
    unused: bool
    break_flag: bool
    decimal: bool
    interrupt: bool
    zero: bool
    carry: bool
    
    def to_mnemonic(self) -> str:
        """Convert flags to mnemonic string (e.g., 'NV-BDIZC')."""
        flags = [
            'N' if self.negative else 'n',
            'V' if self.overflow else 'v',
            '-',  # Unused bit always shown as '-'
            'B' if self.break_flag else 'b',
            'D' if self.decimal else 'd',
            'I' if self.interrupt else 'i',
            'Z' if self.zero else 'z',
            'C' if self.carry else 'c'
        ]
        return ''.join(flags)
    
    def to_dict(self) -> Dict[str, bool]:
        """Convert to dictionary format."""
        return {
            'N': self.negative,
            'V': self.overflow,
            'U': self.unused,
            'B': self.break_flag,
            'D': self.decimal,
            'I': self.interrupt,
            'Z': self.zero,
            'C': self.carry
        }


@dataclass
class MemoryDump:
    """Memory dump with hex and ASCII representation."""
    start_address: int
    data: bytes
    bytes_per_line: int = 16
    
    def format_hex_dump(self, show_ascii: bool = True) -> List[str]:
        """Format memory dump as hex dump lines."""
        lines = []
        
        for i in range(0, len(self.data), self.bytes_per_line):
            address = self.start_address + i
            chunk = self.data[i:i + self.bytes_per_line]
            
            # Format address
            addr_str = f"{address:04X}:"
            
            # Format hex bytes
            hex_bytes = []
            for j, byte in enumerate(chunk):
                if j == 8:  # Add extra space in middle
                    hex_bytes.append(f" {byte:02X}")
                else:
                    hex_bytes.append(f"{byte:02X}")
            
            # Pad hex section if needed
            hex_str = " ".join(hex_bytes)
            if len(chunk) < self.bytes_per_line:
                missing = self.bytes_per_line - len(chunk)
                hex_str += "   " * missing
                if len(chunk) <= 8:
                    hex_str += " "  # Extra space for middle gap
            
            line = f"{addr_str} {hex_str}"
            
            if show_ascii:
                # Format ASCII representation
                ascii_chars = []
                for byte in chunk:
                    if 32 <= byte <= 126:  # Printable ASCII
                        ascii_chars.append(chr(byte))
                    else:
                        ascii_chars.append('.')
                
                ascii_str = ''.join(ascii_chars)
                line += f"  |{ascii_str}|"
            
            lines.append(line)
        
        return lines


class RegisterInspector:
    """Inspects and formats CPU register state."""
    
    def __init__(self, registers: CPURegisters, flags: ProcessorFlags):
        self._registers = registers
        self._flags = flags
    
    def get_register_state(self) -> RegisterState:
        """Get current register state snapshot."""
        return RegisterState(
            a=self._registers.a,
            x=self._registers.x,
            y=self._registers.y,
            pc=self._registers.pc,
            s=self._registers.s,
            p=self._registers.p
        )
    
    def format_registers(self, format_type: DisplayFormat = DisplayFormat.HEXADECIMAL) -> List[str]:
        """Format register display."""
        state = self.get_register_state()
        lines = []
        
        if format_type == DisplayFormat.HEXADECIMAL:
            lines.extend([
                f"A: ${state.a:02X} ({state.a:3d})    X: ${state.x:02X} ({state.x:3d})    Y: ${state.y:02X} ({state.y:3d})",
                f"PC: ${state.pc:04X} ({state.pc:5d})    S: ${state.s:02X} ({state.s:3d})    P: ${state.p:02X} ({state.p:3d})"
            ])
        elif format_type == DisplayFormat.DECIMAL:
            lines.extend([
                f"A: {state.a:3d}    X: {state.x:3d}    Y: {state.y:3d}",
                f"PC: {state.pc:5d}    S: {state.s:3d}    P: {state.p:3d}"
            ])
        elif format_type == DisplayFormat.BINARY:
            lines.extend([
                f"A: {state.a:08b}    X: {state.x:08b}    Y: {state.y:08b}",
                f"PC: {state.pc:016b}    S: {state.s:08b}    P: {state.p:08b}"
            ])
        
        return lines
    
    def compare_registers(self, previous_state: RegisterState) -> Dict[str, Tuple[int, int]]:
        """Compare current state with previous state and return changes."""
        current = self.get_register_state()
        changes = {}
        
        for reg_name in ['a', 'x', 'y', 'pc', 's', 'p']:
            old_val = getattr(previous_state, reg_name)
            new_val = getattr(current, reg_name)
            if old_val != new_val:
                changes[reg_name.upper()] = (old_val, new_val)
        
        return changes


class FlagInspector:
    """Inspects and formats processor flag state."""
    
    def __init__(self, flags: ProcessorFlags):
        self._flags = flags
    
    def get_flag_state(self) -> FlagState:
        """Get current flag state snapshot."""
        return FlagState(
            negative=self._flags.negative,
            overflow=self._flags.overflow,
            unused=True,  # Always true for W65C02S
            break_flag=self._flags.break_flag,
            decimal=self._flags.decimal,
            interrupt=self._flags.interrupt,
            zero=self._flags.zero,
            carry=self._flags.carry
        )
    
    def format_flags(self, show_descriptions: bool = True) -> List[str]:
        """Format flag display."""
        state = self.get_flag_state()
        lines = []
        
        # Mnemonic representation
        mnemonic = state.to_mnemonic()
        lines.append(f"Flags: {mnemonic}")
        
        if show_descriptions:
            flag_descriptions = [
                f"N (Negative):   {'SET' if state.negative else 'CLEAR'}",
                f"V (Overflow):   {'SET' if state.overflow else 'CLEAR'}",
                f"- (Unused):     SET",
                f"B (Break):      {'SET' if state.break_flag else 'CLEAR'}",
                f"D (Decimal):    {'SET' if state.decimal else 'CLEAR'}",
                f"I (Interrupt):  {'SET' if state.interrupt else 'CLEAR'}",
                f"Z (Zero):       {'SET' if state.zero else 'CLEAR'}",
                f"C (Carry):      {'SET' if state.carry else 'CLEAR'}"
            ]
            lines.extend(flag_descriptions)
        
        return lines
    
    def compare_flags(self, previous_state: FlagState) -> Dict[str, Tuple[bool, bool]]:
        """Compare current flags with previous state and return changes."""
        current = self.get_flag_state()
        changes = {}
        
        flag_names = ['negative', 'overflow', 'break_flag', 'decimal', 'interrupt', 'zero', 'carry']
        flag_chars = ['N', 'V', 'B', 'D', 'I', 'Z', 'C']
        
        for flag_name, flag_char in zip(flag_names, flag_chars):
            old_val = getattr(previous_state, flag_name)
            new_val = getattr(current, flag_name)
            if old_val != new_val:
                changes[flag_char] = (old_val, new_val)
        
        return changes


class MemoryInspector:
    """Inspects and formats memory state."""
    
    def __init__(self, memory_controller: MemoryController):
        self._memory = memory_controller
    
    def dump_memory(self, start_address: int, length: int) -> MemoryDump:
        """Dump memory range to MemoryDump object."""
        data = bytearray()
        
        for addr in range(start_address, start_address + length):
            try:
                value = self._memory.read_byte(addr)
                data.append(value)
            except Exception:
                data.append(0)  # Use 0 for inaccessible memory
        
        return MemoryDump(start_address, bytes(data))
    
    def format_memory_dump(self, start_address: int, length: int, 
                          bytes_per_line: int = 16, show_ascii: bool = True) -> List[str]:
        """Format memory dump as hex dump lines."""
        dump = self.dump_memory(start_address, length)
        dump.bytes_per_line = bytes_per_line
        return dump.format_hex_dump(show_ascii)
    
    def search_memory(self, pattern: Union[bytes, str], 
                     start_address: int = 0x0000, end_address: int = 0xFFFF) -> List[int]:
        """Search for pattern in memory and return matching addresses."""
        if isinstance(pattern, str):
            pattern = pattern.encode('ascii')
        
        matches = []
        pattern_len = len(pattern)
        
        for addr in range(start_address, end_address - pattern_len + 1):
            try:
                data = bytes([self._memory.read_byte(addr + i) for i in range(pattern_len)])
                if data == pattern:
                    matches.append(addr)
            except Exception:
                continue
        
        return matches
    
    def get_memory_statistics(self, start_address: int, length: int) -> Dict[str, Any]:
        """Get statistics about a memory range."""
        dump = self.dump_memory(start_address, length)
        data = dump.data
        
        if not data:
            return {'error': 'No data available'}
        
        # Calculate statistics
        zero_bytes = data.count(0)
        ff_bytes = data.count(0xFF)
        unique_values = len(set(data))
        
        # Find most common byte
        byte_counts = {}
        for byte in data:
            byte_counts[byte] = byte_counts.get(byte, 0) + 1
        
        most_common_byte = max(byte_counts.items(), key=lambda x: x[1])
        
        return {
            'start_address': start_address,
            'length': length,
            'zero_bytes': zero_bytes,
            'ff_bytes': ff_bytes,
            'unique_values': unique_values,
            'most_common_byte': most_common_byte[0],
            'most_common_count': most_common_byte[1],
            'entropy': self._calculate_entropy(data)
        }
    
    def _calculate_entropy(self, data: bytes) -> float:
        """Calculate Shannon entropy of data."""
        if not data:
            return 0.0
        
        # Count byte frequencies
        byte_counts = {}
        for byte in data:
            byte_counts[byte] = byte_counts.get(byte, 0) + 1
        
        # Calculate entropy
        entropy = 0.0
        data_len = len(data)
        
        for count in byte_counts.values():
            probability = count / data_len
            if probability > 0:
                entropy -= probability * (probability.bit_length() - 1)
        
        return entropy


class StateInspector:
    """
    Main state inspection interface combining all inspection capabilities.
    
    Provides unified access to CPU registers, processor flags, memory dumps,
    and device state inspection functionality.
    """
    
    def __init__(self, registers: CPURegisters, flags: ProcessorFlags, 
                 memory_controller: MemoryController):
        self.register_inspector = RegisterInspector(registers, flags)
        self.flag_inspector = FlagInspector(flags)
        self.memory_inspector = MemoryInspector(memory_controller)
        self._devices: Dict[str, Device] = {}
    
    def add_device(self, name: str, device: Device) -> None:
        """Add a device for inspection."""
        self._devices[name] = device
    
    def remove_device(self, name: str) -> bool:
        """Remove a device from inspection."""
        if name in self._devices:
            del self._devices[name]
            return True
        return False
    
    def get_full_system_state(self) -> Dict[str, Any]:
        """Get complete system state snapshot."""
        return {
            'registers': self.register_inspector.get_register_state().to_dict(),
            'flags': self.flag_inspector.get_flag_state().to_dict(),
            'devices': {name: self._get_device_state(device) 
                       for name, device in self._devices.items()}
        }
    
    def format_system_summary(self) -> List[str]:
        """Format a complete system state summary."""
        lines = []
        
        # CPU Registers
        lines.append("=== CPU Registers ===")
        lines.extend(self.register_inspector.format_registers())
        lines.append("")
        
        # Processor Flags
        lines.append("=== Processor Flags ===")
        lines.extend(self.flag_inspector.format_flags())
        lines.append("")
        
        # Device States
        if self._devices:
            lines.append("=== Device States ===")
            for name, device in self._devices.items():
                lines.append(f"{name}: {self._format_device_summary(device)}")
            lines.append("")
        
        return lines
    
    def format_memory_region(self, start_address: int, length: int, 
                           label: Optional[str] = None) -> List[str]:
        """Format a labeled memory region dump."""
        lines = []
        
        if label:
            lines.append(f"=== {label} ===")
        
        lines.extend(self.memory_inspector.format_memory_dump(start_address, length))
        lines.append("")
        
        return lines
    
    def _get_device_state(self, device: Device) -> Dict[str, Any]:
        """Get device state information."""
        try:
            # Try to get device state if it has a get_state method
            if hasattr(device, 'get_state'):
                return device.get_state()
            else:
                return {'status': 'active', 'type': type(device).__name__}
        except Exception as e:
            return {'error': str(e), 'type': type(device).__name__}
    
    def _format_device_summary(self, device: Device) -> str:
        """Format a brief device summary."""
        try:
            if hasattr(device, 'get_status'):
                return device.get_status()
            else:
                return f"{type(device).__name__} (active)"
        except Exception:
            return f"{type(device).__name__} (error)"
