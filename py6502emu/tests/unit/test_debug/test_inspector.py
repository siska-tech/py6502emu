"""
Unit tests for state inspection functionality.

Tests PU015: StateInspector functionality including register inspection,
flag inspection, memory inspection, and state formatting.
"""

import pytest
from unittest.mock import Mock, MagicMock

from py6502emu.debug.inspector import (
    StateInspector,
    RegisterInspector,
    FlagInspector,
    MemoryInspector,
    RegisterState,
    FlagState,
    MemoryDump,
    DisplayFormat
)


class TestRegisterState:
    """Test RegisterState functionality."""
    
    def test_register_state_creation(self):
        """Test register state creation."""
        state = RegisterState(
            a=0x42, x=0x10, y=0x20,
            pc=0x1000, s=0xFF, p=0x34
        )
        
        assert state.a == 0x42
        assert state.x == 0x10
        assert state.y == 0x20
        assert state.pc == 0x1000
        assert state.s == 0xFF
        assert state.p == 0x34
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        state = RegisterState(
            a=0x42, x=0x10, y=0x20,
            pc=0x1000, s=0xFF, p=0x34
        )
        
        expected = {
            'A': 0x42, 'X': 0x10, 'Y': 0x20,
            'PC': 0x1000, 'S': 0xFF, 'P': 0x34
        }
        
        assert state.to_dict() == expected


class TestFlagState:
    """Test FlagState functionality."""
    
    def test_flag_state_creation(self):
        """Test flag state creation."""
        state = FlagState(
            negative=True, overflow=False, unused=True,
            break_flag=False, decimal=False, interrupt=True,
            zero=False, carry=True
        )
        
        assert state.negative is True
        assert state.overflow is False
        assert state.carry is True
    
    def test_to_mnemonic(self):
        """Test mnemonic conversion."""
        state = FlagState(
            negative=True, overflow=False, unused=True,
            break_flag=True, decimal=False, interrupt=True,
            zero=False, carry=True
        )
        
        mnemonic = state.to_mnemonic()
        assert mnemonic == "Nv-BdIzC"
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        state = FlagState(
            negative=True, overflow=False, unused=True,
            break_flag=False, decimal=False, interrupt=True,
            zero=False, carry=True
        )
        
        expected = {
            'N': True, 'V': False, 'U': True,
            'B': False, 'D': False, 'I': True,
            'Z': False, 'C': True
        }
        
        assert state.to_dict() == expected


class TestMemoryDump:
    """Test MemoryDump functionality."""
    
    def test_memory_dump_creation(self):
        """Test memory dump creation."""
        data = bytes([0x42, 0x43, 0x44, 0x45])
        dump = MemoryDump(start_address=0x1000, data=data)
        
        assert dump.start_address == 0x1000
        assert dump.data == data
        assert dump.bytes_per_line == 16
    
    def test_format_hex_dump_simple(self):
        """Test hex dump formatting."""
        data = bytes([0x42, 0x43, 0x44, 0x45])
        dump = MemoryDump(start_address=0x1000, data=data, bytes_per_line=4)
        
        lines = dump.format_hex_dump(show_ascii=False)
        assert len(lines) == 1
        assert "1000:" in lines[0]
        assert "42 43 44 45" in lines[0]
    
    def test_format_hex_dump_with_ascii(self):
        """Test hex dump formatting with ASCII."""
        data = bytes([0x41, 0x42, 0x43, 0x44])  # "ABCD"
        dump = MemoryDump(start_address=0x1000, data=data, bytes_per_line=4)
        
        lines = dump.format_hex_dump(show_ascii=True)
        assert len(lines) == 1
        assert "|ABCD|" in lines[0]
    
    def test_format_hex_dump_non_printable(self):
        """Test hex dump with non-printable characters."""
        data = bytes([0x00, 0x01, 0x02, 0x03])
        dump = MemoryDump(start_address=0x1000, data=data, bytes_per_line=4)
        
        lines = dump.format_hex_dump(show_ascii=True)
        assert len(lines) == 1
        assert "|....|" in lines[0]
    
    def test_format_hex_dump_multiple_lines(self):
        """Test hex dump with multiple lines."""
        data = bytes(range(32))  # 32 bytes
        dump = MemoryDump(start_address=0x1000, data=data, bytes_per_line=16)
        
        lines = dump.format_hex_dump()
        assert len(lines) == 2
        assert "1000:" in lines[0]
        assert "1010:" in lines[1]


class TestRegisterInspector:
    """Test RegisterInspector functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_registers = Mock()
        self.mock_registers.a = 0x42
        self.mock_registers.x = 0x10
        self.mock_registers.y = 0x20
        self.mock_registers.pc = 0x1000
        self.mock_registers.s = 0xFF
        self.mock_registers.p = 0x34
        
        self.mock_flags = Mock()
        
        self.inspector = RegisterInspector(self.mock_registers, self.mock_flags)
    
    def test_get_register_state(self):
        """Test getting register state."""
        state = self.inspector.get_register_state()
        
        assert state.a == 0x42
        assert state.x == 0x10
        assert state.y == 0x20
        assert state.pc == 0x1000
        assert state.s == 0xFF
        assert state.p == 0x34
    
    def test_format_registers_hex(self):
        """Test register formatting in hexadecimal."""
        lines = self.inspector.format_registers(DisplayFormat.HEXADECIMAL)
        
        assert len(lines) == 2
        assert "$42" in lines[0]  # A register
        assert "$1000" in lines[1]  # PC register
    
    def test_format_registers_decimal(self):
        """Test register formatting in decimal."""
        lines = self.inspector.format_registers(DisplayFormat.DECIMAL)
        
        assert len(lines) == 2
        assert "66" in lines[0]  # A register (0x42 = 66)
        assert "4096" in lines[1]  # PC register (0x1000 = 4096)
    
    def test_format_registers_binary(self):
        """Test register formatting in binary."""
        lines = self.inspector.format_registers(DisplayFormat.BINARY)
        
        assert len(lines) == 2
        assert "01000010" in lines[0]  # A register (0x42 in binary)
    
    def test_compare_registers(self):
        """Test register comparison."""
        previous_state = RegisterState(
            a=0x41, x=0x10, y=0x20,
            pc=0x1000, s=0xFF, p=0x34
        )
        
        changes = self.inspector.compare_registers(previous_state)
        
        assert 'A' in changes
        assert changes['A'] == (0x41, 0x42)
        assert 'X' not in changes  # No change


class TestFlagInspector:
    """Test FlagInspector functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_flags = Mock()
        self.mock_flags.negative = True
        self.mock_flags.overflow = False
        self.mock_flags.break_flag = False
        self.mock_flags.decimal = False
        self.mock_flags.interrupt = True
        self.mock_flags.zero = False
        self.mock_flags.carry = True
        
        self.inspector = FlagInspector(self.mock_flags)
    
    def test_get_flag_state(self):
        """Test getting flag state."""
        state = self.inspector.get_flag_state()
        
        assert state.negative is True
        assert state.overflow is False
        assert state.unused is True  # Always true
        assert state.carry is True
    
    def test_format_flags(self):
        """Test flag formatting."""
        lines = self.inspector.format_flags(show_descriptions=False)
        
        assert len(lines) == 1
        assert "Nv-bdIzC" in lines[0]
    
    def test_format_flags_with_descriptions(self):
        """Test flag formatting with descriptions."""
        lines = self.inspector.format_flags(show_descriptions=True)
        
        assert len(lines) > 1
        assert "N (Negative):   SET" in lines
        assert "V (Overflow):   CLEAR" in lines
    
    def test_compare_flags(self):
        """Test flag comparison."""
        previous_state = FlagState(
            negative=False, overflow=False, unused=True,
            break_flag=False, decimal=False, interrupt=True,
            zero=False, carry=True
        )
        
        changes = self.inspector.compare_flags(previous_state)
        
        assert 'N' in changes
        assert changes['N'] == (False, True)
        assert 'C' not in changes  # No change


class TestMemoryInspector:
    """Test MemoryInspector functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_memory = Mock()
        self.inspector = MemoryInspector(self.mock_memory)
    
    def test_dump_memory(self):
        """Test memory dumping."""
        # Mock memory reads
        test_data = [0x42, 0x43, 0x44, 0x45]
        self.mock_memory.read_byte.side_effect = test_data
        
        dump = self.inspector.dump_memory(0x1000, 4)
        
        assert dump.start_address == 0x1000
        assert dump.data == bytes(test_data)
        assert self.mock_memory.read_byte.call_count == 4
    
    def test_dump_memory_with_error(self):
        """Test memory dumping with read errors."""
        def mock_read(addr):
            if addr == 0x1001:
                raise Exception("Read error")
            return 0x42
        
        self.mock_memory.read_byte.side_effect = mock_read
        
        dump = self.inspector.dump_memory(0x1000, 4)
        
        assert dump.data[0] == 0x42
        assert dump.data[1] == 0x00  # Error should result in 0
    
    def test_format_memory_dump(self):
        """Test memory dump formatting."""
        test_data = list(range(16))
        self.mock_memory.read_byte.side_effect = test_data
        
        lines = self.inspector.format_memory_dump(0x1000, 16)
        
        assert len(lines) == 1
        assert "1000:" in lines[0]
    
    def test_search_memory(self):
        """Test memory search."""
        # Create test memory pattern
        memory_data = [0x00] * 256
        memory_data[0x10:0x14] = [0x42, 0x43, 0x44, 0x45]  # "BCDE"
        memory_data[0x20:0x24] = [0x42, 0x43, 0x44, 0x45]  # Another "BCDE"
        
        def mock_read(addr):
            return memory_data[addr] if 0 <= addr < len(memory_data) else 0
        
        self.mock_memory.read_byte.side_effect = mock_read
        
        matches = self.inspector.search_memory(bytes([0x42, 0x43]), 0x00, 0xFF)
        
        assert 0x10 in matches
        assert 0x20 in matches
    
    def test_get_memory_statistics(self):
        """Test memory statistics."""
        test_data = [0x00, 0x00, 0xFF, 0x42, 0x42]
        self.mock_memory.read_byte.side_effect = test_data
        
        stats = self.inspector.get_memory_statistics(0x1000, 5)
        
        assert stats['length'] == 5
        assert stats['zero_bytes'] == 2
        assert stats['ff_bytes'] == 1
        assert stats['most_common_byte'] in [0x00, 0x42]  # Both appear twice


class TestStateInspector:
    """Test StateInspector integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_registers = Mock()
        self.mock_registers.a = 0x42
        self.mock_registers.x = 0x10
        self.mock_registers.y = 0x20
        self.mock_registers.pc = 0x1000
        self.mock_registers.s = 0xFF
        self.mock_registers.p = 0x34
        
        self.mock_flags = Mock()
        self.mock_flags.negative = True
        self.mock_flags.overflow = False
        self.mock_flags.break_flag = False
        self.mock_flags.decimal = False
        self.mock_flags.interrupt = True
        self.mock_flags.zero = False
        self.mock_flags.carry = True
        
        self.mock_memory = Mock()
        
        self.inspector = StateInspector(
            self.mock_registers,
            self.mock_flags,
            self.mock_memory
        )
    
    def test_add_remove_device(self):
        """Test device management."""
        mock_device = Mock()
        
        self.inspector.add_device("test_device", mock_device)
        assert "test_device" in self.inspector._devices
        
        assert self.inspector.remove_device("test_device") is True
        assert "test_device" not in self.inspector._devices
        
        assert self.inspector.remove_device("nonexistent") is False
    
    def test_get_full_system_state(self):
        """Test getting full system state."""
        mock_device = Mock()
        mock_device.get_state.return_value = {"status": "active"}
        self.inspector.add_device("test_device", mock_device)
        
        state = self.inspector.get_full_system_state()
        
        assert 'registers' in state
        assert 'flags' in state
        assert 'devices' in state
        assert 'test_device' in state['devices']
    
    def test_format_system_summary(self):
        """Test system summary formatting."""
        lines = self.inspector.format_system_summary()
        
        assert any("CPU Registers" in line for line in lines)
        assert any("Processor Flags" in line for line in lines)
    
    def test_format_memory_region(self):
        """Test memory region formatting."""
        test_data = [0x42, 0x43, 0x44, 0x45]
        self.mock_memory.read_byte.side_effect = test_data
        
        lines = self.inspector.format_memory_region(0x1000, 4, "Test Region")
        
        assert any("Test Region" in line for line in lines)
        assert any("1000:" in line for line in lines)
