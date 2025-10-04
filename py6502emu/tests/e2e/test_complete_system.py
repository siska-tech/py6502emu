"""
エンドツーエンドテスト

Phase4で実装されたシステム統合機能の完全なエンドツーエンドテストを行います。
完全なエミュレーション動作、実際のプログラム実行、システム全体の動作確認を含みます。
"""

import pytest
import time
import threading
from typing import Dict, List, Any
from unittest.mock import Mock

from py6502emu.core.integration import SystemIntegration
from py6502emu.core.orchestrator import SystemConfiguration, ExecutionMode
from py6502emu.core.system_config import SystemConfigurationManager, PerformanceProfile
from py6502emu.core.clock import ClockMode
from py6502emu.core.scheduler import DeviceScheduler, SchedulingConfig
from py6502emu.cpu.interrupt_handler import InterruptHandler
from py6502emu.core.interrupt_controller import InterruptController
from py6502emu.core.interrupt_types import InterruptType
from py6502emu.core.types import DeviceType


class MockCPU:
    """テスト用CPUモック"""
    
    def __init__(self):
        self.pc = 0x0000
        self.status = 0x20
        self.stack_pointer = 0xFF
        self.interrupt_disable_flag = False
        self.cycle_count = 0
        self.instruction_history = []
        self.enabled = True
    
    def tick(self, cycle: int) -> None:
        """CPU Tick実行"""
        if not self.enabled:
            return
        
        self.cycle_count += 1
        
        # 簡単な命令シミュレーション
        instruction = f"NOP_{cycle}"
        self.instruction_history.append({
            'cycle': cycle,
            'pc': self.pc,
            'instruction': instruction
        })
        
        # PC進行
        self.pc = (self.pc + 1) & 0xFFFF
    
    def get_device_id(self) -> str:
        return "cpu"
    
    def initialize(self) -> bool:
        return True
    
    def reset(self) -> None:
        self.pc = 0x0000
        self.status = 0x20
        self.stack_pointer = 0xFF
        self.cycle_count = 0
        self.instruction_history.clear()
    
    def shutdown(self) -> None:
        pass
    
    def is_enabled(self) -> bool:
        return self.enabled
    
    def get_state(self) -> Dict[str, Any]:
        return {
            'pc': self.pc,
            'status': self.status,
            'stack_pointer': self.stack_pointer,
            'cycle_count': self.cycle_count,
            'instruction_count': len(self.instruction_history)
        }


class MockMemory:
    """テスト用メモリモック"""
    
    def __init__(self, size: int = 65536):
        self.size = size
        self.data = [0] * size
        self.read_count = 0
        self.write_count = 0
        self.enabled = True
        
        # 割り込みベクタ設定
        self.data[0xFFFC] = 0x00  # RESET vector low
        self.data[0xFFFD] = 0x10  # RESET vector high
        self.data[0xFFFE] = 0x00  # IRQ vector low
        self.data[0xFFFF] = 0x80  # IRQ vector high
        self.data[0xFFFA] = 0x00  # NMI vector low
        self.data[0xFFFB] = 0x90  # NMI vector high
    
    def read(self, address: int) -> int:
        """メモリ読み取り"""
        if not self.enabled:
            return 0
        
        self.read_count += 1
        return self.data[address & (self.size - 1)]
    
    def write(self, address: int, value: int) -> None:
        """メモリ書き込み"""
        if not self.enabled:
            return
        
        self.write_count += 1
        self.data[address & (self.size - 1)] = value & 0xFF
    
    def tick(self, cycle: int) -> None:
        """メモリ Tick実行（何もしない）"""
        pass
    
    def get_device_id(self) -> str:
        return "memory"
    
    def initialize(self) -> bool:
        return True
    
    def reset(self) -> None:
        self.data = [0] * self.size
        self.read_count = 0
        self.write_count = 0
    
    def shutdown(self) -> None:
        pass
    
    def is_enabled(self) -> bool:
        return self.enabled
    
    def get_state(self) -> Dict[str, Any]:
        return {
            'size': self.size,
            'read_count': self.read_count,
            'write_count': self.write_count
        }


class MockIODevice:
    """テスト用IOデバイスモック"""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.tick_count = 0
        self.io_operations = []
        self.enabled = True
    
    def tick(self, cycle: int) -> None:
        """IO Tick実行"""
        if not self.enabled:
            return
        
        self.tick_count += 1
        
        # 定期的にIO操作をシミュレート
        if cycle % 100 == 0:
            operation = {
                'cycle': cycle,
                'type': 'io_operation',
                'data': f"data_{cycle}"
            }
            self.io_operations.append(operation)
    
    def get_device_id(self) -> str:
        return self.device_id
    
    def initialize(self) -> bool:
        return True
    
    def reset(self) -> None:
        self.tick_count = 0
        self.io_operations.clear()
    
    def shutdown(self) -> None:
        pass
    
    def is_enabled(self) -> bool:
        return self.enabled
    
    def get_state(self) -> Dict[str, Any]:
        return {
            'tick_count': self.tick_count,
            'io_operations': len(self.io_operations)
        }


class TestCompleteSystemIntegration:
    """完全システム統合テスト"""
    
    def test_full_system_startup_and_shutdown(self):
        """完全システム起動・終了テスト"""
        # システム設定
        config_manager = SystemConfigurationManager()
        config_manager.update_runtime_config(
            execution_mode=ExecutionMode.CONTINUOUS,
            master_frequency_hz=100_000,  # 100kHz（テスト用）
            enable_debugging=True
        )
        config_manager.update_performance_config(
            profile=PerformanceProfile.BALANCED
        )
        
        system_config = config_manager.get_system_configuration()
        
        # システム統合
        integration = SystemIntegration()
        
        # システム初期化
        assert integration.initialize_system(system_config) == True
        
        # コンポーネント確認
        assert integration.get_system_orchestrator() is not None
        assert integration.get_system_clock() is not None
        assert integration.get_interrupt_controller() is not None
        assert integration.get_tick_engine() is not None
        
        # システム開始
        orchestrator = integration.get_system_orchestrator()
        assert orchestrator.start() == True
        
        # 短時間実行
        time.sleep(0.1)  # 100ms
        
        # システム状態確認
        from py6502emu.core.orchestrator import SystemStatus
        assert orchestrator.get_status() == SystemStatus.RUNNING
        
        # システム停止
        orchestrator.stop()
        assert orchestrator.get_status() == SystemStatus.STOPPED
        
        # システム終了処理
        integration.shutdown_system()
    
    def test_cpu_memory_integration(self):
        """CPU・メモリ統合テスト"""
        # システム統合
        integration = SystemIntegration()
        config = SystemConfiguration(
            execution_mode=ExecutionMode.CONTINUOUS,
            enable_debugging=False
        )
        integration.initialize_system(config)
        
        # モックCPUとメモリ登録
        cpu = MockCPU()
        memory = MockMemory()
        
        orchestrator = integration.get_system_orchestrator()
        orchestrator.register_device(cpu)
        orchestrator.register_device(memory)
        
        # システム開始
        orchestrator.start()
        
        # 実行
        time.sleep(0.2)  # 200ms
        
        # 結果確認
        cpu_state = cpu.get_state()
        memory_state = memory.get_state()
        
        assert cpu_state['cycle_count'] > 0, "CPU should have executed cycles"
        assert cpu_state['instruction_count'] > 0, "CPU should have executed instructions"
        
        # システム停止
        orchestrator.stop()
        
        print(f"CPU executed {cpu_state['cycle_count']} cycles")
        print(f"CPU executed {cpu_state['instruction_count']} instructions")
        print(f"Memory reads: {memory_state['read_count']}")
        print(f"Memory writes: {memory_state['write_count']}")
    
    def test_interrupt_system_integration(self):
        """割り込みシステム統合テスト"""
        # システム統合
        integration = SystemIntegration()
        config = SystemConfiguration(execution_mode=ExecutionMode.STEP)
        integration.initialize_system(config)
        
        # モックCPUとメモリ
        cpu = MockCPU()
        memory = MockMemory()
        
        orchestrator = integration.get_system_orchestrator()
        orchestrator.register_device(cpu)
        orchestrator.register_device(memory)
        
        # 割り込みハンドラ設定
        interrupt_controller = integration.get_interrupt_controller()
        interrupt_handler = InterruptHandler(interrupt_controller)
        
        # CPUアクセサ設定
        def get_cpu_state():
            return {
                'program_counter': cpu.pc,
                'status_register': cpu.status,
                'stack_pointer': cpu.stack_pointer,
                'interrupt_disable_flag': cpu.interrupt_disable_flag
            }
        
        def set_cpu_state(state):
            cpu.pc = state.get('program_counter', cpu.pc)
            cpu.status = state.get('status_register', cpu.status)
            cpu.stack_pointer = state.get('stack_pointer', cpu.stack_pointer)
            cpu.interrupt_disable_flag = state.get('interrupt_disable_flag', cpu.interrupt_disable_flag)
        
        interrupt_handler.set_cpu_accessors(
            get_cpu_state, set_cpu_state, memory.read, memory.write
        )
        
        # システム初期化・開始
        orchestrator.initialize()
        
        # IRQ割り込み発生
        interrupt_controller.assert_irq("test_device")
        
        # 割り込み処理実行
        cycle = 0
        while interrupt_handler.check_and_handle_interrupts(cycle):
            cycle += 1
            if cycle > 10:  # 安全装置
                break
        
        # 割り込み処理確認
        interrupt_info = interrupt_handler.get_current_interrupt_info()
        assert interrupt_info is None, "Interrupt should be completed"
        
        # 統計確認
        stats = interrupt_handler.get_interrupt_statistics()
        assert stats['interrupt_stats'][InterruptType.IRQ]['total_count'] > 0
        
        print(f"Interrupt processed in {cycle} cycles")
    
    def test_multi_device_coordination(self):
        """マルチデバイス協調テスト"""
        # システム統合
        integration = SystemIntegration()
        config = SystemConfiguration(
            execution_mode=ExecutionMode.CONTINUOUS,
            max_cycles_per_frame=1000
        )
        integration.initialize_system(config)
        
        # 複数デバイス登録
        cpu = MockCPU()
        memory = MockMemory()
        io_devices = [MockIODevice(f"io_device_{i}") for i in range(3)]
        
        orchestrator = integration.get_system_orchestrator()
        orchestrator.register_device(cpu)
        orchestrator.register_device(memory)
        
        for io_device in io_devices:
            orchestrator.register_device(io_device)
        
        # システム開始
        orchestrator.start()
        
        # 実行
        time.sleep(0.3)  # 300ms
        
        # 各デバイスの動作確認
        cpu_state = cpu.get_state()
        memory_state = memory.get_state()
        
        assert cpu_state['cycle_count'] > 0
        
        for io_device in io_devices:
            io_state = io_device.get_state()
            assert io_state['tick_count'] > 0, f"IO device {io_device.device_id} should have ticked"
        
        # システム停止
        orchestrator.stop()
        
        # 結果出力
        print(f"CPU cycles: {cpu_state['cycle_count']}")
        print(f"Memory operations: R={memory_state['read_count']}, W={memory_state['write_count']}")
        for i, io_device in enumerate(io_devices):
            io_state = io_device.get_state()
            print(f"IO Device {i}: {io_state['tick_count']} ticks, {io_state['io_operations']} operations")
    
    def test_system_reset_and_recovery(self):
        """システムリセット・復旧テスト"""
        # システム統合
        integration = SystemIntegration()
        config = SystemConfiguration(execution_mode=ExecutionMode.CONTINUOUS)
        integration.initialize_system(config)
        
        # デバイス登録
        cpu = MockCPU()
        memory = MockMemory()
        
        orchestrator = integration.get_system_orchestrator()
        orchestrator.register_device(cpu)
        orchestrator.register_device(memory)
        
        # 初回実行
        orchestrator.start()
        time.sleep(0.1)
        
        # 実行状態確認
        initial_cpu_state = cpu.get_state()
        assert initial_cpu_state['cycle_count'] > 0
        
        # システムリセット
        orchestrator.reset()
        
        # リセット後状態確認
        reset_cpu_state = cpu.get_state()
        assert reset_cpu_state['pc'] == 0x0000
        assert reset_cpu_state['cycle_count'] == 0
        
        # 再実行
        time.sleep(0.1)
        
        # 再実行後状態確認
        final_cpu_state = cpu.get_state()
        assert final_cpu_state['cycle_count'] > 0
        
        orchestrator.stop()
        
        print("System reset and recovery test completed successfully")
    
    @pytest.mark.timeout(10)
    def test_concurrent_system_operations(self):
        """並行システム操作テスト"""
        # システム統合
        integration = SystemIntegration()
        config = SystemConfiguration(execution_mode=ExecutionMode.CONTINUOUS)
        integration.initialize_system(config)
        
        # デバイス登録
        cpu = MockCPU()
        memory = MockMemory()
        
        orchestrator = integration.get_system_orchestrator()
        orchestrator.register_device(cpu)
        orchestrator.register_device(memory)
        
        # システム開始
        orchestrator.start()
        
        # 並行操作
        operations_completed = []
        
        def pause_resume_operation():
            """一時停止・再開操作"""
            time.sleep(0.05)
            orchestrator.pause()
            time.sleep(0.05)
            orchestrator.resume()
            operations_completed.append("pause_resume")
        
        def step_operation():
            """ステップ実行操作"""
            time.sleep(0.1)
            for _ in range(10):
                orchestrator.step()
                time.sleep(0.001)
            operations_completed.append("step")
        
        def state_monitoring():
            """状態監視操作"""
            for _ in range(20):
                state = orchestrator.get_system_state()
                assert state is not None
                time.sleep(0.01)
            operations_completed.append("monitoring")
        
        # スレッド実行
        threads = [
            threading.Thread(target=pause_resume_operation),
            threading.Thread(target=step_operation),
            threading.Thread(target=state_monitoring)
        ]
        
        for thread in threads:
            thread.start()
        
        # メインスレッドでも動作
        time.sleep(0.3)
        
        # スレッド終了待機
        for thread in threads:
            thread.join()
        
        # システム停止
        orchestrator.stop()
        
        # 全操作完了確認
        assert len(operations_completed) == 3
        assert "pause_resume" in operations_completed
        assert "step" in operations_completed
        assert "monitoring" in operations_completed
        
        print("Concurrent operations test completed successfully")
    
    def test_error_handling_and_recovery(self):
        """エラーハンドリング・復旧テスト"""
        # システム統合
        integration = SystemIntegration()
        config = SystemConfiguration(execution_mode=ExecutionMode.CONTINUOUS)
        integration.initialize_system(config)
        
        # 正常デバイス
        cpu = MockCPU()
        memory = MockMemory()
        
        # エラーを発生させるデバイス
        error_device = Mock()
        error_device.get_device_id.return_value = "error_device"
        error_device.initialize.return_value = True
        error_device.is_enabled.return_value = True
        error_device.tick.side_effect = RuntimeError("Test error")
        error_device.reset.return_value = None
        error_device.shutdown.return_value = None
        error_device.get_state.return_value = {"error": True}
        
        orchestrator = integration.get_system_orchestrator()
        orchestrator.register_device(cpu)
        orchestrator.register_device(memory)
        orchestrator.register_device(error_device)
        
        # システム開始（エラーが発生するが継続すべき）
        orchestrator.start()
        
        # 短時間実行
        time.sleep(0.1)
        
        # 正常デバイスは動作継続確認
        cpu_state = cpu.get_state()
        assert cpu_state['cycle_count'] > 0, "Normal devices should continue working despite errors"
        
        # エラーデバイス削除
        orchestrator.unregister_device("error_device")
        
        # 継続実行
        time.sleep(0.1)
        
        # システム停止
        orchestrator.stop()
        
        print("Error handling and recovery test completed")
    
    def test_performance_under_load(self):
        """負荷下性能テスト"""
        # 高負荷設定
        config_manager = SystemConfigurationManager()
        config_manager.update_performance_config(
            profile=PerformanceProfile.PERFORMANCE,
            max_cycles_per_frame=50000
        )
        config_manager.update_runtime_config(
            master_frequency_hz=1_000_000  # 1MHz
        )
        
        system_config = config_manager.get_system_configuration()
        
        # システム統合
        integration = SystemIntegration()
        integration.initialize_system(system_config)
        
        # 多数のデバイス登録
        devices = []
        orchestrator = integration.get_system_orchestrator()
        
        # CPU・メモリ
        cpu = MockCPU()
        memory = MockMemory()
        devices.extend([cpu, memory])
        
        # 多数のIOデバイス
        for i in range(15):
            io_device = MockIODevice(f"load_test_device_{i}")
            devices.append(io_device)
        
        for device in devices:
            orchestrator.register_device(device)
        
        # 負荷テスト実行
        start_time = time.time()
        orchestrator.start()
        
        # 負荷実行
        time.sleep(1.0)  # 1秒
        
        end_time = time.time()
        orchestrator.stop()
        
        # 性能測定
        elapsed_time = end_time - start_time
        cpu_state = cpu.get_state()
        cycles_per_second = cpu_state['cycle_count'] / elapsed_time
        
        # 性能要件確認
        assert cycles_per_second > 10_000, f"Performance too low: {cycles_per_second} cycles/sec"
        
        print(f"Load test results:")
        print(f"  Devices: {len(devices)}")
        print(f"  Execution time: {elapsed_time:.2f} seconds")
        print(f"  CPU cycles: {cpu_state['cycle_count']}")
        print(f"  Cycles per second: {cycles_per_second:,.0f}")
        
        # 各デバイスの動作確認
        for device in devices[2:]:  # IOデバイスのみ
            device_state = device.get_state()
            assert device_state['tick_count'] > 0, f"Device {device.device_id} should have executed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
