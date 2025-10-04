"""
W65C02S CPU Emulator in Python

A comprehensive emulator for the Western Design Center W65C02S microprocessor,
implementing the complete instruction set with cycle-accurate timing.
"""

__version__ = "0.1.0"
__author__ = "Development Team"
__email__ = "dev@example.com"

from .core.device import Device, CPUDevice, VideoDevice, AudioDevice
from .core.types import InterruptLine, DeviceType, SystemState
from .core.config import ConfigurationManager, SystemConfig, CPUConfig, MemoryConfig

__all__ = [
    "Device",
    "CPUDevice", 
    "VideoDevice",
    "AudioDevice",
    "InterruptLine",
    "DeviceType",
    "SystemState",
    "ConfigurationManager",
    "SystemConfig",
    "CPUConfig",
    "MemoryConfig",
]
