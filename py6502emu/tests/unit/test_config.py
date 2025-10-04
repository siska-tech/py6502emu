"""
ConfigurationManager テスト

PU022: ConfigurationManager の単体テストを実装します。
"""

import pytest
import json
import tempfile
from pathlib import Path
from py6502emu.core.config import (
    ConfigurationManager, SystemConfig, CPUConfig, MemoryConfig,
    ConfigurationError
)


class TestSystemConfig:
    """SystemConfig テストクラス"""
    
    def test_system_config_default_values(self):
        """SystemConfigデフォルト値テスト"""
        config = SystemConfig()
        assert config.master_clock_hz == 1_000_000
        assert config.debug_enabled == False
        assert config.log_level == "INFO"
        assert config.devices == []
    
    def test_system_config_custom_values(self):
        """SystemConfigカスタム値テスト"""
        config = SystemConfig(
            master_clock_hz=2_000_000,
            debug_enabled=True,
            log_level="DEBUG"
        )
        assert config.master_clock_hz == 2_000_000
        assert config.debug_enabled == True
        assert config.log_level == "DEBUG"


class TestCPUConfig:
    """CPUConfig テストクラス"""
    
    def test_cpu_config_default_values(self):
        """CPUConfigデフォルト値テスト"""
        config = CPUConfig(device_id="cpu1")
        assert config.device_id == "cpu1"
        assert config.name == "cpu1"
        assert config.clock_divider == 1
        assert config.reset_vector == 0xFFFC
        assert config.irq_vector == 0xFFFE
        assert config.nmi_vector == 0xFFFA
    
    def test_cpu_config_custom_values(self):
        """CPUConfigカスタム値テスト"""
        config = CPUConfig(
            device_id="main_cpu",
            name="Main CPU",
            clock_divider=2,
            reset_vector=0x8000,
            irq_vector=0x8002,
            nmi_vector=0x8004
        )
        assert config.device_id == "main_cpu"
        assert config.name == "Main CPU"
        assert config.clock_divider == 2
        assert config.reset_vector == 0x8000
        assert config.irq_vector == 0x8002
        assert config.nmi_vector == 0x8004


class TestMemoryConfig:
    """MemoryConfig テストクラス"""
    
    def test_memory_config_default_values(self):
        """MemoryConfigデフォルト値テスト"""
        config = MemoryConfig(device_id="ram1")
        assert config.device_id == "ram1"
        assert config.name == "ram1"
        assert config.size == 65536
        assert config.start_address == 0x0000
        assert config.end_address == 0xFFFF
        assert config.readonly == False
    
    def test_memory_config_custom_values(self):
        """MemoryConfigカスタム値テスト"""
        config = MemoryConfig(
            device_id="main_ram",
            name="Main RAM",
            size=32768,
            start_address=0x0000,
            end_address=0x7FFF,
            readonly=True
        )
        assert config.device_id == "main_ram"
        assert config.name == "Main RAM"
        assert config.size == 32768
        assert config.start_address == 0x0000
        assert config.end_address == 0x7FFF
        assert config.readonly == True


class TestConfigurationManager:
    """ConfigurationManager テストクラス"""
    
    @pytest.fixture
    def config_manager(self):
        return ConfigurationManager()
    
    def test_configuration_manager_creation(self, config_manager):
        """ConfigurationManager作成テスト"""
        assert config_manager is not None
        
        # デフォルトシステム設定確認
        system_config = config_manager.get_system_config()
        assert system_config.master_clock_hz == 1_000_000
        assert system_config.debug_enabled == False
        
        # デバイス設定は空
        assert len(config_manager.list_device_configs()) == 0
    
    def test_system_config_management(self, config_manager):
        """システム設定管理テスト"""
        # カスタム設定作成
        new_config = SystemConfig(
            master_clock_hz=2_000_000,
            debug_enabled=True,
            log_level="DEBUG"
        )
        
        # 設定変更
        config_manager.set_system_config(new_config)
        
        # 設定確認
        retrieved_config = config_manager.get_system_config()
        assert retrieved_config.master_clock_hz == 2_000_000
        assert retrieved_config.debug_enabled == True
        assert retrieved_config.log_level == "DEBUG"
    
    def test_device_config_add_get(self, config_manager):
        """デバイス設定追加・取得テスト"""
        # CPU設定追加
        cpu_config = CPUConfig(
            device_id="main_cpu",
            name="Main CPU",
            clock_divider=2
        )
        config_manager.add_device_config(cpu_config)
        
        # 設定取得確認
        retrieved_config = config_manager.get_device_config("main_cpu")
        assert retrieved_config is not None
        assert isinstance(retrieved_config, CPUConfig)
        assert retrieved_config.device_id == "main_cpu"
        assert retrieved_config.name == "Main CPU"
        assert retrieved_config.clock_divider == 2
        
        # 存在しない設定
        assert config_manager.get_device_config("nonexistent") is None
    
    def test_device_config_remove(self, config_manager):
        """デバイス設定削除テスト"""
        # 設定追加
        cpu_config = CPUConfig(device_id="test_cpu")
        config_manager.add_device_config(cpu_config)
        assert config_manager.get_device_config("test_cpu") is not None
        
        # 設定削除
        config_manager.remove_device_config("test_cpu")
        assert config_manager.get_device_config("test_cpu") is None
        
        # 存在しない設定の削除（エラーにならない）
        config_manager.remove_device_config("nonexistent")
    
    def test_device_config_list(self, config_manager):
        """デバイス設定一覧テスト"""
        # 初期状態は空
        assert len(config_manager.list_device_configs()) == 0
        
        # 複数設定追加
        cpu_config = CPUConfig(device_id="cpu1")
        ram_config = MemoryConfig(device_id="ram1")
        
        config_manager.add_device_config(cpu_config)
        config_manager.add_device_config(ram_config)
        
        # 一覧確認
        configs = config_manager.list_device_configs()
        assert len(configs) == 2
        
        device_ids = [config.device_id for config in configs]
        assert "cpu1" in device_ids
        assert "ram1" in device_ids
    
    def test_load_from_dict_basic(self, config_manager, sample_config_data):
        """辞書からの基本設定読み込みテスト"""
        config_manager.load_from_dict(sample_config_data)
        
        # システム設定確認
        system_config = config_manager.get_system_config()
        assert system_config.master_clock_hz == 1500000
        assert system_config.debug_enabled == True
        assert system_config.log_level == "DEBUG"
        
        # デバイス設定確認
        configs = config_manager.list_device_configs()
        assert len(configs) == 2
        
        cpu_config = config_manager.get_device_config("main_cpu")
        assert isinstance(cpu_config, CPUConfig)
        assert cpu_config.name == "W65C02S CPU"
        assert cpu_config.reset_vector == 0x8000
        
        ram_config = config_manager.get_device_config("main_ram")
        assert isinstance(ram_config, MemoryConfig)
        assert ram_config.name == "System RAM"
        assert ram_config.size == 32768
    
    def test_load_from_dict_empty_system(self, config_manager):
        """空のシステム設定読み込みテスト"""
        config_data = {"devices": []}
        config_manager.load_from_dict(config_data)
        
        # デフォルト値が使用される
        system_config = config_manager.get_system_config()
        assert system_config.master_clock_hz == 1_000_000
        assert system_config.debug_enabled == False
    
    def test_load_from_dict_generic_device(self, config_manager):
        """汎用デバイス設定読み込みテスト"""
        config_data = {
            "devices": [
                {
                    "type": "io",
                    "device_id": "uart1",
                    "name": "UART Controller"
                }
            ]
        }
        config_manager.load_from_dict(config_data)
        
        device_config = config_manager.get_device_config("uart1")
        assert device_config is not None
        assert device_config.device_id == "uart1"
        assert device_config.name == "UART Controller"
    
    def test_serialize_config_basic(self, config_manager):
        """基本設定シリアライズテスト"""
        # 設定作成
        system_config = SystemConfig(
            master_clock_hz=1500000,
            debug_enabled=True,
            log_level="DEBUG"
        )
        config_manager.set_system_config(system_config)
        
        cpu_config = CPUConfig(device_id="cpu1", name="Main CPU")
        ram_config = MemoryConfig(device_id="ram1", name="Main RAM", size=32768)
        
        config_manager.add_device_config(cpu_config)
        config_manager.add_device_config(ram_config)
        
        # シリアライズ
        serialized = config_manager._serialize_config()
        
        # システム設定確認
        assert serialized['system']['master_clock_hz'] == 1500000
        assert serialized['system']['debug_enabled'] == True
        assert serialized['system']['log_level'] == "DEBUG"
        
        # デバイス設定確認
        assert len(serialized['devices']) == 2
        
        cpu_data = next(d for d in serialized['devices'] if d['device_id'] == 'cpu1')
        assert cpu_data['type'] == 'cpu'
        assert cpu_data['name'] == 'Main CPU'
        
        ram_data = next(d for d in serialized['devices'] if d['device_id'] == 'ram1')
        assert ram_data['type'] == 'memory'
        assert ram_data['size'] == 32768
    
    def test_file_operations_success(self, config_manager, sample_config_data):
        """ファイル操作成功テスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_config_data, f)
            config_file = Path(f.name)
        
        try:
            # ファイル読み込み
            config_manager.load_from_file(config_file)
            
            # 設定確認
            system_config = config_manager.get_system_config()
            assert system_config.master_clock_hz == 1500000
            
            # ファイル保存
            config_manager.save_to_file()
            
            # 保存されたファイル確認
            assert config_file.exists()
            
        finally:
            config_file.unlink()  # クリーンアップ
    
    def test_file_load_not_found(self, config_manager):
        """存在しないファイル読み込みテスト"""
        nonexistent_file = Path("nonexistent_config.json")
        
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            config_manager.load_from_file(nonexistent_file)
    
    def test_file_load_invalid_json(self, config_manager):
        """無効JSONファイル読み込みテスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            config_file = Path(f.name)
        
        try:
            with pytest.raises(ConfigurationError, match="Invalid JSON"):
                config_manager.load_from_file(config_file)
        finally:
            config_file.unlink()
    
    def test_save_without_file_path(self, config_manager):
        """ファイルパス未指定保存テスト"""
        with pytest.raises(ConfigurationError, match="No configuration file specified"):
            config_manager.save_to_file()
    
    def test_config_validation_success(self, config_manager):
        """設定検証成功テスト"""
        # 有効な設定
        system_config = SystemConfig(master_clock_hz=1_000_000)
        config_manager.set_system_config(system_config)
        
        cpu_config = CPUConfig(device_id="cpu1", clock_divider=1)
        ram_config = MemoryConfig(
            device_id="ram1",
            size=32768,
            start_address=0x0000,
            end_address=0x7FFF
        )
        
        config_manager.add_device_config(cpu_config)
        config_manager.add_device_config(ram_config)
        
        # 検証実行
        errors = config_manager.validate_config()
        assert len(errors) == 0
    
    def test_config_validation_system_errors(self, config_manager):
        """システム設定検証エラーテスト"""
        # 無効なシステム設定
        invalid_system = SystemConfig(master_clock_hz=-1000)
        config_manager.set_system_config(invalid_system)
        
        errors = config_manager.validate_config()
        assert len(errors) > 0
        assert any("Master clock frequency must be positive" in error for error in errors)
    
    def test_config_validation_duplicate_device_ids(self, config_manager):
        """重複デバイスID検証テスト"""
        # 重複するデバイスID
        config1 = CPUConfig(device_id="duplicate")
        config2 = MemoryConfig(device_id="duplicate", size=1024)
        
        config_manager.add_device_config(config1)
        config_manager.add_device_config(config2)  # 上書きされる
        
        # 実際には上書きされるので重複エラーは発生しない
        # 代わりに手動で重複状態を作成
        config_manager._device_configs["duplicate2"] = CPUConfig(device_id="duplicate")
        
        errors = config_manager.validate_config()
        assert any("Duplicate device ID" in error for error in errors)
    
    def test_config_validation_cpu_errors(self, config_manager):
        """CPU設定検証エラーテスト"""
        # 無効なCPU設定
        invalid_cpu = CPUConfig(device_id="cpu1", clock_divider=0)
        config_manager.add_device_config(invalid_cpu)
        
        errors = config_manager.validate_config()
        assert any("CPU clock divider must be positive" in error for error in errors)
    
    def test_config_validation_memory_errors(self, config_manager):
        """メモリ設定検証エラーテスト"""
        # 無効なメモリサイズ
        invalid_memory1 = MemoryConfig(device_id="ram1", size=0)
        config_manager.add_device_config(invalid_memory1)
        
        # 無効なアドレス範囲
        invalid_memory2 = MemoryConfig(
            device_id="ram2",
            size=1024,
            start_address=0x8000,
            end_address=0x7FFF  # start > end
        )
        config_manager.add_device_config(invalid_memory2)
        
        errors = config_manager.validate_config()
        assert any("Memory size must be positive" in error for error in errors)
        assert any("Invalid memory range" in error for error in errors)
    
    def test_load_from_dict_error_handling(self, config_manager):
        """辞書読み込みエラーハンドリングテスト"""
        # 必須フィールド不足
        invalid_config = {
            "devices": [
                {
                    "type": "cpu"
                    # device_id が不足
                }
            ]
        }
        
        with pytest.raises(ConfigurationError):
            config_manager.load_from_dict(invalid_config)
    
    def test_roundtrip_config_consistency(self, config_manager, sample_config_data):
        """設定の往復変換一貫性テスト"""
        # 元データ読み込み
        config_manager.load_from_dict(sample_config_data)
        
        # シリアライズして再読み込み
        serialized = config_manager._serialize_config()
        config_manager2 = ConfigurationManager()
        config_manager2.load_from_dict(serialized)
        
        # 設定が一致することを確認
        system1 = config_manager.get_system_config()
        system2 = config_manager2.get_system_config()
        
        assert system1.master_clock_hz == system2.master_clock_hz
        assert system1.debug_enabled == system2.debug_enabled
        assert system1.log_level == system2.log_level
        
        configs1 = config_manager.list_device_configs()
        configs2 = config_manager2.list_device_configs()
        assert len(configs1) == len(configs2)
