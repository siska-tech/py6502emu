"""
システム統合インターフェース

W65C02S エミュレータの各コンポーネント間の統合を管理します。
システム全体の初期化シーケンス、コンポーネント間通信の仲介、システム状態の一元管理を含みます。
"""

from typing import Dict, List, Optional, Any, Callable, Type, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum, auto
import threading
import logging
from abc import ABC, abstractmethod

from .types import DeviceType, SystemState
from .device import Device, DeviceConfig
from .clock import SystemClock, ClockConfiguration
from .interrupt_controller import InterruptController
from .orchestrator import SystemOrchestrator, SystemConfiguration
from .tick_engine import TickEngine, Tickable


T = TypeVar('T')


class IntegrationPhase(Enum):
    """統合フェーズ"""
    REGISTRATION = auto()    # コンポーネント登録
    INITIALIZATION = auto()  # 初期化
    CONFIGURATION = auto()   # 設定
    STARTUP = auto()         # 起動
    RUNNING = auto()         # 実行中
    SHUTDOWN = auto()        # 終了


class ComponentState(Enum):
    """コンポーネント状態"""
    UNREGISTERED = auto()
    REGISTERED = auto()
    INITIALIZED = auto()
    CONFIGURED = auto()
    STARTED = auto()
    STOPPED = auto()
    ERROR = auto()


@dataclass
class ComponentInfo:
    """コンポーネント情報"""
    component_id: str
    component_type: str
    instance: Any
    state: ComponentState = ComponentState.UNREGISTERED
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    initialization_order: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ComponentRegistry:
    """コンポーネント登録管理
    
    システム内の全コンポーネントの登録と依存関係を管理します。
    """
    
    def __init__(self):
        """コンポーネント登録管理を初期化"""
        self._components: Dict[str, ComponentInfo] = {}
        self._type_registry: Dict[str, List[str]] = {}
        self._dependency_graph: Dict[str, List[str]] = {}
        self._initialization_order: List[str] = []
        
        # 同期制御
        self._registry_lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
    
    def register_component(
        self, 
        component_id: str, 
        component_type: str, 
        instance: Any,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """コンポーネント登録
        
        Args:
            component_id: コンポーネントID
            component_type: コンポーネント種別
            instance: コンポーネントインスタンス
            dependencies: 依存コンポーネントIDリスト
            metadata: メタデータ
        """
        with self._registry_lock:
            if component_id in self._components:
                raise ValueError(f"Component already registered: {component_id}")
            
            dependencies = dependencies or []
            metadata = metadata or {}
            
            # 依存関係の検証（存在しない依存先は警告して除外）
            valid_dependencies = []
            for dep_id in dependencies:
                if dep_id in self._components:
                    valid_dependencies.append(dep_id)
                else:
                    self._logger.warning(f"Dependency '{dep_id}' not found for component '{component_id}', ignoring")
            
            # コンポーネント情報作成
            component_info = ComponentInfo(
                component_id=component_id,
                component_type=component_type,
                instance=instance,
                state=ComponentState.REGISTERED,
                dependencies=valid_dependencies,
                metadata=metadata.copy()
            )
            
            # 登録
            self._components[component_id] = component_info
            
            # 種別別登録
            if component_type not in self._type_registry:
                self._type_registry[component_type] = []
            self._type_registry[component_type].append(component_id)
            
            # 依存関係更新
            self._update_dependency_graph(component_id, valid_dependencies)
            
            # 初期化順序更新
            self._update_initialization_order()
            
            self._logger.info(f"Component registered: {component_id} ({component_type})")
    
    def unregister_component(self, component_id: str) -> None:
        """コンポーネント登録解除
        
        Args:
            component_id: コンポーネントID
        """
        with self._registry_lock:
            if component_id not in self._components:
                return
            
            component_info = self._components[component_id]
            
            # 依存関係チェック
            if component_info.dependents:
                raise ValueError(
                    f"Cannot unregister component with dependents: {component_info.dependents}"
                )
            
            # 種別別登録から削除
            component_type = component_info.component_type
            if component_type in self._type_registry:
                if component_id in self._type_registry[component_type]:
                    self._type_registry[component_type].remove(component_id)
                if not self._type_registry[component_type]:
                    del self._type_registry[component_type]
            
            # 依存関係から削除
            self._remove_from_dependency_graph(component_id)
            
            # 登録解除
            del self._components[component_id]
            
            # 初期化順序更新
            self._update_initialization_order()
            
            self._logger.info(f"Component unregistered: {component_id}")
    
    def get_component(self, component_id: str) -> Optional[ComponentInfo]:
        """コンポーネント情報取得
        
        Args:
            component_id: コンポーネントID
            
        Returns:
            コンポーネント情報（存在しない場合はNone）
        """
        return self._components.get(component_id)
    
    def get_component_instance(self, component_id: str, component_type: Type[T] = None) -> Optional[T]:
        """コンポーネントインスタンス取得
        
        Args:
            component_id: コンポーネントID
            component_type: 期待する型（型チェック用）
            
        Returns:
            コンポーネントインスタンス（存在しない場合はNone）
        """
        component_info = self.get_component(component_id)
        if component_info is None:
            return None
        
        instance = component_info.instance
        if component_type is not None and not isinstance(instance, component_type):
            return None
        
        return instance
    
    def get_components_by_type(self, component_type: str) -> List[ComponentInfo]:
        """種別別コンポーネント取得
        
        Args:
            component_type: コンポーネント種別
            
        Returns:
            該当するコンポーネント情報のリスト
        """
        component_ids = self._type_registry.get(component_type, [])
        return [self._components[component_id] for component_id in component_ids]
    
    def get_initialization_order(self) -> List[str]:
        """初期化順序取得"""
        return self._initialization_order.copy()
    
    def update_component_state(self, component_id: str, state: ComponentState) -> None:
        """コンポーネント状態更新
        
        Args:
            component_id: コンポーネントID
            state: 新しい状態
        """
        with self._registry_lock:
            if component_id in self._components:
                self._components[component_id].state = state
    
    def get_registry_state(self) -> Dict[str, Any]:
        """レジストリ状態取得"""
        return {
            'component_count': len(self._components),
            'type_count': len(self._type_registry),
            'components': {
                component_id: {
                    'type': info.component_type,
                    'state': info.state.name,
                    'dependencies': info.dependencies,
                    'dependents': info.dependents
                }
                for component_id, info in self._components.items()
            },
            'initialization_order': self._initialization_order
        }
    
    def _update_dependency_graph(self, component_id: str, dependencies: List[str]) -> None:
        """依存関係グラフ更新"""
        # 依存関係設定
        self._dependency_graph[component_id] = dependencies.copy()
        
        # 逆依存関係更新（依存先が存在する場合のみ）
        for dependency_id in dependencies:
            if dependency_id in self._components:
                if component_id not in self._components[dependency_id].dependents:
                    self._components[dependency_id].dependents.append(component_id)
    
    def _remove_from_dependency_graph(self, component_id: str) -> None:
        """依存関係グラフから削除"""
        # 依存関係削除
        if component_id in self._dependency_graph:
            dependencies = self._dependency_graph[component_id]
            for dependency_id in dependencies:
                if dependency_id in self._components:
                    if component_id in self._components[dependency_id].dependents:
                        self._components[dependency_id].dependents.remove(component_id)
            del self._dependency_graph[component_id]
    
    def _update_initialization_order(self) -> None:
        """初期化順序更新（トポロジカルソート）"""
        # Kahn's algorithm for topological sorting
        in_degree = {component_id: 0 for component_id in self._components}
        
        # 入次数計算
        for component_id, dependencies in self._dependency_graph.items():
            for dependency_id in dependencies:
                if dependency_id in in_degree:
                    in_degree[component_id] += 1
        
        # デバッグ情報
        self._logger.debug(f"In-degree: {in_degree}")
        self._logger.debug(f"Dependency graph: {self._dependency_graph}")
        
        # 入次数0のノードをキューに追加
        queue = [component_id for component_id, degree in in_degree.items() if degree == 0]
        result = []
        
        self._logger.debug(f"Initial queue: {queue}")
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            # 現在のコンポーネントに依存しているコンポーネントの入次数を減らす
            for component_id, dependencies in self._dependency_graph.items():
                if current in dependencies:
                    in_degree[component_id] -= 1
                    if in_degree[component_id] == 0:
                        queue.append(component_id)
            
            self._logger.debug(f"Processed {current}, queue: {queue}, result: {result}")
        
        # 循環依存チェック
        if len(result) != len(self._components):
            remaining = set(self._components.keys()) - set(result)
            self._logger.error(f"Circular dependency detected: {remaining}")
            self._logger.error(f"Components: {list(self._components.keys())}")
            self._logger.error(f"Result: {result}")
            self._logger.error(f"Dependency graph: {self._dependency_graph}")
            raise ValueError(f"Circular dependency detected: {remaining}")
        
        self._initialization_order = result


class SystemBridge:
    """システム間ブリッジ
    
    異なるコンポーネント間の通信を仲介し、
    システム全体の協調動作を支援します。
    """
    
    def __init__(self, registry: ComponentRegistry):
        """システムブリッジを初期化
        
        Args:
            registry: コンポーネントレジストリ
        """
        self._registry = registry
        self._message_handlers: Dict[str, List[Callable]] = {}
        self._event_listeners: Dict[str, List[Callable]] = {}
        
        # 同期制御
        self._bridge_lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
    
    def register_message_handler(self, message_type: str, handler: Callable) -> None:
        """メッセージハンドラ登録
        
        Args:
            message_type: メッセージ種別
            handler: ハンドラ関数
        """
        with self._bridge_lock:
            if message_type not in self._message_handlers:
                self._message_handlers[message_type] = []
            self._message_handlers[message_type].append(handler)
    
    def unregister_message_handler(self, message_type: str, handler: Callable) -> None:
        """メッセージハンドラ登録解除
        
        Args:
            message_type: メッセージ種別
            handler: ハンドラ関数
        """
        with self._bridge_lock:
            if message_type in self._message_handlers:
                if handler in self._message_handlers[message_type]:
                    self._message_handlers[message_type].remove(handler)
    
    def send_message(self, message_type: str, sender_id: str, data: Any = None) -> List[Any]:
        """メッセージ送信
        
        Args:
            message_type: メッセージ種別
            sender_id: 送信者ID
            data: メッセージデータ
            
        Returns:
            ハンドラからの戻り値リスト
        """
        results = []
        
        with self._bridge_lock:
            handlers = self._message_handlers.get(message_type, [])
            
            for handler in handlers:
                try:
                    result = handler(sender_id, data)
                    results.append(result)
                except Exception as e:
                    self._logger.error(
                        f"Message handler error [{message_type}]: {e}"
                    )
        
        return results
    
    def register_event_listener(self, event_type: str, listener: Callable) -> None:
        """イベントリスナー登録
        
        Args:
            event_type: イベント種別
            listener: リスナー関数
        """
        with self._bridge_lock:
            if event_type not in self._event_listeners:
                self._event_listeners[event_type] = []
            self._event_listeners[event_type].append(listener)
    
    def unregister_event_listener(self, event_type: str, listener: Callable) -> None:
        """イベントリスナー登録解除
        
        Args:
            event_type: イベント種別
            listener: リスナー関数
        """
        with self._bridge_lock:
            if event_type in self._event_listeners:
                if listener in self._event_listeners[event_type]:
                    self._event_listeners[event_type].remove(listener)
    
    def emit_event(self, event_type: str, source_id: str, data: Any = None) -> None:
        """イベント発行
        
        Args:
            event_type: イベント種別
            source_id: 発行元ID
            data: イベントデータ
        """
        with self._bridge_lock:
            listeners = self._event_listeners.get(event_type, [])
            
            for listener in listeners:
                try:
                    listener(source_id, data)
                except Exception as e:
                    self._logger.error(
                        f"Event listener error [{event_type}]: {e}"
                    )
    
    def get_component_proxy(self, component_id: str, interface_type: Type[T]) -> Optional[T]:
        """コンポーネントプロキシ取得
        
        Args:
            component_id: コンポーネントID
            interface_type: インターフェース型
            
        Returns:
            コンポーネントプロキシ（存在しない場合はNone）
        """
        return self._registry.get_component_instance(component_id, interface_type)


class SystemIntegration:
    """システム統合管理
    
    W65C02Sエミュレータの全コンポーネントの統合を管理し、
    システム全体の協調動作を実現します。
    """
    
    def __init__(self):
        """システム統合管理を初期化"""
        # コアコンポーネント
        self._registry = ComponentRegistry()
        self._bridge = SystemBridge(self._registry)
        
        # 統合状態
        self._current_phase = IntegrationPhase.REGISTRATION
        self._integration_lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
        
        # システムコンポーネント
        self._system_orchestrator: Optional[SystemOrchestrator] = None
        self._system_clock: Optional[SystemClock] = None
        self._interrupt_controller: Optional[InterruptController] = None
        self._tick_engine: Optional[TickEngine] = None
        
        # 初期化フック
        self._phase_hooks: Dict[IntegrationPhase, List[Callable]] = {
            phase: [] for phase in IntegrationPhase
        }
    
    def initialize_system(self, system_config: Optional[SystemConfiguration] = None) -> bool:
        """システム初期化
        
        Args:
            system_config: システム設定
            
        Returns:
            初期化が成功した場合True
        """
        with self._integration_lock:
            try:
                self._logger.info("System integration started")
                
                # フェーズ1: コアコンポーネント作成
                self._current_phase = IntegrationPhase.REGISTRATION
                self._execute_phase_hooks(IntegrationPhase.REGISTRATION)
                
                if not self._create_core_components(system_config):
                    return False
                
                # フェーズ2: 初期化
                self._current_phase = IntegrationPhase.INITIALIZATION
                self._execute_phase_hooks(IntegrationPhase.INITIALIZATION)
                
                if not self._initialize_components():
                    return False
                
                # フェーズ3: 設定
                self._current_phase = IntegrationPhase.CONFIGURATION
                self._execute_phase_hooks(IntegrationPhase.CONFIGURATION)
                
                if not self._configure_components():
                    return False
                
                # フェーズ4: 起動
                self._current_phase = IntegrationPhase.STARTUP
                self._execute_phase_hooks(IntegrationPhase.STARTUP)
                
                if not self._startup_components():
                    return False
                
                self._current_phase = IntegrationPhase.RUNNING
                self._logger.info("System integration completed")
                return True
                
            except Exception as e:
                self._logger.error(f"System integration failed: {e}")
                return False
    
    def shutdown_system(self) -> None:
        """システム終了処理"""
        with self._integration_lock:
            try:
                self._current_phase = IntegrationPhase.SHUTDOWN
                self._execute_phase_hooks(IntegrationPhase.SHUTDOWN)
                
                # システムオーケストレータ終了
                if self._system_orchestrator:
                    self._system_orchestrator.stop()
                
                self._logger.info("System integration shutdown completed")
                
            except Exception as e:
                self._logger.error(f"System integration shutdown failed: {e}")
    
    def get_registry(self) -> ComponentRegistry:
        """コンポーネントレジストリ取得"""
        return self._registry
    
    def get_bridge(self) -> SystemBridge:
        """システムブリッジ取得"""
        return self._bridge
    
    def get_system_orchestrator(self) -> Optional[SystemOrchestrator]:
        """システムオーケストレータ取得"""
        return self._system_orchestrator
    
    def get_system_clock(self) -> Optional[SystemClock]:
        """システムクロック取得"""
        return self._system_clock
    
    def get_interrupt_controller(self) -> Optional[InterruptController]:
        """割り込みコントローラ取得"""
        return self._interrupt_controller
    
    def get_tick_engine(self) -> Optional[TickEngine]:
        """Tick駆動実行エンジン取得"""
        return self._tick_engine
    
    def get_current_phase(self) -> IntegrationPhase:
        """現在の統合フェーズ取得"""
        return self._current_phase
    
    def add_phase_hook(self, phase: IntegrationPhase, hook: Callable) -> None:
        """フェーズフック追加
        
        Args:
            phase: 統合フェーズ
            hook: フック関数
        """
        self._phase_hooks[phase].append(hook)
    
    def get_integration_state(self) -> Dict[str, Any]:
        """統合状態取得"""
        return {
            'current_phase': self._current_phase.name,
            'registry_state': self._registry.get_registry_state(),
            'core_components': {
                'system_orchestrator': self._system_orchestrator is not None,
                'system_clock': self._system_clock is not None,
                'interrupt_controller': self._interrupt_controller is not None,
                'tick_engine': self._tick_engine is not None
            }
        }
    
    def _create_core_components(self, system_config: Optional[SystemConfiguration]) -> bool:
        """コアコンポーネント作成"""
        try:
            # システムクロックを先に作成（依存関係なし）
            if system_config and system_config.clock_config:
                self._system_clock = SystemClock(system_config.clock_config)
            else:
                from .clock import ClockConfiguration
                clock_config = ClockConfiguration()
                self._system_clock = SystemClock(clock_config)
            
            self._registry.register_component(
                'system_clock',
                'clock',
                self._system_clock
            )
            
            # システムオーケストレータ（依存関係なし）
            self._system_orchestrator = SystemOrchestrator(system_config)
            # システムクロックを設定
            self._system_orchestrator.set_system_clock(self._system_clock)
            self._registry.register_component(
                'system_orchestrator',
                'orchestrator',
                self._system_orchestrator
            )
            
            # 割り込みコントローラ（後で登録）
            self._interrupt_controller = self._system_orchestrator.get_interrupt_controller()
            
            # Tick駆動実行エンジン（システムクロックに依存）
            if system_config and system_config.clock_config:
                self._tick_engine = TickEngine(system_config.clock_config.master_frequency_hz)
            else:
                self._tick_engine = TickEngine()
            
            self._registry.register_component(
                'tick_engine',
                'tick_engine',
                self._tick_engine,
                dependencies=['system_clock']
            )
            
            return True
            
        except Exception as e:
            self._logger.error(f"Core component creation failed: {e}")
            return False
    
    def _initialize_components(self) -> bool:
        """コンポーネント初期化"""
        # 割り込みコントローラを登録（システムオーケストレータが初期化された後）
        if self._interrupt_controller:
            self._registry.register_component(
                'interrupt_controller',
                'interrupt',
                self._interrupt_controller,
                dependencies=['system_orchestrator']
            )
        
        initialization_order = self._registry.get_initialization_order()
        
        for component_id in initialization_order:
            component_info = self._registry.get_component(component_id)
            if component_info is None:
                continue
            
            try:
                # 初期化可能なコンポーネントのみ初期化
                instance = component_info.instance
                if hasattr(instance, 'initialize'):
                    if not instance.initialize():
                        self._logger.error(f"Component initialization failed: {component_id}")
                        return False
                
                self._registry.update_component_state(component_id, ComponentState.INITIALIZED)
                
            except Exception as e:
                self._logger.error(f"Component initialization error [{component_id}]: {e}")
                return False
        
        # TickEngineをSystemClockのリスナーとして登録
        if self._tick_engine and self._system_clock:
            self._system_clock.add_listener(self._tick_engine)
            self._logger.debug("TickEngine registered as SystemClock listener")
        
        return True
    
    def _configure_components(self) -> bool:
        """コンポーネント設定"""
        # 設定処理は個別のコンポーネントで実装
        for component_id, component_info in self._registry._components.items():
            self._registry.update_component_state(component_id, ComponentState.CONFIGURED)
        
        return True
    
    def _startup_components(self) -> bool:
        """コンポーネント起動"""
        try:
            # システムオーケストレータ初期化・起動
            if self._system_orchestrator:
                if not self._system_orchestrator.initialize():
                    return False
                if not self._system_orchestrator.start():
                    return False
            
            # Tick駆動実行エンジン起動
            if self._tick_engine:
                self._tick_engine.start()
            
            # 全コンポーネントを起動状態に更新
            for component_id, component_info in self._registry._components.items():
                self._registry.update_component_state(component_id, ComponentState.STARTED)
            
            return True
            
        except Exception as e:
            self._logger.error(f"Component startup failed: {e}")
            return False
    
    def _execute_phase_hooks(self, phase: IntegrationPhase) -> None:
        """フェーズフック実行"""
        hooks = self._phase_hooks.get(phase, [])
        for hook in hooks:
            try:
                hook()
            except Exception as e:
                self._logger.error(f"Phase hook error [{phase.name}]: {e}")
