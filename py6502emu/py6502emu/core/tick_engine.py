"""
Tick駆動実行エンジン

W65C02S エミュレータのTick駆動実行モデルの中核実装を提供します。
サイクル精度の時間管理、デバイス間の同期制御、実行時間の精密測定を含みます。
"""

from typing import Dict, List, Optional, Any, Callable, Protocol
from dataclasses import dataclass, field
from enum import Enum, auto
import time
import threading
from abc import ABC, abstractmethod
from collections import deque

from .types import DeviceType
from .clock import ClockListener


class TickPriority(Enum):
    """Tick実行優先度"""
    CRITICAL = 1    # 最高優先度（CPU等）
    HIGH = 2        # 高優先度（メモリ等）
    NORMAL = 3      # 通常優先度（一般デバイス）
    LOW = 4         # 低優先度（UI等）


class TickPhase(Enum):
    """Tick実行フェーズ"""
    PRE_EXECUTE = auto()    # 実行前処理
    EXECUTE = auto()        # メイン実行
    POST_EXECUTE = auto()   # 実行後処理
    SYNC = auto()           # 同期処理


@dataclass
class TickableConfig:
    """Tickable設定"""
    device_id: str
    priority: TickPriority = TickPriority.NORMAL
    enabled: bool = True
    cycle_interval: int = 1  # 何サイクルごとに実行するか
    phase_offset: int = 0    # フェーズオフセット


@dataclass
class TickStats:
    """Tick統計情報"""
    total_ticks: int = 0
    execution_time_ns: int = 0
    average_tick_time_ns: float = 0.0
    min_tick_time_ns: int = 0
    max_tick_time_ns: int = 0
    last_tick_time_ns: int = 0


class Tickable(Protocol):
    """Tick実行可能インターフェース"""
    
    def tick(self, cycle: int, phase: TickPhase) -> None:
        """Tick実行
        
        Args:
            cycle: 現在のサイクル数
            phase: 実行フェーズ
        """
        ...
    
    def get_tick_config(self) -> TickableConfig:
        """Tick設定取得"""
        ...
    
    def is_tick_enabled(self) -> bool:
        """Tick実行有効チェック"""
        ...


class CycleCounter:
    """サイクルカウンタ
    
    高精度なサイクル計測と時間管理を提供します。
    """
    
    def __init__(self, master_frequency_hz: int = 1_000_000):
        """サイクルカウンタを初期化
        
        Args:
            master_frequency_hz: マスター周波数（Hz）
        """
        self._master_frequency_hz = master_frequency_hz
        self._current_cycle = 0
        self._start_time_ns = 0
        self._last_sync_time_ns = 0
        self._accumulated_cycles = 0
        
        # 時間計算用定数
        self._ns_per_cycle = 1_000_000_000 / master_frequency_hz
        
        # 統計
        self._stats = TickStats()
        self._cycle_history: deque = deque(maxlen=1000)
        
        # 同期制御
        self._sync_lock = threading.Lock()
    
    def start(self) -> None:
        """カウンタ開始"""
        with self._sync_lock:
            current_time_ns = time.time_ns()
            self._start_time_ns = current_time_ns
            self._last_sync_time_ns = current_time_ns
            self._current_cycle = 0
            self._accumulated_cycles = 0
            
            # 統計リセット
            self._stats = TickStats()
            self._cycle_history.clear()
    
    def tick(self) -> int:
        """サイクル進行
        
        Returns:
            現在のサイクル数
        """
        with self._sync_lock:
            tick_start_ns = time.time_ns()
            
            self._current_cycle += 1
            self._accumulated_cycles += 1
            
            # 統計更新
            tick_time_ns = time.time_ns() - tick_start_ns
            self._update_stats(tick_time_ns)
            
            # 履歴記録
            self._cycle_history.append({
                'cycle': self._current_cycle,
                'timestamp_ns': tick_start_ns,
                'execution_time_ns': tick_time_ns
            })
            
            return self._current_cycle
    
    def get_current_cycle(self) -> int:
        """現在のサイクル数取得"""
        return self._current_cycle
    
    def get_elapsed_time_ns(self) -> int:
        """経過時間取得（ナノ秒）"""
        if self._start_time_ns == 0:
            return 0
        return time.time_ns() - self._start_time_ns
    
    def get_target_time_ns(self, cycle: int) -> int:
        """目標時刻取得（ナノ秒）
        
        Args:
            cycle: サイクル数
            
        Returns:
            目標時刻（ナノ秒）
        """
        return self._start_time_ns + int(cycle * self._ns_per_cycle)
    
    def get_frequency_hz(self) -> float:
        """現在の実行周波数取得（Hz）"""
        elapsed_ns = self.get_elapsed_time_ns()
        if elapsed_ns == 0:
            return 0.0
        
        return (self._accumulated_cycles * 1_000_000_000) / elapsed_ns
    
    def get_stats(self) -> TickStats:
        """統計情報取得"""
        return self._stats
    
    def get_cycle_history(self, last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """サイクル履歴取得
        
        Args:
            last_n: 取得する最新エントリ数（Noneの場合は全て）
            
        Returns:
            サイクル履歴のリスト
        """
        history = list(self._cycle_history)
        if last_n is not None and last_n > 0:
            history = history[-last_n:]
        return history
    
    def reset(self) -> None:
        """カウンタリセット"""
        with self._sync_lock:
            self._current_cycle = 0
            self._accumulated_cycles = 0
            self._stats = TickStats()
            self._cycle_history.clear()
    
    def sync_to_realtime(self) -> int:
        """リアルタイム同期
        
        Returns:
            待機時間（ナノ秒）
        """
        current_time_ns = time.time_ns()
        target_time_ns = self.get_target_time_ns(self._current_cycle)
        
        wait_time_ns = max(0, target_time_ns - current_time_ns)
        
        if wait_time_ns > 0:
            time.sleep(wait_time_ns / 1_000_000_000)
        
        return wait_time_ns
    
    def _update_stats(self, tick_time_ns: int) -> None:
        """統計更新"""
        self._stats.total_ticks += 1
        self._stats.execution_time_ns += tick_time_ns
        self._stats.last_tick_time_ns = tick_time_ns
        
        # 平均時間更新
        self._stats.average_tick_time_ns = (
            self._stats.execution_time_ns / self._stats.total_ticks
        )
        
        # 最小・最大時間更新
        if self._stats.min_tick_time_ns == 0 or tick_time_ns < self._stats.min_tick_time_ns:
            self._stats.min_tick_time_ns = tick_time_ns
        
        if tick_time_ns > self._stats.max_tick_time_ns:
            self._stats.max_tick_time_ns = tick_time_ns


class TickScheduler:
    """Tickスケジューラ
    
    複数のTickableオブジェクトの実行順序と優先度を管理します。
    """
    
    def __init__(self):
        """Tickスケジューラを初期化"""
        # Tickable管理
        self._tickables: Dict[str, Tickable] = {}
        self._execution_order: List[str] = []
        self._priority_groups: Dict[TickPriority, List[str]] = {
            priority: [] for priority in TickPriority
        }
        
        # 統計
        self._execution_stats: Dict[str, TickStats] = {}
        
        # 同期制御
        self._scheduler_lock = threading.RLock()
    
    def register_tickable(self, tickable: Tickable) -> None:
        """Tickable登録
        
        Args:
            tickable: 登録するTickable
        """
        with self._scheduler_lock:
            config = tickable.get_tick_config()
            device_id = config.device_id
            
            if device_id in self._tickables:
                raise ValueError(f"Tickable already registered: {device_id}")
            
            self._tickables[device_id] = tickable
            self._execution_stats[device_id] = TickStats()
            
            # 優先度グループに追加
            self._priority_groups[config.priority].append(device_id)
            
            # 実行順序更新
            self._update_execution_order()
    
    def unregister_tickable(self, device_id: str) -> None:
        """Tickable登録解除
        
        Args:
            device_id: デバイスID
        """
        with self._scheduler_lock:
            if device_id not in self._tickables:
                return
            
            tickable = self._tickables[device_id]
            config = tickable.get_tick_config()
            
            # 優先度グループから削除
            if device_id in self._priority_groups[config.priority]:
                self._priority_groups[config.priority].remove(device_id)
            
            # 登録解除
            del self._tickables[device_id]
            del self._execution_stats[device_id]
            
            # 実行順序更新
            self._update_execution_order()
    
    def execute_tick(self, cycle: int, phase: TickPhase) -> Dict[str, int]:
        """Tick実行
        
        Args:
            cycle: 現在のサイクル数
            phase: 実行フェーズ
            
        Returns:
            各デバイスの実行時間（ナノ秒）
        """
        execution_times = {}
        
        with self._scheduler_lock:
            for device_id in self._execution_order:
                if device_id not in self._tickables:
                    continue
                
                tickable = self._tickables[device_id]
                config = tickable.get_tick_config()
                
                # 実行条件チェック
                if not self._should_execute(tickable, cycle, phase):
                    continue
                
                # Tick実行
                start_time_ns = time.time_ns()
                try:
                    tickable.tick(cycle, phase)
                    execution_time_ns = time.time_ns() - start_time_ns
                    execution_times[device_id] = execution_time_ns
                    
                    # 統計更新
                    self._update_execution_stats(device_id, execution_time_ns)
                    
                except Exception as e:
                    execution_time_ns = time.time_ns() - start_time_ns
                    execution_times[device_id] = execution_time_ns
                    raise RuntimeError(f"Tick execution failed [{device_id}]: {e}")
        
        return execution_times
    
    def get_tickable(self, device_id: str) -> Optional[Tickable]:
        """Tickable取得
        
        Args:
            device_id: デバイスID
            
        Returns:
            Tickable（存在しない場合はNone）
        """
        return self._tickables.get(device_id)
    
    def get_execution_order(self) -> List[str]:
        """実行順序取得"""
        return self._execution_order.copy()
    
    def get_execution_stats(self) -> Dict[str, TickStats]:
        """実行統計取得"""
        return self._execution_stats.copy()
    
    def reset_stats(self) -> None:
        """統計リセット"""
        with self._scheduler_lock:
            for device_id in self._execution_stats:
                self._execution_stats[device_id] = TickStats()
    
    def _should_execute(self, tickable: Tickable, cycle: int, phase: TickPhase) -> bool:
        """実行判定
        
        Args:
            tickable: Tickable
            cycle: サイクル数
            phase: 実行フェーズ
            
        Returns:
            実行すべき場合True
        """
        if not tickable.is_tick_enabled():
            return False
        
        config = tickable.get_tick_config()
        
        # サイクル間隔チェック
        if config.cycle_interval > 1:
            adjusted_cycle = cycle + config.phase_offset
            if adjusted_cycle % config.cycle_interval != 0:
                return False
        
        return True
    
    def _update_execution_order(self) -> None:
        """実行順序更新"""
        self._execution_order.clear()
        
        # 優先度順に追加
        for priority in sorted(TickPriority, key=lambda p: p.value):
            self._execution_order.extend(self._priority_groups[priority])
    
    def _update_execution_stats(self, device_id: str, execution_time_ns: int) -> None:
        """実行統計更新"""
        stats = self._execution_stats[device_id]
        
        stats.total_ticks += 1
        stats.execution_time_ns += execution_time_ns
        stats.last_tick_time_ns = execution_time_ns
        
        # 平均時間更新
        stats.average_tick_time_ns = stats.execution_time_ns / stats.total_ticks
        
        # 最小・最大時間更新
        if stats.min_tick_time_ns == 0 or execution_time_ns < stats.min_tick_time_ns:
            stats.min_tick_time_ns = execution_time_ns
        
        if execution_time_ns > stats.max_tick_time_ns:
            stats.max_tick_time_ns = execution_time_ns


class TickEngine(ClockListener):
    """Tick駆動実行エンジン
    
    Tick駆動実行モデルの中核実装を提供します。
    サイクル精度の時間管理とデバイス間の同期制御を行います。
    """
    
    def __init__(self, master_frequency_hz: int = 1_000_000):
        """Tick駆動実行エンジンを初期化
        
        Args:
            master_frequency_hz: マスター周波数（Hz）
        """
        self._master_frequency_hz = master_frequency_hz
        
        # コンポーネント
        self._cycle_counter = CycleCounter(master_frequency_hz)
        self._scheduler = TickScheduler()
        
        # 実行制御
        self._running = False
        self._paused = False
        self._step_mode = False
        
        # 同期制御
        self._engine_lock = threading.RLock()
        self._step_event = threading.Event()
        
        # フック
        self._pre_tick_hooks: List[Callable[[int], None]] = []
        self._post_tick_hooks: List[Callable[[int], None]] = []
        self._sync_hooks: List[Callable[[int], None]] = []
        
        # 統計
        self._total_execution_time_ns = 0
        self._sync_interval = 1000  # 1000サイクルごとに同期
    
    def register_tickable(self, tickable: Tickable) -> None:
        """Tickable登録"""
        self._scheduler.register_tickable(tickable)
    
    def unregister_tickable(self, device_id: str) -> None:
        """Tickable登録解除"""
        self._scheduler.unregister_tickable(device_id)
    
    def start(self) -> None:
        """エンジン開始"""
        with self._engine_lock:
            if self._running:
                return
            
            self._running = True
            self._paused = False
            self._cycle_counter.start()
    
    def stop(self) -> None:
        """エンジン停止"""
        with self._engine_lock:
            self._running = False
            self._paused = False
            self._step_event.set()
    
    def pause(self) -> None:
        """エンジン一時停止"""
        with self._engine_lock:
            self._paused = True
    
    def resume(self) -> None:
        """エンジン再開"""
        with self._engine_lock:
            self._paused = False
            self._step_event.set()
    
    def step(self) -> bool:
        """単一ステップ実行
        
        Returns:
            ステップ実行が成功した場合True
        """
        with self._engine_lock:
            if not self._running:
                return False
            
            self._step_mode = True
            self._paused = False
            return self._execute_tick()
    
    def tick(self) -> bool:
        """Tick実行
        
        Returns:
            Tick実行が成功した場合True
        """
        with self._engine_lock:
            if not self._running:
                return False
            
            # 一時停止チェック
            if self._paused:
                if self._step_mode:
                    self._step_mode = False
                else:
                    self._step_event.wait()
                    self._step_event.clear()
            
            return self._execute_tick()
    
    def get_current_cycle(self) -> int:
        """現在のサイクル数取得"""
        return self._cycle_counter.get_current_cycle()
    
    def get_frequency_hz(self) -> float:
        """現在の実行周波数取得"""
        return self._cycle_counter.get_frequency_hz()
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """エンジン統計取得"""
        return {
            'current_cycle': self.get_current_cycle(),
            'frequency_hz': self.get_frequency_hz(),
            'master_frequency_hz': self._master_frequency_hz,
            'running': self._running,
            'paused': self._paused,
            'total_execution_time_ns': self._total_execution_time_ns,
            'cycle_counter_stats': self._cycle_counter.get_stats().__dict__,
            'scheduler_stats': self._scheduler.get_execution_stats()
        }
    
    def reset(self) -> None:
        """エンジンリセット"""
        with self._engine_lock:
            self._cycle_counter.reset()
            self._scheduler.reset_stats()
            self._total_execution_time_ns = 0
    
    def add_pre_tick_hook(self, hook: Callable[[int], None]) -> None:
        """プリTickフック追加"""
        self._pre_tick_hooks.append(hook)
    
    def add_post_tick_hook(self, hook: Callable[[int], None]) -> None:
        """ポストTickフック追加"""
        self._post_tick_hooks.append(hook)
    
    def add_sync_hook(self, hook: Callable[[int], None]) -> None:
        """同期フック追加"""
        self._sync_hooks.append(hook)
    
    def _execute_tick(self) -> bool:
        """Tick実行処理"""
        tick_start_ns = time.time_ns()
        
        try:
            # サイクル進行
            cycle = self._cycle_counter.tick()
            
            # プリTickフック
            for hook in self._pre_tick_hooks:
                hook(cycle)
            
            # フェーズ別実行
            for phase in [TickPhase.PRE_EXECUTE, TickPhase.EXECUTE, TickPhase.POST_EXECUTE]:
                self._scheduler.execute_tick(cycle, phase)
            
            # 同期処理
            if cycle % self._sync_interval == 0:
                self._scheduler.execute_tick(cycle, TickPhase.SYNC)
                for hook in self._sync_hooks:
                    hook(cycle)
                
                # リアルタイム同期
                self._cycle_counter.sync_to_realtime()
            
            # ポストTickフック
            for hook in self._post_tick_hooks:
                hook(cycle)
            
            # 統計更新
            tick_time_ns = time.time_ns() - tick_start_ns
            self._total_execution_time_ns += tick_time_ns
            
            return True
            
        except Exception as e:
            tick_time_ns = time.time_ns() - tick_start_ns
            self._total_execution_time_ns += tick_time_ns
            raise RuntimeError(f"Tick execution failed: {e}")
    
    # ClockListener interface implementation
    def on_tick(self, cycle: int, timestamp_ns: int) -> None:
        """クロックティック時に呼び出される"""
        # TickEngineのtickを呼び出し
        self.tick()
    
    def on_sync(self, cycle: int, timestamp_ns: int) -> None:
        """同期ポイントで呼び出される"""
        # 同期処理は既にexecute_tick内で実行される
        pass
