"""
pytest設定ファイル

W65C02S エミュレータのテスト実行に必要な共通設定とフィクスチャを定義します。
"""

import pytest
from typing import Dict, Any
from py6502emu.core.device import Device, DeviceConfig, InvalidAddressError, InvalidValueError


class MockDevice:
    """テスト用モックデバイス
    
    Device プロトコルを実装したテスト用のモックデバイス。
    単体テストや統合テストで使用されます。
    """
    
    def __init__(self, config: DeviceConfig) -> None:
        self._config = config
        self._state = {'test': 0}
        self._memory = bytearray(0x10000)  # 64KB memory space
    
    @property
    def name(self) -> str:
        return self._config.name
    
    def reset(self) -> None:
        self._state = {'test': 0}
        self._memory = bytearray(0x10000)
    
    def tick(self, master_cycles: int) -> int:
        return master_cycles
    
    def read(self, address: int) -> int:
        if not (0 <= address <= 0xFFFF):
            raise InvalidAddressError(address)
        return self._memory[address]
    
    def write(self, address: int, value: int) -> None:
        if not (0 <= address <= 0xFFFF):
            raise InvalidAddressError(address)
        if not (0 <= value <= 0xFF):
            raise InvalidValueError(value)
        self._memory[address] = value
    
    def get_state(self) -> Dict[str, Any]:
        return self._state.copy()
    
    def set_state(self, state: Dict[str, Any]) -> None:
        self._state = state.copy()


@pytest.fixture
def mock_device_config():
    """モックデバイス設定フィクスチャ"""
    return DeviceConfig(device_id="test_device", name="Test Device")


@pytest.fixture
def mock_device(mock_device_config):
    """モックデバイスフィクスチャ"""
    return MockDevice(mock_device_config)


@pytest.fixture
def sample_config_data():
    """サンプル設定データフィクスチャ"""
    return {
        "system": {
            "master_clock_hz": 1500000,
            "debug_enabled": True,
            "log_level": "DEBUG"
        },
        "devices": [
            {
                "type": "cpu",
                "device_id": "main_cpu",
                "name": "W65C02S CPU",
                "clock_divider": 1,
                "reset_vector": 0x8000,
                "irq_vector": 0xFFFE,
                "nmi_vector": 0xFFFA
            },
            {
                "type": "memory",
                "device_id": "main_ram",
                "name": "System RAM",
                "size": 32768,
                "start_address": 0x0000,
                "end_address": 0x7FFF,
                "readonly": False
            }
        ]
    }
