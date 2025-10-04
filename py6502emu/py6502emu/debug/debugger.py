"""
Integrated debugger interface for W65C02S emulator.

This module provides a unified debugging interface that combines all
debug functionality including breakpoints, stepping, state inspection,
and command-line interaction similar to pdb.
"""

from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, auto
import cmd
import sys
import traceback
import time

from .breakpoint import BreakpointManager, BreakpointHitInfo, BreakpointType
from .step_controller import StepController, StepMode, ExecutionState
from .inspector import StateInspector, DisplayFormat
from .disassembler import Disassembler
from .serializer import SerializationFormat
from .serializer import StateSerializer, StateFormat
from .validator import StateValidator, ValidationReport

from ..cpu.registers import CPURegisters
from ..cpu.flags import ProcessorFlags
from ..memory.memory_controller import MemoryController
from ..core.device import Device


class DebuggerState(Enum):
    """Current state of the debugger."""
    INACTIVE = auto()       # Debugger not active
    ACTIVE = auto()         # Debugger active, program running
    PAUSED = auto()         # Program paused, waiting for commands
    STEPPING = auto()       # In step mode
    TERMINATED = auto()     # Debugging session ended


@dataclass
class DebugContext:
    """Current debugging context information."""
    current_address: int = 0
    last_instruction: str = ""
    cycle_count: int = 0
    step_count: int = 0
    breakpoint_hits: int = 0
    session_start_time: float = field(default_factory=time.time)
    
    def get_runtime(self) -> float:
        """Get total runtime of debug session."""
        return time.time() - self.session_start_time


class DebugSession:
    """Manages a debugging session with state and history."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.context = DebugContext()
        self.command_history: List[str] = []
        self.state_snapshots: List[StateFormat] = []
        self.breakpoint_history: List[BreakpointHitInfo] = []
        self.created_at = time.time()
    
    def add_command(self, command: str) -> None:
        """Add command to history."""
        self.command_history.append(command)
    
    def add_state_snapshot(self, state: StateFormat) -> None:
        """Add state snapshot."""
        self.state_snapshots.append(state)
        
        # Limit snapshots to prevent memory issues
        if len(self.state_snapshots) > 100:
            self.state_snapshots.pop(0)
    
    def add_breakpoint_hit(self, hit_info: BreakpointHitInfo) -> None:
        """Add breakpoint hit to history."""
        self.breakpoint_history.append(hit_info)
        self.context.breakpoint_hits += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get session statistics."""
        return {
            'session_id': self.session_id,
            'runtime': time.time() - self.created_at,
            'commands_executed': len(self.command_history),
            'state_snapshots': len(self.state_snapshots),
            'breakpoint_hits': len(self.breakpoint_history),
            'current_address': self.context.current_address,
            'cycle_count': self.context.cycle_count,
            'step_count': self.context.step_count
        }


class CommandInterface(cmd.Cmd):
    """Command-line interface for the debugger (pdb-style)."""
    
    intro = "W65C02S Emulator Debugger\nType 'help' or '?' for commands.\n"
    prompt = "(w65c02s-db) "
    
    def __init__(self, debugger: 'Debugger'):
        super().__init__()
        self.debugger = debugger
        self.last_command = ""
    
    def emptyline(self) -> bool:
        """Handle empty line - repeat last command if appropriate."""
        if self.last_command in ['s', 'step', 'n', 'next', 'c', 'continue']:
            self.onecmd(self.last_command)
        return False
    
    def default(self, line: str) -> None:
        """Handle unknown commands."""
        print(f"Unknown command: {line}")
        print("Type 'help' for available commands.")
    
    def do_step(self, arg: str) -> None:
        """s(tep) - Execute next single instruction."""
        self.debugger.step_into()
        self.last_command = 'step'
    
    def do_s(self, arg: str) -> None:
        """Alias for step."""
        self.do_step(arg)
    
    def do_next(self, arg: str) -> None:
        """n(ext) - Execute next instruction, step over calls."""
        self.debugger.step_over()
        self.last_command = 'next'
    
    def do_n(self, arg: str) -> None:
        """Alias for next."""
        self.do_next(arg)
    
    def do_continue(self, arg: str) -> None:
        """c(ont) - Continue execution."""
        self.debugger.continue_execution()
        self.last_command = 'continue'
    
    def do_c(self, arg: str) -> None:
        """Alias for continue."""
        self.do_continue(arg)
    
    def do_finish(self, arg: str) -> None:
        """f(inish) - Execute until return from current function."""
        self.debugger.step_out()
        self.last_command = 'finish'
    
    def do_f(self, arg: str) -> None:
        """Alias for finish."""
        self.do_finish(arg)
    
    def do_break(self, arg: str) -> None:
        """b(reak) [address] - Set breakpoint at address."""
        if not arg:
            # List breakpoints
            self.debugger.list_breakpoints()
            return
        
        try:
            if arg.startswith('0x') or arg.startswith('$'):
                address = int(arg.replace('$', '0x'), 16)
            else:
                address = int(arg)
            
            bp_id = self.debugger.set_breakpoint(address)
            print(f"Breakpoint {bp_id} set at address 0x{address:04X}")
        except ValueError:
            print(f"Invalid address: {arg}")
    
    def do_b(self, arg: str) -> None:
        """Alias for break."""
        self.do_break(arg)
    
    def do_clear(self, arg: str) -> None:
        """clear [breakpoint_id] - Clear breakpoint."""
        if not arg:
            print("Usage: clear <breakpoint_id>")
            return
        
        try:
            bp_id = int(arg)
            if self.debugger.clear_breakpoint(bp_id):
                print(f"Breakpoint {bp_id} cleared")
            else:
                print(f"Breakpoint {bp_id} not found")
        except ValueError:
            print(f"Invalid breakpoint ID: {arg}")
    
    def do_disable(self, arg: str) -> None:
        """disable <breakpoint_id> - Disable breakpoint."""
        if not arg:
            print("Usage: disable <breakpoint_id>")
            return
        
        try:
            bp_id = int(arg)
            if self.debugger.disable_breakpoint(bp_id):
                print(f"Breakpoint {bp_id} disabled")
            else:
                print(f"Breakpoint {bp_id} not found")
        except ValueError:
            print(f"Invalid breakpoint ID: {arg}")
    
    def do_enable(self, arg: str) -> None:
        """enable <breakpoint_id> - Enable breakpoint."""
        if not arg:
            print("Usage: enable <breakpoint_id>")
            return
        
        try:
            bp_id = int(arg)
            if self.debugger.enable_breakpoint(bp_id):
                print(f"Breakpoint {bp_id} enabled")
            else:
                print(f"Breakpoint {bp_id} not found")
        except ValueError:
            print(f"Invalid breakpoint ID: {arg}")
    
    def do_info(self, arg: str) -> None:
        """info [registers|flags|breakpoints|stack] - Show information."""
        if not arg or arg == 'registers':
            self.debugger.show_registers()
        elif arg == 'flags':
            self.debugger.show_flags()
        elif arg == 'breakpoints':
            self.debugger.list_breakpoints()
        elif arg == 'stack':
            self.debugger.show_call_stack()
        else:
            print(f"Unknown info command: {arg}")
            print("Available: registers, flags, breakpoints, stack")
    
    def do_print(self, arg: str) -> None:
        """p(rint) <expression> - Print expression value."""
        if not arg:
            print("Usage: print <expression>")
            return
        
        # Simple expression evaluation for memory/register access
        try:
            if arg.startswith('$') or arg.startswith('0x'):
                # Memory address
                address = int(arg.replace('$', '0x'), 16)
                value = self.debugger.read_memory_byte(address)
                print(f"Memory[0x{address:04X}] = 0x{value:02X} ({value})")
            elif arg.upper() in ['A', 'X', 'Y', 'PC', 'S', 'P']:
                # Register
                value = self.debugger.get_register_value(arg.upper())
                if value is not None:
                    if arg.upper() == 'PC':
                        print(f"{arg.upper()} = 0x{value:04X} ({value})")
                    else:
                        print(f"{arg.upper()} = 0x{value:02X} ({value})")
                else:
                    print(f"Unknown register: {arg}")
            else:
                print(f"Cannot evaluate expression: {arg}")
        except Exception as e:
            print(f"Error evaluating expression: {e}")
    
    def do_p(self, arg: str) -> None:
        """Alias for print."""
        self.do_print(arg)
    
    def do_disasm(self, arg: str) -> None:
        """disasm [address] [count] - Disassemble instructions."""
        parts = arg.split() if arg else []
        
        if len(parts) == 0:
            # Disassemble around current PC
            address = self.debugger.get_current_address()
            count = 10
        elif len(parts) == 1:
            try:
                address = int(parts[0].replace('$', '0x'), 16)
                count = 10
            except ValueError:
                print(f"Invalid address: {parts[0]}")
                return
        else:
            try:
                address = int(parts[0].replace('$', '0x'), 16)
                count = int(parts[1])
            except ValueError:
                print("Invalid arguments")
                return
        
        self.debugger.disassemble(address, count)
    
    def do_memory(self, arg: str) -> None:
        """memory <address> [length] - Show memory dump."""
        parts = arg.split() if arg else []
        
        if len(parts) == 0:
            print("Usage: memory <address> [length]")
            return
        
        try:
            address = int(parts[0].replace('$', '0x'), 16)
            length = int(parts[1]) if len(parts) > 1 else 64
            self.debugger.show_memory(address, length)
        except ValueError:
            print("Invalid arguments")
    
    def do_save(self, arg: str) -> None:
        """save <filename> - Save current state."""
        if not arg:
            print("Usage: save <filename>")
            return
        
        try:
            self.debugger.save_state(arg)
            print(f"State saved to {arg}")
        except Exception as e:
            print(f"Error saving state: {e}")
    
    def do_load(self, arg: str) -> None:
        """load <filename> - Load state from file."""
        if not arg:
            print("Usage: load <filename>")
            return
        
        try:
            self.debugger.load_state(arg)
            print(f"State loaded from {arg}")
        except Exception as e:
            print(f"Error loading state: {e}")
    
    def do_validate(self, arg: str) -> None:
        """validate - Validate current state."""
        self.debugger.validate_state()
    
    def do_quit(self, arg: str) -> None:
        """q(uit) - Quit debugger."""
        print("Quitting debugger...")
        return True
    
    def do_q(self, arg: str) -> None:
        """Alias for quit."""
        return self.do_quit(arg)
    
    def do_help(self, arg: str) -> None:
        """Show help for commands."""
        if not arg:
            print("\nAvailable commands:")
            print("  s(tep)              - Execute next single instruction")
            print("  n(ext)              - Execute next instruction, step over calls")
            print("  c(ont)              - Continue execution")
            print("  f(inish)            - Execute until return from current function")
            print("  b(reak) [addr]      - Set/list breakpoints")
            print("  clear <id>          - Clear breakpoint")
            print("  disable/enable <id> - Disable/enable breakpoint")
            print("  info [type]         - Show information (registers, flags, etc.)")
            print("  p(rint) <expr>      - Print expression value")
            print("  disasm [addr] [cnt] - Disassemble instructions")
            print("  memory <addr> [len] - Show memory dump")
            print("  save <file>         - Save current state")
            print("  load <file>         - Load state from file")
            print("  validate            - Validate current state")
            print("  q(uit)              - Quit debugger")
            print("\nPress Enter to repeat last step/next/continue command.")
        else:
            super().do_help(arg)


class Debugger:
    """
    Integrated debugger providing unified access to all debugging functionality.
    
    Combines breakpoint management, step control, state inspection, and
    command-line interface into a cohesive debugging environment.
    """
    
    def __init__(self, registers: CPURegisters, flags: ProcessorFlags,
                 memory_controller: MemoryController):
        # Core components
        self._registers = registers
        self._flags = flags
        self._memory = memory_controller
        
        # Debug subsystems
        self._breakpoint_manager = BreakpointManager()
        self._step_controller = StepController()
        self._state_inspector = StateInspector(registers, flags, memory_controller)
        self._disassembler = Disassembler(memory_controller)
        self._serializer = StateSerializer()
        self._validator = StateValidator()
        
        # Debugger state
        self._state = DebuggerState.INACTIVE
        self._current_session: Optional[DebugSession] = None
        self._command_interface: Optional[CommandInterface] = None
        
        # Callbacks
        self._on_breakpoint_hit: List[Callable[[BreakpointHitInfo], None]] = []
        self._on_step_complete: List[Callable[[int], None]] = []
        self._on_state_change: List[Callable[[DebuggerState], None]] = []
        
        # Setup callbacks
        self._breakpoint_manager.add_hit_callback(self._handle_breakpoint_hit)
        self._step_controller.add_step_callback(self._handle_step_complete)
    
    def start_session(self, session_id: Optional[str] = None) -> str:
        """Start a new debugging session."""
        if session_id is None:
            session_id = f"debug_session_{int(time.time())}"
        
        self._current_session = DebugSession(session_id)
        self._state = DebuggerState.ACTIVE
        self._notify_state_change()
        
        return session_id
    
    def end_session(self) -> Optional[Dict[str, Any]]:
        """End current debugging session and return statistics."""
        if self._current_session is None:
            return None
        
        stats = self._current_session.get_statistics()
        self._current_session = None
        self._state = DebuggerState.INACTIVE
        self._notify_state_change()
        
        return stats
    
    def start_interactive(self) -> None:
        """Start interactive command-line debugging session."""
        if self._current_session is None:
            self.start_session()
        
        self._command_interface = CommandInterface(self)
        self._state = DebuggerState.PAUSED
        self._notify_state_change()
        
        try:
            self._command_interface.cmdloop()
        except KeyboardInterrupt:
            print("\nDebugging interrupted.")
        finally:
            self.end_session()
    
    def set_breakpoint(self, address: int, condition: Optional[str] = None) -> int:
        """Set a breakpoint at the specified address."""
        bp_type = BreakpointType.CONDITIONAL if condition else BreakpointType.ADDRESS
        bp_id = self._breakpoint_manager.add_breakpoint(address, bp_type, condition)
        
        if self._current_session:
            self._current_session.add_command(f"break 0x{address:04X}")
        
        return bp_id
    
    def clear_breakpoint(self, breakpoint_id: int) -> bool:
        """Clear a breakpoint by ID."""
        result = self._breakpoint_manager.remove_breakpoint(breakpoint_id)
        
        if self._current_session and result:
            self._current_session.add_command(f"clear {breakpoint_id}")
        
        return result
    
    def enable_breakpoint(self, breakpoint_id: int) -> bool:
        """Enable a breakpoint."""
        return self._breakpoint_manager.enable_breakpoint(breakpoint_id)
    
    def disable_breakpoint(self, breakpoint_id: int) -> bool:
        """Disable a breakpoint."""
        return self._breakpoint_manager.disable_breakpoint(breakpoint_id)
    
    def step_into(self) -> None:
        """Execute next single instruction."""
        current_address = self._registers.pc
        self._step_controller.step_into(current_address)
        self._state = DebuggerState.STEPPING
        self._notify_state_change()
        
        if self._current_session:
            self._current_session.add_command("step")
            self._current_session.context.step_count += 1
    
    def step_over(self) -> None:
        """Execute next instruction, stepping over calls."""
        current_address = self._registers.pc
        # This would need actual instruction decoding in practice
        instruction = "NOP"  # Placeholder
        next_address = current_address + 1  # Placeholder
        
        self._step_controller.step_over(current_address, instruction, next_address)
        self._state = DebuggerState.STEPPING
        self._notify_state_change()
        
        if self._current_session:
            self._current_session.add_command("next")
            self._current_session.context.step_count += 1
    
    def step_out(self) -> None:
        """Execute until return from current function."""
        current_address = self._registers.pc
        stack_pointer = self._registers.s
        
        self._step_controller.step_out(current_address, stack_pointer)
        self._state = DebuggerState.STEPPING
        self._notify_state_change()
        
        if self._current_session:
            self._current_session.add_command("finish")
    
    def continue_execution(self) -> None:
        """Continue normal execution."""
        self._step_controller.continue_execution()
        self._state = DebuggerState.ACTIVE
        self._notify_state_change()
        
        if self._current_session:
            self._current_session.add_command("continue")
    
    def pause_execution(self) -> None:
        """Pause execution."""
        current_address = self._registers.pc
        self._step_controller.pause_execution(current_address)
        self._state = DebuggerState.PAUSED
        self._notify_state_change()
    
    def check_breakpoints(self, address: int, context: Optional[Dict[str, Any]] = None) -> Optional[BreakpointHitInfo]:
        """Check if any breakpoint should trigger at the given address."""
        if context is None:
            context = self._get_execution_context()
        
        return self._breakpoint_manager.check_breakpoint_hit(address, context)
    
    def should_break_on_step(self, address: int, instruction: str) -> bool:
        """Check if execution should break for step mode."""
        stack_pointer = self._registers.s
        return self._step_controller.should_break(address, instruction, stack_pointer)
    
    def show_registers(self) -> None:
        """Display CPU registers."""
        lines = self._state_inspector.register_inspector.format_registers()
        for line in lines:
            print(line)
    
    def show_flags(self) -> None:
        """Display CPU flags."""
        lines = self._state_inspector.flag_inspector.format_flags()
        for line in lines:
            print(line)
    
    def show_memory(self, address: int, length: int = 64) -> None:
        """Display memory dump."""
        lines = self._state_inspector.memory_inspector.format_memory_dump(address, length)
        for line in lines:
            print(line)
    
    def show_call_stack(self) -> None:
        """Display call stack."""
        call_stack = self._step_controller.get_call_stack()
        frames = call_stack.get_frames()
        
        if not frames:
            print("Call stack is empty")
            return
        
        print("Call Stack:")
        for i, frame in enumerate(reversed(frames)):
            print(f"  #{i}: Return to 0x{frame.return_address:04X} (SP: 0x{frame.stack_pointer:02X})")
            if frame.function_name:
                print(f"       Function: {frame.function_name}")
    
    def list_breakpoints(self) -> None:
        """List all breakpoints."""
        breakpoints = self._breakpoint_manager.get_all_breakpoints()
        
        if not breakpoints:
            print("No breakpoints set")
            return
        
        print("Breakpoints:")
        for bp in breakpoints:
            status = "enabled" if bp.state.name == "ENABLED" else "disabled"
            print(f"  {bp.id}: 0x{bp.address:04X} ({status}) - hits: {bp.hit_count}")
            if bp.description:
                print(f"       {bp.description}")
    
    def disassemble(self, address: int, count: int = 10) -> None:
        """Disassemble instructions."""
        instructions = self._disassembler.disassemble_count(address, count)
        lines = self._disassembler.format_disassembly(instructions)
        
        for line in lines:
            print(line)
    
    def save_state(self, filename: str) -> None:
        """Save current state to file."""
        devices = {}  # Would need to be populated with actual devices
        state = self._serializer.serialize_state(
            self._registers, self._flags, self._memory, devices
        )
        
        self._serializer.save_to_file(state, filename)
        
        if self._current_session:
            self._current_session.add_state_snapshot(state)
    
    def load_state(self, filename: str) -> None:
        """Load state from file."""
        state = self._serializer.load_from_file(filename)
        
        # This would need actual state restoration logic
        print(f"State loaded from {filename} (restoration not implemented)")
    
    def validate_state(self) -> None:
        """Validate current state."""
        devices = {}  # Would need actual devices
        state = self._serializer.serialize_state(
            self._registers, self._flags, self._memory, devices
        )
        
        report = self._validator.validate_state(state)
        
        print(report.get_summary())
        if report.issues:
            print("\nIssues found:")
            for issue in report.issues:
                print(f"  {issue}")
    
    def get_current_address(self) -> int:
        """Get current program counter value."""
        return self._registers.pc
    
    def get_register_value(self, register_name: str) -> Optional[int]:
        """Get register value by name."""
        reg_map = {
            'A': self._registers.a,
            'X': self._registers.x,
            'Y': self._registers.y,
            'PC': self._registers.pc,
            'S': self._registers.s,
            'P': self._registers.p
        }
        return reg_map.get(register_name.upper())
    
    def read_memory_byte(self, address: int) -> int:
        """Read a byte from memory."""
        return self._memory.read_byte(address)
    
    def add_device(self, name: str, device: Device) -> None:
        """Add a device for debugging."""
        self._state_inspector.add_device(name, device)
    
    def _get_execution_context(self) -> Dict[str, Any]:
        """Get current execution context for breakpoint evaluation."""
        return {
            'A': self._registers.a,
            'X': self._registers.x,
            'Y': self._registers.y,
            'PC': self._registers.pc,
            'S': self._registers.s,
            'P': self._registers.p,
            'cycle_count': self._current_session.context.cycle_count if self._current_session else 0
        }
    
    def _handle_breakpoint_hit(self, hit_info: BreakpointHitInfo) -> None:
        """Handle breakpoint hit."""
        self._state = DebuggerState.PAUSED
        self._notify_state_change()
        
        if self._current_session:
            self._current_session.add_breakpoint_hit(hit_info)
            self._current_session.context.current_address = hit_info.address
        
        # Notify callbacks
        for callback in self._on_breakpoint_hit:
            try:
                callback(hit_info)
            except Exception:
                pass
        
        print(f"\nBreakpoint {hit_info.breakpoint_id} hit at 0x{hit_info.address:04X}")
        self.show_registers()
    
    def _handle_step_complete(self, context: Any) -> None:
        """Handle step completion."""
        if self._current_session:
            self._current_session.context.current_address = context.current_address
        
        # Notify callbacks
        for callback in self._on_step_complete:
            try:
                callback(context.current_address)
            except Exception:
                pass
    
    def _notify_state_change(self) -> None:
        """Notify state change callbacks."""
        for callback in self._on_state_change:
            try:
                callback(self._state)
            except Exception:
                pass
    
    def add_breakpoint_callback(self, callback: Callable[[BreakpointHitInfo], None]) -> None:
        """Add breakpoint hit callback."""
        self._on_breakpoint_hit.append(callback)
    
    def add_step_callback(self, callback: Callable[[int], None]) -> None:
        """Add step complete callback."""
        self._on_step_complete.append(callback)
    
    def add_state_change_callback(self, callback: Callable[[DebuggerState], None]) -> None:
        """Add state change callback."""
        self._on_state_change.append(callback)
    
    def get_debugger_state(self) -> DebuggerState:
        """Get current debugger state."""
        return self._state
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get current session information."""
        if self._current_session is None:
            return None
        
        return self._current_session.get_statistics()
