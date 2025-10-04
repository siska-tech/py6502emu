"""
共通型定義

W65C02S エミュレータで使用される共通の型定義とデータ構造を提供します。
"""

from typing import TypedDict, List, Dict, Any
from enum import Enum, auto


class InterruptLine(Enum):
    """割り込み線定義"""
    IRQ = auto()
    NMI = auto()
    RESET = auto()


class DeviceType(Enum):
    """デバイス種別"""
    CPU = auto()
    MEMORY = auto()
    VIDEO = auto()
    AUDIO = auto()
    IO = auto()


class SystemState(TypedDict):
    """システム状態"""
    devices: Dict[str, Dict[str, Any]]
    system_time: int
    master_clock: int


class MemoryMapping(TypedDict):
    """メモリマッピング情報"""
    start_address: int
    end_address: int
    device_id: str
    device_name: str
    size: int
