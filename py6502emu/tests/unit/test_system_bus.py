"""
SystemBus テスト

PU020: SystemBus の単体テストを実装します。
"""

import pytest
from py6502emu.memory.mmu import SystemBus, DeviceMapping
from py6502emu.core.device import DeviceConfig, InvalidAddressError, InvalidValueError
from tests.conftest import MockDevice


class TestDeviceMapping:
    """DeviceMapping テストクラス"""
    
    @pytest.fixture
    def device_mapping(self, mock_device):
        return DeviceMapping(
            device=mock_device,
            start_address=0x1000,
            end_address=0x1FFF,
            name="Test Mapping"
        )
    
    def test_device_mapping_creation(self, device_mapping, mock_device):
        """DeviceMapping作成テスト"""
        assert device_mapping.device == mock_device
        assert device_mapping.start_address == 0x1000
        assert device_mapping.end_address == 0x1FFF
        assert device_mapping.name == "Test Mapping"
    
    def test_device_mapping_contains(self, device_mapping):
        """アドレス範囲チェックテスト"""
        # 範囲内アドレス
        assert device_mapping.contains(0x1000) == True
        assert device_mapping.contains(0x1500) == True
        assert device_mapping.contains(0x1FFF) == True
        
        # 範囲外アドレス
        assert device_mapping.contains(0x0FFF) == False
        assert device_mapping.contains(0x2000) == False
        assert device_mapping.contains(0x0000) == False
        assert device_mapping.contains(0xFFFF) == False
    
    def test_device_mapping_translate_address(self, device_mapping):
        """アドレス変換テスト"""
        assert device_mapping.translate_address(0x1000) == 0x0000
        assert device_mapping.translate_address(0x1001) == 0x0001
        assert device_mapping.translate_address(0x1500) == 0x0500
        assert device_mapping.translate_address(0x1FFF) == 0x0FFF
    
    def test_device_mapping_size(self, device_mapping):
        """マッピングサイズテスト"""
        assert device_mapping.size == 0x1000  # 4KB


class TestSystemBus:
    """SystemBus テストクラス"""
    
    @pytest.fixture
    def system_bus(self):
        return SystemBus()
    
    @pytest.fixture
    def debug_system_bus(self):
        return SystemBus(debug_enabled=True)
    
    @pytest.fixture
    def device1(self):
        config = DeviceConfig("dev1", "Device 1")
        return MockDevice(config)
    
    @pytest.fixture
    def device2(self):
        config = DeviceConfig("dev2", "Device 2")
        return MockDevice(config)
    
    def test_system_bus_creation(self, system_bus):
        """SystemBus作成テスト"""
        assert system_bus is not None
        assert system_bus.get_current_master() is None
        assert len(system_bus.get_memory_map()) == 0
    
    def test_device_mapping_success(self, system_bus, device1, device2):
        """デバイスマッピング成功テスト"""
        # 正常マッピング
        system_bus.map_device(device1, 0x0000, 0x7FFF, "RAM")
        system_bus.map_device(device2, 0x8000, 0xFFFF, "ROM")
        
        memory_map = system_bus.get_memory_map()
        assert len(memory_map) == 2
        assert memory_map[0]['device'] == "RAM"
        assert memory_map[0]['start'] == "$0000"
        assert memory_map[0]['end'] == "$7FFF"
        assert memory_map[1]['device'] == "ROM"
        assert memory_map[1]['start'] == "$8000"
        assert memory_map[1]['end'] == "$FFFF"
    
    def test_device_mapping_with_default_name(self, system_bus, device1):
        """デフォルト名でのデバイスマッピングテスト"""
        system_bus.map_device(device1, 0x0000, 0x7FFF)
        
        memory_map = system_bus.get_memory_map()
        assert len(memory_map) == 1
        assert memory_map[0]['device'] == "Device 1"  # デバイス名が使用される
    
    def test_device_mapping_invalid_range(self, system_bus, device1):
        """無効アドレス範囲マッピングテスト"""
        # 無効な範囲
        with pytest.raises(ValueError, match="Invalid address range"):
            system_bus.map_device(device1, 0x8000, 0x7FFF)  # start > end
        
        with pytest.raises(ValueError, match="Invalid address range"):
            system_bus.map_device(device1, -1, 0x7FFF)  # 負の開始アドレス
        
        with pytest.raises(ValueError, match="Invalid address range"):
            system_bus.map_device(device1, 0x0000, 0x10000)  # 範囲外終了アドレス
    
    def test_device_mapping_overlap_detection(self, system_bus, device1, device2):
        """アドレス重複検出テスト"""
        system_bus.map_device(device1, 0x0000, 0x7FFF)
        
        # 重複するマッピングでエラー
        with pytest.raises(ValueError, match="Address range overlap"):
            system_bus.map_device(device2, 0x4000, 0x8FFF)
        
        with pytest.raises(ValueError, match="Address range overlap"):
            system_bus.map_device(device2, 0x0000, 0x0FFF)  # 開始アドレス重複
        
        with pytest.raises(ValueError, match="Address range overlap"):
            system_bus.map_device(device2, 0x7000, 0x7FFF)  # 終了アドレス重複
    
    def test_device_mapping_adjacent_ranges(self, system_bus, device1, device2):
        """隣接アドレス範囲マッピングテスト"""
        # 隣接する範囲は重複とみなされない
        system_bus.map_device(device1, 0x0000, 0x7FFF)
        system_bus.map_device(device2, 0x8000, 0xFFFF)  # 隣接範囲
        
        memory_map = system_bus.get_memory_map()
        assert len(memory_map) == 2
    
    def test_device_unmapping(self, system_bus, device1, device2):
        """デバイスマッピング解除テスト"""
        system_bus.map_device(device1, 0x0000, 0x7FFF)
        system_bus.map_device(device2, 0x8000, 0xFFFF)
        
        assert len(system_bus.get_memory_map()) == 2
        
        # 1つ目のマッピング解除
        system_bus.unmap_device(0x0000, 0x7FFF)
        memory_map = system_bus.get_memory_map()
        assert len(memory_map) == 1
        assert memory_map[0]['start'] == "$8000"
    
    def test_bus_read_mapped_device(self, system_bus, device1):
        """マップされたデバイスからの読み取りテスト"""
        system_bus.map_device(device1, 0x1000, 0x1FFF)
        
        # デバイスにデータを書き込み
        device1.write(0x0100, 0x42)  # デバイス内相対アドレス
        
        # バス経由で読み取り
        value = system_bus.read(0x1100)  # システムバスアドレス
        assert value == 0x42
    
    def test_bus_write_mapped_device(self, system_bus, device1):
        """マップされたデバイスへの書き込みテスト"""
        system_bus.map_device(device1, 0x1000, 0x1FFF)
        
        # バス経由で書き込み
        system_bus.write(0x1100, 0x42)
        
        # デバイスから直接読み取り
        value = device1.read(0x0100)  # デバイス内相対アドレス
        assert value == 0x42
    
    def test_bus_read_unmapped_address(self, system_bus):
        """未マップアドレスからの読み取りテスト（オープンバス）"""
        value = system_bus.read(0x8000)
        assert value == 0xFF  # オープンバスは0xFFを返す
    
    def test_bus_write_unmapped_address(self, system_bus):
        """未マップアドレスへの書き込みテスト（無視）"""
        # 例外が発生しないことを確認
        system_bus.write(0x8000, 0x42)
    
    def test_bus_invalid_address_read(self, system_bus):
        """無効アドレス読み取りテスト"""
        with pytest.raises(InvalidAddressError):
            system_bus.read(-1)
        
        with pytest.raises(InvalidAddressError):
            system_bus.read(0x10000)
    
    def test_bus_invalid_address_write(self, system_bus):
        """無効アドレス書き込みテスト"""
        with pytest.raises(InvalidAddressError):
            system_bus.write(-1, 0x00)
        
        with pytest.raises(InvalidAddressError):
            system_bus.write(0x10000, 0x00)
    
    def test_bus_invalid_value_write(self, system_bus):
        """無効値書き込みテスト"""
        with pytest.raises(InvalidValueError):
            system_bus.write(0x1000, -1)
        
        with pytest.raises(InvalidValueError):
            system_bus.write(0x1000, 256)
    
    def test_bus_mastership_request(self, system_bus, device1, device2):
        """バスマスタ権要求テスト"""
        # 最初のマスタ権取得
        assert system_bus.request_mastership(device1) == True
        assert system_bus.get_current_master() == device1
        
        # 既にマスタがいる場合は失敗
        assert system_bus.request_mastership(device2) == False
        assert system_bus.get_current_master() == device1
    
    def test_bus_mastership_release(self, system_bus, device1, device2):
        """バスマスタ権解放テスト"""
        system_bus.request_mastership(device1)
        assert system_bus.get_current_master() == device1
        
        # マスタ権解放
        system_bus.release_mastership(device1)
        assert system_bus.get_current_master() is None
        
        # 別のデバイスがマスタ権取得可能
        assert system_bus.request_mastership(device2) == True
        assert system_bus.get_current_master() == device2
    
    def test_bus_mastership_wrong_device_release(self, system_bus, device1, device2):
        """間違ったデバイスによるマスタ権解放テスト"""
        system_bus.request_mastership(device1)
        
        # 別のデバイスが解放を試みても無効
        system_bus.release_mastership(device2)
        assert system_bus.get_current_master() == device1
    
    def test_debug_mode_enable_disable(self, system_bus):
        """デバッグモード有効/無効テスト"""
        # 初期状態は無効
        debug_info = system_bus.get_debug_info()
        assert debug_info['debug_enabled'] == False
        
        # デバッグモード有効化
        system_bus.enable_debug(True)
        debug_info = system_bus.get_debug_info()
        assert debug_info['debug_enabled'] == True
        
        # デバッグモード無効化
        system_bus.enable_debug(False)
        debug_info = system_bus.get_debug_info()
        assert debug_info['debug_enabled'] == False
    
    def test_access_log_functionality(self, debug_system_bus, device1):
        """アクセスログ機能テスト"""
        debug_system_bus.map_device(device1, 0x1000, 0x1FFF)
        
        # 初期ログは空
        assert len(debug_system_bus.get_access_log()) == 0
        
        # 読み書き実行
        debug_system_bus.write(0x1100, 0x42)
        debug_system_bus.read(0x1100)
        
        # ログ確認
        log = debug_system_bus.get_access_log()
        assert len(log) == 2
        
        write_log = log[0]
        assert write_log['operation'] == 'WRITE'
        assert write_log['address'] == 0x1100
        assert write_log['value'] == 0x42
        assert write_log['device'] == 'Device 1'
        
        read_log = log[1]
        assert read_log['operation'] == 'READ'
        assert read_log['address'] == 0x1100
        assert read_log['value'] == 0x42
        assert read_log['device'] == 'Device 1'
    
    def test_access_log_unmapped_addresses(self, debug_system_bus):
        """未マップアドレスのアクセスログテスト"""
        debug_system_bus.read(0x8000)
        debug_system_bus.write(0x8000, 0x42)
        
        log = debug_system_bus.get_access_log()
        assert len(log) == 2
        
        read_log = log[0]
        assert read_log['operation'] == 'READ'
        assert read_log['device'] == 'OPEN_BUS'
        assert read_log['value'] == 0xFF
        
        write_log = log[1]
        assert write_log['operation'] == 'WRITE'
        assert write_log['device'] == 'IGNORED'
    
    def test_access_log_clear(self, debug_system_bus, device1):
        """アクセスログクリアテスト"""
        debug_system_bus.map_device(device1, 0x1000, 0x1FFF)
        debug_system_bus.read(0x1000)
        
        assert len(debug_system_bus.get_access_log()) == 1
        
        debug_system_bus.clear_access_log()
        assert len(debug_system_bus.get_access_log()) == 0
    
    def test_memory_map_information(self, system_bus, device1, device2):
        """メモリマップ情報テスト"""
        system_bus.map_device(device1, 0x0000, 0x3FFF, "Lower RAM")
        system_bus.map_device(device2, 0x8000, 0xFFFF, "Upper ROM")
        
        memory_map = system_bus.get_memory_map()
        assert len(memory_map) == 2
        
        # ソート順確認（アドレス順）
        assert memory_map[0]['start'] == "$0000"
        assert memory_map[0]['end'] == "$3FFF"
        assert memory_map[0]['size'] == 0x4000
        assert memory_map[0]['device'] == "Lower RAM"
        
        assert memory_map[1]['start'] == "$8000"
        assert memory_map[1]['end'] == "$FFFF"
        assert memory_map[1]['size'] == 0x8000
        assert memory_map[1]['device'] == "Upper ROM"
    
    def test_debug_info_comprehensive(self, system_bus, device1, device2):
        """包括的デバッグ情報テスト"""
        system_bus.map_device(device1, 0x0000, 0x7FFF)
        system_bus.request_mastership(device1)
        system_bus.enable_debug(True)
        
        debug_info = system_bus.get_debug_info()
        
        assert debug_info['mappings_count'] == 1
        assert debug_info['bus_masters'] == ['Device 1']
        assert debug_info['current_master'] == 'Device 1'
        assert debug_info['debug_enabled'] == True
        assert debug_info['access_log_size'] == 0
