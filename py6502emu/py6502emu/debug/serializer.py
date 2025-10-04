"""
State serialization system for W65C02S emulator debugging.

This module implements PU017: StateSerializer functionality including:
- Complete system state serialization to dict format
- CPU, memory, and device state integration
- State data compression functionality
- Version management support
- Metadata attachment functionality
"""

from typing import Dict, List, Optional, Any, Union, Tuple, BinaryIO
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
import json
import pickle
import zlib
import time
import hashlib
from datetime import datetime

from ..cpu.registers import CPURegisters
from ..cpu.flags import ProcessorFlags
from ..memory.memory_controller import MemoryController
from ..core.device import Device


class SerializationFormat(Enum):
    """Supported serialization formats."""
    JSON = auto()           # Human-readable JSON format
    PICKLE = auto()         # Python pickle format (binary)
    COMPRESSED_JSON = auto() # Compressed JSON format
    COMPRESSED_PICKLE = auto() # Compressed pickle format


class CompressionLevel(Enum):
    """Compression levels for state data."""
    NONE = 0
    FAST = 1
    BALANCED = 6
    BEST = 9


@dataclass
class StateMetadata:
    """Metadata associated with serialized state."""
    version: str = "1.0"
    timestamp: float = field(default_factory=time.time)
    description: str = ""
    emulator_version: str = "W65C02S-Emu-1.0"
    format_version: int = 1
    checksum: Optional[str] = None
    compression: CompressionLevel = CompressionLevel.NONE
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        data = asdict(self)
        data['compression'] = self.compression.value
        data['datetime'] = datetime.fromtimestamp(self.timestamp).isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateMetadata':
        """Create metadata from dictionary."""
        # Handle compression level
        if 'compression' in data:
            data['compression'] = CompressionLevel(data['compression'])
        
        # Remove datetime field if present (we use timestamp)
        data.pop('datetime', None)
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class StateFormat:
    """Defines the structure of serialized state data."""
    metadata: StateMetadata
    cpu_registers: Dict[str, int]
    cpu_flags: Dict[str, bool]
    memory_ranges: List[Dict[str, Any]]  # List of {start, end, data} dicts
    devices: Dict[str, Dict[str, Any]]
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_checksum(self) -> str:
        """Calculate checksum of state data (excluding metadata)."""
        # Create a copy without metadata for checksum calculation
        state_copy = {
            'cpu_registers': self.cpu_registers,
            'cpu_flags': self.cpu_flags,
            'memory_ranges': self.memory_ranges,
            'devices': self.devices,
            'custom_data': self.custom_data
        }
        
        # Serialize to JSON for consistent checksum
        json_data = json.dumps(state_copy, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(json_data.encode('utf-8')).hexdigest()


class CompressionHandler:
    """Handles compression and decompression of state data."""
    
    @staticmethod
    def compress(data: bytes, level: CompressionLevel = CompressionLevel.BALANCED) -> bytes:
        """Compress data using zlib."""
        if level == CompressionLevel.NONE:
            return data
        
        return zlib.compress(data, level.value)
    
    @staticmethod
    def decompress(compressed_data: bytes) -> bytes:
        """Decompress data using zlib."""
        try:
            return zlib.decompress(compressed_data)
        except zlib.error as e:
            raise ValueError(f"Failed to decompress data: {e}")
    
    @staticmethod
    def get_compression_ratio(original_size: int, compressed_size: int) -> float:
        """Calculate compression ratio."""
        if original_size == 0:
            return 0.0
        return compressed_size / original_size


class StateSerializer:
    """
    Serializes and deserializes complete W65C02S emulator state.
    
    Provides functionality for saving and restoring the complete state
    of the emulator including CPU registers, memory contents, and device states.
    """
    
    def __init__(self):
        self._compression_handler = CompressionHandler()
        self._memory_chunk_size = 4096  # Size of memory chunks to serialize
        self._include_empty_memory = False  # Whether to include zero-filled memory
    
    def set_options(self, memory_chunk_size: int = 4096, 
                   include_empty_memory: bool = False) -> None:
        """Set serialization options."""
        self._memory_chunk_size = memory_chunk_size
        self._include_empty_memory = include_empty_memory
    
    def serialize_state(self, registers: CPURegisters, flags: ProcessorFlags,
                       memory_controller: MemoryController,
                       devices: Optional[Dict[str, Device]] = None,
                       metadata: Optional[StateMetadata] = None,
                       memory_ranges: Optional[List[Tuple[int, int]]] = None) -> StateFormat:
        """
        Serialize complete system state.
        
        Args:
            registers: CPU registers object
            flags: CPU flags object
            memory_controller: Memory controller for memory access
            devices: Dictionary of devices to serialize
            metadata: Optional metadata for the state
            memory_ranges: Optional list of (start, end) tuples for memory ranges to serialize
            
        Returns:
            StateFormat object containing all state data
        """
        if metadata is None:
            metadata = StateMetadata()
        
        if devices is None:
            devices = {}
        
        # Serialize CPU registers
        cpu_registers = {
            'A': registers.a,
            'X': registers.x,
            'Y': registers.y,
            'PC': registers.pc,
            'S': registers.s,
            'P': registers.p
        }
        
        # Serialize CPU flags
        cpu_flags = {
            'N': flags.negative,
            'V': flags.overflow,
            'U': True,  # Unused bit always true
            'B': flags.break_flag,
            'D': flags.decimal,
            'I': flags.interrupt,
            'Z': flags.zero,
            'C': flags.carry
        }
        
        # Serialize memory
        if memory_ranges is None:
            # Default to full 64KB address space
            memory_ranges = [(0x0000, 0xFFFF)]
        
        memory_data = self._serialize_memory(memory_controller, memory_ranges)
        
        # Serialize devices
        device_data = {}
        for name, device in devices.items():
            device_data[name] = self._serialize_device(device)
        
        # Create state format
        state = StateFormat(
            metadata=metadata,
            cpu_registers=cpu_registers,
            cpu_flags=cpu_flags,
            memory_ranges=memory_data,
            devices=device_data
        )
        
        # Calculate and set checksum
        metadata.checksum = state.calculate_checksum()
        
        return state
    
    def deserialize_state(self, state: StateFormat) -> Dict[str, Any]:
        """
        Deserialize state format into component data.
        
        Args:
            state: StateFormat object to deserialize
            
        Returns:
            Dictionary containing deserialized components
        """
        # Verify checksum if present
        if state.metadata.checksum:
            calculated_checksum = state.calculate_checksum()
            if calculated_checksum != state.metadata.checksum:
                raise ValueError(f"State checksum mismatch: expected {state.metadata.checksum}, "
                               f"got {calculated_checksum}")
        
        return {
            'metadata': state.metadata,
            'cpu_registers': state.cpu_registers,
            'cpu_flags': state.cpu_flags,
            'memory_ranges': state.memory_ranges,
            'devices': state.devices,
            'custom_data': state.custom_data
        }
    
    def save_to_file(self, state: StateFormat, filename: str,
                    format_type: SerializationFormat = SerializationFormat.COMPRESSED_JSON) -> None:
        """
        Save state to file.
        
        Args:
            state: State to save
            filename: Output filename
            format_type: Serialization format to use
        """
        # Update metadata
        state.metadata.compression = self._get_compression_level(format_type)
        
        if format_type in [SerializationFormat.JSON, SerializationFormat.COMPRESSED_JSON]:
            # JSON format
            data = self._state_to_json(state)
            data_bytes = data.encode('utf-8')
            
            if format_type == SerializationFormat.COMPRESSED_JSON:
                data_bytes = self._compression_handler.compress(data_bytes, state.metadata.compression)
            
        else:
            # Pickle format
            data_bytes = pickle.dumps(state)
            
            if format_type == SerializationFormat.COMPRESSED_PICKLE:
                data_bytes = self._compression_handler.compress(data_bytes, state.metadata.compression)
        
        # Update size in metadata
        state.metadata.size_bytes = len(data_bytes)
        
        # Write to file
        with open(filename, 'wb') as f:
            f.write(data_bytes)
    
    def load_from_file(self, filename: str,
                      format_type: Optional[SerializationFormat] = None) -> StateFormat:
        """
        Load state from file.
        
        Args:
            filename: Input filename
            format_type: Expected format (auto-detect if None)
            
        Returns:
            Loaded StateFormat object
        """
        with open(filename, 'rb') as f:
            data_bytes = f.read()
        
        # Auto-detect format if not specified
        if format_type is None:
            format_type = self._detect_format(data_bytes)
        
        # Decompress if needed
        if format_type in [SerializationFormat.COMPRESSED_JSON, SerializationFormat.COMPRESSED_PICKLE]:
            try:
                data_bytes = self._compression_handler.decompress(data_bytes)
            except ValueError:
                # Maybe it's not compressed after all
                pass
        
        # Deserialize based on format
        if format_type in [SerializationFormat.JSON, SerializationFormat.COMPRESSED_JSON]:
            data_str = data_bytes.decode('utf-8')
            return self._state_from_json(data_str)
        else:
            return pickle.loads(data_bytes)
    
    def _serialize_memory(self, memory_controller: MemoryController,
                         ranges: List[Tuple[int, int]]) -> List[Dict[str, Any]]:
        """Serialize memory ranges."""
        memory_data = []
        
        for start_addr, end_addr in ranges:
            # Read memory in chunks
            current_addr = start_addr
            
            while current_addr <= end_addr:
                chunk_end = min(current_addr + self._memory_chunk_size - 1, end_addr)
                chunk_data = []
                
                # Read chunk
                for addr in range(current_addr, chunk_end + 1):
                    try:
                        value = memory_controller.read_byte(addr)
                        chunk_data.append(value)
                    except Exception:
                        chunk_data.append(0)  # Use 0 for inaccessible memory
                
                # Check if chunk is empty (all zeros) and skip if configured
                if not self._include_empty_memory and all(b == 0 for b in chunk_data):
                    current_addr = chunk_end + 1
                    continue
                
                # Add chunk to memory data
                memory_data.append({
                    'start': current_addr,
                    'end': chunk_end,
                    'data': chunk_data
                })
                
                current_addr = chunk_end + 1
        
        return memory_data
    
    def _serialize_device(self, device: Device) -> Dict[str, Any]:
        """Serialize a single device."""
        device_data = {
            'type': type(device).__name__,
            'class_module': type(device).__module__
        }
        
        # Try to get device state
        try:
            if hasattr(device, 'get_state'):
                device_data['state'] = device.get_state()
            elif hasattr(device, '__dict__'):
                # Fallback: serialize device attributes
                device_data['attributes'] = {
                    k: v for k, v in device.__dict__.items()
                    if not k.startswith('_') and not callable(v)
                }
        except Exception as e:
            device_data['error'] = str(e)
        
        return device_data
    
    def _state_to_json(self, state: StateFormat) -> str:
        """Convert state to JSON string."""
        # Convert state to dictionary
        state_dict = {
            'metadata': state.metadata.to_dict(),
            'cpu_registers': state.cpu_registers,
            'cpu_flags': state.cpu_flags,
            'memory_ranges': state.memory_ranges,
            'devices': state.devices,
            'custom_data': state.custom_data
        }
        
        return json.dumps(state_dict, indent=2, separators=(',', ': '))
    
    def _state_from_json(self, json_str: str) -> StateFormat:
        """Create state from JSON string."""
        data = json.loads(json_str)
        
        metadata = StateMetadata.from_dict(data.get('metadata', {}))
        
        return StateFormat(
            metadata=metadata,
            cpu_registers=data.get('cpu_registers', {}),
            cpu_flags=data.get('cpu_flags', {}),
            memory_ranges=data.get('memory_ranges', []),
            devices=data.get('devices', {}),
            custom_data=data.get('custom_data', {})
        )
    
    def _detect_format(self, data_bytes: bytes) -> SerializationFormat:
        """Auto-detect serialization format from data."""
        # Try to detect if it's compressed
        try:
            decompressed = self._compression_handler.decompress(data_bytes)
            # If decompression succeeded, check the decompressed data
            if decompressed.startswith(b'{'):
                return SerializationFormat.COMPRESSED_JSON
            else:
                return SerializationFormat.COMPRESSED_PICKLE
        except ValueError:
            pass
        
        # Check if it starts with JSON
        if data_bytes.strip().startswith(b'{'):
            return SerializationFormat.JSON
        
        # Assume pickle format
        return SerializationFormat.PICKLE
    
    def _get_compression_level(self, format_type: SerializationFormat) -> CompressionLevel:
        """Get compression level for format type."""
        if format_type in [SerializationFormat.COMPRESSED_JSON, SerializationFormat.COMPRESSED_PICKLE]:
            return CompressionLevel.BALANCED
        return CompressionLevel.NONE
    
    def create_state_diff(self, old_state: StateFormat, new_state: StateFormat) -> Dict[str, Any]:
        """
        Create a diff between two states.
        
        Args:
            old_state: Previous state
            new_state: Current state
            
        Returns:
            Dictionary containing differences
        """
        diff = {
            'metadata': {
                'old_timestamp': old_state.metadata.timestamp,
                'new_timestamp': new_state.metadata.timestamp,
                'time_delta': new_state.metadata.timestamp - old_state.metadata.timestamp
            },
            'cpu_registers': {},
            'cpu_flags': {},
            'memory_changes': [],
            'device_changes': {}
        }
        
        # Compare CPU registers
        for reg, new_val in new_state.cpu_registers.items():
            old_val = old_state.cpu_registers.get(reg, 0)
            if old_val != new_val:
                diff['cpu_registers'][reg] = {'old': old_val, 'new': new_val}
        
        # Compare CPU flags
        for flag, new_val in new_state.cpu_flags.items():
            old_val = old_state.cpu_flags.get(flag, False)
            if old_val != new_val:
                diff['cpu_flags'][flag] = {'old': old_val, 'new': new_val}
        
        # Compare memory (simplified - just count changes)
        old_memory_map = {(r['start'], r['end']): r['data'] for r in old_state.memory_ranges}
        new_memory_map = {(r['start'], r['end']): r['data'] for r in new_state.memory_ranges}
        
        memory_changes = 0
        for range_key, new_data in new_memory_map.items():
            old_data = old_memory_map.get(range_key, [])
            if old_data != new_data:
                memory_changes += 1
        
        diff['memory_changes'] = memory_changes
        
        # Compare devices
        for device_name, new_device in new_state.devices.items():
            old_device = old_state.devices.get(device_name, {})
            if old_device != new_device:
                diff['device_changes'][device_name] = {
                    'changed': True,
                    'old_type': old_device.get('type', 'unknown'),
                    'new_type': new_device.get('type', 'unknown')
                }
        
        return diff
    
    def get_state_statistics(self, state: StateFormat) -> Dict[str, Any]:
        """Get statistics about a state object."""
        total_memory_bytes = sum(len(r['data']) for r in state.memory_ranges)
        memory_ranges_count = len(state.memory_ranges)
        device_count = len(state.devices)
        
        return {
            'metadata': {
                'version': state.metadata.version,
                'timestamp': state.metadata.timestamp,
                'size_bytes': state.metadata.size_bytes,
                'compression': state.metadata.compression.name,
                'has_checksum': state.metadata.checksum is not None
            },
            'cpu': {
                'register_count': len(state.cpu_registers),
                'flag_count': len(state.cpu_flags)
            },
            'memory': {
                'total_bytes': total_memory_bytes,
                'range_count': memory_ranges_count,
                'average_range_size': total_memory_bytes / memory_ranges_count if memory_ranges_count > 0 else 0
            },
            'devices': {
                'device_count': device_count,
                'device_types': list(set(d.get('type', 'unknown') for d in state.devices.values()))
            }
        }
