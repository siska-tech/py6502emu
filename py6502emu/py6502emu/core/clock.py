"""
システムクロック管理
PU010: SystemClock

W65C02S エミュレータのマスタークロック管理と分周機能を提供します。
デバイス別クロック分周、時間進行の精密制御、クロック同期メカニズムを含みます。
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum, auto
import time
import threading
from abc import ABC, abstractmethod

from .types import DeviceType


class ClockMode(Enum):
    """クロック動作モード"""
    REALTIME = auto()    # リアルタイム実行
    STEP = auto()        # ステップ実行
    FAST = auto()        # 高速実行
    SYNC = auto()        # 同期実行


@dataclass
class ClockConfiguration:
    """クロック設定"""
    master_frequency_hz: int = 1_000_000  # 1MHz
    mode: ClockMode = ClockMode.REALTIME
    max_fast_multiplier: float = 10.0
    sync_interval_cycles: int = 1000
    enable_drift_correction: bool = True
    drift_correction_threshold_ns: int = 1000  # 1μs


@dataclass
class ClockDividerConfig:
    """クロック分周器設定"""
    device_id: str
    device_type: DeviceType
    divider_ratio: int = 1
    phase_offset: int = 0
    enabled: bool = True


@dataclass
class TimingStats:
    """タイミング統計情報"""
    total_cycles: int = 0
    elapsed_time_ns: int = 0
    average_frequency_hz: float = 0.0
    drift_ns: int = 0
    correction_count: int = 0
    last_sync_time_ns: int = 0


class ClockListener(ABC):
    """クロックイベントリスナー"""
    
    @abstractmethod
    def on_tick(self, cycle: int, timestamp_ns: int) -> None:
        """クロックティック時に呼び出される"""
        pass
    
    @abstractmethod
    def on_sync(self, cycle: int, timestamp_ns: int) -> None:
        """同期ポイントで呼び出される"""
        pass


class ClockDivider:
    """クロック分周器
    
    デバイス別のクロック分周機能を提供します。
    """
    
    def __init__(self, config: ClockDividerConfig):
        """分周器を初期化
        
        Args:
            config: 分周器設定
        """
        self.config = config
        self._cycle_counter = 0
        self._output_state = False
        self._last_output_cycle = -1
        
        # 設定検証
        if config.divider_ratio <= 0:
            raise ValueError("Divider ratio must be positive")
        if config.phase_offset < 0 or config.phase_offset >= config.divider_ratio:
            raise ValueError("Phase offset must be within divider ratio")
    
    def tick(self, master_cycle: int) -> bool:
        """マスタークロックティック処理
        
        Args:
            master_cycle: マスタークロックサイクル数
            
        Returns:
            分周クロック出力状態（True: High, False: Low）
        """
        if not self.config.enabled:
            return False
        
        # 位相オフセット適用
        adjusted_cycle = master_cycle + self.config.phase_offset
        
        # 分周処理
        divided_cycle = adjusted_cycle // self.config.divider_ratio
        
        # 出力状態更新
        if divided_cycle != self._last_output_cycle:
            self._output_state = not self._output_state
            self._last_output_cycle = divided_cycle
            return True
        
        return False
    
    def get_divided_cycle(self, master_cycle: int) -> int:
        """分周後サイクル数取得
        
        Args:
            master_cycle: マスタークロックサイクル数
            
        Returns:
            分周後のサイクル数
        """
        if not self.config.enabled:
            return 0
        
        adjusted_cycle = master_cycle + self.config.phase_offset
        return adjusted_cycle // self.config.divider_ratio
    
    def reset(self) -> None:
        """分周器リセット"""
        self._cycle_counter = 0
        self._output_state = False
        self._last_output_cycle = -1
    
    def get_state(self) -> Dict[str, Any]:
        """分周器状態取得"""
        return {
            'device_id': self.config.device_id,
            'device_type': self.config.device_type.name,
            'divider_ratio': self.config.divider_ratio,
            'phase_offset': self.config.phase_offset,
            'enabled': self.config.enabled,
            'output_state': self._output_state,
            'last_output_cycle': self._last_output_cycle
        }


class TimingController:
    """タイミング制御
    
    精密な時間制御とドリフト補正機能を提供します。
    """
    
    def __init__(self, config: ClockConfiguration):
        """タイミング制御を初期化
        
        Args:
            config: クロック設定
        """
        self.config = config
        self._start_time_ns = 0
        self._last_sync_time_ns = 0
        self._accumulated_drift_ns = 0
        self._stats = TimingStats()
        
        # 時間計算用定数
        self._ns_per_cycle = 1_000_000_000 / config.master_frequency_hz
        self._sync_interval_ns = self._ns_per_cycle * config.sync_interval_cycles
    
    def start(self) -> None:
        """タイミング制御開始"""
        current_time_ns = time.time_ns()
        self._start_time_ns = current_time_ns
        self._last_sync_time_ns = current_time_ns
        self._accumulated_drift_ns = 0
        
        # 統計リセット
        self._stats = TimingStats()
        self._stats.last_sync_time_ns = current_time_ns
    
    def calculate_target_time(self, cycle: int) -> int:
        """目標時刻計算
        
        Args:
            cycle: サイクル数
            
        Returns:
            目標時刻（ナノ秒）
        """
        return self._start_time_ns + int(cycle * self._ns_per_cycle)
    
    def wait_for_sync(self, cycle: int) -> int:
        """同期待機
        
        Args:
            cycle: 現在のサイクル数
            
        Returns:
            実際の待機時間（ナノ秒）
        """
        if self.config.mode != ClockMode.REALTIME:
            return 0
        
        current_time_ns = time.time_ns()
        target_time_ns = self.calculate_target_time(cycle)
        
        # ドリフト計算
        drift_ns = current_time_ns - target_time_ns
        self._accumulated_drift_ns += drift_ns
        
        # 待機時間計算
        wait_time_ns = max(0, target_time_ns - current_time_ns)
        
        # 実際の待機
        if wait_time_ns > 0:
            time.sleep(wait_time_ns / 1_000_000_000)
            actual_wait_ns = time.time_ns() - current_time_ns
        else:
            actual_wait_ns = 0
        
        # ドリフト補正
        if self.config.enable_drift_correction:
            self._apply_drift_correction()
        
        # 統計更新
        self._update_timing_stats(cycle, current_time_ns, drift_ns)
        
        return actual_wait_ns
    
    def get_current_frequency(self) -> float:
        """現在の実行周波数取得
        
        Returns:
            実行周波数（Hz）
        """
        if self._stats.elapsed_time_ns == 0:
            return 0.0
        
        return (self._stats.total_cycles * 1_000_000_000) / self._stats.elapsed_time_ns
    
    def get_timing_stats(self) -> TimingStats:
        """タイミング統計取得"""
        return self._stats
    
    def reset_stats(self) -> None:
        """統計リセット"""
        self._stats = TimingStats()
        self._accumulated_drift_ns = 0
    
    def _apply_drift_correction(self) -> None:
        """ドリフト補正適用"""
        if abs(self._accumulated_drift_ns) > self.config.drift_correction_threshold_ns:
            # 補正量計算（段階的補正）
            correction_ns = self._accumulated_drift_ns // 2
            
            # 次回同期時刻調整
            self._last_sync_time_ns -= correction_ns
            self._accumulated_drift_ns -= correction_ns
            
            # 統計更新
            self._stats.correction_count += 1
    
    def _update_timing_stats(self, cycle: int, current_time_ns: int, drift_ns: int) -> None:
        """タイミング統計更新"""
        self._stats.total_cycles = cycle
        self._stats.elapsed_time_ns = current_time_ns - self._start_time_ns
        self._stats.drift_ns = drift_ns
        
        if self._stats.elapsed_time_ns > 0:
            self._stats.average_frequency_hz = (
                cycle * 1_000_000_000
            ) / self._stats.elapsed_time_ns


class SystemClock:
    """システムクロック
    
    W65C02Sエミュレータのマスタークロック管理を行います。
    デバイス別分周、同期制御、タイミング管理機能を提供します。
    """
    
    def __init__(self, config: Optional[ClockConfiguration] = None):
        """システムクロックを初期化
        
        Args:
            config: クロック設定（省略時はデフォルト設定）
        """
        self.config = config or ClockConfiguration()
        
        # コンポーネント初期化
        self._timing_controller = TimingController(self.config)
        self._dividers: Dict[str, ClockDivider] = {}
        self._listeners: List[ClockListener] = []
        
        # 状態管理
        self._current_cycle = 0
        self._running = False
        self._paused = False
        
        # 同期制御
        self._sync_lock = threading.Lock()
        self._step_event = threading.Event()
        
        # フック
        self._tick_hooks: List[Callable[[int, int], None]] = []
        self._sync_hooks: List[Callable[[int, int], None]] = []
    
    def add_divider(self, config: ClockDividerConfig) -> None:
        """クロック分周器追加
        
        Args:
            config: 分周器設定
        """
        if config.device_id in self._dividers:
            raise ValueError(f"Divider already exists: {config.device_id}")
        
        self._dividers[config.device_id] = ClockDivider(config)
    
    def remove_divider(self, device_id: str) -> None:
        """クロック分周器削除
        
        Args:
            device_id: デバイスID
        """
        if device_id in self._dividers:
            del self._dividers[device_id]
    
    def get_divider(self, device_id: str) -> Optional[ClockDivider]:
        """クロック分周器取得
        
        Args:
            device_id: デバイスID
            
        Returns:
            クロック分周器（存在しない場合はNone）
        """
        return self._dividers.get(device_id)
    
    def add_listener(self, listener: ClockListener) -> None:
        """クロックリスナー追加"""
        self._listeners.append(listener)
    
    def remove_listener(self, listener: ClockListener) -> None:
        """クロックリスナー削除"""
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    def start(self) -> None:
        """クロック開始"""
        with self._sync_lock:
            if self._running:
                return
            
            self._running = True
            self._paused = False
            self._timing_controller.start()
    
    def stop(self) -> None:
        """クロック停止"""
        with self._sync_lock:
            self._running = False
            self._paused = False
            self._step_event.set()  # ステップ待機解除
    
    def pause(self) -> None:
        """クロック一時停止"""
        with self._sync_lock:
            self._paused = True
    
    def resume(self) -> None:
        """クロック再開"""
        with self._sync_lock:
            self._paused = False
            self._step_event.set()
    
    def step(self) -> bool:
        """単一ステップ実行
        
        Returns:
            ステップ実行が成功した場合True
        """
        if not self._running:
            return False
        
        return self._execute_tick()
    
    def tick(self) -> bool:
        """クロックティック実行
        
        Returns:
            ティック実行が成功した場合True
        """
        if not self._running:
            return False
        
        # 一時停止チェック
        if self._paused and self.config.mode == ClockMode.STEP:
            self._step_event.wait()
            self._step_event.clear()
        
        return self._execute_tick()
    
    def get_current_cycle(self) -> int:
        """現在のサイクル数取得"""
        return self._current_cycle
    
    def get_frequency(self) -> float:
        """現在の実行周波数取得"""
        return self._timing_controller.get_current_frequency()
    
    def get_state(self) -> Dict[str, Any]:
        """システムクロック状態取得"""
        return {
            'current_cycle': self._current_cycle,
            'running': self._running,
            'paused': self._paused,
            'mode': self.config.mode.name,
            'master_frequency_hz': self.config.master_frequency_hz,
            'current_frequency_hz': self.get_frequency(),
            'divider_count': len(self._dividers),
            'listener_count': len(self._listeners),
            'timing_stats': self._timing_controller.get_timing_stats().__dict__
        }
    
    def get_divider_states(self) -> Dict[str, Dict[str, Any]]:
        """全分周器状態取得"""
        return {
            device_id: divider.get_state()
            for device_id, divider in self._dividers.items()
        }
    
    def reset(self) -> None:
        """システムクロックリセット"""
        with self._sync_lock:
            self._current_cycle = 0
            
            # 分周器リセット
            for divider in self._dividers.values():
                divider.reset()
            
            # 統計リセット
            self._timing_controller.reset_stats()
    
    def add_tick_hook(self, hook: Callable[[int, int], None]) -> None:
        """ティックフック追加"""
        self._tick_hooks.append(hook)
    
    def add_sync_hook(self, hook: Callable[[int, int], None]) -> None:
        """同期フック追加"""
        self._sync_hooks.append(hook)
    
    def remove_tick_hook(self, hook: Callable[[int, int], None]) -> None:
        """ティックフック削除"""
        if hook in self._tick_hooks:
            self._tick_hooks.remove(hook)
    
    def remove_sync_hook(self, hook: Callable[[int, int], None]) -> None:
        """同期フック削除"""
        if hook in self._sync_hooks:
            self._sync_hooks.remove(hook)
    
    def _execute_tick(self) -> bool:
        """ティック実行処理"""
        current_time_ns = time.time_ns()
        
        # 分周器更新
        active_devices = []
        for device_id, divider in self._dividers.items():
            if divider.tick(self._current_cycle):
                active_devices.append(device_id)
        
        # リスナー通知（サイクル更新前に実行）
        for listener in self._listeners:
            listener.on_tick(self._current_cycle, current_time_ns)
        
        # フック実行
        for hook in self._tick_hooks:
            hook(self._current_cycle, current_time_ns)
        
        # 同期処理
        if self._current_cycle % self.config.sync_interval_cycles == 0:
            self._execute_sync(current_time_ns)
        
        # タイミング制御
        if self.config.mode == ClockMode.REALTIME:
            self._timing_controller.wait_for_sync(self._current_cycle)
        
        # サイクル更新
        self._current_cycle += 1
        
        return True
    
    def _execute_sync(self, timestamp_ns: int) -> None:
        """同期処理実行"""
        # リスナー通知
        for listener in self._listeners:
            listener.on_sync(self._current_cycle, timestamp_ns)
        
        # フック実行
        for hook in self._sync_hooks:
            hook(self._current_cycle, timestamp_ns)
