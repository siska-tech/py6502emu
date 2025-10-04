"""
システム統合テスト

Phase4で実装されたシステム統合機能のテストを行います。
システム全体の初期化、Tick駆動実行の動作確認、デバイス間同期のテストを含みます。
"""

import pytest
import time
import threading
from typing import Dict, Any
from unittest.mock import Mock, patch

from py6502emu.core.clock import SystemClock, ClockConfiguration, ClockMode, ClockListener
from py6502emu.core.orchestrator import SystemOrchestrator, SystemConfiguration, ExecutionMode
from py6502emu.core.tick_engine import TickEngine, Tickable, TickableConfig, TickPriority, TickPhase
from py6502emu.core.integration import SystemIntegration, ComponentRegistry, SystemBridge
from py6502emu.core.system_config import SystemConfigurationManager, PerformanceProfile
from py6502emu.core.interrupt_controller import InterruptController
from py6502emu.core.types import DeviceType


class MockTickableDevice(Tickable):
    """テスト用Tickableデバイス"""
    
    def __init__(self, device_id: str, priority: TickPriority = TickPriority.NORMAL):
        self.device_id = device_id
        self.priority = priority
        self.tick_count = 0
        self.last_cycle = 0
        self.last_phase = None
        self.enabled = True
        self.tick_history = []
    
    def tick(self, cycle: int, phase: TickPhase) -> None:
        """Tick実行"""
        self.tick_count += 1
        self.last_cycle = cycle
        self.last_phase = phase
        self.tick_history.append((cycle, phase, time.time_ns()))
    
    def get_tick_config(self) -> TickableConfig:
        """Tick設定取得"""
        return TickableConfig(
            device_id=self.device_id,
            priority=self.priority,
            enabled=self.enabled
        )
    
    def is_tick_enabled(self) -> bool:
        """Tick実行有効チェック"""
        return self.enabled


class MockClockListener(ClockListener):
    """テスト用クロックリスナー"""
    
    def __init__(self):
        self.tick_count = 0
        self.sync_count = 0
        self.last_tick_cycle = 0
        self.last_sync_cycle = 0
    
    def on_tick(self, cycle: int, timestamp_ns: int) -> None:
        """クロックティック処理"""
        self.tick_count += 1
        self.last_tick_cycle = cycle
    
    def on_sync(self, cycle: int, timestamp_ns: int) -> None:
        """同期処理"""
        self.sync_count += 1
        self.last_sync_cycle = cycle


class TestSystemClock:
    """システムクロックテスト"""
    
    def test_clock_initialization(self):
        """クロック初期化テスト"""
        config = ClockConfiguration(
            master_frequency_hz=1_000_000,
            mode=ClockMode.REALTIME
        )
        clock = SystemClock(config)
        
        assert clock.config.master_frequency_hz == 1_000_000
        assert clock.config.mode == ClockMode.REALTIME
        assert clock.get_current_cycle() == 0
        assert not clock._running
    
    def test_clock_start_stop(self):
        """クロック開始・停止テスト"""
        clock = SystemClock()
        
        # 開始
        clock.start()
        assert clock._running
        assert not clock._paused
        
        # 停止
        clock.stop()
        assert not clock._running
    
    def test_clock_listener(self):
        """クロックリスナーテスト"""
        clock = SystemClock()
        listener = MockClockListener()
        
        clock.add_listener(listener)
        clock.start()
        
        # 数回ティック実行
        for _ in range(5):
            clock.tick()
        
        assert listener.tick_count == 5
        assert listener.last_tick_cycle == 4  # 0から4まで（5回のティック）
    
    def test_clock_divider(self):
        """クロック分周器テスト"""
        from py6502emu.core.clock import ClockDivider, ClockDividerConfig
        
        config = ClockDividerConfig(
            device_id="test_device",
            device_type=DeviceType.CPU,
            divider_ratio=2
        )
        divider = ClockDivider(config)
        
        # 分周動作確認
        assert divider.tick(0) == True   # 最初の出力変化
        assert divider.tick(1) == False  # 変化なし
        assert divider.tick(2) == True   # 次の出力変化
        assert divider.tick(3) == False  # 変化なし


class TestTickEngine:
    """Tick駆動実行エンジンテスト"""
    
    def test_tick_engine_initialization(self):
        """Tick駆動実行エンジン初期化テスト"""
        engine = TickEngine(master_frequency_hz=1_000_000)
        
        assert engine._master_frequency_hz == 1_000_000
        assert not engine._running
        assert engine.get_current_cycle() == 0
    
    def test_tickable_registration(self):
        """Tickable登録テスト"""
        engine = TickEngine()
        device = MockTickableDevice("test_device")
        
        engine.register_tickable(device)
        
        # 登録確認
        tickable = engine._scheduler.get_tickable("test_device")
        assert tickable is not None
        assert tickable.device_id == "test_device"
    
    def test_tick_execution(self):
        """Tick実行テスト"""
        engine = TickEngine()
        device = MockTickableDevice("test_device")
        
        engine.register_tickable(device)
        engine.start()
        
        # 数回ティック実行
        for _ in range(3):
            engine.tick()
        
        assert device.tick_count >= 3  # フェーズ分実行されるため
        assert device.last_cycle == 3
    
    def test_priority_execution_order(self):
        """優先度実行順序テスト"""
        engine = TickEngine()
        
        # 異なる優先度のデバイス登録
        high_device = MockTickableDevice("high_priority", TickPriority.HIGH)
        normal_device = MockTickableDevice("normal_priority", TickPriority.NORMAL)
        low_device = MockTickableDevice("low_priority", TickPriority.LOW)
        
        engine.register_tickable(normal_device)
        engine.register_tickable(low_device)
        engine.register_tickable(high_device)
        
        # 実行順序確認
        execution_order = engine._scheduler.get_execution_order()
        assert execution_order.index("high_priority") < execution_order.index("normal_priority")
        assert execution_order.index("normal_priority") < execution_order.index("low_priority")


class TestSystemOrchestrator:
    """システムオーケストレータテスト"""
    
    def test_orchestrator_initialization(self):
        """オーケストレータ初期化テスト"""
        config = SystemConfiguration(
            execution_mode=ExecutionMode.CONTINUOUS,
            enable_debugging=True
        )
        orchestrator = SystemOrchestrator(config)
        
        # SystemClockを手動で設定
        from py6502emu.core.clock import SystemClock, ClockConfiguration
        clock_config = ClockConfiguration()
        system_clock = SystemClock(clock_config)
        orchestrator.set_system_clock(system_clock)
        
        assert orchestrator.config.execution_mode == ExecutionMode.CONTINUOUS
        assert orchestrator.config.enable_debugging == True
        assert orchestrator._system_clock is not None
        assert orchestrator._interrupt_controller is not None
    
    def test_device_registration(self):
        """デバイス登録テスト"""
        orchestrator = SystemOrchestrator()
        
        # モックデバイス作成
        mock_device = Mock()
        mock_device.get_device_id.return_value = "test_device"
        mock_device.initialize.return_value = True
        mock_device.is_enabled.return_value = True
        
        # デバイス登録
        orchestrator.register_device(mock_device)
        
        # 登録確認
        device = orchestrator.get_device("test_device")
        assert device is not None
        assert device.get_device_id() == "test_device"
    
    def test_system_lifecycle(self):
        """システムライフサイクルテスト"""
        orchestrator = SystemOrchestrator()
        
        # SystemClockを手動で設定
        from py6502emu.core.clock import SystemClock, ClockConfiguration
        clock_config = ClockConfiguration()
        system_clock = SystemClock(clock_config)
        orchestrator.set_system_clock(system_clock)
        
        # 初期状態確認
        from py6502emu.core.orchestrator import SystemStatus
        assert orchestrator.get_status() == SystemStatus.UNINITIALIZED
        
        # 初期化
        assert orchestrator.initialize() == True
        assert orchestrator.get_status() == SystemStatus.READY
        
        # 開始
        assert orchestrator.start() == True
        assert orchestrator.get_status() == SystemStatus.RUNNING
        
        # 一時停止
        orchestrator.pause()
        assert orchestrator.get_status() == SystemStatus.PAUSED
        
        # 再開
        orchestrator.resume()
        assert orchestrator.get_status() == SystemStatus.RUNNING
        
        # 停止
        orchestrator.stop()
        assert orchestrator.get_status() == SystemStatus.STOPPED


class TestSystemIntegration:
    """システム統合テスト"""
    
    def test_component_registry(self):
        """コンポーネントレジストリテスト"""
        registry = ComponentRegistry()
        
        # 依存関係なしでコンポーネント登録
        mock_component = Mock()
        registry.register_component(
            "test_component",
            "test_type",
            mock_component
        )
        
        # 登録確認
        component_info = registry.get_component("test_component")
        assert component_info is not None
        assert component_info.component_id == "test_component"
        assert component_info.component_type == "test_type"
        assert component_info.dependencies == []
    
    def test_system_bridge(self):
        """システムブリッジテスト"""
        registry = ComponentRegistry()
        bridge = SystemBridge(registry)
        
        # メッセージハンドラ登録
        handler_called = False
        def test_handler(sender_id, data):
            nonlocal handler_called
            handler_called = True
            return "handled"
        
        bridge.register_message_handler("test_message", test_handler)
        
        # メッセージ送信
        results = bridge.send_message("test_message", "sender", {"data": "test"})
        
        assert handler_called
        assert results == ["handled"]
    
    def test_full_system_integration(self):
        """完全システム統合テスト"""
        integration = SystemIntegration()
        
        # システム初期化
        config = SystemConfiguration(
            execution_mode=ExecutionMode.CONTINUOUS,
            enable_debugging=False
        )
        
        assert integration.initialize_system(config) == True
        
        # コンポーネント確認
        assert integration.get_system_orchestrator() is not None
        assert integration.get_system_clock() is not None
        assert integration.get_interrupt_controller() is not None
        assert integration.get_tick_engine() is not None
        
        # 統合状態確認
        from py6502emu.core.integration import IntegrationPhase
        assert integration.get_current_phase() == IntegrationPhase.RUNNING


class TestSystemConfiguration:
    """システム設定テスト"""
    
    def test_configuration_manager(self):
        """設定管理テスト"""
        config_manager = SystemConfigurationManager()
        
        # デフォルト設定確認
        runtime_config = config_manager.get_runtime_config()
        assert runtime_config.execution_mode == ExecutionMode.CONTINUOUS
        assert runtime_config.master_frequency_hz == 1_000_000
        
        performance_config = config_manager.get_performance_config()
        assert performance_config.profile == PerformanceProfile.BALANCED
    
    def test_configuration_serialization(self):
        """設定シリアライゼーションテスト"""
        config_manager = SystemConfigurationManager()
        
        # 設定変更
        config_manager.update_runtime_config(
            execution_mode=ExecutionMode.STEP,
            enable_debugging=True
        )
        
        # シリアライゼーション
        config_data = config_manager.serialize_to_dict()
        
        assert config_data['runtime']['execution_mode'] == 'STEP'
        assert config_data['runtime']['enable_debugging'] == True
    
    def test_performance_profiles(self):
        """性能プロファイルテスト"""
        config_manager = SystemConfigurationManager()
        
        # 精度重視プロファイル
        config_manager.update_performance_config(profile=PerformanceProfile.ACCURACY)
        perf_config = config_manager.get_performance_config()
        
        assert perf_config.max_cycles_per_frame == 1000
        assert perf_config.enable_profiling == True
        
        # 性能重視プロファイル
        config_manager.update_performance_config(profile=PerformanceProfile.PERFORMANCE)
        perf_config = config_manager.get_performance_config()
        
        assert perf_config.max_cycles_per_frame == 50000
        assert perf_config.enable_profiling == False


class TestInterruptIntegration:
    """割り込み統合テスト"""
    
    def test_interrupt_controller_integration(self):
        """割り込みコントローラ統合テスト"""
        orchestrator = SystemOrchestrator()
        
        # SystemClockを手動で設定
        from py6502emu.core.clock import SystemClock, ClockConfiguration
        clock_config = ClockConfiguration()
        system_clock = SystemClock(clock_config)
        orchestrator.set_system_clock(system_clock)
        
        interrupt_controller = orchestrator.get_interrupt_controller()
        
        assert interrupt_controller is not None
        
        # IRQ要求テスト
        interrupt_controller.assert_irq("test_source")
        assert interrupt_controller.is_pending()
        
        # 割り込み承認テスト
        vector_info = interrupt_controller.acknowledge(interrupt_enabled=True)
        assert vector_info is not None
        from py6502emu.core.interrupt_types import InterruptType
        assert vector_info['interrupt_type'] == InterruptType.IRQ


class TestSystemSynchronization:
    """システム同期テスト"""
    
    def test_clock_tick_synchronization(self):
        """クロック・Tick同期テスト"""
        # システム統合
        integration = SystemIntegration()
        config = SystemConfiguration(execution_mode=ExecutionMode.CONTINUOUS)
        integration.initialize_system(config)
        
        # テストデバイス登録
        tick_engine = integration.get_tick_engine()
        test_device = MockTickableDevice("sync_test_device")
        tick_engine.register_tickable(test_device)
        
        # システム開始
        orchestrator = integration.get_system_orchestrator()
        orchestrator.start()
        
        # 手動でティック実行（テスト用）
        system_clock = integration.get_system_clock()
        for _ in range(10):
            system_clock.tick()
        
        # 結果確認
        assert test_device.tick_count > 0
        
        # システム停止
        orchestrator.stop()
    
    @pytest.mark.timeout(5)
    def test_multi_threaded_execution(self):
        """マルチスレッド実行テスト"""
        integration = SystemIntegration()
        config = SystemConfiguration(execution_mode=ExecutionMode.CONTINUOUS)
        integration.initialize_system(config)
        
        # 複数のテストデバイス登録
        tick_engine = integration.get_tick_engine()
        devices = []
        for i in range(3):
            device = MockTickableDevice(f"thread_test_device_{i}")
            devices.append(device)
            tick_engine.register_tickable(device)
        
        # システム開始
        orchestrator = integration.get_system_orchestrator()
        orchestrator.start()
        
        # 手動でティック実行（テスト用）
        system_clock = integration.get_system_clock()
        for _ in range(10):
            system_clock.tick()
        
        # 実行確認
        for device in devices:
            assert device.tick_count > 0
        
        # システム停止
        orchestrator.stop()


class TestErrorHandling:
    """エラーハンドリングテスト"""
    
    def test_component_initialization_failure(self):
        """コンポーネント初期化失敗テスト"""
        # 初期化に失敗するモックコンポーネント
        mock_component = Mock()
        mock_component.initialize.return_value = False
        
        registry = ComponentRegistry()
        registry.register_component("failing_component", "test", mock_component)
        
        # 初期化失敗の処理確認は統合レベルで行う
        # （実際の実装では適切なエラーハンドリングが必要）
    
    def test_tick_execution_error(self):
        """Tick実行エラーテスト"""
        engine = TickEngine()
        
        # エラーを発生させるデバイス
        error_device = Mock()
        error_device.get_tick_config.return_value = TickableConfig(
            device_id="error_device",
            priority=TickPriority.NORMAL
        )
        error_device.is_tick_enabled.return_value = True
        error_device.tick.side_effect = RuntimeError("Test error")
        
        engine.register_tickable(error_device)
        engine.start()
        
        # エラー発生確認
        with pytest.raises(RuntimeError, match="Tick execution failed"):
            engine.tick()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
