"""
Device プロトコルテスト

PU019: DeviceProtocol の単体テストを実装します。
"""

import pytest
from typing import Dict, Any
from py6502emu.core.device import (
    Device, CPUDevice, VideoDevice, AudioDevice,
    DeviceConfig, DeviceError, InvalidAddressError, InvalidValueError
)
from tests.conftest import MockDevice


class TestDeviceConfig:
    """DeviceConfig テストクラス"""
    
    def test_device_config_creation_with_name(self):
        """名前付きDeviceConfig作成テスト"""
        config = DeviceConfig(device_id="test", name="Test Device")
        assert config.device_id == "test"
        assert config.name == "Test Device"
    
    def test_device_config_creation_without_name(self):
        """名前なしDeviceConfig作成テスト（自動設定）"""
        config = DeviceConfig(device_id="test_device")
        assert config.device_id == "test_device"
        assert config.name == "test_device"
    
    def test_device_config_empty_name_auto_fill(self):
        """空の名前の自動補完テスト"""
        config = DeviceConfig(device_id="auto_name", name="")
        assert config.device_id == "auto_name"
        assert config.name == "auto_name"


class TestDeviceProtocol:
    """Device プロトコルテスト"""
    
    def test_device_protocol_compliance(self, mock_device):
        """Deviceプロトコル準拠テスト"""
        # プロトコル準拠チェック
        assert isinstance(mock_device, Device)
        
        # 基本プロパティテスト
        assert mock_device.name == "Test Device"
    
    def test_device_reset(self, mock_device):
        """デバイスリセットテスト"""
        # 初期状態設定
        mock_device.write(0x1000, 0x42)
        mock_device.set_state({'test': 99})
        
        # リセット実行
        mock_device.reset()
        
        # リセット後確認
        assert mock_device.read(0x1000) == 0x00
        assert mock_device.get_state()['test'] == 0
    
    def test_device_tick(self, mock_device):
        """時間進行処理テスト"""
        cycles = mock_device.tick(10)
        assert cycles == 10
        
        cycles = mock_device.tick(0)
        assert cycles == 0
    
    def test_device_read_write(self, mock_device):
        """読み書き操作テスト"""
        # 書き込み・読み取りテスト
        mock_device.write(0x1000, 0x42)
        value = mock_device.read(0x1000)
        assert value == 0x42
        
        # 複数アドレステスト
        test_data = [(0x0000, 0x00), (0x7FFF, 0xFF), (0x8000, 0xAA), (0xFFFF, 0x55)]
        for addr, val in test_data:
            mock_device.write(addr, val)
            assert mock_device.read(addr) == val
    
    def test_device_state_management(self, mock_device):
        """状態管理テスト"""
        # 初期状態確認
        initial_state = mock_device.get_state()
        assert 'test' in initial_state
        assert initial_state['test'] == 0
        
        # 状態変更
        new_state = {'test': 42, 'custom': 'value'}
        mock_device.set_state(new_state)
        
        # 状態確認
        retrieved_state = mock_device.get_state()
        assert retrieved_state['test'] == 42
        assert retrieved_state['custom'] == 'value'
    
    def test_invalid_address_error_read(self, mock_device):
        """無効アドレス読み取りエラーテスト"""
        invalid_addresses = [-1, 0x10000, 0x20000, -100]
        
        for addr in invalid_addresses:
            with pytest.raises(InvalidAddressError) as exc_info:
                mock_device.read(addr)
            assert exc_info.value.address == addr
    
    def test_invalid_address_error_write(self, mock_device):
        """無効アドレス書き込みエラーテスト"""
        invalid_addresses = [-1, 0x10000, 0x20000, -100]
        
        for addr in invalid_addresses:
            with pytest.raises(InvalidAddressError) as exc_info:
                mock_device.write(addr, 0x00)
            assert exc_info.value.address == addr
    
    def test_invalid_value_error(self, mock_device):
        """無効値エラーテスト"""
        invalid_values = [-1, 256, 512, -100]
        
        for val in invalid_values:
            with pytest.raises(InvalidValueError) as exc_info:
                mock_device.write(0x1000, val)
            assert exc_info.value.value == val
    
    def test_valid_address_range(self, mock_device):
        """有効アドレス範囲テスト"""
        valid_addresses = [0x0000, 0x0001, 0x7FFF, 0x8000, 0xFFFE, 0xFFFF]
        
        for addr in valid_addresses:
            # 例外が発生しないことを確認
            mock_device.write(addr, 0x00)
            value = mock_device.read(addr)
            assert value == 0x00
    
    def test_valid_value_range(self, mock_device):
        """有効値範囲テスト"""
        valid_values = [0x00, 0x01, 0x7F, 0x80, 0xFE, 0xFF]
        
        for val in valid_values:
            # 例外が発生しないことを確認
            mock_device.write(0x1000, val)
            read_val = mock_device.read(0x1000)
            assert read_val == val


class TestDeviceExceptions:
    """デバイス例外テスト"""
    
    def test_device_error_inheritance(self):
        """DeviceError継承テスト"""
        error = DeviceError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"
    
    def test_invalid_address_error_message(self):
        """InvalidAddressError メッセージテスト"""
        error = InvalidAddressError(0x1234)
        assert error.address == 0x1234
        assert "Invalid address: $1234" in str(error)
        
        error = InvalidAddressError(0xABCD)
        assert error.address == 0xABCD
        assert "Invalid address: $ABCD" in str(error)
    
    def test_invalid_value_error_message(self):
        """InvalidValueError メッセージテスト"""
        error = InvalidValueError(256)
        assert error.value == 256
        assert "Invalid value: 256" in str(error)
        
        error = InvalidValueError(-1)
        assert error.value == -1
        assert "Invalid value: -1" in str(error)


class MockCPUDevice(MockDevice):
    """テスト用CPU モックデバイス"""
    
    def __init__(self, config: DeviceConfig):
        super().__init__(config)
        self._registers = {'A': 0, 'X': 0, 'Y': 0, 'PC': 0x8000, 'SP': 0xFF, 'P': 0x20}
        self._interrupt_enabled = True
    
    def step(self) -> int:
        # 簡単な命令実行シミュレーション
        self._registers['PC'] += 1
        return 2  # 2サイクル
    
    def get_registers(self) -> Dict[str, int]:
        return self._registers.copy()
    
    def set_pc(self, address: int) -> None:
        if not (0 <= address <= 0xFFFF):
            raise InvalidAddressError(address)
        self._registers['PC'] = address
    
    def is_interrupt_enabled(self) -> bool:
        return self._interrupt_enabled


class TestCPUDeviceProtocol:
    """CPUDevice プロトコルテスト"""
    
    @pytest.fixture
    def cpu_device(self, mock_device_config):
        return MockCPUDevice(mock_device_config)
    
    def test_cpu_device_protocol_compliance(self, cpu_device):
        """CPUDeviceプロトコル準拠テスト"""
        assert isinstance(cpu_device, Device)
        assert isinstance(cpu_device, CPUDevice)
    
    def test_cpu_step_execution(self, cpu_device):
        """CPU命令実行テスト"""
        initial_pc = cpu_device.get_registers()['PC']
        cycles = cpu_device.step()
        
        assert cycles == 2
        assert cpu_device.get_registers()['PC'] == initial_pc + 1
    
    def test_cpu_register_access(self, cpu_device):
        """CPUレジスタアクセステスト"""
        registers = cpu_device.get_registers()
        
        # 基本レジスタの存在確認
        expected_registers = ['A', 'X', 'Y', 'PC', 'SP', 'P']
        for reg in expected_registers:
            assert reg in registers
        
        # 初期値確認
        assert registers['PC'] == 0x8000
        assert registers['SP'] == 0xFF
    
    def test_cpu_pc_setting(self, cpu_device):
        """PC設定テスト"""
        cpu_device.set_pc(0x1234)
        assert cpu_device.get_registers()['PC'] == 0x1234
        
        cpu_device.set_pc(0xFFFF)
        assert cpu_device.get_registers()['PC'] == 0xFFFF
        
        cpu_device.set_pc(0x0000)
        assert cpu_device.get_registers()['PC'] == 0x0000
    
    def test_cpu_pc_invalid_address(self, cpu_device):
        """PC無効アドレステスト"""
        with pytest.raises(InvalidAddressError):
            cpu_device.set_pc(-1)
        
        with pytest.raises(InvalidAddressError):
            cpu_device.set_pc(0x10000)
    
    def test_cpu_interrupt_status(self, cpu_device):
        """割り込み状態テスト"""
        assert cpu_device.is_interrupt_enabled() == True


class MockVideoDevice(MockDevice):
    """テスト用ビデオ モックデバイス"""
    
    def __init__(self, config: DeviceConfig):
        super().__init__(config)
        self._framebuffer = bytes(320 * 240)  # 320x240 モノクロ
    
    def get_framebuffer(self) -> bytes:
        return self._framebuffer


class TestVideoDeviceProtocol:
    """VideoDevice プロトコルテスト"""
    
    @pytest.fixture
    def video_device(self, mock_device_config):
        return MockVideoDevice(mock_device_config)
    
    def test_video_device_protocol_compliance(self, video_device):
        """VideoDeviceプロトコル準拠テスト"""
        assert isinstance(video_device, Device)
        assert isinstance(video_device, VideoDevice)
    
    def test_video_framebuffer_access(self, video_device):
        """フレームバッファアクセステスト"""
        framebuffer = video_device.get_framebuffer()
        assert isinstance(framebuffer, bytes)
        assert len(framebuffer) == 320 * 240


class MockAudioDevice(MockDevice):
    """テスト用オーディオ モックデバイス"""
    
    def __init__(self, config: DeviceConfig):
        super().__init__(config)
        self._sample_rate = 44100
    
    def get_audio_buffer(self, samples: int) -> bytes:
        # 無音データを返す
        return bytes(samples * 2)  # 16-bit samples


class TestAudioDeviceProtocol:
    """AudioDevice プロトコルテスト"""
    
    @pytest.fixture
    def audio_device(self, mock_device_config):
        return MockAudioDevice(mock_device_config)
    
    def test_audio_device_protocol_compliance(self, audio_device):
        """AudioDeviceプロトコル準拠テスト"""
        assert isinstance(audio_device, Device)
        assert isinstance(audio_device, AudioDevice)
    
    def test_audio_buffer_access(self, audio_device):
        """オーディオバッファアクセステスト"""
        buffer = audio_device.get_audio_buffer(1024)
        assert isinstance(buffer, bytes)
        assert len(buffer) == 1024 * 2
        
        buffer = audio_device.get_audio_buffer(512)
        assert len(buffer) == 512 * 2
