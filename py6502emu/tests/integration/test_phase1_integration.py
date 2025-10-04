"""
Phase 1 統合テスト

Phase 1で実装された各プログラムユニット間の統合テストを実装します。
PU019 (DeviceProtocol)、PU020 (SystemBus)、PU022 (ConfigurationManager) の
連携動作を検証します。
"""

import pytest
import tempfile
import json
from pathlib import Path
from py6502emu.core.device import DeviceConfig
from py6502emu.core.config import ConfigurationManager, CPUConfig, MemoryConfig, SystemConfig
from py6502emu.memory.mmu import SystemBus
from tests.conftest import MockDevice


class TestPhase1Integration:
    """Phase 1 統合テスト"""
    
    @pytest.fixture
    def config_manager(self):
        return ConfigurationManager()
    
    @pytest.fixture
    def system_bus(self):
        return SystemBus()
    
    @pytest.fixture
    def complete_system_config(self):
        """完全なシステム設定"""
        return {
            "system": {
                "master_clock_hz": 1000000,
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
                },
                {
                    "type": "memory",
                    "device_id": "main_rom",
                    "name": "System ROM",
                    "size": 32768,
                    "start_address": 0x8000,
                    "end_address": 0xFFFF,
                    "readonly": True
                }
            ]
        }
    
    def test_complete_system_setup(self, config_manager, system_bus):
        """完全なシステムセットアップテスト"""
        # 設定管理
        cpu_config = CPUConfig(device_id="cpu", name="Main CPU")
        ram_config = MemoryConfig(device_id="ram", name="Main RAM", size=32768)
        rom_config = MemoryConfig(device_id="rom", name="Main ROM", size=32768, readonly=True)
        
        config_manager.add_device_config(cpu_config)
        config_manager.add_device_config(ram_config)
        config_manager.add_device_config(rom_config)
        
        # デバイス作成
        cpu_device = MockDevice(cpu_config)
        ram_device = MockDevice(ram_config)
        rom_device = MockDevice(rom_config)
        
        # システムバスにマッピング
        system_bus.map_device(ram_device, 0x0000, 0x7FFF, "RAM")
        system_bus.map_device(rom_device, 0x8000, 0xFFFF, "ROM")
        
        # システム動作確認
        system_bus.write(0x1000, 0x42)
        value = system_bus.read(0x1000)
        assert value == 0x42
        
        # メモリマップ確認
        memory_map = system_bus.get_memory_map()
        assert len(memory_map) == 2
        assert memory_map[0]['device'] == "RAM"
        assert memory_map[1]['device'] == "ROM"
        
        # 設定管理確認
        device_configs = config_manager.list_device_configs()
        assert len(device_configs) == 3
        
        # 設定検証
        errors = config_manager.validate_config()
        assert len(errors) == 0
    
    def test_configuration_driven_setup(self, config_manager, system_bus, complete_system_config):
        """設定駆動セットアップテスト"""
        # 設定読み込み
        config_manager.load_from_dict(complete_system_config)
        
        # 設定からデバイス作成
        devices = {}
        for config in config_manager.list_device_configs():
            devices[config.device_id] = MockDevice(config)
        
        # システムバスにマッピング
        ram_config = config_manager.get_device_config("main_ram")
        rom_config = config_manager.get_device_config("main_rom")
        
        if ram_config and "main_ram" in devices:
            system_bus.map_device(
                devices["main_ram"],
                ram_config.start_address,
                ram_config.end_address,
                ram_config.name
            )
        
        if rom_config and "main_rom" in devices:
            system_bus.map_device(
                devices["main_rom"],
                rom_config.start_address,
                rom_config.end_address,
                rom_config.name
            )
        
        # 動作確認
        assert len(devices) == 3
        memory_map = system_bus.get_memory_map()
        assert len(memory_map) == 2
        
        # システム設定確認
        system_config = config_manager.get_system_config()
        assert system_config.master_clock_hz == 1000000
        assert system_config.debug_enabled == True
    
    def test_device_protocol_bus_integration(self, system_bus):
        """デバイスプロトコルとバス統合テスト"""
        # 複数のデバイスタイプを作成
        cpu_config = CPUConfig(device_id="cpu1", name="CPU")
        ram_config = MemoryConfig(device_id="ram1", name="RAM")
        
        cpu_device = MockDevice(cpu_config)
        ram_device = MockDevice(ram_config)
        
        # バスにマッピング
        system_bus.map_device(ram_device, 0x0000, 0x7FFF, "System RAM")
        system_bus.map_device(cpu_device, 0x8000, 0x8FFF, "CPU Registers")
        
        # デバイスプロトコル機能テスト
        # 1. リセット機能
        ram_device.reset()
        cpu_device.reset()
        
        # 2. 状態管理
        ram_device.set_state({"initialized": True})
        cpu_device.set_state({"pc": 0x8000})
        
        assert ram_device.get_state()["initialized"] == True
        assert cpu_device.get_state()["pc"] == 0x8000
        
        # 3. バス経由アクセス
        system_bus.write(0x1000, 0xAA)  # RAM
        system_bus.write(0x8000, 0x55)  # CPU
        
        assert system_bus.read(0x1000) == 0xAA
        assert system_bus.read(0x8000) == 0x55
        
        # 4. tick機能
        ram_cycles = ram_device.tick(10)
        cpu_cycles = cpu_device.tick(10)
        assert ram_cycles == 10
        assert cpu_cycles == 10
    
    def test_config_file_system_integration(self, config_manager, system_bus, complete_system_config):
        """設定ファイルとシステム統合テスト"""
        # 設定ファイル作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(complete_system_config, f)
            config_file = Path(f.name)
        
        try:
            # ファイルから設定読み込み
            config_manager.load_from_file(config_file)
            
            # システム構築
            devices = {}
            for config in config_manager.list_device_configs():
                devices[config.device_id] = MockDevice(config)
            
            # メモリマッピング
            for device_id, device in devices.items():
                if device_id.startswith("main_"):
                    config = config_manager.get_device_config(device_id)
                    if isinstance(config, MemoryConfig):
                        system_bus.map_device(
                            device,
                            config.start_address,
                            config.end_address,
                            config.name
                        )
            
            # システム動作テスト
            system_bus.write(0x1000, 0x12)  # RAM
            system_bus.write(0x9000, 0x34)  # ROM
            
            assert system_bus.read(0x1000) == 0x12
            assert system_bus.read(0x9000) == 0x34
            
            # 設定保存テスト
            config_manager.save_to_file()
            
            # 保存された設定の再読み込み
            config_manager2 = ConfigurationManager()
            config_manager2.load_from_file(config_file)
            
            # 設定一致確認
            system1 = config_manager.get_system_config()
            system2 = config_manager2.get_system_config()
            assert system1.master_clock_hz == system2.master_clock_hz
            
        finally:
            config_file.unlink()
    
    def test_bus_mastership_device_integration(self, system_bus):
        """バスマスタシップとデバイス統合テスト"""
        # デバイス作成
        cpu_config = CPUConfig(device_id="cpu", name="CPU")
        dma_config = DeviceConfig(device_id="dma", name="DMA Controller")
        
        cpu_device = MockDevice(cpu_config)
        dma_device = MockDevice(dma_config)
        
        # メモリデバイス
        ram_config = MemoryConfig(device_id="ram", name="RAM")
        ram_device = MockDevice(ram_config)
        
        system_bus.map_device(ram_device, 0x0000, 0xFFFF, "System RAM")
        
        # CPU がマスタ権取得
        assert system_bus.request_mastership(cpu_device) == True
        assert system_bus.get_current_master() == cpu_device
        
        # CPU によるメモリアクセス
        system_bus.write(0x1000, 0xAA)
        assert system_bus.read(0x1000) == 0xAA
        
        # DMA がマスタ権要求（失敗）
        assert system_bus.request_mastership(dma_device) == False
        
        # CPU がマスタ権解放
        system_bus.release_mastership(cpu_device)
        assert system_bus.get_current_master() is None
        
        # DMA がマスタ権取得
        assert system_bus.request_mastership(dma_device) == True
        assert system_bus.get_current_master() == dma_device
        
        # DMA によるメモリアクセス
        system_bus.write(0x2000, 0x55)
        assert system_bus.read(0x2000) == 0x55
    
    def test_debug_mode_integration(self, config_manager, system_bus):
        """デバッグモード統合テスト"""
        # デバッグ有効なシステム設定
        system_config = SystemConfig(debug_enabled=True)
        config_manager.set_system_config(system_config)
        
        # デバッグ有効なバス
        system_bus.enable_debug(True)
        
        # デバイス作成とマッピング
        ram_config = MemoryConfig(device_id="ram", name="Debug RAM")
        ram_device = MockDevice(ram_config)
        system_bus.map_device(ram_device, 0x0000, 0x7FFF, "Debug RAM")
        
        # アクセス実行
        system_bus.write(0x1000, 0x42)
        system_bus.read(0x1000)
        system_bus.read(0x8000)  # 未マップ領域
        
        # ログ確認
        access_log = system_bus.get_access_log()
        assert len(access_log) == 3
        
        # 書き込みログ
        write_log = access_log[0]
        assert write_log['operation'] == 'WRITE'
        assert write_log['address'] == 0x1000
        assert write_log['value'] == 0x42
        assert write_log['device'] == 'Debug RAM'
        
        # 読み取りログ
        read_log = access_log[1]
        assert read_log['operation'] == 'READ'
        assert read_log['device'] == 'Debug RAM'
        
        # オープンバスログ
        open_bus_log = access_log[2]
        assert open_bus_log['operation'] == 'READ'
        assert open_bus_log['device'] == 'OPEN_BUS'
        assert open_bus_log['value'] == 0xFF
        
        # デバッグ情報確認
        debug_info = system_bus.get_debug_info()
        assert debug_info['debug_enabled'] == True
        assert debug_info['access_log_size'] == 3
    
    def test_error_handling_integration(self, config_manager, system_bus):
        """エラーハンドリング統合テスト"""
        # 無効な設定でのエラー
        invalid_config = {
            "system": {"master_clock_hz": -1000},
            "devices": [
                {
                    "type": "cpu",
                    "device_id": "cpu1",
                    "clock_divider": 0  # 無効
                },
                {
                    "type": "memory",
                    "device_id": "mem1",
                    "size": -100,  # 無効
                    "start_address": 0x8000,
                    "end_address": 0x7FFF  # 無効範囲
                }
            ]
        }
        
        config_manager.load_from_dict(invalid_config)
        
        # 設定検証でエラー検出
        errors = config_manager.validate_config()
        assert len(errors) >= 3  # 複数のエラーが検出される
        
        # バスでの無効操作
        ram_device = MockDevice(MemoryConfig(device_id="ram"))
        system_bus.map_device(ram_device, 0x0000, 0x7FFF)
        
        # 重複マッピングエラー
        with pytest.raises(ValueError, match="Address range overlap"):
            system_bus.map_device(ram_device, 0x4000, 0x8FFF)
        
        # 無効アドレスアクセスエラー
        from py6502emu.core.device import InvalidAddressError, InvalidValueError
        
        with pytest.raises(InvalidAddressError):
            system_bus.read(-1)
        
        with pytest.raises(InvalidValueError):
            system_bus.write(0x1000, 256)
    
    def test_performance_integration(self, system_bus):
        """性能統合テスト"""
        import time
        
        # 大きなメモリ空間のセットアップ
        devices = []
        for i in range(16):  # 16個のデバイス
            config = MemoryConfig(device_id=f"mem_{i}", name=f"Memory {i}")
            device = MockDevice(config)
            devices.append(device)
            
            start_addr = i * 0x1000
            end_addr = start_addr + 0x0FFF
            system_bus.map_device(device, start_addr, end_addr, f"Memory {i}")
        
        # 大量アクセステスト
        start_time = time.time()
        
        for i in range(1000):
            addr = (i * 16) % 0x10000
            system_bus.write(addr, i % 256)
            value = system_bus.read(addr)
            assert value == (i % 256)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # 性能目標: 1000回のアクセスが1秒以内
        assert elapsed < 1.0, f"Performance test failed: {elapsed:.3f}s"
        
        # メモリマップ確認
        memory_map = system_bus.get_memory_map()
        assert len(memory_map) == 16
    
    def test_state_management_integration(self, config_manager, system_bus):
        """状態管理統合テスト"""
        # システム設定
        system_config = SystemConfig(master_clock_hz=2000000)
        config_manager.set_system_config(system_config)
        
        # デバイス作成
        cpu_config = CPUConfig(device_id="cpu", reset_vector=0x8000)
        ram_config = MemoryConfig(device_id="ram", size=32768)
        
        config_manager.add_device_config(cpu_config)
        config_manager.add_device_config(ram_config)
        
        cpu_device = MockDevice(cpu_config)
        ram_device = MockDevice(ram_config)
        
        system_bus.map_device(ram_device, 0x0000, 0x7FFF)
        
        # 初期状態設定
        cpu_device.set_state({"pc": 0x8000, "a": 0x42})
        ram_device.set_state({"initialized": True})
        
        # メモリ初期化
        for addr in range(0x1000, 0x1010):
            system_bus.write(addr, addr & 0xFF)
        
        # 状態確認
        cpu_state = cpu_device.get_state()
        ram_state = ram_device.get_state()
        
        assert cpu_state["pc"] == 0x8000
        assert cpu_state["a"] == 0x42
        assert ram_state["initialized"] == True
        
        # メモリ内容確認
        for addr in range(0x1000, 0x1010):
            assert system_bus.read(addr) == (addr & 0xFF)
        
        # システム全体のリセット
        cpu_device.reset()
        ram_device.reset()
        
        # リセット後確認
        cpu_state_after = cpu_device.get_state()
        ram_state_after = ram_device.get_state()
        
        assert cpu_state_after["test"] == 0  # MockDeviceのリセット状態
        assert ram_state_after["test"] == 0
        
        # メモリもクリアされる
        assert system_bus.read(0x1000) == 0x00
