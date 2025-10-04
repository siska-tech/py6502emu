"""
Breakpoint management system for W65C02S emulator debugging.

This module implements PU013: BreakpointManager functionality including:
- Address-based breakpoints
- Conditional breakpoints with Python expression evaluation
- Breakpoint hit detection and management
- Temporary breakpoint support
"""

from typing import Dict, List, Optional, Set, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
import re


class BreakpointType(Enum):
    """Types of breakpoints supported by the system."""
    ADDRESS = auto()           # Break at specific address
    CONDITIONAL = auto()       # Break when condition is met
    TEMPORARY = auto()         # One-time breakpoint
    READ_WATCH = auto()        # Break on memory read
    WRITE_WATCH = auto()       # Break on memory write
    ACCESS_WATCH = auto()      # Break on memory read or write


class BreakpointState(Enum):
    """Current state of a breakpoint."""
    ENABLED = auto()           # Active and will trigger
    DISABLED = auto()          # Inactive but preserved
    HIT = auto()               # Recently triggered
    DELETED = auto()           # Marked for removal


@dataclass
class BreakpointHitInfo:
    """Information about a breakpoint hit event."""
    breakpoint_id: int
    address: int
    cycle_count: int
    instruction: Optional[str] = None
    registers: Optional[Dict[str, int]] = None
    condition_result: Optional[Any] = None
    hit_count: int = 1
    timestamp: Optional[float] = None


@dataclass
class Breakpoint:
    """Base breakpoint class with common functionality."""
    id: int
    address: int
    type: BreakpointType
    state: BreakpointState = BreakpointState.ENABLED
    hit_count: int = 0
    ignore_count: int = 0
    description: str = ""
    created_at: Optional[float] = None
    
    def should_trigger(self, current_address: int) -> bool:
        """Check if this breakpoint should trigger at the given address."""
        if self.state != BreakpointState.ENABLED:
            return False
        
        if current_address != self.address:
            return False
            
        if self.ignore_count > 0:
            self.ignore_count -= 1
            return False
            
        return True
    
    def on_hit(self, context: Dict[str, Any]) -> BreakpointHitInfo:
        """Handle breakpoint hit and return hit information."""
        self.hit_count += 1
        self.state = BreakpointState.HIT
        
        return BreakpointHitInfo(
            breakpoint_id=self.id,
            address=self.address,
            cycle_count=context.get('cycle_count', 0),
            instruction=context.get('instruction'),
            registers=context.get('registers', {}),
            hit_count=self.hit_count
        )


@dataclass
class ConditionalBreakpoint(Breakpoint):
    """Breakpoint that triggers based on a Python expression condition."""
    condition: str = ""
    compiled_condition: Optional[Callable] = field(default=None, init=False)
    
    def __post_init__(self):
        """Compile the condition expression after initialization."""
        if self.condition:
            self.compile_condition()
    
    def compile_condition(self) -> None:
        """Compile the condition string into executable code."""
        if not self.condition:
            self.compiled_condition = None
            return
            
        try:
            # Validate that the condition is a safe Python expression
            if not self._is_safe_expression(self.condition):
                raise ValueError(f"Unsafe expression in condition: {self.condition}")
            
            # Compile the expression
            compiled = compile(self.condition, '<breakpoint>', 'eval')
            self.compiled_condition = lambda ctx: eval(compiled, {"__builtins__": {}}, ctx)
            
        except Exception as e:
            raise ValueError(f"Invalid condition expression '{self.condition}': {e}")
    
    def _is_safe_expression(self, expr: str) -> bool:
        """Check if the expression is safe to evaluate."""
        # Disallow potentially dangerous operations
        dangerous_patterns = [
            r'__.*__',      # Dunder methods
            r'import\s',    # Import statements
            r'exec\s*\(',   # Exec calls
            r'eval\s*\(',   # Eval calls
            r'open\s*\(',   # File operations
            r'\.write\s*\(',# Write operations
            r'\.read\s*\(', # Read operations
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, expr, re.IGNORECASE):
                return False
        
        return True
    
    def should_trigger(self, current_address: int, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if this conditional breakpoint should trigger."""
        if not super().should_trigger(current_address):
            return False
        
        if not self.compiled_condition:
            return True  # No condition means always trigger
        
        if context is None:
            context = {}
        
        try:
            # Evaluate the condition with the current context
            result = self.compiled_condition(context)
            return bool(result)
        except Exception:
            # If condition evaluation fails, don't trigger
            return False


class BreakpointManager:
    """
    Manages all breakpoints in the debugging system.
    
    Provides functionality for:
    - Creating and managing different types of breakpoints
    - Checking for breakpoint hits during execution
    - Managing breakpoint state and lifecycle
    """
    
    def __init__(self):
        self._breakpoints: Dict[int, Breakpoint] = {}
        self._next_id: int = 1
        self._address_map: Dict[int, Set[int]] = {}  # address -> set of breakpoint IDs
        self._hit_callbacks: List[Callable[[BreakpointHitInfo], None]] = []
    
    def add_breakpoint(self, address: int, 
                      breakpoint_type: BreakpointType = BreakpointType.ADDRESS,
                      condition: Optional[str] = None,
                      description: str = "",
                      ignore_count: int = 0) -> int:
        """
        Add a new breakpoint and return its ID.
        
        Args:
            address: Memory address where breakpoint should trigger
            breakpoint_type: Type of breakpoint to create
            condition: Python expression for conditional breakpoints
            description: Human-readable description
            ignore_count: Number of hits to ignore before triggering
            
        Returns:
            Unique breakpoint ID
        """
        breakpoint_id = self._next_id
        self._next_id += 1
        
        if breakpoint_type == BreakpointType.CONDITIONAL and condition:
            breakpoint = ConditionalBreakpoint(
                id=breakpoint_id,
                address=address,
                type=breakpoint_type,
                condition=condition,
                description=description,
                ignore_count=ignore_count
            )
        else:
            breakpoint = Breakpoint(
                id=breakpoint_id,
                address=address,
                type=breakpoint_type,
                description=description,
                ignore_count=ignore_count
            )
        
        self._breakpoints[breakpoint_id] = breakpoint
        
        # Update address mapping
        if address not in self._address_map:
            self._address_map[address] = set()
        self._address_map[address].add(breakpoint_id)
        
        return breakpoint_id
    
    def remove_breakpoint(self, breakpoint_id: int) -> bool:
        """
        Remove a breakpoint by ID.
        
        Args:
            breakpoint_id: ID of breakpoint to remove
            
        Returns:
            True if breakpoint was removed, False if not found
        """
        if breakpoint_id not in self._breakpoints:
            return False
        
        breakpoint = self._breakpoints[breakpoint_id]
        
        # Remove from address mapping
        if breakpoint.address in self._address_map:
            self._address_map[breakpoint.address].discard(breakpoint_id)
            if not self._address_map[breakpoint.address]:
                del self._address_map[breakpoint.address]
        
        # Remove the breakpoint
        del self._breakpoints[breakpoint_id]
        return True
    
    def enable_breakpoint(self, breakpoint_id: int) -> bool:
        """Enable a breakpoint."""
        if breakpoint_id in self._breakpoints:
            self._breakpoints[breakpoint_id].state = BreakpointState.ENABLED
            return True
        return False
    
    def disable_breakpoint(self, breakpoint_id: int) -> bool:
        """Disable a breakpoint."""
        if breakpoint_id in self._breakpoints:
            self._breakpoints[breakpoint_id].state = BreakpointState.DISABLED
            return True
        return False
    
    def get_breakpoint(self, breakpoint_id: int) -> Optional[Breakpoint]:
        """Get a breakpoint by ID."""
        return self._breakpoints.get(breakpoint_id)
    
    def get_breakpoints_at_address(self, address: int) -> List[Breakpoint]:
        """Get all breakpoints at a specific address."""
        if address not in self._address_map:
            return []
        
        return [self._breakpoints[bp_id] for bp_id in self._address_map[address]
                if bp_id in self._breakpoints]
    
    def get_all_breakpoints(self) -> List[Breakpoint]:
        """Get all breakpoints."""
        return list(self._breakpoints.values())
    
    def clear_all_breakpoints(self) -> int:
        """Remove all breakpoints and return count of removed breakpoints."""
        count = len(self._breakpoints)
        self._breakpoints.clear()
        self._address_map.clear()
        return count
    
    def check_breakpoint_hit(self, address: int, context: Optional[Dict[str, Any]] = None) -> Optional[BreakpointHitInfo]:
        """
        Check if any breakpoint should trigger at the given address.
        
        Args:
            address: Current execution address
            context: Execution context (registers, memory, etc.)
            
        Returns:
            BreakpointHitInfo if a breakpoint was hit, None otherwise
        """
        if address not in self._address_map:
            return None
        
        if context is None:
            context = {}
        
        for breakpoint_id in self._address_map[address]:
            if breakpoint_id not in self._breakpoints:
                continue
                
            breakpoint = self._breakpoints[breakpoint_id]
            
            # Check if this breakpoint should trigger
            should_trigger = False
            if isinstance(breakpoint, ConditionalBreakpoint):
                should_trigger = breakpoint.should_trigger(address, context)
            else:
                should_trigger = breakpoint.should_trigger(address)
            
            if should_trigger:
                hit_info = breakpoint.on_hit(context)
                
                # Handle temporary breakpoints
                if breakpoint.type == BreakpointType.TEMPORARY:
                    self.remove_breakpoint(breakpoint_id)
                
                # Notify hit callbacks
                for callback in self._hit_callbacks:
                    try:
                        callback(hit_info)
                    except Exception:
                        pass  # Don't let callback errors break debugging
                
                return hit_info
        
        return None
    
    def add_hit_callback(self, callback: Callable[[BreakpointHitInfo], None]) -> None:
        """Add a callback to be called when a breakpoint is hit."""
        self._hit_callbacks.append(callback)
    
    def remove_hit_callback(self, callback: Callable[[BreakpointHitInfo], None]) -> bool:
        """Remove a hit callback."""
        try:
            self._hit_callbacks.remove(callback)
            return True
        except ValueError:
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get breakpoint statistics."""
        total = len(self._breakpoints)
        enabled = sum(1 for bp in self._breakpoints.values() 
                     if bp.state == BreakpointState.ENABLED)
        disabled = sum(1 for bp in self._breakpoints.values() 
                      if bp.state == BreakpointState.DISABLED)
        hit = sum(1 for bp in self._breakpoints.values() 
                 if bp.state == BreakpointState.HIT)
        
        total_hits = sum(bp.hit_count for bp in self._breakpoints.values())
        
        return {
            'total_breakpoints': total,
            'enabled': enabled,
            'disabled': disabled,
            'recently_hit': hit,
            'total_hits': total_hits,
            'addresses_with_breakpoints': len(self._address_map)
        }
