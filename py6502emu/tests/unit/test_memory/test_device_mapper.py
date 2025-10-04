"""
DeviceMapper テスト

デバイス動的マッピング、アドレス範囲重複検出、
マッピング情報管理のテストを提供します。
"""

import pytest
from unittest.mock import Mock, MagicMock
from py6502emu.memory.device_mapper import (
    DeviceMapper, 
    DeviceMapping, 
    DeviceMappingError, 
    AddressOverlapError
)
from py6502emu.core.device import Device


class MockDevice:
    """テスト用モックデバイス"""
    
    def __init__(self, name: str = "mock_device"):
        self.name = name
        self._memory = bytearray(0x1000)  # 4KB
    
    def reset(self) -> None:
        pass
    
    def tick(self, master_cycles: int) -> int:
        return 0
    
    def read(self, address: int) -> int:
        return self._memory[address] if address < len(self._memory) else 0
    
    def write(self, address: int, value: int) -> None:
        if address < len(self._memory):
            self._memory[address] = value
    
    def get_state(self) -> dict:
        return {}
    
    def set_state(self, state: dict) -> None:
        pass


class TestDeviceMapping:
    """DeviceMapping クラステスト"""
    
    def test_device_mapping_creation(self):
        """デバイスマッピング作成テスト"""
        device = MockDevice("test_device")
        mapping = DeviceMapping(
            device=device,
            start_address=0x8000,
            end_address=0x8FFF,
            name="ROM",
            device_offset=0x0000,
            read_only=True
        )
        
        assert mapping.device == device
        assert mapping.start_address == 0x8000
        assert mapping.end_address == 0x8FFF
        assert mapping.name == "ROM"
        assert mapping.device_offset == 0x0000
        assert mapping.read_only is True
        assert mapping.size == 0x1000
    
    def test_device_mapping_invalid_address_range(self):
        """無効アドレス範囲テスト"""
        device = MockDevice()
        
        # 開始アドレス > 終了アドレス
        with pytest.raises(ValueError, match="Start address must be <= end address"):
            DeviceMapping(device, 0x9000, 0x8000, "invalid")
        
        # アドレス範囲外
        with pytest.raises(ValueError, match="Start address must be 0x0000-0xFFFF"):
            DeviceMapping(device, -1, 0x8000, "invalid")
        
        with pytest.raises(ValueError, match="End address must be 0x0000-0xFFFF"):
            DeviceMapping(device, 0x8000, 0x10000, "invalid")
    
    def test_contains_address(self):
        """アドレス包含チェックテスト"""
        device = MockDevice()
        mapping = DeviceMapping(device, 0x8000, 0x8FFF, "ROM")
        
        assert mapping.contains_address(0x8000)
        assert mapping.contains_address(0x8500)
        assert mapping.contains_address(0x8FFF)
        assert not mapping.contains_address(0x7FFF)
        assert not mapping.contains_address(0x9000)
    
    def test_overlaps_with(self):
        """重複チェックテスト"""
        device = MockDevice()
        mapping = DeviceMapping(device, 0x8000, 0x8FFF, "ROM")
        
        # 重複あり
        assert mapping.overlaps_with(0x7000, 0x8000)  # 境界重複
        assert mapping.overlaps_with(0x8FFF, 0x9000)  # 境界重複
        assert mapping.overlaps_with(0x8500, 0x8600)  # 内包
        assert mapping.overlaps_with(0x7000, 0x9000)  # 包含
        
        # 重複なし
        assert not mapping.overlaps_with(0x7000, 0x7FFF)
        assert not mapping.overlaps_with(0x9000, 0x9FFF)
    
    def test_get_device_address(self):
        """デバイスアドレス変換テスト"""
        device = MockDevice()
        mapping = DeviceMapping(device, 0x8000, 0x8FFF, "ROM", device_offset=0x100)
        
        assert mapping.get_device_address(0x8000) == 0x100
        assert mapping.get_device_address(0x8001) == 0x101
        assert mapping.get_device_address(0x8FFF) == 0x10FF
        
        # 範囲外アドレス
        with pytest.raises(ValueError, match="Address .* is not in mapping range"):
            mapping.get_device_address(0x7FFF)


class TestDeviceMapper:
    """DeviceMapper クラステスト"""
    
    def setup_method(self):
        """各テストメソッド前の初期化"""
        self.mapper = DeviceMapper()
        self.device1 = MockDevice("device1")
        self.device2 = MockDevice("device2")
        self.device3 = MockDevice("device3")
    
    def test_initialization(self):
        """初期化テスト"""
        assert self.mapper.get_mapping_count() == 0
        assert self.mapper.get_total_mapped_size() == 0
        assert self.mapper.get_memory_map() == []
    
    def test_map_device_basic(self):
        """基本デバイスマッピングテスト"""
        self.mapper.map_device(self.device1, 0x8000, 0x8FFF, "ROM")
        
        assert self.mapper.get_mapping_count() == 1
        assert self.mapper.get_total_mapped_size() == 0x1000
        
        mapping = self.mapper.find_device(0x8000)
        assert mapping is not None
        assert mapping.device == self.device1
        assert mapping.name == "ROM"
    
    def test_map_device_with_default_name(self):
        """デフォルト名でのマッピングテスト"""
        self.mapper.map_device(self.device1, 0x8000, 0x8FFF)
        
        mapping = self.mapper.find_device(0x8000)
        assert mapping.name == "device1"  # デバイス名を使用
    
    def test_map_device_overlap_detection(self):
        """重複検出テスト"""
        # 最初のマッピング
        self.mapper.map_device(self.device1, 0x8000, 0x8FFF, "ROM1")
        
        # 重複するマッピング試行
        with pytest.raises(AddressOverlapError) as exc_info:
            self.mapper.map_device(self.device2, 0x8500, 0x9500, "ROM2")
        
        assert "overlaps with existing device 'ROM1'" in str(exc_info.value)
        assert exc_info.value.start == 0x8500
        assert exc_info.value.end == 0x9500
        assert exc_info.value.existing_name == "ROM1"
    
    def test_map_device_name_conflict(self):
        """名前重複テスト"""
        self.mapper.map_device(self.device1, 0x8000, 0x8FFF, "ROM")
        
        with pytest.raises(DeviceMappingError, match="Device name 'ROM' already exists"):
            self.mapper.map_device(self.device2, 0x9000, 0x9FFF, "ROM")
    
    def test_multiple_device_mapping(self):
        """複数デバイスマッピングテスト"""
        mappings = [
            (self.device1, 0x0000, 0x7FFF, "RAM"),
            (self.device2, 0x8000, 0x8FFF, "ROM"),
            (self.device3, 0xC000, 0xCFFF, "IO")
        ]
        
        for device, start, end, name in mappings:
            self.mapper.map_device(device, start, end, name)
        
        assert self.mapper.get_mapping_count() == 3
        assert self.mapper.get_total_mapped_size() == 0x8000 + 0x1000 + 0x1000
        
        # 各マッピングの確認
        for device, start, end, name in mappings:
            mapping = self.mapper.find_device(start)
            assert mapping is not None
            assert mapping.device == device
            assert mapping.name == name
    
    def test_find_device(self):
        """デバイス検索テスト"""
        self.mapper.map_device(self.device1, 0x8000, 0x8FFF, "ROM")
        
        # 範囲内アドレス
        mapping = self.mapper.find_device(0x8000)
        assert mapping is not None
        assert mapping.device == self.device1
        
        mapping = self.mapper.find_device(0x8500)
        assert mapping is not None
        assert mapping.device == self.device1
        
        mapping = self.mapper.find_device(0x8FFF)
        assert mapping is not None
        assert mapping.device == self.device1
        
        # 範囲外アドレス
        assert self.mapper.find_device(0x7FFF) is None
        assert self.mapper.find_device(0x9000) is None
    
    def test_get_device_by_name(self):
        """名前によるデバイス取得テスト"""
        self.mapper.map_device(self.device1, 0x8000, 0x8FFF, "ROM")
        
        mapping = self.mapper.get_device_by_name("ROM")
        assert mapping is not None
        assert mapping.device == self.device1
        
        assert self.mapper.get_device_by_name("nonexistent") is None
    
    def test_unmap_device_by_address(self):
        """アドレス指定でのマッピング解除テスト"""
        self.mapper.map_device(self.device1, 0x8000, 0x8FFF, "ROM")
        assert self.mapper.get_mapping_count() == 1
        
        self.mapper.unmap_device(0x8000, 0x8FFF)
        assert self.mapper.get_mapping_count() == 0
        assert self.mapper.find_device(0x8000) is None
    
    def test_unmap_device_by_name(self):
        """名前指定でのマッピング解除テスト"""
        self.mapper.map_device(self.device1, 0x8000, 0x8FFF, "ROM")
        assert self.mapper.get_mapping_count() == 1
        
        self.mapper.unmap_device_by_name("ROM")
        assert self.mapper.get_mapping_count() == 0
        assert self.mapper.find_device(0x8000) is None
    
    def test_unmap_nonexistent_device(self):
        """存在しないマッピング解除テスト"""
        with pytest.raises(DeviceMappingError, match="No mapping found for range"):
            self.mapper.unmap_device(0x8000, 0x8FFF)
        
        with pytest.raises(DeviceMappingError, match="No mapping found with name"):
            self.mapper.unmap_device_by_name("nonexistent")
    
    def test_get_memory_map(self):
        """メモリマップ取得テスト"""
        self.mapper.map_device(self.device1, 0x0000, 0x7FFF, "RAM")
        self.mapper.map_device(self.device2, 0x8000, 0x8FFF, "ROM", read_only=True)
        
        memory_map = self.mapper.get_memory_map()
        assert len(memory_map) == 2
        
        # RAM マッピング確認
        ram_mapping = next(m for m in memory_map if m['name'] == 'RAM')
        assert ram_mapping['start_address'] == 0x0000
        assert ram_mapping['end_address'] == 0x7FFF
        assert ram_mapping['size'] == 0x8000
        assert ram_mapping['read_only'] is False
        
        # ROM マッピング確認
        rom_mapping = next(m for m in memory_map if m['name'] == 'ROM')
        assert rom_mapping['start_address'] == 0x8000
        assert rom_mapping['end_address'] == 0x8FFF
        assert rom_mapping['size'] == 0x1000
        assert rom_mapping['read_only'] is True
    
    def test_get_unmapped_ranges(self):
        """未マッピング領域取得テスト"""
        # 部分的なマッピング
        self.mapper.map_device(self.device1, 0x1000, 0x1FFF, "DEV1")
        self.mapper.map_device(self.device2, 0x8000, 0x8FFF, "DEV2")
        
        unmapped = self.mapper.get_unmapped_ranges()
        
        # 期待される未マッピング領域
        expected_ranges = [
            {'start_address': 0x0000, 'end_address': 0x0FFF, 'size': 0x1000},
            {'start_address': 0x2000, 'end_address': 0x7FFF, 'size': 0x6000},
            {'start_address': 0x9000, 'end_address': 0xFFFF, 'size': 0x7000}
        ]
        
        assert len(unmapped) == len(expected_ranges)
        for expected in expected_ranges:
            assert expected in unmapped
    
    def test_validate_mapping_integrity(self):
        """マッピング整合性チェックテスト"""
        # 正常なマッピング
        self.mapper.map_device(self.device1, 0x0000, 0x7FFF, "RAM")
        self.mapper.map_device(self.device2, 0x8000, 0x8FFF, "ROM")
        
        issues = self.mapper.validate_mapping_integrity()
        assert len(issues) == 0
        
        # 整合性を破壊（テスト用）
        # 実際の実装では内部状態を直接操作することは推奨されない
        
    def test_clear_all_mappings(self):
        """全マッピング削除テスト"""
        self.mapper.map_device(self.device1, 0x0000, 0x7FFF, "RAM")
        self.mapper.map_device(self.device2, 0x8000, 0x8FFF, "ROM")
        
        assert self.mapper.get_mapping_count() == 2
        
        self.mapper.clear_all_mappings()
        
        assert self.mapper.get_mapping_count() == 0
        assert self.mapper.get_total_mapped_size() == 0
        assert self.mapper.find_device(0x0000) is None
        assert self.mapper.find_device(0x8000) is None
    
    def test_mapping_with_device_offset(self):
        """デバイスオフセット付きマッピングテスト"""
        self.mapper.map_device(
            self.device1, 
            0x8000, 0x8FFF, 
            "ROM", 
            device_offset=0x1000
        )
        
        mapping = self.mapper.find_device(0x8000)
        assert mapping is not None
        assert mapping.device_offset == 0x1000
        assert mapping.get_device_address(0x8000) == 0x1000
        assert mapping.get_device_address(0x8001) == 0x1001
    
    def test_read_only_mapping(self):
        """読み取り専用マッピングテスト"""
        self.mapper.map_device(
            self.device1, 
            0x8000, 0x8FFF, 
            "ROM", 
            read_only=True
        )
        
        mapping = self.mapper.find_device(0x8000)
        assert mapping is not None
        assert mapping.read_only is True
    
    def test_binary_search_efficiency(self):
        """バイナリサーチ効率テスト"""
        # 多数のマッピングを作成
        devices = [MockDevice(f"device_{i}") for i in range(100)]
        
        for i, device in enumerate(devices):
            start = i * 0x100
            end = start + 0xFF
            if end <= 0xFFFF:  # アドレス空間内のみ
                self.mapper.map_device(device, start, end, f"dev_{i}")
        
        # 検索テスト（バイナリサーチの効率を確認）
        for i in range(0, min(100, 0x10000 // 0x100)):
            addr = i * 0x100
            mapping = self.mapper.find_device(addr)
            assert mapping is not None
            assert mapping.name == f"dev_{i}"
