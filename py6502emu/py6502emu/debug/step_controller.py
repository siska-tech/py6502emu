"""
Step execution control system for W65C02S emulator debugging.

This module implements PU014: StepController functionality including:
- Step into (single instruction execution)
- Step over (skip subroutine calls)
- Step out (return from current subroutine)
- Call stack tracking and management
- Execution control state management
"""

from typing import Dict, List, Optional, Set, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod


class StepMode(Enum):
    """Different stepping modes supported by the debugger."""
    STEP_INTO = auto()      # Execute next single instruction
    STEP_OVER = auto()      # Execute next instruction, skip subroutine calls
    STEP_OUT = auto()       # Execute until return from current subroutine
    RUN_TO_CURSOR = auto()  # Execute until reaching specific address
    CONTINUE = auto()       # Continue normal execution


class ExecutionState(Enum):
    """Current execution state of the debugged program."""
    RUNNING = auto()        # Program is executing normally
    PAUSED = auto()         # Program is paused at a breakpoint or step
    STEPPING = auto()       # Program is in step mode
    FINISHED = auto()       # Program execution has completed
    ERROR = auto()          # Program encountered an error


@dataclass
class CallFrame:
    """Represents a single frame in the call stack."""
    return_address: int     # Address to return to
    stack_pointer: int      # Stack pointer when call was made
    frame_pointer: Optional[int] = None  # Frame pointer if available
    function_name: Optional[str] = None  # Function name if known
    source_file: Optional[str] = None    # Source file if available
    source_line: Optional[int] = None    # Source line if available


@dataclass
class StepContext:
    """Context information for step execution."""
    current_address: int
    target_address: Optional[int] = None
    step_mode: StepMode = StepMode.STEP_INTO
    step_count: int = 0
    call_depth: int = 0
    original_stack_pointer: Optional[int] = None
    break_on_return: bool = False


class CallStack:
    """
    Manages the call stack for debugging purposes.
    
    Tracks subroutine calls and returns to enable step over/out functionality.
    """
    
    def __init__(self):
        self._frames: List[CallFrame] = []
        self._call_instructions = {'JSR', 'BSR'}  # W65C02S call instructions
        self._return_instructions = {'RTS', 'RTI'}  # W65C02S return instructions
    
    def push_frame(self, return_address: int, stack_pointer: int, 
                   function_name: Optional[str] = None) -> None:
        """Push a new call frame onto the stack."""
        frame = CallFrame(
            return_address=return_address,
            stack_pointer=stack_pointer,
            function_name=function_name
        )
        self._frames.append(frame)
    
    def pop_frame(self) -> Optional[CallFrame]:
        """Pop the top call frame from the stack."""
        if self._frames:
            return self._frames.pop()
        return None
    
    def peek_frame(self) -> Optional[CallFrame]:
        """Get the top call frame without removing it."""
        if self._frames:
            return self._frames[-1]
        return None
    
    def get_depth(self) -> int:
        """Get the current call stack depth."""
        return len(self._frames)
    
    def get_frames(self) -> List[CallFrame]:
        """Get all call frames (copy)."""
        return self._frames.copy()
    
    def clear(self) -> None:
        """Clear the call stack."""
        self._frames.clear()
    
    def update_on_instruction(self, instruction: str, address: int, 
                            stack_pointer: int, next_address: int) -> None:
        """
        Update call stack based on executed instruction.
        
        Args:
            instruction: The instruction mnemonic (e.g., 'JSR', 'RTS')
            address: Current instruction address
            stack_pointer: Current stack pointer value
            next_address: Address of next instruction to execute
        """
        if instruction in self._call_instructions:
            # This is a subroutine call - push frame
            self.push_frame(next_address, stack_pointer)
        
        elif instruction in self._return_instructions:
            # This is a return - pop frame
            self.pop_frame()


class StepController:
    """
    Controls step-by-step execution of the W65C02S emulator.
    
    Provides different stepping modes and manages execution state
    to enable precise debugging control.
    """
    
    def __init__(self):
        self._execution_state = ExecutionState.PAUSED
        self._step_context = StepContext(current_address=0)
        self._call_stack = CallStack()
        self._step_callbacks: List[Callable[[StepContext], None]] = []
        self._state_change_callbacks: List[Callable[[ExecutionState, ExecutionState], None]] = []
        
        # Instruction analysis
        self._call_instructions = {'JSR', 'BSR'}
        self._return_instructions = {'RTS', 'RTI'}
        self._branch_instructions = {
            'BCC', 'BCS', 'BEQ', 'BMI', 'BNE', 'BPL', 'BVC', 'BVS',
            'BRA', 'BBR0', 'BBR1', 'BBR2', 'BBR3', 'BBR4', 'BBR5', 'BBR6', 'BBR7',
            'BBS0', 'BBS1', 'BBS2', 'BBS3', 'BBS4', 'BBS5', 'BBS6', 'BBS7'
        }
    
    def step_into(self, current_address: int) -> StepContext:
        """
        Execute a single instruction (step into).
        
        Args:
            current_address: Current program counter value
            
        Returns:
            Updated step context
        """
        self._set_execution_state(ExecutionState.STEPPING)
        
        self._step_context.current_address = current_address
        self._step_context.step_mode = StepMode.STEP_INTO
        self._step_context.target_address = None
        self._step_context.step_count += 1
        
        self._notify_step_callbacks()
        return self._step_context
    
    def step_over(self, current_address: int, instruction: str, 
                  next_address: int) -> StepContext:
        """
        Execute next instruction, stepping over subroutine calls.
        
        Args:
            current_address: Current program counter value
            instruction: Current instruction mnemonic
            next_address: Address of next instruction
            
        Returns:
            Updated step context
        """
        self._set_execution_state(ExecutionState.STEPPING)
        
        self._step_context.current_address = current_address
        self._step_context.step_mode = StepMode.STEP_OVER
        self._step_context.step_count += 1
        
        if instruction in self._call_instructions:
            # Set target to the instruction after the call
            self._step_context.target_address = next_address
            self._step_context.call_depth = self._call_stack.get_depth()
        else:
            # Regular step for non-call instructions
            self._step_context.target_address = None
        
        self._notify_step_callbacks()
        return self._step_context
    
    def step_out(self, current_address: int, stack_pointer: int) -> StepContext:
        """
        Execute until return from current subroutine.
        
        Args:
            current_address: Current program counter value
            stack_pointer: Current stack pointer value
            
        Returns:
            Updated step context
        """
        self._set_execution_state(ExecutionState.STEPPING)
        
        self._step_context.current_address = current_address
        self._step_context.step_mode = StepMode.STEP_OUT
        self._step_context.step_count += 1
        self._step_context.original_stack_pointer = stack_pointer
        self._step_context.call_depth = self._call_stack.get_depth()
        self._step_context.break_on_return = True
        
        # If we're not in a subroutine, just do a single step
        if self._call_stack.get_depth() == 0:
            return self.step_into(current_address)
        
        self._notify_step_callbacks()
        return self._step_context
    
    def run_to_cursor(self, current_address: int, target_address: int) -> StepContext:
        """
        Execute until reaching the specified target address.
        
        Args:
            current_address: Current program counter value
            target_address: Address to run to
            
        Returns:
            Updated step context
        """
        self._set_execution_state(ExecutionState.STEPPING)
        
        self._step_context.current_address = current_address
        self._step_context.step_mode = StepMode.RUN_TO_CURSOR
        self._step_context.target_address = target_address
        self._step_context.step_count += 1
        
        self._notify_step_callbacks()
        return self._step_context
    
    def continue_execution(self) -> StepContext:
        """Continue normal execution."""
        self._set_execution_state(ExecutionState.RUNNING)
        
        self._step_context.step_mode = StepMode.CONTINUE
        self._step_context.target_address = None
        self._step_context.break_on_return = False
        
        self._notify_step_callbacks()
        return self._step_context
    
    def pause_execution(self, current_address: int) -> StepContext:
        """Pause execution at the current address."""
        self._set_execution_state(ExecutionState.PAUSED)
        
        self._step_context.current_address = current_address
        self._step_context.step_mode = StepMode.STEP_INTO  # Default to step mode
        
        self._notify_step_callbacks()
        return self._step_context
    
    def should_break(self, current_address: int, instruction: str, 
                    stack_pointer: int) -> bool:
        """
        Check if execution should break at the current instruction.
        
        Args:
            current_address: Current program counter value
            instruction: Current instruction mnemonic
            stack_pointer: Current stack pointer value
            
        Returns:
            True if execution should break, False otherwise
        """
        if self._execution_state != ExecutionState.STEPPING:
            return False
        
        # Update call stack
        next_address = self._calculate_next_address(current_address, instruction)
        self._call_stack.update_on_instruction(instruction, current_address, 
                                             stack_pointer, next_address)
        
        # Check different step modes
        if self._step_context.step_mode == StepMode.STEP_INTO:
            return True  # Always break on step into
        
        elif self._step_context.step_mode == StepMode.STEP_OVER:
            if self._step_context.target_address is not None:
                # We're stepping over a call - break when we reach the target
                return current_address == self._step_context.target_address
            else:
                # Regular step over - break after this instruction
                return True
        
        elif self._step_context.step_mode == StepMode.STEP_OUT:
            if self._step_context.break_on_return:
                # Break when we return to a shallower call depth
                current_depth = self._call_stack.get_depth()
                return current_depth < self._step_context.call_depth
            return False
        
        elif self._step_context.step_mode == StepMode.RUN_TO_CURSOR:
            return current_address == self._step_context.target_address
        
        return False
    
    def _calculate_next_address(self, current_address: int, instruction: str) -> int:
        """
        Calculate the address of the next instruction.
        This is a simplified version - in practice, this would need
        to consider instruction lengths and operands.
        """
        # This is a placeholder - actual implementation would need
        # to decode the instruction to determine its length
        instruction_lengths = {
            'BRK': 1, 'NOP': 1, 'RTI': 1, 'RTS': 1,
            'JSR': 3, 'JMP': 3,
            # Add more as needed
        }
        
        length = instruction_lengths.get(instruction, 1)
        return current_address + length
    
    def get_execution_state(self) -> ExecutionState:
        """Get the current execution state."""
        return self._execution_state
    
    def get_step_context(self) -> StepContext:
        """Get the current step context."""
        return self._step_context
    
    def get_call_stack(self) -> CallStack:
        """Get the call stack manager."""
        return self._call_stack
    
    def reset(self) -> None:
        """Reset the step controller to initial state."""
        self._execution_state = ExecutionState.PAUSED
        self._step_context = StepContext(current_address=0)
        self._call_stack.clear()
    
    def add_step_callback(self, callback: Callable[[StepContext], None]) -> None:
        """Add a callback to be called on step events."""
        self._step_callbacks.append(callback)
    
    def remove_step_callback(self, callback: Callable[[StepContext], None]) -> bool:
        """Remove a step callback."""
        try:
            self._step_callbacks.remove(callback)
            return True
        except ValueError:
            return False
    
    def add_state_change_callback(self, 
                                callback: Callable[[ExecutionState, ExecutionState], None]) -> None:
        """Add a callback to be called when execution state changes."""
        self._state_change_callbacks.append(callback)
    
    def remove_state_change_callback(self, 
                                   callback: Callable[[ExecutionState, ExecutionState], None]) -> bool:
        """Remove a state change callback."""
        try:
            self._state_change_callbacks.remove(callback)
            return True
        except ValueError:
            return False
    
    def _set_execution_state(self, new_state: ExecutionState) -> None:
        """Set execution state and notify callbacks."""
        old_state = self._execution_state
        if old_state != new_state:
            self._execution_state = new_state
            
            # Notify state change callbacks
            for callback in self._state_change_callbacks:
                try:
                    callback(old_state, new_state)
                except Exception:
                    pass  # Don't let callback errors break debugging
    
    def _notify_step_callbacks(self) -> None:
        """Notify all step callbacks of the current context."""
        for callback in self._step_callbacks:
            try:
                callback(self._step_context)
            except Exception:
                pass  # Don't let callback errors break debugging
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get step controller statistics."""
        return {
            'execution_state': self._execution_state.name,
            'step_mode': self._step_context.step_mode.name,
            'step_count': self._step_context.step_count,
            'call_depth': self._call_stack.get_depth(),
            'current_address': self._step_context.current_address,
            'target_address': self._step_context.target_address,
            'registered_callbacks': len(self._step_callbacks) + len(self._state_change_callbacks)
        }
