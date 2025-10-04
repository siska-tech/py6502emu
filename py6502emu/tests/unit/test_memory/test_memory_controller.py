"""
MemoryController テスト

統合メモリアクセス制御、デバイスルーティング、
アクセス権限チェックのテストを提供します。
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from py6502emu.memory.memory_controller import (
    MemoryController, 
    AccessType, 
    AccessLog, 
    MemoryAccessError
)
from py6502emu.memory.address_space import AddressSpace
from py6502emu.memory.device_mapper import DeviceMapper
from py6502emu.core.device import InvalidAddressError, InvalidValueError


class MockDevice:
    """テスト用モックデバイス"""
    
    def __init__(self, name: str = "mock_device"):
        self.name = name
        self._memory = bytearray(0x1000)  # 4KB
        self.read_calls = []
        self.write_calls = []
    
    def reset(self) -> None:
        pass
    
    def tick(self, master_cycles: int) -> int:
        return 0
    
    def read(self, address: int) -> int:
        self.read_calls.append(address)
        if address >= len(self._memory):
            raise InvalidAddressError(address)
        return self._memory[address]
    
    def write(self, address: int, value: int) -> None:
        self.write_calls.append((address, value))
        if address >= len(self._memory):
            raise InvalidAddressError(address)
        if not (0 <= value <= 255):
            raise InvalidValueError(value)
        self._memory[address] = value
    
    def get_state(self) -> dict:
        return {}
    
    def set_state(self, state: dict) -> None:
        pass


class TestMemoryController:
    """MemoryController クラステスト"""
    
    def setup_method(self):
        """各テストメソッド前の初期化"""
        self.address_space = AddressSpace()
        self.device_mapper = DeviceMapper()
        self.controller = MemoryController(self.address_space, self.device_mapper)
        
        self.mock_device = MockDevice("test_device")
    
    def test_initialization(self):
        """初期化テスト"""
        assert self.controller._address_space == self.address_space
        assert self.controller._device_mapper == self.device_mapper
        assert not self.controller._access_logging_enabled
        assert len(self.controller._access_log) == 0
    
    def test_read_from_address_space(self):
        """アドレス空間からの読み取りテスト"""
        # アドレス空間に直接書き込み
        self.address_space.write_byte(0x1000, 0x42)
        
        # コントローラ経由で読み取り
        value = self.controller.read(0x1000)
        assert value == 0x42
    
    def test_write_to_address_space(self):
        """アドレス空間への書き込みテスト"""
        # コントローラ経由で書き込み
        self.controller.write(0x1000, 0x42)
        
        # アドレス空間から直接読み取り
        value = self.address_space.read_byte(0x1000)
        assert value == 0x42
    
    def test_read_from_mapped_device(self):
        """マップされたデバイスからの読み取りテスト"""
        # デバイスマッピング
        self.device_mapper.map_device(self.mock_device, 0x8000, 0x8FFF, "ROM")
        
        # デバイスにテストデータ設定
        self.mock_device._memory[0x100] = 0x55
        
        # コントローラ経由で読み取り（システムアドレス0x8100 -> デバイスアドレス0x100）
        value = self.controller.read(0x8100)
        assert value == 0x55
        assert 0x100 in self.mock_device.read_calls
    
    def test_write_to_mapped_device(self):
        """マップされたデバイスへの書き込みテスト"""
        # デバイスマッピング
        self.device_mapper.map_device(self.mock_device, 0x8000, 0x8FFF, "RAM")
        
        # コントローラ経由で書き込み
        self.controller.write(0x8100, 0x55)
        
        # デバイスの状態確認
        assert (0x100, 0x55) in self.mock_device.write_calls
        assert self.mock_device._memory[0x100] == 0x55
    
    def test_write_to_read_only_device(self):
        """読み取り専用デバイスへの書き込みテスト"""
        # 読み取り専用デバイスマッピング
        self.device_mapper.map_device(
            self.mock_device, 0x8000, 0x8FFF, "ROM", read_only=True
        )
        
        # 書き込み試行（MemoryAccessErrorでラップされる）
        with pytest.raises(MemoryAccessError, match="Write error at"):
            self.controller.write(0x8000, 0x42)
    
    def test_read_word_little_endian(self):
        """16ビット読み取り（リトルエンディアン）テスト"""
        # テストデータ設定
        self.controller.write(0x1000, 0x34)  # Low byte
        self.controller.write(0x1001, 0x12)  # High byte
        
        # 16ビット読み取り
        value = self.controller.read_word(0x1000)
        assert value == 0x1234
    
    def test_write_word_little_endian(self):
        """16ビット書き込み（リトルエンディアン）テスト"""
        # 16ビット書き込み
        self.controller.write_word(0x1000, 0x1234)
        
        # バイト単位で確認
        assert self.controller.read(0x1000) == 0x34  # Low byte
        assert self.controller.read(0x1001) == 0x12  # High byte
    
    def test_word_access_invalid_address(self):
        """16ビットアクセス無効アドレステスト"""
        with pytest.raises(InvalidAddressError):
            self.controller.read_word(0xFFFF)
        
        with pytest.raises(InvalidAddressError):
            self.controller.write_word(0xFFFF, 0x1234)
    
    def test_invalid_address_access(self):
        """無効アドレスアクセステスト"""
        with pytest.raises(InvalidAddressError):
            self.controller.read(-1)
        
        with pytest.raises(InvalidAddressError):
            self.controller.read(0x10000)
        
        with pytest.raises(InvalidAddressError):
            self.controller.write(-1, 0x00)
        
        with pytest.raises(InvalidAddressError):
            self.controller.write(0x10000, 0x00)
    
    def test_invalid_value_write(self):
        """無効値書き込みテスト"""
        with pytest.raises(InvalidValueError):
            self.controller.write(0x1000, -1)
        
        with pytest.raises(InvalidValueError):
            self.controller.write(0x1000, 0x100)
    
    def test_bulk_read(self):
        """バルク読み取りテスト"""
        # テストデータ準備
        test_data = [0xAA, 0x55, 0xCC, 0x33]
        for i, value in enumerate(test_data):
            self.controller.write(0x1000 + i, value)
        
        # バルク読み取り
        data = self.controller.bulk_read(0x1000, len(test_data))
        assert data == bytes(test_data)
    
    def test_bulk_write(self):
        """バルク書き込みテスト"""
        test_data = bytes([0xAA, 0x55, 0xCC, 0x33])
        
        # バルク書き込み
        self.controller.bulk_write(0x1000, test_data)
        
        # 確認
        for i, expected in enumerate(test_data):
            assert self.controller.read(0x1000 + i) == expected
    
    def test_bulk_operations_invalid_parameters(self):
        """バルク操作無効パラメータテスト"""
        # 無効サイズ
        with pytest.raises(ValueError, match="Size must be positive"):
            self.controller.bulk_read(0x1000, 0)
        
        # アドレス空間超過
        with pytest.raises(ValueError, match="exceeds address space"):
            self.controller.bulk_read(0xFFFF, 2)
        
        with pytest.raises(ValueError, match="exceeds address space"):
            self.controller.bulk_write(0xFFFF, bytes([0x00, 0x01]))
    
    def test_access_logging(self):
        """アクセスログテスト"""
        # ログ有効化
        self.controller.enable_access_logging(True)
        
        # アクセス実行
        self.controller.write(0x1000, 0x42)
        self.controller.read(0x1000)
        
        # ログ確認
        log = self.controller.get_access_log()
        assert len(log) == 2
        
        write_log = log[0]
        assert write_log.access_type == AccessType.WRITE
        assert write_log.address == 0x1000
        assert write_log.value == 0x42
        assert write_log.device_name is None
        
        read_log = log[1]
        assert read_log.access_type == AccessType.READ
        assert read_log.address == 0x1000
        assert read_log.value == 0x42
        assert read_log.device_name is None
    
    def test_access_logging_with_device(self):
        """デバイスアクセスログテスト"""
        # デバイスマッピング
        self.device_mapper.map_device(self.mock_device, 0x8000, 0x8FFF, "ROM")
        
        # ログ有効化
        self.controller.enable_access_logging(True)
        
        # デバイスアクセス
        self.controller.write(0x8000, 0x55)
        
        # ログ確認
        log = self.controller.get_access_log()
        assert len(log) == 1
        assert log[0].device_name == "ROM"
    
    def test_access_logging_disable(self):
        """アクセスログ無効化テスト"""
        self.controller.enable_access_logging(True)
        self.controller.write(0x1000, 0x42)
        assert len(self.controller.get_access_log()) == 1
        
        # ログ無効化
        self.controller.enable_access_logging(False)
        assert len(self.controller.get_access_log()) == 0
        
        # 新しいアクセス
        self.controller.read(0x1000)
        assert len(self.controller.get_access_log()) == 0
    
    def test_access_hooks(self):
        """アクセスフックテスト"""
        read_hook_calls = []
        write_hook_calls = []
        
        def read_hook(address, value):
            read_hook_calls.append((address, value))
        
        def write_hook(address, value):
            write_hook_calls.append((address, value))
        
        # フック追加
        self.controller.add_read_hook(read_hook)
        self.controller.add_write_hook(write_hook)
        
        # アクセス実行
        self.controller.write(0x1000, 0x42)
        self.controller.read(0x1000)
        
        # フック呼び出し確認
        assert write_hook_calls == [(0x1000, 0x42)]
        assert read_hook_calls == [(0x1000, 0x42)]
        
        # フック削除
        self.controller.remove_read_hook(read_hook)
        self.controller.remove_write_hook(write_hook)
        
        # 新しいアクセス
        self.controller.write(0x2000, 0x55)
        self.controller.read(0x2000)
        
        # フック呼び出しされないことを確認
        assert len(write_hook_calls) == 1
        assert len(read_hook_calls) == 1
    
    def test_access_statistics(self):
        """アクセス統計テスト"""
        # デバイスマッピング
        self.device_mapper.map_device(self.mock_device, 0x8000, 0x8FFF, "ROM")
        
        # アクセス実行
        self.controller.read(0x1000)  # アドレス空間
        self.controller.write(0x1000, 0x42)  # アドレス空間
        self.controller.read(0x8000)  # デバイス
        self.controller.write(0x8000, 0x55)  # デバイス
        
        # 統計確認
        stats = self.controller.get_access_statistics()
        assert stats['total_reads'] == 2
        assert stats['total_writes'] == 2
        assert 'ROM' in stats['device_access_count']
        assert stats['device_access_count']['ROM']['read'] == 1
        assert stats['device_access_count']['ROM']['write'] == 1
    
    def test_memory_map_info(self):
        """メモリマップ情報テスト"""
        # デバイスマッピング
        self.device_mapper.map_device(self.mock_device, 0x8000, 0x8FFF, "ROM")
        
        # メモリマップ情報取得
        info = self.controller.get_memory_map_info()
        
        assert 'device_mappings' in info
        assert 'unmapped_ranges' in info
        assert 'total_mapped_size' in info
        assert 'mapping_count' in info
        
        assert info['mapping_count'] == 1
        assert info['total_mapped_size'] == 0x1000
    
    def test_system_integrity_validation(self):
        """システム整合性チェックテスト"""
        # 正常なマッピング
        self.device_mapper.map_device(self.mock_device, 0x8000, 0x8FFF, "ROM")
        
        issues = self.controller.validate_system_integrity()
        assert len(issues) == 0
    
    def test_device_mapping_cache(self):
        """デバイスマッピングキャッシュテスト"""
        # デバイスマッピング
        self.device_mapper.map_device(self.mock_device, 0x8000, 0x8FFF, "ROM")
        
        # 同じ範囲内での連続アクセス（キャッシュ効果確認）
        self.controller.read(0x8000)
        self.controller.read(0x8001)
        self.controller.read(0x8002)
        
        # キャッシュが正しく動作していることを間接的に確認
        # （実装の詳細に依存するため、主に性能テスト）
        assert len(self.mock_device.read_calls) == 3
    
    def test_error_handling(self):
        """エラーハンドリングテスト"""
        # デバイスエラーのラップ
        error_device = Mock()
        error_device.name = "error_device"
        error_device.read.side_effect = Exception("Device error")
        
        self.device_mapper.map_device(error_device, 0x8000, 0x8FFF, "ERROR")
        
        with pytest.raises(MemoryAccessError, match="Read error at"):
            self.controller.read(0x8000)
    
    def test_statistics_reset(self):
        """統計リセットテスト"""
        # アクセス実行
        self.controller.read(0x1000)
        self.controller.write(0x1000, 0x42)
        
        # ログ有効化してアクセス
        self.controller.enable_access_logging(True)
        self.controller.read(0x2000)
        
        # 統計確認
        stats = self.controller.get_access_statistics()
        assert stats['total_reads'] > 0
        assert stats['total_writes'] > 0
        assert len(self.controller.get_access_log()) > 0
        
        # リセット
        self.controller.reset_statistics()
        
        # リセット後確認
        stats = self.controller.get_access_statistics()
        assert stats['total_reads'] == 0
        assert stats['total_writes'] == 0
        assert len(self.controller.get_access_log()) == 0
    
    def test_access_log_limit(self):
        """アクセスログ制限テスト"""
        self.controller.enable_access_logging(True)
        
        # ログ制限を小さく設定（テスト用）
        original_limit = self.controller._max_log_entries
        self.controller._max_log_entries = 5
        
        try:
            # 制限を超えるアクセス
            for i in range(10):
                self.controller.write(0x1000 + i, i)
            
            # ログ数が制限内であることを確認
            log = self.controller.get_access_log()
            assert len(log) == 5
            
            # 最新のエントリが保持されていることを確認
            assert log[-1].value == 9
            
        finally:
            self.controller._max_log_entries = original_limit
