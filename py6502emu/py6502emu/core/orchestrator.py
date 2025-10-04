"""
システムオーケストレータ
PU012: SystemOrchestrator

W65C02S エミュレータのシステム全体制御とメインエミュレーションループを提供します。
システム初期化・リセット・終了処理、デバイス登録・管理機能を含みます。
"""

from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum, auto
import threading
import time
import logging
from abc import ABC, abstractmethod

from .clock import SystemClock, ClockConfiguration, ClockListener
from .device import Device, DeviceConfig
from .interrupt_controller import InterruptController
from .types import DeviceType, SystemState


class SystemStatus(Enum):
    """システム状態"""
    UNINITIALIZED = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPING = auto()
    STOPPED = auto()
    ERROR = auto()


class ExecutionMode(Enum):
    """実行モード"""
    CONTINUOUS = auto()    # 連続実行
    STEP = auto()         # ステップ実行
    BREAKPOINT = auto()   # ブレークポイント実行
    TRACE = auto()        # トレース実行


@dataclass
class SystemConfiguration:
    """システム設定"""
    clock_config: ClockConfiguration = field(default_factory=ClockConfiguration)
    execution_mode: ExecutionMode = ExecutionMode.CONTINUOUS
    max_cycles_per_frame: int = 10000
    enable_debugging: bool = False
    enable_profiling: bool = False
    auto_start: bool = False


@dataclass
class ExecutionStats:
    """実行統計"""
    total_cycles: int = 0
    execution_time_ms: float = 0.0
    cycles_per_second: float = 0.0
    frame_count: int = 0
    average_frame_time_ms: float = 0.0
    device_execution_times: Dict[str, float] = field(default_factory=dict)


class SystemComponent(ABC):
    """システムコンポーネント基底クラス"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """コンポーネント初期化"""
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """コンポーネントリセット"""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """コンポーネント終了処理"""
        pass
    
    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """コンポーネント状態取得"""
        pass


class EmulationLoop(ClockListener):
    """メインエミュレーションループ
    
    システムクロックに同期してデバイスの実行を制御します。
    """
    
    def __init__(self, orchestrator: 'SystemOrchestrator'):
        """エミュレーションループを初期化
        
        Args:
            orchestrator: システムオーケストレータ
        """
        self._orchestrator = orchestrator
        self._running = False
        self._paused = False
        self._step_mode = False
        self._breakpoints: Set[int] = set()
        self._current_breakpoint: Optional[int] = None
        
        # 統計
        self._stats = ExecutionStats()
        self._frame_start_time = 0.0
        self._last_stats_update = 0.0
        
        # フック
        self._pre_cycle_hooks: List[Callable[[int], None]] = []
        self._post_cycle_hooks: List[Callable[[int], None]] = []
        self._breakpoint_hooks: List[Callable[[int], None]] = []
    
    def start(self) -> None:
        """エミュレーションループ開始"""
        self._running = True
        self._paused = False
        self._frame_start_time = time.time()
        self._last_stats_update = self._frame_start_time
    
    def stop(self) -> None:
        """エミュレーションループ停止"""
        self._running = False
        self._paused = False
    
    def pause(self) -> None:
        """エミュレーションループ一時停止"""
        self._paused = True
    
    def resume(self) -> None:
        """エミュレーションループ再開"""
        self._paused = False
    
    def step(self) -> None:
        """単一ステップ実行"""
        self._step_mode = True
        self._paused = False
    
    def add_breakpoint(self, cycle: int) -> None:
        """ブレークポイント追加"""
        self._breakpoints.add(cycle)
    
    def remove_breakpoint(self, cycle: int) -> None:
        """ブレークポイント削除"""
        self._breakpoints.discard(cycle)
    
    def clear_breakpoints(self) -> None:
        """全ブレークポイントクリア"""
        self._breakpoints.clear()
    
    def on_tick(self, cycle: int, timestamp_ns: int) -> None:
        """クロックティック処理"""
        if not self._running or self._paused:
            return
        
        # ブレークポイントチェック
        if cycle in self._breakpoints:
            self._current_breakpoint = cycle
            self._paused = True
            for hook in self._breakpoint_hooks:
                hook(cycle)
            return
        
        # プリサイクルフック
        for hook in self._pre_cycle_hooks:
            hook(cycle)
        
        # デバイス実行
        self._execute_devices(cycle, timestamp_ns)
        
        # ポストサイクルフック
        for hook in self._post_cycle_hooks:
            hook(cycle)
        
        # ステップモード処理
        if self._step_mode:
            self._step_mode = False
            self._paused = True
        
        # 統計更新
        self._update_stats(cycle)
    
    def on_sync(self, cycle: int, timestamp_ns: int) -> None:
        """同期処理"""
        # フレーム統計更新
        current_time = time.time()
        frame_time = current_time - self._frame_start_time
        
        self._stats.frame_count += 1
        self._stats.average_frame_time_ms = (
            self._stats.average_frame_time_ms * (self._stats.frame_count - 1) + 
            frame_time * 1000
        ) / self._stats.frame_count
        
        self._frame_start_time = current_time
    
    def get_stats(self) -> ExecutionStats:
        """実行統計取得"""
        return self._stats
    
    def reset_stats(self) -> None:
        """統計リセット"""
        self._stats = ExecutionStats()
        self._frame_start_time = time.time()
        self._last_stats_update = self._frame_start_time
    
    def add_pre_cycle_hook(self, hook: Callable[[int], None]) -> None:
        """プリサイクルフック追加"""
        self._pre_cycle_hooks.append(hook)
    
    def add_post_cycle_hook(self, hook: Callable[[int], None]) -> None:
        """ポストサイクルフック追加"""
        self._post_cycle_hooks.append(hook)
    
    def add_breakpoint_hook(self, hook: Callable[[int], None]) -> None:
        """ブレークポイントフック追加"""
        self._breakpoint_hooks.append(hook)
    
    def _execute_devices(self, cycle: int, timestamp_ns: int) -> None:
        """デバイス実行処理"""
        device_start_time = time.time()
        
        # 登録されたデバイスを実行
        for device_id, device in self._orchestrator._devices.items():
            if device.is_enabled():
                try:
                    device_exec_start = time.time()
                    device.tick(cycle)
                    device_exec_time = (time.time() - device_exec_start) * 1000
                    
                    # デバイス実行時間記録
                    if device_id not in self._stats.device_execution_times:
                        self._stats.device_execution_times[device_id] = 0.0
                    self._stats.device_execution_times[device_id] += device_exec_time
                    
                except Exception as e:
                    self._orchestrator._logger.error(
                        f"Device execution error [{device_id}]: {e}"
                    )
    
    def _update_stats(self, cycle: int) -> None:
        """統計更新"""
        current_time = time.time()
        
        self._stats.total_cycles = cycle
        
        # 1秒ごとに統計更新
        if current_time - self._last_stats_update >= 1.0:
            elapsed_time = current_time - self._last_stats_update
            cycles_in_period = cycle - (self._stats.total_cycles - cycle)
            
            self._stats.cycles_per_second = cycles_in_period / elapsed_time
            self._stats.execution_time_ms = elapsed_time * 1000
            
            self._last_stats_update = current_time


class SystemController:
    """システム制御機能
    
    システムの初期化、リセット、終了処理を管理します。
    """
    
    def __init__(self, orchestrator: 'SystemOrchestrator'):
        """システム制御を初期化
        
        Args:
            orchestrator: システムオーケストレータ
        """
        self._orchestrator = orchestrator
        self._initialization_order: List[str] = []
        self._shutdown_hooks: List[Callable[[], None]] = []
        self._reset_hooks: List[Callable[[], None]] = []
    
    def initialize_system(self) -> bool:
        """システム初期化
        
        Returns:
            初期化が成功した場合True
        """
        try:
            self._orchestrator._status = SystemStatus.INITIALIZING
            self._orchestrator._logger.info("System initialization started")
            
            # コンポーネント初期化
            for component in self._orchestrator._components.values():
                if not component.initialize():
                    self._orchestrator._logger.error(
                        f"Component initialization failed: {component}"
                    )
                    return False
            
            # デバイス初期化
            for device_id in self._initialization_order:
                if device_id in self._orchestrator._devices:
                    device = self._orchestrator._devices[device_id]
                    if not device.initialize():
                        self._orchestrator._logger.error(
                            f"Device initialization failed: {device_id}"
                        )
                        return False
            
            # システムクロック初期化
            if self._orchestrator._system_clock:
                self._orchestrator._system_clock.start()
            
            self._orchestrator._status = SystemStatus.READY
            self._orchestrator._logger.info("System initialization completed")
            return True
            
        except Exception as e:
            self._orchestrator._logger.error(f"System initialization error: {e}")
            self._orchestrator._status = SystemStatus.ERROR
            return False
    
    def reset_system(self) -> None:
        """システムリセット"""
        try:
            self._orchestrator._logger.info("System reset started")
            
            # システムクロック停止
            if self._orchestrator._system_clock:
                self._orchestrator._system_clock.stop()
            
            # デバイスリセット
            for device in self._orchestrator._devices.values():
                device.reset()
            
            # コンポーネントリセット
            for component in self._orchestrator._components.values():
                component.reset()
            
            # 割り込みコントローラリセット
            if self._orchestrator._interrupt_controller:
                self._orchestrator._interrupt_controller.force_clear_all_interrupts()
            
            # リセットフック実行
            for hook in self._reset_hooks:
                hook()
            
            # システムクロック再開
            if self._orchestrator._system_clock:
                self._orchestrator._system_clock.reset()
                self._orchestrator._system_clock.start()
            
            self._orchestrator._logger.info("System reset completed")
            
        except Exception as e:
            self._orchestrator._logger.error(f"System reset error: {e}")
    
    def shutdown_system(self) -> None:
        """システム終了処理"""
        try:
            self._orchestrator._status = SystemStatus.STOPPING
            self._orchestrator._logger.info("System shutdown started")
            
            # エミュレーションループ停止
            if self._orchestrator._emulation_loop:
                self._orchestrator._emulation_loop.stop()
            
            # システムクロック停止
            if self._orchestrator._system_clock:
                self._orchestrator._system_clock.stop()
            
            # 終了フック実行
            for hook in self._shutdown_hooks:
                hook()
            
            # デバイス終了処理
            for device in self._orchestrator._devices.values():
                device.shutdown()
            
            # コンポーネント終了処理
            for component in self._orchestrator._components.values():
                component.shutdown()
            
            self._orchestrator._status = SystemStatus.STOPPED
            self._orchestrator._logger.info("System shutdown completed")
            
        except Exception as e:
            self._orchestrator._logger.error(f"System shutdown error: {e}")
            self._orchestrator._status = SystemStatus.ERROR
    
    def set_initialization_order(self, device_ids: List[str]) -> None:
        """初期化順序設定"""
        self._initialization_order = device_ids.copy()
    
    def add_shutdown_hook(self, hook: Callable[[], None]) -> None:
        """終了フック追加"""
        self._shutdown_hooks.append(hook)
    
    def add_reset_hook(self, hook: Callable[[], None]) -> None:
        """リセットフック追加"""
        self._reset_hooks.append(hook)


class SystemOrchestrator:
    """システムオーケストレータ
    
    W65C02Sエミュレータのシステム全体を統括し、
    各コンポーネントの協調動作を制御します。
    """
    
    def __init__(self, config: Optional[SystemConfiguration] = None):
        """システムオーケストレータを初期化
        
        Args:
            config: システム設定（省略時はデフォルト設定）
        """
        self.config = config or SystemConfiguration()
        
        # 状態管理
        self._status = SystemStatus.UNINITIALIZED
        self._logger = logging.getLogger(__name__)
        
        # コアコンポーネント
        self._system_clock: Optional[SystemClock] = None
        self._interrupt_controller: Optional[InterruptController] = None
        self._emulation_loop: Optional[EmulationLoop] = None
        self._system_controller: Optional[SystemController] = None
        
        # デバイス・コンポーネント管理
        self._devices: Dict[str, Device] = {}
        self._components: Dict[str, SystemComponent] = {}
        
        # 同期制御
        self._execution_lock = threading.RLock()
        
        # 初期化（システムクロックが設定された後に実行）
        # self._initialize_core_components()
    
    def register_device(self, device: Device) -> None:
        """デバイス登録
        
        Args:
            device: 登録するデバイス
        """
        if device.get_device_id() in self._devices:
            raise ValueError(f"Device already registered: {device.get_device_id()}")
        
        self._devices[device.get_device_id()] = device
        self._logger.info(f"Device registered: {device.get_device_id()}")
    
    def unregister_device(self, device_id: str) -> None:
        """デバイス登録解除
        
        Args:
            device_id: デバイスID
        """
        if device_id in self._devices:
            device = self._devices[device_id]
            device.shutdown()
            del self._devices[device_id]
            self._logger.info(f"Device unregistered: {device_id}")
    
    def get_device(self, device_id: str) -> Optional[Device]:
        """デバイス取得
        
        Args:
            device_id: デバイスID
            
        Returns:
            デバイス（存在しない場合はNone）
        """
        return self._devices.get(device_id)
    
    def register_component(self, name: str, component: SystemComponent) -> None:
        """システムコンポーネント登録
        
        Args:
            name: コンポーネント名
            component: コンポーネント
        """
        if name in self._components:
            raise ValueError(f"Component already registered: {name}")
        
        self._components[name] = component
        self._logger.info(f"Component registered: {name}")
    
    def get_component(self, name: str) -> Optional[SystemComponent]:
        """システムコンポーネント取得
        
        Args:
            name: コンポーネント名
            
        Returns:
            コンポーネント（存在しない場合はNone）
        """
        return self._components.get(name)
    
    def initialize(self) -> bool:
        """システム初期化
        
        Returns:
            初期化が成功した場合True
        """
        with self._execution_lock:
            if self._system_controller:
                return self._system_controller.initialize_system()
            return False
    
    def start(self) -> bool:
        """システム開始
        
        Returns:
            開始が成功した場合True
        """
        with self._execution_lock:
            if self._status != SystemStatus.READY:
                if not self.initialize():
                    return False
            
            try:
                self._status = SystemStatus.RUNNING
                
                # エミュレーションループ開始
                if self._emulation_loop:
                    self._emulation_loop.start()
                
                self._logger.info("System started")
                return True
                
            except Exception as e:
                self._logger.error(f"System start error: {e}")
                self._status = SystemStatus.ERROR
                return False
    
    def stop(self) -> None:
        """システム停止"""
        with self._execution_lock:
            if self._system_controller:
                self._system_controller.shutdown_system()
    
    def pause(self) -> None:
        """システム一時停止"""
        with self._execution_lock:
            if self._status == SystemStatus.RUNNING:
                self._status = SystemStatus.PAUSED
                if self._emulation_loop:
                    self._emulation_loop.pause()
                if self._system_clock:
                    self._system_clock.pause()
    
    def resume(self) -> None:
        """システム再開"""
        with self._execution_lock:
            if self._status == SystemStatus.PAUSED:
                self._status = SystemStatus.RUNNING
                if self._emulation_loop:
                    self._emulation_loop.resume()
                if self._system_clock:
                    self._system_clock.resume()
    
    def reset(self) -> None:
        """システムリセット"""
        with self._execution_lock:
            if self._system_controller:
                self._system_controller.reset_system()
    
    def step(self) -> bool:
        """単一ステップ実行
        
        Returns:
            ステップ実行が成功した場合True
        """
        with self._execution_lock:
            if self._status not in [SystemStatus.RUNNING, SystemStatus.PAUSED]:
                return False
            
            if self._emulation_loop:
                self._emulation_loop.step()
                return True
            
            return False
    
    def get_status(self) -> SystemStatus:
        """システム状態取得"""
        return self._status
    
    def get_system_state(self) -> SystemState:
        """システム状態情報取得"""
        devices_state = {}
        for device_id, device in self._devices.items():
            devices_state[device_id] = device.get_state()
        
        return {
            'devices': devices_state,
            'system_time': self._system_clock.get_current_cycle() if self._system_clock else 0,
            'master_clock': self.config.clock_config.master_frequency_hz
        }
    
    def get_execution_stats(self) -> Optional[ExecutionStats]:
        """実行統計取得"""
        if self._emulation_loop:
            return self._emulation_loop.get_stats()
        return None
    
    def get_system_clock(self) -> Optional[SystemClock]:
        """システムクロック取得"""
        return self._system_clock
    
    def set_system_clock(self, system_clock: SystemClock) -> None:
        """システムクロック設定"""
        self._system_clock = system_clock
        # システムクロックが設定された後にコアコンポーネントを初期化
        self._initialize_core_components()
    
    def get_interrupt_controller(self) -> Optional[InterruptController]:
        """割り込みコントローラ取得"""
        return self._interrupt_controller
    
    def _initialize_core_components(self) -> None:
        """コアコンポーネント初期化"""
        # システムクロック（既に外部で作成済みの場合は使用、そうでなければ作成）
        if not self._system_clock:
            self._system_clock = SystemClock(self.config.clock_config)
        
        # 割り込みコントローラ
        self._interrupt_controller = InterruptController()
        
        # エミュレーションループ
        self._emulation_loop = EmulationLoop(self)
        self._system_clock.add_listener(self._emulation_loop)
        
        # システム制御
        self._system_controller = SystemController(self)
        
        self._logger.info("Core components initialized")
