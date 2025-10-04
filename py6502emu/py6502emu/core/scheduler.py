"""
デバイススケジューラ
PU011: DeviceScheduler

W65C02S エミュレータのデバイススケジューリング管理を提供します。
CPU → ペリフェラル → 割り込み処理の順序制御、デバイス間の実行優先度管理、
タイムスライス分配機能、実行キューの管理を含みます。
"""

from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum, auto
import time
import threading
import heapq
from abc import ABC, abstractmethod

from .types import DeviceType


class SchedulingPolicy(Enum):
    """スケジューリングポリシー"""
    ROUND_ROBIN = auto()      # ラウンドロビン
    PRIORITY_BASED = auto()   # 優先度ベース
    FAIR_SHARE = auto()       # フェアシェア
    REAL_TIME = auto()        # リアルタイム
    CUSTOM = auto()           # カスタム


class ExecutionPhase(Enum):
    """実行フェーズ"""
    CPU_EXECUTION = auto()        # CPU実行
    PERIPHERAL_UPDATE = auto()    # ペリフェラル更新
    INTERRUPT_PROCESSING = auto() # 割り込み処理
    MEMORY_SYNC = auto()          # メモリ同期
    CLEANUP = auto()              # クリーンアップ


class TaskState(Enum):
    """タスク状態"""
    READY = auto()      # 実行可能
    RUNNING = auto()    # 実行中
    WAITING = auto()    # 待機中
    BLOCKED = auto()    # ブロック中
    COMPLETED = auto()  # 完了


@dataclass
class SchedulingConfig:
    """スケジューリング設定"""
    policy: SchedulingPolicy = SchedulingPolicy.PRIORITY_BASED
    time_slice_cycles: int = 1000
    max_execution_time_ns: int = 1_000_000  # 1ms
    enable_preemption: bool = True
    enable_load_balancing: bool = False
    priority_boost_interval: int = 10000
    starvation_threshold_cycles: int = 50000


@dataclass
class ExecutionTask:
    """実行タスク"""
    task_id: str
    device_id: str
    device_type: DeviceType
    phase: ExecutionPhase
    priority: int
    cycle_interval: int = 1
    time_slice_cycles: int = 1000
    
    # 実行統計
    total_executions: int = 0
    total_execution_time_ns: int = 0
    last_execution_cycle: int = 0
    last_execution_time_ns: int = 0
    
    # 状態管理
    state: TaskState = TaskState.READY
    blocked_until_cycle: int = 0
    waiting_for_resource: Optional[str] = None
    
    def __lt__(self, other: 'ExecutionTask') -> bool:
        """優先度比較（heapq用）"""
        return self.priority < other.priority


class ExecutionQueue:
    """実行キュー管理
    
    タスクの実行順序とタイムスライス管理を行います。
    """
    
    def __init__(self, config: SchedulingConfig):
        """実行キューを初期化
        
        Args:
            config: スケジューリング設定
        """
        self.config = config
        
        # キュー管理
        self._ready_queue: List[ExecutionTask] = []
        self._waiting_queue: List[ExecutionTask] = []
        self._blocked_queue: List[ExecutionTask] = []
        self._completed_queue: List[ExecutionTask] = []
        
        # タスク管理
        self._tasks: Dict[str, ExecutionTask] = {}
        self._current_task: Optional[ExecutionTask] = None
        
        # 統計
        self._total_tasks_executed = 0
        self._total_execution_time_ns = 0
        self._queue_stats: Dict[TaskState, int] = {
            state: 0 for state in TaskState
        }
        
        # 同期制御
        self._queue_lock = threading.RLock()
    
    def add_task(self, task: ExecutionTask) -> None:
        """タスク追加
        
        Args:
            task: 追加するタスク
        """
        with self._queue_lock:
            if task.task_id in self._tasks:
                raise ValueError(f"Task already exists: {task.task_id}")
            
            self._tasks[task.task_id] = task
            self._add_to_ready_queue(task)
    
    def remove_task(self, task_id: str) -> None:
        """タスク削除
        
        Args:
            task_id: タスクID
        """
        with self._queue_lock:
            if task_id not in self._tasks:
                return
            
            task = self._tasks[task_id]
            
            # 各キューから削除
            self._remove_from_all_queues(task)
            
            # 現在実行中タスクの場合
            if self._current_task and self._current_task.task_id == task_id:
                self._current_task = None
            
            del self._tasks[task_id]
    
    def get_next_task(self, current_cycle: int) -> Optional[ExecutionTask]:
        """次の実行タスク取得
        
        Args:
            current_cycle: 現在のサイクル数
            
        Returns:
            次に実行するタスク（なければNone）
        """
        with self._queue_lock:
            # ブロック解除チェック
            self._update_blocked_tasks(current_cycle)
            
            # スケジューリングポリシーに基づいてタスク選択
            if self.config.policy == SchedulingPolicy.PRIORITY_BASED:
                return self._get_highest_priority_task()
            elif self.config.policy == SchedulingPolicy.ROUND_ROBIN:
                return self._get_round_robin_task()
            elif self.config.policy == SchedulingPolicy.FAIR_SHARE:
                return self._get_fair_share_task()
            elif self.config.policy == SchedulingPolicy.REAL_TIME:
                return self._get_real_time_task(current_cycle)
            else:
                return self._get_highest_priority_task()
    
    def mark_task_completed(self, task_id: str, execution_time_ns: int) -> None:
        """タスク完了マーク
        
        Args:
            task_id: タスクID
            execution_time_ns: 実行時間（ナノ秒）
        """
        with self._queue_lock:
            if task_id not in self._tasks:
                return
            
            task = self._tasks[task_id]
            
            # 統計更新
            task.total_executions += 1
            task.total_execution_time_ns += execution_time_ns
            task.last_execution_time_ns = execution_time_ns
            
            # 全体統計更新
            self._total_tasks_executed += 1
            self._total_execution_time_ns += execution_time_ns
            
            # 状態更新
            task.state = TaskState.COMPLETED
            self._move_to_completed_queue(task)
            
            # 現在タスククリア
            if self._current_task and self._current_task.task_id == task_id:
                self._current_task = None
    
    def block_task(self, task_id: str, until_cycle: int, resource: Optional[str] = None) -> None:
        """タスクブロック
        
        Args:
            task_id: タスクID
            until_cycle: ブロック解除サイクル
            resource: 待機リソース名
        """
        with self._queue_lock:
            if task_id not in self._tasks:
                return
            
            task = self._tasks[task_id]
            task.state = TaskState.BLOCKED
            task.blocked_until_cycle = until_cycle
            task.waiting_for_resource = resource
            
            self._move_to_blocked_queue(task)
    
    def unblock_task(self, task_id: str) -> None:
        """タスクブロック解除
        
        Args:
            task_id: タスクID
        """
        with self._queue_lock:
            if task_id not in self._tasks:
                return
            
            task = self._tasks[task_id]
            if task.state == TaskState.BLOCKED:
                task.state = TaskState.READY
                task.blocked_until_cycle = 0
                task.waiting_for_resource = None
                
                self._move_to_ready_queue(task)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """キュー統計取得"""
        with self._queue_lock:
            return {
                'ready_queue_size': len(self._ready_queue),
                'waiting_queue_size': len(self._waiting_queue),
                'blocked_queue_size': len(self._blocked_queue),
                'completed_queue_size': len(self._completed_queue),
                'total_tasks': len(self._tasks),
                'total_tasks_executed': self._total_tasks_executed,
                'total_execution_time_ns': self._total_execution_time_ns,
                'average_execution_time_ns': (
                    self._total_execution_time_ns / max(1, self._total_tasks_executed)
                ),
                'current_task': self._current_task.task_id if self._current_task else None
            }
    
    def _add_to_ready_queue(self, task: ExecutionTask) -> None:
        """レディキューに追加"""
        task.state = TaskState.READY
        heapq.heappush(self._ready_queue, task)
        self._queue_stats[TaskState.READY] += 1
    
    def _move_to_ready_queue(self, task: ExecutionTask) -> None:
        """レディキューに移動"""
        self._remove_from_all_queues(task)
        self._add_to_ready_queue(task)
    
    def _move_to_blocked_queue(self, task: ExecutionTask) -> None:
        """ブロックキューに移動"""
        self._remove_from_all_queues(task)
        self._blocked_queue.append(task)
        self._queue_stats[TaskState.BLOCKED] += 1
    
    def _move_to_completed_queue(self, task: ExecutionTask) -> None:
        """完了キューに移動"""
        self._remove_from_all_queues(task)
        self._completed_queue.append(task)
        self._queue_stats[TaskState.COMPLETED] += 1
    
    def _remove_from_all_queues(self, task: ExecutionTask) -> None:
        """全キューから削除"""
        # レディキューから削除
        if task in self._ready_queue:
            self._ready_queue.remove(task)
            heapq.heapify(self._ready_queue)
            self._queue_stats[TaskState.READY] -= 1
        
        # 待機キューから削除
        if task in self._waiting_queue:
            self._waiting_queue.remove(task)
            self._queue_stats[TaskState.WAITING] -= 1
        
        # ブロックキューから削除
        if task in self._blocked_queue:
            self._blocked_queue.remove(task)
            self._queue_stats[TaskState.BLOCKED] -= 1
        
        # 完了キューから削除
        if task in self._completed_queue:
            self._completed_queue.remove(task)
            self._queue_stats[TaskState.COMPLETED] -= 1
    
    def _update_blocked_tasks(self, current_cycle: int) -> None:
        """ブロックタスク更新"""
        unblocked_tasks = []
        
        for task in self._blocked_queue:
            if current_cycle >= task.blocked_until_cycle:
                unblocked_tasks.append(task)
        
        for task in unblocked_tasks:
            self.unblock_task(task.task_id)
    
    def _get_highest_priority_task(self) -> Optional[ExecutionTask]:
        """最高優先度タスク取得"""
        if not self._ready_queue:
            return None
        
        task = heapq.heappop(self._ready_queue)
        self._queue_stats[TaskState.READY] -= 1
        
        task.state = TaskState.RUNNING
        self._current_task = task
        
        return task
    
    def _get_round_robin_task(self) -> Optional[ExecutionTask]:
        """ラウンドロビンタスク取得"""
        if not self._ready_queue:
            return None
        
        # 先頭タスク取得（FIFO）
        task = self._ready_queue.pop(0)
        heapq.heapify(self._ready_queue)
        self._queue_stats[TaskState.READY] -= 1
        
        task.state = TaskState.RUNNING
        self._current_task = task
        
        return task
    
    def _get_fair_share_task(self) -> Optional[ExecutionTask]:
        """フェアシェアタスク取得"""
        if not self._ready_queue:
            return None
        
        # 実行時間が最も少ないタスクを選択
        min_execution_time = float('inf')
        selected_task = None
        
        for task in self._ready_queue:
            if task.total_execution_time_ns < min_execution_time:
                min_execution_time = task.total_execution_time_ns
                selected_task = task
        
        if selected_task:
            self._ready_queue.remove(selected_task)
            heapq.heapify(self._ready_queue)
            self._queue_stats[TaskState.READY] -= 1
            
            selected_task.state = TaskState.RUNNING
            self._current_task = selected_task
        
        return selected_task
    
    def _get_real_time_task(self, current_cycle: int) -> Optional[ExecutionTask]:
        """リアルタイムタスク取得"""
        if not self._ready_queue:
            return None
        
        # デッドラインが最も近いタスクを選択
        earliest_deadline = float('inf')
        selected_task = None
        
        for task in self._ready_queue:
            # 簡単なデッドライン計算（次回実行予定サイクル）
            next_execution_cycle = task.last_execution_cycle + task.cycle_interval
            deadline = next_execution_cycle - current_cycle
            
            if deadline < earliest_deadline:
                earliest_deadline = deadline
                selected_task = task
        
        if selected_task:
            self._ready_queue.remove(selected_task)
            heapq.heapify(self._ready_queue)
            self._queue_stats[TaskState.READY] -= 1
            
            selected_task.state = TaskState.RUNNING
            self._current_task = selected_task
        
        return selected_task


class DeviceScheduler:
    """デバイススケジューラ
    
    W65C02Sエミュレータのデバイススケジューリング管理を行います。
    CPU → ペリフェラル → 割り込み処理の順序制御と実行優先度管理を提供します。
    """
    
    def __init__(self, config: Optional[SchedulingConfig] = None):
        """デバイススケジューラを初期化
        
        Args:
            config: スケジューリング設定（省略時はデフォルト設定）
        """
        self.config = config or SchedulingConfig()
        
        # 実行キュー
        self._execution_queue = ExecutionQueue(self.config)
        
        # フェーズ別実行順序
        self._phase_order = [
            ExecutionPhase.CPU_EXECUTION,
            ExecutionPhase.PERIPHERAL_UPDATE,
            ExecutionPhase.INTERRUPT_PROCESSING,
            ExecutionPhase.MEMORY_SYNC,
            ExecutionPhase.CLEANUP
        ]
        
        # デバイス登録
        self._registered_devices: Dict[str, Any] = {}
        self._device_tasks: Dict[str, List[str]] = {}  # device_id -> task_ids
        
        # 実行制御
        self._current_cycle = 0
        self._current_phase = ExecutionPhase.CPU_EXECUTION
        self._phase_index = 0
        
        # 統計
        self._execution_stats: Dict[ExecutionPhase, Dict[str, Any]] = {
            phase: {
                'total_executions': 0,
                'total_time_ns': 0,
                'average_time_ns': 0.0,
                'last_execution_time_ns': 0
            }
            for phase in ExecutionPhase
        }
        
        # フック
        self._pre_phase_hooks: Dict[ExecutionPhase, List[Callable]] = {
            phase: [] for phase in ExecutionPhase
        }
        self._post_phase_hooks: Dict[ExecutionPhase, List[Callable]] = {
            phase: [] for phase in ExecutionPhase
        }
        
        # 同期制御
        self._scheduler_lock = threading.RLock()
    
    def register_device(self, device_id: str, device: Any, device_type: DeviceType) -> None:
        """デバイス登録
        
        Args:
            device_id: デバイスID
            device: デバイスオブジェクト
            device_type: デバイス種別
        """
        with self._scheduler_lock:
            if device_id in self._registered_devices:
                raise ValueError(f"Device already registered: {device_id}")
            
            self._registered_devices[device_id] = device
            self._device_tasks[device_id] = []
            
            # デバイス種別に応じたタスク作成
            self._create_device_tasks(device_id, device_type)
    
    def unregister_device(self, device_id: str) -> None:
        """デバイス登録解除
        
        Args:
            device_id: デバイスID
        """
        with self._scheduler_lock:
            if device_id not in self._registered_devices:
                return
            
            # デバイスのタスクを全て削除
            task_ids = self._device_tasks.get(device_id, [])
            for task_id in task_ids:
                self._execution_queue.remove_task(task_id)
            
            del self._registered_devices[device_id]
            del self._device_tasks[device_id]
    
    def execute_cycle(self, cycle: int) -> Dict[str, Any]:
        """サイクル実行
        
        Args:
            cycle: サイクル数
            
        Returns:
            実行結果統計
        """
        with self._scheduler_lock:
            self._current_cycle = cycle
            execution_results = {}
            
            # 全フェーズ実行
            for phase in self._phase_order:
                self._current_phase = phase
                
                # プリフェーズフック
                for hook in self._pre_phase_hooks[phase]:
                    hook(cycle, phase)
                
                # フェーズ実行
                phase_result = self._execute_phase(cycle, phase)
                execution_results[phase.name] = phase_result
                
                # ポストフェーズフック
                for hook in self._post_phase_hooks[phase]:
                    hook(cycle, phase)
            
            return execution_results
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """スケジューラ統計取得"""
        with self._scheduler_lock:
            return {
                'current_cycle': self._current_cycle,
                'current_phase': self._current_phase.name,
                'registered_devices': len(self._registered_devices),
                'total_tasks': len(self._execution_queue._tasks),
                'queue_stats': self._execution_queue.get_queue_stats(),
                'execution_stats': self._execution_stats,
                'config': {
                    'policy': self.config.policy.name,
                    'time_slice_cycles': self.config.time_slice_cycles,
                    'enable_preemption': self.config.enable_preemption
                }
            }
    
    def add_pre_phase_hook(self, phase: ExecutionPhase, hook: Callable) -> None:
        """プリフェーズフック追加"""
        self._pre_phase_hooks[phase].append(hook)
    
    def add_post_phase_hook(self, phase: ExecutionPhase, hook: Callable) -> None:
        """ポストフェーズフック追加"""
        self._post_phase_hooks[phase].append(hook)
    
    def set_device_priority(self, device_id: str, priority: int) -> None:
        """デバイス優先度設定
        
        Args:
            device_id: デバイスID
            priority: 優先度（小さいほど高優先度）
        """
        with self._scheduler_lock:
            task_ids = self._device_tasks.get(device_id, [])
            for task_id in task_ids:
                if task_id in self._execution_queue._tasks:
                    task = self._execution_queue._tasks[task_id]
                    task.priority = priority
    
    def block_device(self, device_id: str, until_cycle: int) -> None:
        """デバイスブロック
        
        Args:
            device_id: デバイスID
            until_cycle: ブロック解除サイクル
        """
        with self._scheduler_lock:
            task_ids = self._device_tasks.get(device_id, [])
            for task_id in task_ids:
                self._execution_queue.block_task(task_id, until_cycle)
    
    def unblock_device(self, device_id: str) -> None:
        """デバイスブロック解除
        
        Args:
            device_id: デバイスID
        """
        with self._scheduler_lock:
            task_ids = self._device_tasks.get(device_id, [])
            for task_id in task_ids:
                self._execution_queue.unblock_task(task_id)
    
    def _create_device_tasks(self, device_id: str, device_type: DeviceType) -> None:
        """デバイスタスク作成"""
        # デバイス種別に応じた優先度とフェーズ設定
        if device_type == DeviceType.CPU:
            priority = 1  # 最高優先度
            phases = [ExecutionPhase.CPU_EXECUTION]
        elif device_type == DeviceType.MEMORY:
            priority = 2
            phases = [ExecutionPhase.MEMORY_SYNC]
        elif device_type == DeviceType.IO:
            priority = 3
            phases = [ExecutionPhase.PERIPHERAL_UPDATE]
        else:
            priority = 4
            phases = [ExecutionPhase.PERIPHERAL_UPDATE]
        
        # 各フェーズ用のタスク作成
        for phase in phases:
            task_id = f"{device_id}_{phase.name}"
            task = ExecutionTask(
                task_id=task_id,
                device_id=device_id,
                device_type=device_type,
                phase=phase,
                priority=priority,
                time_slice_cycles=self.config.time_slice_cycles
            )
            
            self._execution_queue.add_task(task)
            self._device_tasks[device_id].append(task_id)
    
    def _execute_phase(self, cycle: int, phase: ExecutionPhase) -> Dict[str, Any]:
        """フェーズ実行"""
        phase_start_time = time.time_ns()
        executed_tasks = []
        total_execution_time = 0
        
        # フェーズ内のタスクを実行
        while True:
            task = self._execution_queue.get_next_task(cycle)
            if task is None or task.phase != phase:
                break
            
            # タスク実行
            task_start_time = time.time_ns()
            
            try:
                device = self._registered_devices[task.device_id]
                if hasattr(device, 'tick'):
                    device.tick(cycle)
                
                task_execution_time = time.time_ns() - task_start_time
                
                # タスク完了マーク
                self._execution_queue.mark_task_completed(task.task_id, task_execution_time)
                
                executed_tasks.append(task.task_id)
                total_execution_time += task_execution_time
                
            except Exception as e:
                task_execution_time = time.time_ns() - task_start_time
                total_execution_time += task_execution_time
                
                # エラー処理（ログ出力等）
                print(f"Task execution error [{task.task_id}]: {e}")
        
        # フェーズ統計更新
        phase_time = time.time_ns() - phase_start_time
        stats = self._execution_stats[phase]
        stats['total_executions'] += len(executed_tasks)
        stats['total_time_ns'] += phase_time
        stats['last_execution_time_ns'] = phase_time
        
        if stats['total_executions'] > 0:
            stats['average_time_ns'] = stats['total_time_ns'] / stats['total_executions']
        
        return {
            'executed_tasks': executed_tasks,
            'execution_count': len(executed_tasks),
            'total_execution_time_ns': total_execution_time,
            'phase_time_ns': phase_time
        }
