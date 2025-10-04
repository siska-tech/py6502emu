"""
Debug functionality for W65C02S emulator.

This package provides comprehensive debugging capabilities including:
- Breakpoint management
- Step execution control  
- State inspection and formatting
- Disassembly functionality
- State serialization and validation
- Integrated debugger interface
- Source-level debugging support

Phase 5 Implementation - Complete debugging and analysis tools.
"""

# Core debugging components
from .breakpoint import (
    BreakpointManager,
    Breakpoint,
    ConditionalBreakpoint,
    BreakpointHitInfo,
    BreakpointType,
    BreakpointState
)

from .step_controller import (
    StepController,
    StepMode,
    ExecutionState,
    CallFrame,
    CallStack,
    StepContext
)

from .inspector import (
    StateInspector,
    RegisterInspector,
    FlagInspector,
    MemoryInspector,
    RegisterState,
    FlagState,
    MemoryDump,
    DisplayFormat
)

from .disassembler import (
    Disassembler,
    DisassembledInstruction,
    InstructionFormatter,
    SymbolResolver,
    SourceMapper,
    AddressingMode,
    InstructionInfo
)

from .serializer import (
    StateSerializer,
    StateFormat,
    StateMetadata,
    CompressionHandler,
    SerializationFormat,
    CompressionLevel
)

from .validator import (
    StateValidator,
    ValidationReport,
    ValidationIssue,
    ValidationRule,
    IntegrityChecker,
    ValidationSeverity,
    ValidationCategory
)

from .debugger import (
    Debugger,
    DebugSession,
    CommandInterface,
    DebugContext,
    DebuggerState
)

from .source_debug import (
    SourceDebugger,
    ReportParser,
    MapParser,
    SymbolManager,
    SourceFile,
    SourceLine,
    Symbol,
    SourceFileType
)

# Version information
__version__ = "1.0.0"
__phase__ = "Phase 5"

# Main exports for easy access
__all__ = [
    # Breakpoint management
    'BreakpointManager',
    'Breakpoint', 
    'ConditionalBreakpoint',
    'BreakpointHitInfo',
    'BreakpointType',
    'BreakpointState',
    
    # Step control
    'StepController',
    'StepMode',
    'ExecutionState', 
    'CallFrame',
    'CallStack',
    'StepContext',
    
    # State inspection
    'StateInspector',
    'RegisterInspector',
    'FlagInspector', 
    'MemoryInspector',
    'RegisterState',
    'FlagState',
    'MemoryDump',
    'DisplayFormat',
    
    # Disassembly
    'Disassembler',
    'DisassembledInstruction',
    'InstructionFormatter',
    'SymbolResolver',
    'SourceMapper',
    'AddressingMode',
    'InstructionInfo',
    
    # Serialization
    'StateSerializer',
    'StateFormat',
    'StateMetadata', 
    'CompressionHandler',
    'SerializationFormat',
    'CompressionLevel',
    
    # Validation
    'StateValidator',
    'ValidationReport',
    'ValidationIssue',
    'ValidationRule',
    'IntegrityChecker', 
    'ValidationSeverity',
    'ValidationCategory',
    
    # Main debugger
    'Debugger',
    'DebugSession',
    'CommandInterface',
    'DebugContext',
    'DebuggerState',
    
    # Source debugging
    'SourceDebugger',
    'ReportParser',
    'MapParser',
    'SymbolManager',
    'SourceFile',
    'SourceLine',
    'Symbol',
    'SourceFileType'
]


def create_debugger(registers, flags, memory_controller):
    """
    Convenience function to create a fully configured debugger.
    
    Args:
        registers: CPURegisters instance
        flags: ProcessorFlags instance  
        memory_controller: MemoryController instance
        
    Returns:
        Configured Debugger instance
    """
    return Debugger(registers, flags, memory_controller)


def create_source_debugger():
    """
    Convenience function to create a source debugger.
    
    Returns:
        SourceDebugger instance
    """
    return SourceDebugger()


# Package information
def get_debug_info():
    """Get information about the debug package."""
    return {
        'version': __version__,
        'phase': __phase__,
        'components': [
            'BreakpointManager - PU013',
            'StepController - PU014', 
            'StateInspector - PU015',
            'Disassembler - PU016',
            'StateSerializer - PU017',
            'StateValidator - PU018',
            'Debugger - Integrated Interface',
            'SourceDebugger - Source-level debugging'
        ],
        'features': [
            'Address and conditional breakpoints',
            'Step into/over/out execution control',
            'CPU register and memory inspection',
            'W65C02S instruction disassembly',
            'State save/restore with validation',
            'pdb-style command interface',
            'Source code mapping and display'
        ]
    }