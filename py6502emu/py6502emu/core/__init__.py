"""
Core services for the W65C02S emulator.

This module provides the fundamental infrastructure components including:
- Device protocols and interfaces
- System configuration management  
- Common type definitions
"""

from .device import Device, CPUDevice, VideoDevice, AudioDevice, DeviceConfig
from .types import InterruptLine, DeviceType, SystemState, MemoryMapping
from .config import ConfigurationManager, SystemConfig, CPUConfig, MemoryConfig

__all__ = [
    "Device",
    "CPUDevice",
    "VideoDevice", 
    "AudioDevice",
    "DeviceConfig",
    "InterruptLine",
    "DeviceType",
    "SystemState",
    "MemoryMapping",
    "ConfigurationManager",
    "SystemConfig",
    "CPUConfig",
    "MemoryConfig",
]
