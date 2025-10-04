"""
Unit tests for breakpoint management system.

Tests PU013: BreakpointManager functionality including address breakpoints,
conditional breakpoints, and breakpoint state management.
"""

import pytest
from unittest.mock import Mock, patch
import time

from py6502emu.debug.breakpoint import (
    BreakpointManager,
    Breakpoint,
    ConditionalBreakpoint,
    BreakpointHitInfo,
    BreakpointType,
    BreakpointState
)


class TestBreakpoint:
    """Test basic Breakpoint functionality."""
    
    def test_breakpoint_creation(self):
        """Test basic breakpoint creation."""
        bp = Breakpoint(
            id=1,
            address=0x1000,
            type=BreakpointType.ADDRESS,
            description="Test breakpoint"
        )
        
        assert bp.id == 1
        assert bp.address == 0x1000
        assert bp.type == BreakpointType.ADDRESS
        assert bp.state == BreakpointState.ENABLED
        assert bp.hit_count == 0
        assert bp.description == "Test breakpoint"
    
    def test_should_trigger_enabled(self):
        """Test breakpoint triggering when enabled."""
        bp = Breakpoint(id=1, address=0x1000, type=BreakpointType.ADDRESS)
        
        assert bp.should_trigger(0x1000) is True
        assert bp.should_trigger(0x1001) is False
    
    def test_should_trigger_disabled(self):
        """Test breakpoint not triggering when disabled."""
        bp = Breakpoint(id=1, address=0x1000, type=BreakpointType.ADDRESS)
        bp.state = BreakpointState.DISABLED
        
        assert bp.should_trigger(0x1000) is False
    
    def test_ignore_count(self):
        """Test ignore count functionality."""
        bp = Breakpoint(id=1, address=0x1000, type=BreakpointType.ADDRESS, ignore_count=2)
        
        # First two hits should be ignored
        assert bp.should_trigger(0x1000) is False
        assert bp.ignore_count == 1
        
        assert bp.should_trigger(0x1000) is False
        assert bp.ignore_count == 0
        
        # Third hit should trigger
        assert bp.should_trigger(0x1000) is True
    
    def test_on_hit(self):
        """Test breakpoint hit handling."""
        bp = Breakpoint(id=1, address=0x1000, type=BreakpointType.ADDRESS)
        
        context = {
            'cycle_count': 100,
            'instruction': 'LDA #$42',
            'registers': {'A': 0x42}
        }
        
        hit_info = bp.on_hit(context)
        
        assert hit_info.breakpoint_id == 1
        assert hit_info.address == 0x1000
        assert hit_info.cycle_count == 100
        assert hit_info.instruction == 'LDA #$42'
        assert hit_info.registers == {'A': 0x42}
        assert hit_info.hit_count == 1
        
        assert bp.hit_count == 1
        assert bp.state == BreakpointState.HIT


class TestConditionalBreakpoint:
    """Test ConditionalBreakpoint functionality."""
    
    def test_conditional_breakpoint_creation(self):
        """Test conditional breakpoint creation."""
        bp = ConditionalBreakpoint(
            id=1,
            address=0x1000,
            type=BreakpointType.CONDITIONAL,
            condition="A == 0x42"
        )
        
        assert bp.condition == "A == 0x42"
        assert bp.compiled_condition is not None
    
    def test_condition_compilation(self):
        """Test condition compilation."""
        bp = ConditionalBreakpoint(
            id=1,
            address=0x1000,
            type=BreakpointType.CONDITIONAL
        )
        
        bp.condition = "A > 10"
        bp.compile_condition()
        
        assert bp.compiled_condition is not None
    
    def test_invalid_condition(self):
        """Test invalid condition handling."""
        bp = ConditionalBreakpoint(
            id=1,
            address=0x1000,
            type=BreakpointType.CONDITIONAL
        )
        
        with pytest.raises(ValueError):
            bp.condition = "invalid syntax +"
            bp.compile_condition()
    
    def test_unsafe_condition(self):
        """Test unsafe condition detection."""
        bp = ConditionalBreakpoint(
            id=1,
            address=0x1000,
            type=BreakpointType.CONDITIONAL
        )
        
        with pytest.raises(ValueError):
            bp.condition = "__import__('os').system('rm -rf /')"
            bp.compile_condition()
    
    def test_condition_evaluation(self):
        """Test condition evaluation."""
        bp = ConditionalBreakpoint(
            id=1,
            address=0x1000,
            type=BreakpointType.CONDITIONAL,
            condition="A == 0x42"
        )
        
        context = {'A': 0x42}
        assert bp.should_trigger(0x1000, context) is True
        
        context = {'A': 0x43}
        assert bp.should_trigger(0x1000, context) is False
    
    def test_condition_evaluation_error(self):
        """Test condition evaluation error handling."""
        bp = ConditionalBreakpoint(
            id=1,
            address=0x1000,
            type=BreakpointType.CONDITIONAL,
            condition="nonexistent_var == 42"
        )
        
        context = {'A': 0x42}
        # Should not trigger on evaluation error
        assert bp.should_trigger(0x1000, context) is False


class TestBreakpointManager:
    """Test BreakpointManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = BreakpointManager()
    
    def test_add_breakpoint(self):
        """Test adding breakpoints."""
        bp_id = self.manager.add_breakpoint(0x1000)
        
        assert bp_id == 1
        assert len(self.manager.get_all_breakpoints()) == 1
        
        bp = self.manager.get_breakpoint(bp_id)
        assert bp is not None
        assert bp.address == 0x1000
        assert bp.type == BreakpointType.ADDRESS
    
    def test_add_conditional_breakpoint(self):
        """Test adding conditional breakpoints."""
        bp_id = self.manager.add_breakpoint(
            0x1000,
            BreakpointType.CONDITIONAL,
            condition="A == 0x42"
        )
        
        bp = self.manager.get_breakpoint(bp_id)
        assert isinstance(bp, ConditionalBreakpoint)
        assert bp.condition == "A == 0x42"
    
    def test_remove_breakpoint(self):
        """Test removing breakpoints."""
        bp_id = self.manager.add_breakpoint(0x1000)
        
        assert self.manager.remove_breakpoint(bp_id) is True
        assert len(self.manager.get_all_breakpoints()) == 0
        assert self.manager.get_breakpoint(bp_id) is None
        
        # Try to remove non-existent breakpoint
        assert self.manager.remove_breakpoint(999) is False
    
    def test_enable_disable_breakpoint(self):
        """Test enabling/disabling breakpoints."""
        bp_id = self.manager.add_breakpoint(0x1000)
        
        assert self.manager.disable_breakpoint(bp_id) is True
        bp = self.manager.get_breakpoint(bp_id)
        assert bp.state == BreakpointState.DISABLED
        
        assert self.manager.enable_breakpoint(bp_id) is True
        bp = self.manager.get_breakpoint(bp_id)
        assert bp.state == BreakpointState.ENABLED
        
        # Try to enable/disable non-existent breakpoint
        assert self.manager.enable_breakpoint(999) is False
        assert self.manager.disable_breakpoint(999) is False
    
    def test_get_breakpoints_at_address(self):
        """Test getting breakpoints at specific address."""
        bp_id1 = self.manager.add_breakpoint(0x1000)
        bp_id2 = self.manager.add_breakpoint(0x1000, condition="A > 10")
        bp_id3 = self.manager.add_breakpoint(0x2000)
        
        breakpoints_1000 = self.manager.get_breakpoints_at_address(0x1000)
        assert len(breakpoints_1000) == 2
        
        breakpoints_2000 = self.manager.get_breakpoints_at_address(0x2000)
        assert len(breakpoints_2000) == 1
        
        breakpoints_3000 = self.manager.get_breakpoints_at_address(0x3000)
        assert len(breakpoints_3000) == 0
    
    def test_clear_all_breakpoints(self):
        """Test clearing all breakpoints."""
        self.manager.add_breakpoint(0x1000)
        self.manager.add_breakpoint(0x2000)
        self.manager.add_breakpoint(0x3000)
        
        count = self.manager.clear_all_breakpoints()
        assert count == 3
        assert len(self.manager.get_all_breakpoints()) == 0
    
    def test_check_breakpoint_hit(self):
        """Test breakpoint hit detection."""
        bp_id = self.manager.add_breakpoint(0x1000)
        
        # No hit at different address
        hit_info = self.manager.check_breakpoint_hit(0x2000)
        assert hit_info is None
        
        # Hit at correct address
        context = {'cycle_count': 100}
        hit_info = self.manager.check_breakpoint_hit(0x1000, context)
        assert hit_info is not None
        assert hit_info.breakpoint_id == bp_id
        assert hit_info.address == 0x1000
        assert hit_info.cycle_count == 100
    
    def test_check_conditional_breakpoint_hit(self):
        """Test conditional breakpoint hit detection."""
        bp_id = self.manager.add_breakpoint(
            0x1000,
            BreakpointType.CONDITIONAL,
            condition="A == 0x42"
        )
        
        # Condition not met
        context = {'A': 0x43}
        hit_info = self.manager.check_breakpoint_hit(0x1000, context)
        assert hit_info is None
        
        # Condition met
        context = {'A': 0x42}
        hit_info = self.manager.check_breakpoint_hit(0x1000, context)
        assert hit_info is not None
        assert hit_info.breakpoint_id == bp_id
    
    def test_temporary_breakpoint(self):
        """Test temporary breakpoint removal after hit."""
        bp_id = self.manager.add_breakpoint(0x1000, BreakpointType.TEMPORARY)
        
        # Hit the breakpoint
        hit_info = self.manager.check_breakpoint_hit(0x1000)
        assert hit_info is not None
        
        # Breakpoint should be removed
        assert self.manager.get_breakpoint(bp_id) is None
    
    def test_hit_callbacks(self):
        """Test breakpoint hit callbacks."""
        callback_called = False
        hit_info_received = None
        
        def test_callback(hit_info):
            nonlocal callback_called, hit_info_received
            callback_called = True
            hit_info_received = hit_info
        
        self.manager.add_hit_callback(test_callback)
        bp_id = self.manager.add_breakpoint(0x1000)
        
        # Trigger breakpoint
        hit_info = self.manager.check_breakpoint_hit(0x1000)
        
        assert callback_called is True
        assert hit_info_received is hit_info
        
        # Test callback removal
        assert self.manager.remove_hit_callback(test_callback) is True
        assert self.manager.remove_hit_callback(test_callback) is False
    
    def test_statistics(self):
        """Test breakpoint statistics."""
        # Add various breakpoints
        bp_id1 = self.manager.add_breakpoint(0x1000)
        bp_id2 = self.manager.add_breakpoint(0x2000)
        self.manager.disable_breakpoint(bp_id2)
        
        # Hit one breakpoint
        self.manager.check_breakpoint_hit(0x1000)
        
        stats = self.manager.get_statistics()
        
        assert stats['total_breakpoints'] == 2
        assert stats['enabled'] == 1
        assert stats['disabled'] == 1
        assert stats['recently_hit'] == 1
        assert stats['total_hits'] == 1
        assert stats['addresses_with_breakpoints'] == 2
