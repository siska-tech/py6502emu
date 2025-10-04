"""
システム性能テスト

Phase4で実装されたシステム統合機能の性能測定を行います。
実行速度の測定、メモリ使用量の監視、システム応答時間の測定、負荷テストを含みます。
"""

import pytest
import time
import psutil
import threading
import gc
from typing import Dict, List, Any
from unittest.mock import Mock

from py6502emu.core.clock import SystemClock, ClockConfiguration, ClockMode
from py6502emu.core.orchestrator import SystemOrchestrator, SystemConfiguration, ExecutionMode
from py6502emu.core.tick_engine import TickEngine, Tickable, TickableConfig, TickPriority, TickPhase
from py6502emu.core.integration import SystemIntegration
from py6502emu.core.system_config import SystemConfigurationManager, PerformanceProfile
from py6502emu.core.scheduler import DeviceScheduler, SchedulingConfig, SchedulingPolicy
from py6502emu.cpu.interrupt_handler import InterruptHandler
from py6502emu.core.interrupt_controller import InterruptController
from py6502emu.core.types import DeviceType


class PerformanceTestDevice(Tickable):
    """性能テスト用デバイス"""
    
    def __init__(self, device_id: str, workload_cycles: int = 100):
        self.device_id = device_id
        self.workload_cycles = workload_cycles
        self.tick_count = 0
        self.total_work_done = 0
        self.enabled = True
    
    def tick(self, cycle: int, phase: TickPhase) -> None:
        """Tick実行（計算負荷シミュレーション）"""
        self.tick_count += 1
        
        # 計算負荷シミュレーション
        work = 0
        for i in range(self.workload_cycles):
            work += i * i
        
        self.total_work_done += work
    
    def get_tick_config(self) -> TickableConfig:
        """Tick設定取得"""
        return TickableConfig(
            device_id=self.device_id,
            priority=TickPriority.NORMAL,
            enabled=self.enabled
        )
    
    def is_tick_enabled(self) -> bool:
        """Tick実行有効チェック"""
        return self.enabled


class MemoryMonitor:
    """メモリ使用量監視"""
    
    def __init__(self):
        self.initial_memory = 0
        self.peak_memory = 0
        self.current_memory = 0
        self.measurements = []
    
    def start_monitoring(self) -> None:
        """監視開始"""
        gc.collect()  # ガベージコレクション実行
        process = psutil.Process()
        self.initial_memory = process.memory_info().rss
        self.peak_memory = self.initial_memory
        self.measurements = []
    
    def measure(self) -> int:
        """現在のメモリ使用量測定"""
        process = psutil.Process()
        self.current_memory = process.memory_info().rss
        self.peak_memory = max(self.peak_memory, self.current_memory)
        
        measurement = {
            'timestamp': time.time(),
            'memory_bytes': self.current_memory,
            'memory_mb': self.current_memory / (1024 * 1024)
        }
        self.measurements.append(measurement)
        
        return self.current_memory
    
    def get_memory_usage_mb(self) -> float:
        """現在のメモリ使用量取得（MB）"""
        return self.current_memory / (1024 * 1024)
    
    def get_peak_memory_mb(self) -> float:
        """ピークメモリ使用量取得（MB）"""
        return self.peak_memory / (1024 * 1024)
    
    def get_memory_increase_mb(self) -> float:
        """メモリ増加量取得（MB）"""
        return (self.current_memory - self.initial_memory) / (1024 * 1024)


class PerformanceBenchmark:
    """性能ベンチマーク"""
    
    def __init__(self):
        self.results = {}
        self.memory_monitor = MemoryMonitor()
    
    def run_execution_speed_test(self, duration_seconds: float = 1.0) -> Dict[str, Any]:
        """実行速度テスト"""
        # システム統合
        integration = SystemIntegration()
        config = SystemConfiguration(
            execution_mode=ExecutionMode.CONTINUOUS,
            enable_debugging=False
        )
        integration.initialize_system(config)
        
        # テストデバイス登録
        tick_engine = integration.get_tick_engine()
        test_devices = []
        for i in range(5):
            device = PerformanceTestDevice(f"perf_device_{i}", workload_cycles=50)
            test_devices.append(device)
            tick_engine.register_tickable(device)
        
        # メモリ監視開始
        self.memory_monitor.start_monitoring()
        
        # システム開始
        orchestrator = integration.get_system_orchestrator()
        orchestrator.start()
        
        # 実行時間測定
        start_time = time.time()
        start_cycle = tick_engine.get_current_cycle()
        
        # 指定時間実行
        time.sleep(duration_seconds)
        
        # 測定終了
        end_time = time.time()
        end_cycle = tick_engine.get_current_cycle()
        
        # システム停止
        orchestrator.stop()
        
        # メモリ測定
        final_memory = self.memory_monitor.measure()
        
        # 結果計算
        elapsed_time = end_time - start_time
        cycles_executed = end_cycle - start_cycle
        cycles_per_second = cycles_executed / elapsed_time if elapsed_time > 0 else 0
        
        # デバイス統計
        device_stats = {}
        for device in test_devices:
            device_stats[device.device_id] = {
                'tick_count': device.tick_count,
                'work_done': device.total_work_done
            }
        
        return {
            'elapsed_time_seconds': elapsed_time,
            'cycles_executed': cycles_executed,
            'cycles_per_second': cycles_per_second,
            'target_frequency_hz': config.clock_config.master_frequency_hz,
            'efficiency_percent': (cycles_per_second / config.clock_config.master_frequency_hz) * 100,
            'memory_usage_mb': self.memory_monitor.get_memory_usage_mb(),
            'memory_increase_mb': self.memory_monitor.get_memory_increase_mb(),
            'device_stats': device_stats
        }
    
    def run_memory_usage_test(self, device_count: int = 10) -> Dict[str, Any]:
        """メモリ使用量テスト"""
        self.memory_monitor.start_monitoring()
        
        # システム統合
        integration = SystemIntegration()
        config = SystemConfiguration(execution_mode=ExecutionMode.CONTINUOUS)
        integration.initialize_system(config)
        
        initial_memory = self.memory_monitor.measure()
        
        # 複数デバイス登録
        tick_engine = integration.get_tick_engine()
        devices = []
        
        for i in range(device_count):
            device = PerformanceTestDevice(f"mem_test_device_{i}")
            devices.append(device)
            tick_engine.register_tickable(device)
            
            # 定期的にメモリ測定
            if i % 5 == 0:
                self.memory_monitor.measure()
        
        after_registration_memory = self.memory_monitor.measure()
        
        # 短時間実行
        orchestrator = integration.get_system_orchestrator()
        orchestrator.start()
        time.sleep(0.1)  # 100ms
        orchestrator.stop()
        
        after_execution_memory = self.memory_monitor.measure()
        
        # デバイス登録解除
        for device in devices:
            tick_engine.unregister_tickable(device.device_id)
        
        after_cleanup_memory = self.memory_monitor.measure()
        
        return {
            'device_count': device_count,
            'initial_memory_mb': initial_memory / (1024 * 1024),
            'after_registration_mb': after_registration_memory / (1024 * 1024),
            'after_execution_mb': after_execution_memory / (1024 * 1024),
            'after_cleanup_mb': after_cleanup_memory / (1024 * 1024),
            'registration_overhead_mb': (after_registration_memory - initial_memory) / (1024 * 1024),
            'execution_overhead_mb': (after_execution_memory - after_registration_memory) / (1024 * 1024),
            'memory_per_device_kb': ((after_registration_memory - initial_memory) / device_count) / 1024,
            'peak_memory_mb': self.memory_monitor.get_peak_memory_mb()
        }
    
    def run_response_time_test(self, iterations: int = 100) -> Dict[str, Any]:
        """応答時間テスト"""
        # システム統合
        integration = SystemIntegration()
        config = SystemConfiguration(execution_mode=ExecutionMode.STEP)
        integration.initialize_system(config)
        
        orchestrator = integration.get_system_orchestrator()
        orchestrator.initialize()
        
        response_times = []
        
        for i in range(iterations):
            # ステップ実行の応答時間測定
            start_time = time.time_ns()
            orchestrator.step()
            end_time = time.time_ns()
            
            response_time_ns = end_time - start_time
            response_times.append(response_time_ns)
        
        # 統計計算
        min_response = min(response_times)
        max_response = max(response_times)
        avg_response = sum(response_times) / len(response_times)
        
        # パーセンタイル計算
        sorted_times = sorted(response_times)
        p50 = sorted_times[len(sorted_times) // 2]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]
        
        return {
            'iterations': iterations,
            'min_response_ns': min_response,
            'max_response_ns': max_response,
            'avg_response_ns': avg_response,
            'p50_response_ns': p50,
            'p95_response_ns': p95,
            'p99_response_ns': p99,
            'min_response_us': min_response / 1000,
            'max_response_us': max_response / 1000,
            'avg_response_us': avg_response / 1000
        }
    
    def run_load_test(self, device_count: int = 20, duration_seconds: float = 2.0) -> Dict[str, Any]:
        """負荷テスト"""
        self.memory_monitor.start_monitoring()
        
        # 高負荷設定
        config = SystemConfiguration(
            execution_mode=ExecutionMode.CONTINUOUS,
            max_cycles_per_frame=50000,  # 高負荷
            enable_debugging=False,
            enable_profiling=True
        )
        
        integration = SystemIntegration()
        integration.initialize_system(config)
        
        # 多数のデバイス登録
        tick_engine = integration.get_tick_engine()
        devices = []
        
        for i in range(device_count):
            # 異なる負荷レベルのデバイス
            workload = 50 + (i % 5) * 20  # 50-130サイクルの負荷
            device = PerformanceTestDevice(f"load_device_{i}", workload_cycles=workload)
            devices.append(device)
            tick_engine.register_tickable(device)
        
        # 負荷テスト実行
        orchestrator = integration.get_system_orchestrator()
        orchestrator.start()
        
        # 定期的な測定
        measurements = []
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            measurement_time = time.time()
            current_cycle = tick_engine.get_current_cycle()
            memory_usage = self.memory_monitor.measure()
            
            measurements.append({
                'timestamp': measurement_time,
                'cycle': current_cycle,
                'memory_mb': memory_usage / (1024 * 1024)
            })
            
            time.sleep(0.1)  # 100ms間隔
        
        orchestrator.stop()
        
        # 結果分析
        total_cycles = tick_engine.get_current_cycle()
        elapsed_time = time.time() - start_time
        
        # デバイス統計
        total_ticks = sum(device.tick_count for device in devices)
        total_work = sum(device.total_work_done for device in devices)
        
        return {
            'device_count': device_count,
            'duration_seconds': elapsed_time,
            'total_cycles': total_cycles,
            'cycles_per_second': total_cycles / elapsed_time,
            'total_device_ticks': total_ticks,
            'total_work_done': total_work,
            'ticks_per_device': total_ticks / device_count,
            'peak_memory_mb': self.memory_monitor.get_peak_memory_mb(),
            'memory_increase_mb': self.memory_monitor.get_memory_increase_mb(),
            'measurements': measurements
        }


class TestSystemPerformance:
    """システム性能テスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.benchmark = PerformanceBenchmark()
    
    def test_execution_speed_performance(self):
        """実行速度性能テスト"""
        result = self.benchmark.run_execution_speed_test(duration_seconds=1.0)
        
        # 性能要件チェック
        assert result['cycles_per_second'] > 100_000, f"Too slow: {result['cycles_per_second']} cycles/sec"
        assert result['efficiency_percent'] > 10, f"Low efficiency: {result['efficiency_percent']}%"
        assert result['memory_usage_mb'] < 100, f"High memory usage: {result['memory_usage_mb']} MB"
        
        print(f"Execution Speed Test Results:")
        print(f"  Cycles per second: {result['cycles_per_second']:,.0f}")
        print(f"  Efficiency: {result['efficiency_percent']:.1f}%")
        print(f"  Memory usage: {result['memory_usage_mb']:.1f} MB")
    
    def test_memory_usage_performance(self):
        """メモリ使用量性能テスト"""
        result = self.benchmark.run_memory_usage_test(device_count=10)
        
        # メモリ要件チェック
        assert result['peak_memory_mb'] < 100, f"High peak memory: {result['peak_memory_mb']} MB"
        assert result['memory_per_device_kb'] < 100, f"High per-device memory: {result['memory_per_device_kb']} KB"
        
        print(f"Memory Usage Test Results:")
        print(f"  Peak memory: {result['peak_memory_mb']:.1f} MB")
        print(f"  Memory per device: {result['memory_per_device_kb']:.1f} KB")
        print(f"  Registration overhead: {result['registration_overhead_mb']:.1f} MB")
    
    def test_response_time_performance(self):
        """応答時間性能テスト"""
        result = self.benchmark.run_response_time_test(iterations=100)
        
        # 応答時間要件チェック
        assert result['avg_response_us'] < 1000, f"High average response time: {result['avg_response_us']} μs"
        assert result['p95_response_us'] < 2000, f"High P95 response time: {result['p95_response_us']} μs"
        
        print(f"Response Time Test Results:")
        print(f"  Average response: {result['avg_response_us']:.1f} μs")
        print(f"  P95 response: {result['p95_response_us']:.1f} μs")
        print(f"  P99 response: {result['p99_response_us']:.1f} μs")
    
    def test_load_performance(self):
        """負荷性能テスト"""
        result = self.benchmark.run_load_test(device_count=20, duration_seconds=2.0)
        
        # 負荷要件チェック
        assert result['cycles_per_second'] > 50_000, f"Low performance under load: {result['cycles_per_second']}"
        assert result['peak_memory_mb'] < 150, f"High memory under load: {result['peak_memory_mb']} MB"
        
        print(f"Load Test Results:")
        print(f"  Device count: {result['device_count']}")
        print(f"  Cycles per second: {result['cycles_per_second']:,.0f}")
        print(f"  Total device ticks: {result['total_device_ticks']:,}")
        print(f"  Peak memory: {result['peak_memory_mb']:.1f} MB")
    
    @pytest.mark.timeout(10)
    def test_scheduler_performance(self):
        """スケジューラ性能テスト"""
        # 異なるスケジューリングポリシーのテスト
        policies = [
            SchedulingPolicy.PRIORITY_BASED,
            SchedulingPolicy.ROUND_ROBIN,
            SchedulingPolicy.FAIR_SHARE
        ]
        
        results = {}
        
        for policy in policies:
            config = SchedulingConfig(
                policy=policy,
                time_slice_cycles=1000
            )
            scheduler = DeviceScheduler(config)
            
            # テストデバイス登録
            for i in range(10):
                mock_device = Mock()
                mock_device.tick = Mock()
                scheduler.register_device(f"device_{i}", mock_device, DeviceType.IO)
            
            # 性能測定
            start_time = time.time()
            
            for cycle in range(1000):
                scheduler.execute_cycle(cycle)
            
            elapsed_time = time.time() - start_time
            
            results[policy.name] = {
                'elapsed_time': elapsed_time,
                'cycles_per_second': 1000 / elapsed_time,
                'stats': scheduler.get_scheduler_stats()
            }
        
        # 結果出力
        print("Scheduler Performance Results:")
        for policy_name, result in results.items():
            print(f"  {policy_name}: {result['cycles_per_second']:,.0f} cycles/sec")
    
    def test_interrupt_handler_performance(self):
        """割り込みハンドラ性能テスト"""
        interrupt_controller = InterruptController()
        interrupt_handler = InterruptHandler(interrupt_controller)
        
        # モックCPUアクセサ設定
        cpu_state = {
            'program_counter': 0x1000,
            'status_register': 0x20,
            'stack_pointer': 0xFF,
            'interrupt_disable_flag': False
        }
        memory = [0] * 65536
        memory[0xFFFE] = 0x00  # IRQ vector low
        memory[0xFFFF] = 0x80  # IRQ vector high
        
        def get_cpu_state():
            return cpu_state.copy()
        
        def set_cpu_state(new_state):
            cpu_state.update(new_state)
        
        def read_memory(address):
            return memory[address & 0xFFFF]
        
        def write_memory(address, value):
            memory[address & 0xFFFF] = value & 0xFF
        
        interrupt_handler.set_cpu_accessors(
            get_cpu_state, set_cpu_state, read_memory, write_memory
        )
        
        # 割り込み性能測定
        interrupt_times = []
        
        for i in range(50):
            # IRQ要求
            interrupt_controller.assert_irq(f"test_source_{i}")
            
            start_time = time.time_ns()
            cycle = 0
            
            # 割り込みシーケンス実行
            while interrupt_handler.check_and_handle_interrupts(cycle):
                cycle += 1
                if cycle > 10:  # 安全装置
                    break
            
            end_time = time.time_ns()
            interrupt_times.append(end_time - start_time)
        
        # 統計計算
        avg_time = sum(interrupt_times) / len(interrupt_times)
        min_time = min(interrupt_times)
        max_time = max(interrupt_times)
        
        print(f"Interrupt Handler Performance:")
        print(f"  Average interrupt time: {avg_time/1000:.1f} μs")
        print(f"  Min interrupt time: {min_time/1000:.1f} μs")
        print(f"  Max interrupt time: {max_time/1000:.1f} μs")
        
        # 性能要件チェック
        assert avg_time < 100_000, f"High average interrupt time: {avg_time/1000} μs"  # 100μs以下


class TestPerformanceProfiles:
    """性能プロファイルテスト"""
    
    def test_accuracy_profile_performance(self):
        """精度重視プロファイル性能テスト"""
        config_manager = SystemConfigurationManager()
        config_manager.update_performance_config(profile=PerformanceProfile.ACCURACY)
        
        system_config = config_manager.get_system_configuration()
        
        # 精度重視設定の確認
        perf_config = config_manager.get_performance_config()
        assert perf_config.max_cycles_per_frame == 1000
        assert perf_config.enable_profiling == True
        
        # 実際の性能測定
        benchmark = PerformanceBenchmark()
        result = benchmark.run_execution_speed_test(duration_seconds=0.5)
        
        print(f"Accuracy Profile Performance:")
        print(f"  Cycles per second: {result['cycles_per_second']:,.0f}")
        print(f"  Memory usage: {result['memory_usage_mb']:.1f} MB")
    
    def test_performance_profile_performance(self):
        """性能重視プロファイル性能テスト"""
        config_manager = SystemConfigurationManager()
        config_manager.update_performance_config(profile=PerformanceProfile.PERFORMANCE)
        
        # 性能重視設定の確認
        perf_config = config_manager.get_performance_config()
        assert perf_config.max_cycles_per_frame == 50000
        assert perf_config.enable_profiling == False
        
        # 実際の性能測定
        benchmark = PerformanceBenchmark()
        result = benchmark.run_execution_speed_test(duration_seconds=0.5)
        
        print(f"Performance Profile Performance:")
        print(f"  Cycles per second: {result['cycles_per_second']:,.0f}")
        print(f"  Memory usage: {result['memory_usage_mb']:.1f} MB")
    
    def test_balanced_profile_performance(self):
        """バランス重視プロファイル性能テスト"""
        config_manager = SystemConfigurationManager()
        config_manager.update_performance_config(profile=PerformanceProfile.BALANCED)
        
        # バランス設定の確認
        perf_config = config_manager.get_performance_config()
        assert perf_config.max_cycles_per_frame == 10000
        
        # 実際の性能測定
        benchmark = PerformanceBenchmark()
        result = benchmark.run_execution_speed_test(duration_seconds=0.5)
        
        print(f"Balanced Profile Performance:")
        print(f"  Cycles per second: {result['cycles_per_second']:,.0f}")
        print(f"  Memory usage: {result['memory_usage_mb']:.1f} MB")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
