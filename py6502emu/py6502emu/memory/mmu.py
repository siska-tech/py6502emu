"""
システムバス実装
PU020: SystemBus

W65C02S エミュレータのシステムバス機能を提供します。
デバイス間の通信、メモリマッピング、バスマスタシップ制御、
アクセスログ機能を実装します。
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import logging
from ..core.device import Device, InvalidAddressError, InvalidValueError


@dataclass
class DeviceMapping:
    """デバイスマッピング情報
    
    システムバス上のデバイスマッピングを表現するデータクラス。
    """
    device: Device
    start_address: int
    end_address: int
    name: str
    
    def contains(self, address: int) -> bool:
        """アドレス範囲チェック
        
        指定されたアドレスがこのマッピング範囲に含まれるかを確認します。
        
        Args:
            address: チェックするアドレス
            
        Returns:
            bool: 範囲内の場合True
        """
        return self.start_address <= address <= self.end_address
    
    def translate_address(self, address: int) -> int:
        """相対アドレス変換
        
        システムバス上のアドレスをデバイス内の相対アドレスに変換します。
        
        Args:
            address: システムバス上のアドレス
            
        Returns:
            int: デバイス内相対アドレス
        """
        return address - self.start_address
    
    @property
    def size(self) -> int:
        """マッピングサイズ
        
        Returns:
            int: マッピング範囲のサイズ（バイト数）
        """
        return self.end_address - self.start_address + 1


class SystemBus:
    """システムバス実装
    
    W65C02S システムのメインバス機能を提供します。
    デバイスマッピング、バス調停、アクセス制御、デバッグ支援機能を含みます。
    """
    
    def __init__(self, debug_enabled: bool = False) -> None:
        """SystemBus初期化
        
        Args:
            debug_enabled: デバッグモードの有効/無効
        """
        self._mappings: List[DeviceMapping] = []
        self._bus_masters: List[Device] = []
        self._current_master: Optional[Device] = None
        self._access_log: List[Dict[str, Any]] = []
        self._debug_enabled = debug_enabled
        self._logger = logging.getLogger(__name__)
    
    def map_device(self, device: Device, start: int, end: int, name: str = "") -> None:
        """デバイスマッピング
        
        指定されたアドレス範囲にデバイスをマッピングします。
        
        Args:
            device: マッピングするデバイス
            start: 開始アドレス
            end: 終了アドレス
            name: マッピング名（省略時はデバイス名を使用）
            
        Raises:
            ValueError: 無効なアドレス範囲または重複が検出された場合
        """
        # アドレス範囲検証
        if not (0 <= start <= end <= 0xFFFF):
            raise ValueError(f"Invalid address range: ${start:04X}-${end:04X}")
        
        # 重複チェック
        for mapping in self._mappings:
            if not (end < mapping.start_address or start > mapping.end_address):
                raise ValueError(f"Address range overlap: ${start:04X}-${end:04X}")
        
        # マッピング追加
        mapping = DeviceMapping(device, start, end, name or device.name)
        self._mappings.append(mapping)
        self._mappings.sort(key=lambda m: m.start_address)
        
        self._logger.info(f"Mapped device '{mapping.name}' to ${start:04X}-${end:04X}")
    
    def unmap_device(self, start: int, end: int) -> None:
        """デバイスマッピング解除
        
        指定されたアドレス範囲のマッピングを解除します。
        
        Args:
            start: 開始アドレス
            end: 終了アドレス
        """
        original_count = len(self._mappings)
        self._mappings = [m for m in self._mappings 
                         if not (m.start_address == start and m.end_address == end)]
        
        removed_count = original_count - len(self._mappings)
        if removed_count > 0:
            self._logger.info(f"Unmapped device from ${start:04X}-${end:04X}")
    
    def read(self, address: int) -> int:
        """バス読み取り
        
        指定されたアドレスからデータを読み取ります。
        
        Args:
            address: 読み取りアドレス
            
        Returns:
            int: 読み取った値（0x00-0xFF）
            
        Raises:
            InvalidAddressError: 無効なアドレスが指定された場合
        """
        if not self._validate_address(address):
            raise InvalidAddressError(address)
        
        # デバイス検索
        device_mapping = self._find_device_mapping(address)
        if device_mapping:
            relative_addr = device_mapping.translate_address(address)
            value = device_mapping.device.read(relative_addr)
            
            if self._debug_enabled:
                self._log_access('READ', address, value, device_mapping.name)
            
            return value
        else:
            # マップされていないアドレス（オープンバス）
            if self._debug_enabled:
                self._log_access('READ', address, 0xFF, 'OPEN_BUS')
            return 0xFF
    
    def write(self, address: int, value: int) -> None:
        """バス書き込み
        
        指定されたアドレスにデータを書き込みます。
        
        Args:
            address: 書き込みアドレス
            value: 書き込み値（0x00-0xFF）
            
        Raises:
            InvalidAddressError: 無効なアドレスが指定された場合
            InvalidValueError: 無効な値が指定された場合
        """
        if not self._validate_address(address):
            raise InvalidAddressError(address)
        
        if not self._validate_value(value):
            raise InvalidValueError(value)
        
        # デバイス検索
        device_mapping = self._find_device_mapping(address)
        if device_mapping:
            relative_addr = device_mapping.translate_address(address)
            device_mapping.device.write(relative_addr, value)
            
            if self._debug_enabled:
                self._log_access('WRITE', address, value, device_mapping.name)
        else:
            # マップされていないアドレス（書き込み無視）
            if self._debug_enabled:
                self._log_access('WRITE', address, value, 'IGNORED')
    
    def request_mastership(self, device: Device) -> bool:
        """バスマスタ権要求
        
        指定されたデバイスがバスマスタ権を要求します。
        
        Args:
            device: マスタ権を要求するデバイス
            
        Returns:
            bool: マスタ権取得成功の場合True
        """
        if self._current_master is None:
            self._current_master = device
            if device not in self._bus_masters:
                self._bus_masters.append(device)
            self._logger.debug(f"Bus mastership granted to {device.name}")
            return True
        return False
    
    def release_mastership(self, device: Device) -> None:
        """バスマスタ権解放
        
        指定されたデバイスがバスマスタ権を解放します。
        
        Args:
            device: マスタ権を解放するデバイス
        """
        if self._current_master == device:
            self._current_master = None
            self._logger.debug(f"Bus mastership released by {device.name}")
    
    def get_current_master(self) -> Optional[Device]:
        """現在のバスマスタ取得
        
        Returns:
            Optional[Device]: 現在のバスマスタ（存在しない場合はNone）
        """
        return self._current_master
    
    def enable_debug(self, enabled: bool = True) -> None:
        """デバッグモード設定
        
        Args:
            enabled: デバッグモードの有効/無効
        """
        self._debug_enabled = enabled
        self._logger.info(f"Debug mode {'enabled' if enabled else 'disabled'}")
    
    def get_access_log(self) -> List[Dict[str, Any]]:
        """アクセスログ取得
        
        Returns:
            List[Dict[str, Any]]: アクセスログのコピー
        """
        return self._access_log.copy()
    
    def clear_access_log(self) -> None:
        """アクセスログクリア"""
        self._access_log.clear()
        self._logger.debug("Access log cleared")
    
    def get_memory_map(self) -> List[Dict[str, Any]]:
        """メモリマップ取得
        
        Returns:
            List[Dict[str, Any]]: メモリマップ情報のリスト
        """
        return [
            {
                'start': f"${m.start_address:04X}",
                'end': f"${m.end_address:04X}",
                'size': m.size,
                'device': m.name
            }
            for m in self._mappings
        ]
    
    def get_debug_info(self) -> Dict[str, Any]:
        """デバッグ情報取得
        
        Returns:
            Dict[str, Any]: システムバスのデバッグ情報
        """
        return {
            'mappings_count': len(self._mappings),
            'bus_masters': [m.name for m in self._bus_masters],
            'current_master': self._current_master.name if self._current_master else None,
            'debug_enabled': self._debug_enabled,
            'access_log_size': len(self._access_log)
        }
    
    def _find_device_mapping(self, address: int) -> Optional[DeviceMapping]:
        """デバイスマッピング検索
        
        Args:
            address: 検索するアドレス
            
        Returns:
            Optional[DeviceMapping]: 見つかったマッピング（存在しない場合はNone）
        """
        for mapping in self._mappings:
            if mapping.contains(address):
                return mapping
        return None
    
    def _validate_address(self, address: int) -> bool:
        """アドレス検証
        
        Args:
            address: 検証するアドレス
            
        Returns:
            bool: 有効なアドレスの場合True
        """
        return 0 <= address <= 0xFFFF
    
    def _validate_value(self, value: int) -> bool:
        """値検証
        
        Args:
            value: 検証する値
            
        Returns:
            bool: 有効な値の場合True
        """
        return 0 <= value <= 0xFF
    
    def _log_access(self, operation: str, address: int, value: int, device: str) -> None:
        """アクセスログ記録
        
        Args:
            operation: 操作種別（READ/WRITE）
            address: アクセスアドレス
            value: アクセス値
            device: デバイス名
        """
        log_entry = {
            'operation': operation,
            'address': address,
            'value': value,
            'device': device,
            'master': self._current_master.name if self._current_master else 'CPU'
        }
        self._access_log.append(log_entry)
        
        # ログサイズ制限
        if len(self._access_log) > 1000:
            self._access_log = self._access_log[-500:]
