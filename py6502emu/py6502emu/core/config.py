"""
設定管理システム
PU022: ConfigurationManager

W65C02S エミュレータのシステム設定とデバイス設定を統一的に管理します。
JSON形式での設定ファイルの読み書き、実行時設定変更、設定検証機能を提供します。
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging
from .device import DeviceConfig
from .types import DeviceType


@dataclass
class SystemConfig:
    """システム設定
    
    エミュレータ全体の動作を制御するシステムレベルの設定。
    """
    master_clock_hz: int = 1_000_000  # 1MHz
    debug_enabled: bool = False
    log_level: str = "INFO"
    devices: List[DeviceConfig] = field(default_factory=list)


@dataclass
class CPUConfig(DeviceConfig):
    """CPU設定
    
    CPUデバイス固有の設定パラメータ。
    """
    clock_divider: int = 1
    reset_vector: int = 0xFFFC
    irq_vector: int = 0xFFFE
    nmi_vector: int = 0xFFFA


@dataclass
class MemoryConfig(DeviceConfig):
    """メモリ設定
    
    メモリデバイス固有の設定パラメータ。
    """
    size: int = 65536  # 64KB
    start_address: int = 0x0000
    end_address: int = 0xFFFF
    readonly: bool = False


class ConfigurationManager:
    """設定管理クラス
    
    システム設定とデバイス設定の統一管理を行います。
    JSON形式での設定ファイルの読み書き、設定検証、実行時設定変更をサポートします。
    """
    
    def __init__(self) -> None:
        self._system_config: Optional[SystemConfig] = None
        self._device_configs: Dict[str, DeviceConfig] = {}
        self._config_file: Optional[Path] = None
        self._logger = logging.getLogger(__name__)
    
    def load_from_file(self, config_path: Path) -> None:
        """設定ファイル読み込み
        
        指定されたJSONファイルから設定を読み込みます。
        
        Args:
            config_path: 設定ファイルのパス
            
        Raises:
            ConfigurationError: 設定ファイルの読み込みに失敗した場合
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            self._parse_config(config_data)
            self._config_file = config_path
            self._logger.info(f"Configuration loaded from {config_path}")
            
        except FileNotFoundError:
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration: {e}")
    
    def load_from_dict(self, config_data: Dict[str, Any]) -> None:
        """辞書から設定読み込み
        
        辞書形式のデータから設定を読み込みます。
        
        Args:
            config_data: 設定データの辞書
            
        Raises:
            ConfigurationError: 設定データの解析に失敗した場合
        """
        try:
            self._parse_config(config_data)
            self._logger.info("Configuration loaded from dictionary")
        except Exception as e:
            raise ConfigurationError(f"Error parsing configuration: {e}")
    
    def save_to_file(self, config_path: Optional[Path] = None) -> None:
        """設定ファイル保存
        
        現在の設定をJSONファイルに保存します。
        
        Args:
            config_path: 保存先ファイルパス（省略時は読み込み元ファイル）
            
        Raises:
            ConfigurationError: 設定ファイルの保存に失敗した場合
        """
        if config_path is None:
            config_path = self._config_file
        
        if config_path is None:
            raise ConfigurationError("No configuration file specified")
        
        try:
            config_data = self._serialize_config()
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self._logger.info(f"Configuration saved to {config_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Error saving configuration: {e}")
    
    def get_system_config(self) -> SystemConfig:
        """システム設定取得
        
        Returns:
            SystemConfig: システム設定オブジェクト
        """
        if self._system_config is None:
            self._system_config = SystemConfig()
        return self._system_config
    
    def set_system_config(self, config: SystemConfig) -> None:
        """システム設定設定
        
        Args:
            config: 設定するシステム設定
        """
        self._system_config = config
    
    def get_device_config(self, device_id: str) -> Optional[DeviceConfig]:
        """デバイス設定取得
        
        Args:
            device_id: デバイスID
            
        Returns:
            Optional[DeviceConfig]: デバイス設定（存在しない場合はNone）
        """
        return self._device_configs.get(device_id)
    
    def add_device_config(self, config: DeviceConfig) -> None:
        """デバイス設定追加
        
        Args:
            config: 追加するデバイス設定
        """
        self._device_configs[config.device_id] = config
        self._logger.debug(f"Added device config: {config.device_id}")
    
    def remove_device_config(self, device_id: str) -> None:
        """デバイス設定削除
        
        Args:
            device_id: 削除するデバイスID
        """
        if device_id in self._device_configs:
            del self._device_configs[device_id]
            self._logger.debug(f"Removed device config: {device_id}")
    
    def list_device_configs(self) -> List[DeviceConfig]:
        """デバイス設定一覧取得
        
        Returns:
            List[DeviceConfig]: 全デバイス設定のリスト
        """
        return list(self._device_configs.values())
    
    def validate_config(self) -> List[str]:
        """設定検証
        
        現在の設定の妥当性を検証し、エラーメッセージのリストを返します。
        
        Returns:
            List[str]: 検証エラーメッセージのリスト（エラーがない場合は空リスト）
        """
        errors = []
        
        # システム設定検証
        system_config = self.get_system_config()
        if system_config.master_clock_hz <= 0:
            errors.append("Master clock frequency must be positive")
        
        # デバイス設定検証
        device_ids = set()
        for config in self._device_configs.values():
            if config.device_id in device_ids:
                errors.append(f"Duplicate device ID: {config.device_id}")
            device_ids.add(config.device_id)
            
            # デバイス固有検証
            if isinstance(config, CPUConfig):
                if config.clock_divider <= 0:
                    errors.append(f"CPU clock divider must be positive: {config.device_id}")
            
            elif isinstance(config, MemoryConfig):
                if config.size <= 0:
                    errors.append(f"Memory size must be positive: {config.device_id}")
                if config.start_address > config.end_address:
                    errors.append(f"Invalid memory range: {config.device_id}")
        
        return errors
    
    def _parse_config(self, config_data: Dict[str, Any]) -> None:
        """設定データ解析
        
        Args:
            config_data: 解析する設定データ
        """
        # システム設定解析
        system_data = config_data.get('system', {})
        self._system_config = SystemConfig(
            master_clock_hz=system_data.get('master_clock_hz', 1_000_000),
            debug_enabled=system_data.get('debug_enabled', False),
            log_level=system_data.get('log_level', 'INFO')
        )
        
        # デバイス設定解析
        devices_data = config_data.get('devices', [])
        self._device_configs.clear()
        
        for device_data in devices_data:
            device_type = device_data.get('type', 'generic')
            device_id = device_data['device_id']
            
            if device_type == 'cpu':
                config = CPUConfig(
                    device_id=device_id,
                    name=device_data.get('name', device_id),
                    clock_divider=device_data.get('clock_divider', 1),
                    reset_vector=device_data.get('reset_vector', 0xFFFC),
                    irq_vector=device_data.get('irq_vector', 0xFFFE),
                    nmi_vector=device_data.get('nmi_vector', 0xFFFA)
                )
            elif device_type == 'memory':
                config = MemoryConfig(
                    device_id=device_id,
                    name=device_data.get('name', device_id),
                    size=device_data.get('size', 65536),
                    start_address=device_data.get('start_address', 0x0000),
                    end_address=device_data.get('end_address', 0xFFFF),
                    readonly=device_data.get('readonly', False)
                )
            else:
                config = DeviceConfig(
                    device_id=device_id,
                    name=device_data.get('name', device_id)
                )
            
            self._device_configs[device_id] = config
    
    def _serialize_config(self) -> Dict[str, Any]:
        """設定データシリアライズ
        
        Returns:
            Dict[str, Any]: シリアライズされた設定データ
        """
        system_config = self.get_system_config()
        
        config_data = {
            'system': {
                'master_clock_hz': system_config.master_clock_hz,
                'debug_enabled': system_config.debug_enabled,
                'log_level': system_config.log_level
            },
            'devices': []
        }
        
        for config in self._device_configs.values():
            device_data = {
                'device_id': config.device_id,
                'name': config.name
            }
            
            if isinstance(config, CPUConfig):
                device_data.update({
                    'type': 'cpu',
                    'clock_divider': config.clock_divider,
                    'reset_vector': config.reset_vector,
                    'irq_vector': config.irq_vector,
                    'nmi_vector': config.nmi_vector
                })
            elif isinstance(config, MemoryConfig):
                device_data.update({
                    'type': 'memory',
                    'size': config.size,
                    'start_address': config.start_address,
                    'end_address': config.end_address,
                    'readonly': config.readonly
                })
            else:
                device_data['type'] = 'generic'
            
            config_data['devices'].append(device_data)
        
        return config_data


class ConfigurationError(Exception):
    """設定エラー例外
    
    設定関連の処理で発生するエラーを表す例外クラス。
    """
    pass
