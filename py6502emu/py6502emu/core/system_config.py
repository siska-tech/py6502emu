"""
システム設定管理（拡張版）

W65C02S エミュレータのシステム全体の設定管理を提供します。
実行時パラメータの調整、性能チューニング設定、デバイス間設定の調整を含みます。
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum, auto
import json
import logging
from pathlib import Path

from .config import ConfigurationManager, SystemConfig, DeviceConfig, ConfigurationError
from .clock import ClockConfiguration, ClockMode
from .orchestrator import SystemConfiguration, ExecutionMode


class PerformanceProfile(Enum):
    """性能プロファイル"""
    ACCURACY = auto()      # 精度重視
    PERFORMANCE = auto()   # 性能重視
    BALANCED = auto()      # バランス重視
    CUSTOM = auto()        # カスタム


class LogLevel(Enum):
    """ログレベル"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class PerformanceConfiguration:
    """性能設定"""
    profile: PerformanceProfile = PerformanceProfile.BALANCED
    max_cycles_per_frame: int = 10000
    sync_interval_cycles: int = 1000
    enable_cycle_counting: bool = True
    enable_timing_stats: bool = True
    enable_profiling: bool = False
    memory_optimization: bool = True
    cache_size_kb: int = 64
    
    # 実行制御
    max_execution_time_ms: float = 16.67  # 60 FPS
    cpu_usage_limit_percent: float = 80.0
    
    # デバッグ設定
    enable_debug_hooks: bool = False
    debug_output_interval: int = 10000
    
    def apply_profile(self) -> None:
        """プロファイル適用"""
        if self.profile == PerformanceProfile.ACCURACY:
            self.max_cycles_per_frame = 1000
            self.sync_interval_cycles = 100
            self.enable_cycle_counting = True
            self.enable_timing_stats = True
            self.enable_profiling = True
            self.max_execution_time_ms = 100.0
            
        elif self.profile == PerformanceProfile.PERFORMANCE:
            self.max_cycles_per_frame = 50000
            self.sync_interval_cycles = 5000
            self.enable_cycle_counting = False
            self.enable_timing_stats = False
            self.enable_profiling = False
            self.max_execution_time_ms = 8.33  # 120 FPS
            
        elif self.profile == PerformanceProfile.BALANCED:
            self.max_cycles_per_frame = 10000
            self.sync_interval_cycles = 1000
            self.enable_cycle_counting = True
            self.enable_timing_stats = True
            self.enable_profiling = False
            self.max_execution_time_ms = 16.67  # 60 FPS


@dataclass
class RuntimeConfiguration:
    """実行時設定"""
    execution_mode: ExecutionMode = ExecutionMode.CONTINUOUS
    clock_mode: ClockMode = ClockMode.REALTIME
    master_frequency_hz: int = 1_000_000
    
    # 実行制御
    auto_start: bool = False
    pause_on_error: bool = True
    continue_on_breakpoint: bool = False
    
    # デバッグ設定
    enable_debugging: bool = False
    enable_tracing: bool = False
    trace_buffer_size: int = 10000
    
    # 割り込み設定
    enable_interrupts: bool = True
    interrupt_latency_cycles: int = 7
    
    # メモリ設定
    memory_size_kb: int = 64
    enable_memory_protection: bool = False
    
    def validate(self) -> List[str]:
        """設定検証
        
        Returns:
            検証エラーメッセージのリスト
        """
        errors = []
        
        if self.master_frequency_hz <= 0:
            errors.append("Master frequency must be positive")
        
        if self.trace_buffer_size <= 0:
            errors.append("Trace buffer size must be positive")
        
        if self.interrupt_latency_cycles < 0:
            errors.append("Interrupt latency cycles cannot be negative")
        
        if self.memory_size_kb <= 0:
            errors.append("Memory size must be positive")
        
        return errors


@dataclass
class DebuggingConfiguration:
    """デバッグ設定"""
    enable_debugging: bool = False
    log_level: LogLevel = LogLevel.INFO
    log_to_file: bool = False
    log_file_path: Optional[str] = None
    
    # ブレークポイント設定
    enable_breakpoints: bool = True
    max_breakpoints: int = 100
    
    # トレース設定
    enable_instruction_trace: bool = False
    enable_memory_trace: bool = False
    enable_interrupt_trace: bool = False
    trace_output_format: str = "text"  # text, json, binary
    
    # プロファイリング設定
    enable_profiling: bool = False
    profiling_interval_ms: int = 100
    profile_output_path: Optional[str] = None
    
    # 統計設定
    enable_statistics: bool = True
    statistics_interval_cycles: int = 10000
    
    def get_log_level_value(self) -> str:
        """ログレベル値取得"""
        return self.log_level.value


class SystemConfigurationManager:
    """システム設定管理（拡張版）
    
    基本的な設定管理に加えて、実行時設定、性能設定、デバッグ設定を統合管理します。
    """
    
    def __init__(self):
        """システム設定管理を初期化"""
        # 基本設定管理
        self._base_config_manager = ConfigurationManager()
        
        # 拡張設定
        self._runtime_config = RuntimeConfiguration()
        self._performance_config = PerformanceConfiguration()
        self._debugging_config = DebuggingConfiguration()
        
        # 設定履歴
        self._config_history: List[Dict[str, Any]] = []
        self._max_history_entries = 10
        
        # 設定変更通知
        self._change_listeners: List[callable] = []
        
        self._logger = logging.getLogger(__name__)
    
    def load_from_file(self, config_path: Path) -> None:
        """設定ファイル読み込み
        
        Args:
            config_path: 設定ファイルのパス
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            self.load_from_dict(config_data)
            self._logger.info(f"System configuration loaded from {config_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load system configuration: {e}")
    
    def load_from_dict(self, config_data: Dict[str, Any]) -> None:
        """辞書から設定読み込み
        
        Args:
            config_data: 設定データの辞書
        """
        try:
            # 基本設定読み込み
            self._base_config_manager.load_from_dict(config_data)
            
            # 実行時設定読み込み
            runtime_data = config_data.get('runtime', {})
            self._load_runtime_config(runtime_data)
            
            # 性能設定読み込み
            performance_data = config_data.get('performance', {})
            self._load_performance_config(performance_data)
            
            # デバッグ設定読み込み
            debugging_data = config_data.get('debugging', {})
            self._load_debugging_config(debugging_data)
            
            # 設定履歴に追加
            self._add_to_history(config_data)
            
            # 変更通知
            self._notify_config_change()
            
        except Exception as e:
            raise ConfigurationError(f"Failed to parse system configuration: {e}")
    
    def save_to_file(self, config_path: Optional[Path] = None) -> None:
        """設定ファイル保存
        
        Args:
            config_path: 保存先ファイルパス
        """
        try:
            config_data = self.serialize_to_dict()
            
            if config_path is None:
                config_path = Path("system_config.json")
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self._logger.info(f"System configuration saved to {config_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save system configuration: {e}")
    
    def serialize_to_dict(self) -> Dict[str, Any]:
        """辞書にシリアライズ
        
        Returns:
            設定データの辞書
        """
        # 基本設定取得
        base_config = self._base_config_manager._serialize_config()
        
        # 拡張設定追加
        config_data = base_config.copy()
        
        config_data['runtime'] = {
            'execution_mode': self._runtime_config.execution_mode.name,
            'clock_mode': self._runtime_config.clock_mode.name,
            'master_frequency_hz': self._runtime_config.master_frequency_hz,
            'auto_start': self._runtime_config.auto_start,
            'pause_on_error': self._runtime_config.pause_on_error,
            'continue_on_breakpoint': self._runtime_config.continue_on_breakpoint,
            'enable_debugging': self._runtime_config.enable_debugging,
            'enable_tracing': self._runtime_config.enable_tracing,
            'trace_buffer_size': self._runtime_config.trace_buffer_size,
            'enable_interrupts': self._runtime_config.enable_interrupts,
            'interrupt_latency_cycles': self._runtime_config.interrupt_latency_cycles,
            'memory_size_kb': self._runtime_config.memory_size_kb,
            'enable_memory_protection': self._runtime_config.enable_memory_protection
        }
        
        config_data['performance'] = {
            'profile': self._performance_config.profile.name,
            'max_cycles_per_frame': self._performance_config.max_cycles_per_frame,
            'sync_interval_cycles': self._performance_config.sync_interval_cycles,
            'enable_cycle_counting': self._performance_config.enable_cycle_counting,
            'enable_timing_stats': self._performance_config.enable_timing_stats,
            'enable_profiling': self._performance_config.enable_profiling,
            'memory_optimization': self._performance_config.memory_optimization,
            'cache_size_kb': self._performance_config.cache_size_kb,
            'max_execution_time_ms': self._performance_config.max_execution_time_ms,
            'cpu_usage_limit_percent': self._performance_config.cpu_usage_limit_percent,
            'enable_debug_hooks': self._performance_config.enable_debug_hooks,
            'debug_output_interval': self._performance_config.debug_output_interval
        }
        
        config_data['debugging'] = {
            'enable_debugging': self._debugging_config.enable_debugging,
            'log_level': self._debugging_config.log_level.value,
            'log_to_file': self._debugging_config.log_to_file,
            'log_file_path': self._debugging_config.log_file_path,
            'enable_breakpoints': self._debugging_config.enable_breakpoints,
            'max_breakpoints': self._debugging_config.max_breakpoints,
            'enable_instruction_trace': self._debugging_config.enable_instruction_trace,
            'enable_memory_trace': self._debugging_config.enable_memory_trace,
            'enable_interrupt_trace': self._debugging_config.enable_interrupt_trace,
            'trace_output_format': self._debugging_config.trace_output_format,
            'enable_profiling': self._debugging_config.enable_profiling,
            'profiling_interval_ms': self._debugging_config.profiling_interval_ms,
            'profile_output_path': self._debugging_config.profile_output_path,
            'enable_statistics': self._debugging_config.enable_statistics,
            'statistics_interval_cycles': self._debugging_config.statistics_interval_cycles
        }
        
        return config_data
    
    def get_system_configuration(self) -> SystemConfiguration:
        """SystemConfiguration生成
        
        Returns:
            SystemConfiguration オブジェクト
        """
        # ClockConfiguration生成
        clock_config = ClockConfiguration(
            master_frequency_hz=self._runtime_config.master_frequency_hz,
            mode=self._runtime_config.clock_mode,
            sync_interval_cycles=self._performance_config.sync_interval_cycles,
            enable_drift_correction=True
        )
        
        # SystemConfiguration生成
        return SystemConfiguration(
            clock_config=clock_config,
            execution_mode=self._runtime_config.execution_mode,
            max_cycles_per_frame=self._performance_config.max_cycles_per_frame,
            enable_debugging=self._runtime_config.enable_debugging,
            enable_profiling=self._performance_config.enable_profiling,
            auto_start=self._runtime_config.auto_start
        )
    
    def get_runtime_config(self) -> RuntimeConfiguration:
        """実行時設定取得"""
        return self._runtime_config
    
    def get_performance_config(self) -> PerformanceConfiguration:
        """性能設定取得"""
        return self._performance_config
    
    def get_debugging_config(self) -> DebuggingConfiguration:
        """デバッグ設定取得"""
        return self._debugging_config
    
    def update_runtime_config(self, **kwargs) -> None:
        """実行時設定更新
        
        Args:
            **kwargs: 更新する設定項目
        """
        for key, value in kwargs.items():
            if hasattr(self._runtime_config, key):
                setattr(self._runtime_config, key, value)
        
        self._notify_config_change()
    
    def update_performance_config(self, **kwargs) -> None:
        """性能設定更新
        
        Args:
            **kwargs: 更新する設定項目
        """
        for key, value in kwargs.items():
            if hasattr(self._performance_config, key):
                setattr(self._performance_config, key, value)
        
        # プロファイル適用
        if 'profile' in kwargs:
            self._performance_config.apply_profile()
        
        self._notify_config_change()
    
    def update_debugging_config(self, **kwargs) -> None:
        """デバッグ設定更新
        
        Args:
            **kwargs: 更新する設定項目
        """
        for key, value in kwargs.items():
            if hasattr(self._debugging_config, key):
                setattr(self._debugging_config, key, value)
        
        self._notify_config_change()
    
    def validate_all_configs(self) -> List[str]:
        """全設定検証
        
        Returns:
            検証エラーメッセージのリスト
        """
        errors = []
        
        # 基本設定検証
        errors.extend(self._base_config_manager.validate_config())
        
        # 実行時設定検証
        errors.extend(self._runtime_config.validate())
        
        return errors
    
    def get_config_history(self) -> List[Dict[str, Any]]:
        """設定履歴取得"""
        return self._config_history.copy()
    
    def add_change_listener(self, listener: callable) -> None:
        """設定変更リスナー追加
        
        Args:
            listener: 変更通知を受け取る関数
        """
        self._change_listeners.append(listener)
    
    def remove_change_listener(self, listener: callable) -> None:
        """設定変更リスナー削除
        
        Args:
            listener: 削除するリスナー関数
        """
        if listener in self._change_listeners:
            self._change_listeners.remove(listener)
    
    def create_preset_config(self, preset_name: str) -> Dict[str, Any]:
        """プリセット設定作成
        
        Args:
            preset_name: プリセット名
            
        Returns:
            プリセット設定データ
        """
        if preset_name == "development":
            return self._create_development_preset()
        elif preset_name == "production":
            return self._create_production_preset()
        elif preset_name == "testing":
            return self._create_testing_preset()
        else:
            raise ValueError(f"Unknown preset: {preset_name}")
    
    def _load_runtime_config(self, runtime_data: Dict[str, Any]) -> None:
        """実行時設定読み込み"""
        self._runtime_config.execution_mode = ExecutionMode[
            runtime_data.get('execution_mode', 'CONTINUOUS')
        ]
        self._runtime_config.clock_mode = ClockMode[
            runtime_data.get('clock_mode', 'REALTIME')
        ]
        self._runtime_config.master_frequency_hz = runtime_data.get(
            'master_frequency_hz', 1_000_000
        )
        self._runtime_config.auto_start = runtime_data.get('auto_start', False)
        self._runtime_config.pause_on_error = runtime_data.get('pause_on_error', True)
        self._runtime_config.continue_on_breakpoint = runtime_data.get(
            'continue_on_breakpoint', False
        )
        self._runtime_config.enable_debugging = runtime_data.get('enable_debugging', False)
        self._runtime_config.enable_tracing = runtime_data.get('enable_tracing', False)
        self._runtime_config.trace_buffer_size = runtime_data.get('trace_buffer_size', 10000)
        self._runtime_config.enable_interrupts = runtime_data.get('enable_interrupts', True)
        self._runtime_config.interrupt_latency_cycles = runtime_data.get(
            'interrupt_latency_cycles', 7
        )
        self._runtime_config.memory_size_kb = runtime_data.get('memory_size_kb', 64)
        self._runtime_config.enable_memory_protection = runtime_data.get(
            'enable_memory_protection', False
        )
    
    def _load_performance_config(self, performance_data: Dict[str, Any]) -> None:
        """性能設定読み込み"""
        self._performance_config.profile = PerformanceProfile[
            performance_data.get('profile', 'BALANCED')
        ]
        self._performance_config.max_cycles_per_frame = performance_data.get(
            'max_cycles_per_frame', 10000
        )
        self._performance_config.sync_interval_cycles = performance_data.get(
            'sync_interval_cycles', 1000
        )
        self._performance_config.enable_cycle_counting = performance_data.get(
            'enable_cycle_counting', True
        )
        self._performance_config.enable_timing_stats = performance_data.get(
            'enable_timing_stats', True
        )
        self._performance_config.enable_profiling = performance_data.get(
            'enable_profiling', False
        )
        self._performance_config.memory_optimization = performance_data.get(
            'memory_optimization', True
        )
        self._performance_config.cache_size_kb = performance_data.get('cache_size_kb', 64)
        self._performance_config.max_execution_time_ms = performance_data.get(
            'max_execution_time_ms', 16.67
        )
        self._performance_config.cpu_usage_limit_percent = performance_data.get(
            'cpu_usage_limit_percent', 80.0
        )
        self._performance_config.enable_debug_hooks = performance_data.get(
            'enable_debug_hooks', False
        )
        self._performance_config.debug_output_interval = performance_data.get(
            'debug_output_interval', 10000
        )
        
        # プロファイル適用
        if self._performance_config.profile != PerformanceProfile.CUSTOM:
            self._performance_config.apply_profile()
    
    def _load_debugging_config(self, debugging_data: Dict[str, Any]) -> None:
        """デバッグ設定読み込み"""
        self._debugging_config.enable_debugging = debugging_data.get('enable_debugging', False)
        self._debugging_config.log_level = LogLevel(
            debugging_data.get('log_level', 'INFO')
        )
        self._debugging_config.log_to_file = debugging_data.get('log_to_file', False)
        self._debugging_config.log_file_path = debugging_data.get('log_file_path')
        self._debugging_config.enable_breakpoints = debugging_data.get('enable_breakpoints', True)
        self._debugging_config.max_breakpoints = debugging_data.get('max_breakpoints', 100)
        self._debugging_config.enable_instruction_trace = debugging_data.get(
            'enable_instruction_trace', False
        )
        self._debugging_config.enable_memory_trace = debugging_data.get(
            'enable_memory_trace', False
        )
        self._debugging_config.enable_interrupt_trace = debugging_data.get(
            'enable_interrupt_trace', False
        )
        self._debugging_config.trace_output_format = debugging_data.get(
            'trace_output_format', 'text'
        )
        self._debugging_config.enable_profiling = debugging_data.get('enable_profiling', False)
        self._debugging_config.profiling_interval_ms = debugging_data.get(
            'profiling_interval_ms', 100
        )
        self._debugging_config.profile_output_path = debugging_data.get('profile_output_path')
        self._debugging_config.enable_statistics = debugging_data.get('enable_statistics', True)
        self._debugging_config.statistics_interval_cycles = debugging_data.get(
            'statistics_interval_cycles', 10000
        )
    
    def _add_to_history(self, config_data: Dict[str, Any]) -> None:
        """設定履歴に追加"""
        if len(self._config_history) >= self._max_history_entries:
            self._config_history.pop(0)
        
        import time
        history_entry = {
            'timestamp': time.time(),
            'config': config_data.copy()
        }
        self._config_history.append(history_entry)
    
    def _notify_config_change(self) -> None:
        """設定変更通知"""
        for listener in self._change_listeners:
            try:
                listener()
            except Exception as e:
                self._logger.error(f"Config change listener error: {e}")
    
    def _create_development_preset(self) -> Dict[str, Any]:
        """開発用プリセット作成"""
        return {
            'runtime': {
                'execution_mode': 'STEP',
                'enable_debugging': True,
                'enable_tracing': True,
                'pause_on_error': True
            },
            'performance': {
                'profile': 'ACCURACY',
                'enable_profiling': True
            },
            'debugging': {
                'enable_debugging': True,
                'log_level': 'DEBUG',
                'enable_instruction_trace': True,
                'enable_memory_trace': True,
                'enable_interrupt_trace': True
            }
        }
    
    def _create_production_preset(self) -> Dict[str, Any]:
        """本番用プリセット作成"""
        return {
            'runtime': {
                'execution_mode': 'CONTINUOUS',
                'enable_debugging': False,
                'enable_tracing': False,
                'pause_on_error': False
            },
            'performance': {
                'profile': 'PERFORMANCE',
                'enable_profiling': False
            },
            'debugging': {
                'enable_debugging': False,
                'log_level': 'WARNING',
                'enable_instruction_trace': False,
                'enable_memory_trace': False,
                'enable_interrupt_trace': False
            }
        }
    
    def _create_testing_preset(self) -> Dict[str, Any]:
        """テスト用プリセット作成"""
        return {
            'runtime': {
                'execution_mode': 'CONTINUOUS',
                'enable_debugging': True,
                'enable_tracing': False,
                'pause_on_error': True
            },
            'performance': {
                'profile': 'BALANCED',
                'enable_profiling': True
            },
            'debugging': {
                'enable_debugging': True,
                'log_level': 'INFO',
                'enable_statistics': True
            }
        }
