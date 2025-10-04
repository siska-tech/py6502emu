# W65C02S CPU Emulator

A comprehensive Python emulator for the Western Design Center W65C02S microprocessor, implementing the complete instruction set with cycle-accurate timing and advanced debugging capabilities.

[![GitHub](https://img.shields.io/badge/GitHub-siska--tech%2Fpy6502emu-blue)](https://github.com/siska-tech/py6502emu)
[![Python](https://img.shields.io/badge/Python-3.8+-green)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## Project Status

🎉 **ALL PHASES COMPLETED** 🎉

**Phase 1: Foundation** ✅ **COMPLETED**
- ✅ Device Protocol (PU019) - Unified device interface
- ✅ System Bus (PU020) - Device communication and memory mapping
- ✅ Configuration Manager (PU022) - System and device configuration management

**Phase 2: CPU Core** ✅ **COMPLETED**
- ✅ CPURegisters (PU001) - CPU register management
- ✅ ProcessorFlags (PU002) - Processor status flags
- ✅ AddressingModes (PU003) - W65C02S addressing modes
- ✅ InstructionDecoder (PU004) - Instruction decoding engine
- ✅ InterruptHandler (PU021) - Interrupt processing system

**Phase 3: Memory & I/O** ✅ **COMPLETED**
- ✅ AddressSpace (PU005) - Memory address space management
- ✅ DeviceMapper (PU006) - Device address mapping
- ✅ MemoryController (PU007) - Unified memory access control
- ✅ MMU (PU008) - Memory management unit

**Phase 4: System Integration** ✅ **COMPLETED & VERIFIED**
- ✅ TickEngine (PU009) - Precise timing control with ClockListener integration
- ✅ SystemClock (PU010) - Master clock management with cycle-accurate timing
- ✅ Scheduler (PU011) - Task scheduling system
- ✅ SystemOrchestrator (PU012) - System coordination and lifecycle management
- ✅ InterruptController (PU023) - System interrupt management
- ✅ ComponentRegistry - Dependency management with topological sorting
- ✅ SystemIntegration - Complete system initialization and orchestration

**Phase 5: Debug & Tools** ✅ **COMPLETED**
- ✅ BreakpointManager (PU013) - Breakpoint management system
- ✅ StepController (PU014) - Step execution control
- ✅ StateInspector (PU015) - State inspection functionality
- ✅ Disassembler (PU016) - W65C02S instruction disassembly
- ✅ StateSerializer (PU017) - State serialization and compression
- ✅ StateValidator (PU018) - State validation and integrity checking
- ✅ Integrated Debugger - pdb-style command interface
- ✅ Source-level Debugging - Assembly source mapping

## Features

### Complete W65C02S Emulation

- **Full Instruction Set**: Complete W65C02S instruction set with cycle-accurate timing
- **CPU Core**: Registers, flags, addressing modes, and instruction decoding
- **Memory Management**: 64KB address space with device mapping and MMU
- **Interrupt System**: IRQ, NMI, and BRK interrupt handling
- **Timing Control**: Precise clock management and scheduling system

### Foundation & Architecture

- **Unified Device Protocol**: Common interface for all emulated devices (CPU, memory, I/O)
- **System Bus**: Memory mapping, bus arbitration, and device communication
- **Configuration Management**: JSON-based configuration with validation
- **Modular Design**: Clean separation of concerns with extensible architecture
- **Comprehensive Testing**: Unit tests, integration tests, and performance tests

### Advanced Debugging & Analysis

- **Interactive Debugger**: pdb-style command-line interface with full debugging capabilities
- **Breakpoint System**: Address-based and conditional breakpoints with Python expression evaluation
- **Step Execution**: Step into/over/out functionality with call stack tracking
- **State Inspection**: CPU registers, processor flags, and memory dump visualization
- **Disassembly Engine**: Complete W65C02S instruction set disassembly with symbolic labels
- **State Management**: Save/restore system state with compression and validation
- **Source Integration**: Assembly source code mapping and symbol resolution
- **Performance Analysis**: Execution statistics and performance profiling

## Installation

```bash
# Clone the repository
git clone https://github.com/siska-tech/py6502emu.git
cd py6502emu

# Install in development mode
pip install -e .[dev]
```

## Quick Start

### Complete System Setup

```python
from py6502emu.core.integration import SystemIntegration
from py6502emu.core.system_config import SystemConfiguration, ExecutionMode

# Create and configure the system using the new integration approach
integration = SystemIntegration()
config = SystemConfiguration(
    execution_mode=ExecutionMode.CONTINUOUS,
    enable_debugging=True
)

# Initialize the complete system
if integration.initialize_system(config):
    print("System initialized successfully!")
    
    # Get system components
    orchestrator = integration.get_system_orchestrator()
    system_clock = integration.get_system_clock()
    tick_engine = integration.get_tick_engine()
    
    # Start the system
    orchestrator.start()
    
    # The system is now running with all components integrated
    print("System is running!")
else:
    print("System initialization failed!")
```

### Debug Environment Setup

```python
from py6502emu.debug import create_debugger, create_source_debugger

# Create integrated debugger (using components from system setup above)
debugger = create_debugger(registers, flags, memory_controller)

# Set breakpoints
bp_id = debugger.set_breakpoint(0x1000)
conditional_bp = debugger.set_breakpoint(0x2000, condition="A == 0x42")

# Add devices for debugging
debugger.add_device("main_ram", ram_device)
debugger.add_device("main_cpu", cpu_device)

# Start interactive debugging session
debugger.start_interactive()

# Or use programmatically
debugger.start_session("debug_session_1")
debugger.step_into()  # Execute one instruction
debugger.show_registers()  # Display CPU state
debugger.disassemble(0x1000, 10)  # Show disassembly
```

### Source-level Debugging

```python
from py6502emu.debug import create_source_debugger

# Create source debugger
source_debugger = create_source_debugger()

# Load assembler output files
source_debugger.load_report_file("program.rpt")
source_debugger.load_map_file("program.lmap")

# Get source location for address
location = source_debugger.get_source_location(0x1000)
if location:
    file_path, line_number, source_line = location
    print(f"Address 0x1000 -> {file_path}:{line_number}")

# Show source context
context = source_debugger.show_source_context(0x1000, context_lines=5)
for line in context:
    print(line)
```

## Configuration

The emulator uses JSON configuration files:

```json
{
  "system": {
    "master_clock_hz": 1000000,
    "debug_enabled": true,
    "log_level": "INFO"
  },
  "devices": [
    {
      "type": "cpu",
      "device_id": "main_cpu",
      "name": "W65C02S CPU",
      "clock_divider": 1,
      "reset_vector": 65532,
      "irq_vector": 65534,
      "nmi_vector": 65530
    },
    {
      "type": "memory",
      "device_id": "main_ram",
      "name": "System RAM",
      "size": 32768,
      "start_address": 0,
      "end_address": 32767,
      "readonly": false
    }
  ]
}
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=py6502emu --cov-report=html

# Run specific test categories
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests (44 tests, 100% passing)
pytest tests/unit/test_debug/  # Debug functionality tests

# Verify system integration
pytest tests/integration/test_system_integration.py -v
```

**Current Test Status**: ✅ **44/44 integration tests passing**

### Code Quality

```bash
# Type checking
mypy py6502emu/

# Code formatting
black py6502emu/

# Linting
pylint py6502emu/
```

## Architecture

The emulator follows a modular architecture with clear separation of concerns:

- **Core Services** (`py6502emu.core`): Device protocols, configuration management, system orchestration
- **CPU Core** (`py6502emu.cpu`): Complete W65C02S CPU implementation with registers, flags, and instruction decoding
- **Memory Management** (`py6502emu.memory`): Address space management, device mapping, and memory controllers
- **Debug Tools** (`py6502emu.debug`): Comprehensive debugging and analysis tools

### Complete System Architecture

The emulator provides a full-featured W65C02S system:

#### CPU Subsystem
- **Register Management**: A, X, Y, PC, S, P registers with validation
- **Flag Processing**: N, V, B, D, I, Z, C flags with automatic updates
- **Addressing Modes**: All 13 W65C02S addressing modes
- **Instruction Decoding**: Complete instruction set with cycle-accurate timing
- **Interrupt Handling**: IRQ, NMI, and BRK interrupt processing

#### Memory Subsystem
- **Address Space**: Full 64KB address space management
- **Device Mapping**: Flexible device-to-address mapping
- **Memory Controller**: Unified memory access with logging and validation
- **MMU**: Memory management unit with protection and translation

#### System Integration
- **Timing Engine**: Precise clock control and cycle counting
- **Scheduler**: Task scheduling and execution management
- **Orchestrator**: System-wide coordination and control
- **Interrupt Controller**: System interrupt management and prioritization

#### Debug Environment
- **Breakpoint System**: Address and conditional breakpoints with hit detection
- **Execution Control**: Step-by-step execution with call stack management
- **State Management**: Register, flag, and memory inspection with formatting
- **Disassembly Engine**: W65C02S instruction disassembly with symbol resolution
- **Serialization**: State save/restore with compression and validation
- **Interactive Interface**: Command-line debugger with pdb-style commands
- **Source Integration**: Assembly source mapping and symbol management

## Implementation Complete

🎉 **All phases have been successfully implemented!** 🎉

- **Phase 1**: Foundation ✅ **COMPLETED**
- **Phase 2**: CPU Core Implementation ✅ **COMPLETED**
- **Phase 3**: Memory Management and I/O ✅ **COMPLETED**
- **Phase 4**: System Integration and Optimization ✅ **COMPLETED**
- **Phase 5**: Debug Tools and Advanced Features ✅ **COMPLETED**

### Project Statistics

- **Total Program Units**: 23 PUs implemented
- **Core Components**: 8 modules (core, cpu, memory, debug)
- **Test Coverage**: 44/44 integration tests passing (100% success rate)
- **System Integration**: All components verified and working together
- **Documentation**: Complete technical documentation
- **Architecture**: Modular, extensible, and maintainable design

### Recent Updates (Phase 4 Completion)

✅ **System Integration Fully Verified**
- Resolved circular dependency issues in component initialization
- Fixed topological sorting algorithm in ComponentRegistry
- Implemented ClockListener interface in TickEngine
- Verified complete system initialization and orchestration
- All 44 integration tests passing successfully

✅ **Key Improvements**
- Enhanced dependency management with validation
- Improved system lifecycle management
- Better error handling and logging
- Robust component registration and initialization

### Debug Commands Reference

The integrated debugger provides pdb-style commands:

```
s(tep)              - Execute next single instruction
n(ext)              - Execute next instruction, step over calls
c(ont)              - Continue execution
f(inish)            - Execute until return from current function
b(reak) [addr]      - Set/list breakpoints
clear <id>          - Clear breakpoint
disable/enable <id> - Disable/enable breakpoint
info [type]         - Show information (registers, flags, etc.)
p(rint) <expr>      - Print expression value
disasm [addr] [cnt] - Disassemble instructions
memory <addr> [len] - Show memory dump
save <file>         - Save current state
load <file>         - Load state from file
validate            - Validate current state
q(uit)              - Quit debugger
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass and code quality checks succeed
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Author

**Siska-Tech** - [GitHub](https://github.com/siska-tech)

## Repository

**GitHub**: https://github.com/siska-tech/py6502emu

## Documentation

- [Implementation Plan](docs/implement_plan.md)
- [Software Requirements](docs/w65c02s_software_requirements_specification.md)
- [Architecture Design](docs/w65c02s_software_architecture_design.md)
- [Detailed Design](docs/w65c02s_software_detailed_design.md)
