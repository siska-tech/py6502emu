"""
メモリアクセス制御

W65C02S エミュレータの統合メモリアクセス制御を提供します。
メモリとデバイスのルーティング、アクセス権限チェック、ログ機能を含みます。
"""

from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum, auto
import time

from .address_space import AddressSpace
from .device_mapper import DeviceMapper, DeviceMapping
from ..core.device import Device, InvalidAddressError, InvalidValueError


class AccessType(Enum):
    """アクセス種別"""
    READ = auto()
    WRITE = auto()


@dataclass
class AccessLog:
    """アクセスログエントリ"""
    timestamp: float
    access_type: AccessType
    address: int
    value: int
    device_name: Optional[str] = None
    cycles: int = 1


class MemoryAccessError(Exception):
    """メモリアクセス例外"""
    pass


class MemoryController:
    """メモリアクセス制御クラス
    
    システム全体のメモリアクセスを統合的に制御し、
    AddressSpaceとDeviceMapperを組み合わせて
    統一されたメモリインターフェイスを提供します。
    """
    
    def __init__(self, address_space: AddressSpace, device_mapper: DeviceMapper):
        """メモリコントローラを初期化
        
        Args:
            address_space: アドレス空間管理オブジェクト
            device_mapper: デバイスマッピング管理オブジェクト
        """
        self._address_space = address_space
        self._device_mapper = device_mapper
        
        # アクセスログ機能
        self._access_logging_enabled = False
        self._access_log: List[AccessLog] = []
        self._max_log_entries = 10000
        
        # パフォーマンス統計
        self._access_count = {'read': 0, 'write': 0}
        self._device_access_count: Dict[str, Dict[str, int]] = {}
        
        # アクセスフック（デバッグ・トレース用）
        self._read_hooks: List[Callable[[int, int], None]] = []
        self._write_hooks: List[Callable[[int, int], None]] = []
        
        # キャッシュ（最後にアクセスしたデバイスマッピング）
        self._last_mapping: Optional[DeviceMapping] = None
        self._last_address_range: Optional[tuple[int, int]] = None
    
    def read(self, address: int) -> int:
        """統合メモリ読み取り
        
        指定されたアドレスからデータを読み取ります。
        デバイスがマッピングされている場合はデバイスから、
        そうでなければアドレス空間から読み取ります。
        
        Args:
            address: 読み取りアドレス (0x0000-0xFFFF)
            
        Returns:
            読み取った8ビット値 (0x00-0xFF)
            
        Raises:
            InvalidAddressError: 無効なアドレスが指定された場合
            MemoryAccessError: メモリアクセスエラーが発生した場合
        """
        self._validate_address(address)
        
        try:
            # デバイスマッピングチェック
            device_mapping = self._find_device_mapping(address)
            
            if device_mapping:
                # デバイスから読み取り
                device_address = device_mapping.get_device_address(address)
                value = device_mapping.device.read(device_address)
                device_name = device_mapping.name
            else:
                # アドレス空間から読み取り
                value = self._address_space.read_byte(address)
                device_name = None
            
            # 統計・ログ更新
            self._update_access_stats('read', device_name)
            self._log_access(AccessType.READ, address, value, device_name)
            
            # フック実行
            for hook in self._read_hooks:
                hook(address, value)
            
            return value
            
        except Exception as e:
            raise MemoryAccessError(f"Read error at ${address:04X}: {e}") from e
    
    def write(self, address: int, value: int) -> None:
        """統合メモリ書き込み
        
        指定されたアドレスにデータを書き込みます。
        デバイスがマッピングされている場合はデバイスに、
        そうでなければアドレス空間に書き込みます。
        
        Args:
            address: 書き込みアドレス (0x0000-0xFFFF)
            value: 書き込み値 (0x00-0xFF)
            
        Raises:
            InvalidAddressError: 無効なアドレスが指定された場合
            InvalidValueError: 無効な値が指定された場合
            MemoryAccessError: メモリアクセスエラーが発生した場合
            PermissionError: 読み取り専用領域への書き込みの場合
        """
        self._validate_address(address)
        self._validate_byte_value(value)
        
        try:
            # デバイスマッピングチェック
            device_mapping = self._find_device_mapping(address)
            
            if device_mapping:
                # 読み取り専用チェック
                if device_mapping.read_only:
                    raise PermissionError(
                        f"Cannot write to read-only device '{device_mapping.name}' at ${address:04X}"
                    )
                
                # デバイスに書き込み
                device_address = device_mapping.get_device_address(address)
                device_mapping.device.write(device_address, value)
                device_name = device_mapping.name
            else:
                # アドレス空間に書き込み
                self._address_space.write_byte(address, value)
                device_name = None
            
            # 統計・ログ更新
            self._update_access_stats('write', device_name)
            self._log_access(AccessType.WRITE, address, value, device_name)
            
            # フック実行
            for hook in self._write_hooks:
                hook(address, value)
                
        except Exception as e:
            raise MemoryAccessError(f"Write error at ${address:04X}: {e}") from e
    
    def read_word(self, address: int) -> int:
        """16ビット読み取り（リトルエンディアン）
        
        Args:
            address: 読み取りアドレス (0x0000-0xFFFE)
            
        Returns:
            読み取った16ビット値 (0x0000-0xFFFF)
        """
        if not (0x0000 <= address <= 0xFFFE):
            raise InvalidAddressError(address)
        
        low_byte = self.read(address)
        high_byte = self.read(address + 1)
        
        return low_byte | (high_byte << 8)
    
    def write_word(self, address: int, value: int) -> None:
        """16ビット書き込み（リトルエンディアン）
        
        Args:
            address: 書き込みアドレス (0x0000-0xFFFE)
            value: 書き込み値 (0x0000-0xFFFF)
        """
        if not (0x0000 <= address <= 0xFFFE):
            raise InvalidAddressError(address)
        
        if not (0x0000 <= value <= 0xFFFF):
            raise InvalidValueError(value)
        
        low_byte = value & 0xFF
        high_byte = (value >> 8) & 0xFF
        
        self.write(address, low_byte)
        self.write(address + 1, high_byte)
    
    def bulk_read(self, start_address: int, size: int) -> bytes:
        """バルク読み取り
        
        Args:
            start_address: 開始アドレス
            size: 読み取りサイズ（バイト数）
            
        Returns:
            読み取ったデータ
        """
        if size <= 0:
            raise ValueError("Size must be positive")
        
        if start_address + size > 0x10000:
            raise ValueError("Bulk read exceeds address space")
        
        data = bytearray(size)
        for i in range(size):
            data[i] = self.read(start_address + i)
        
        return bytes(data)
    
    def bulk_write(self, start_address: int, data: bytes) -> None:
        """バルク書き込み
        
        Args:
            start_address: 開始アドレス
            data: 書き込みデータ
        """
        if not data:
            return
        
        if start_address + len(data) > 0x10000:
            raise ValueError("Bulk write exceeds address space")
        
        for i, byte_value in enumerate(data):
            self.write(start_address + i, byte_value)
    
    def enable_access_logging(self, enabled: bool = True) -> None:
        """アクセスログ機能の有効/無効切り替え"""
        self._access_logging_enabled = enabled
        if not enabled:
            self._access_log.clear()
    
    def get_access_log(self, last_n: Optional[int] = None) -> List[AccessLog]:
        """アクセスログ取得
        
        Args:
            last_n: 取得する最新エントリ数（Noneの場合は全て）
            
        Returns:
            アクセスログエントリのリスト
        """
        if last_n is None:
            return self._access_log.copy()
        else:
            return self._access_log[-last_n:] if last_n > 0 else []
    
    def clear_access_log(self) -> None:
        """アクセスログクリア"""
        self._access_log.clear()
    
    def add_read_hook(self, hook: Callable[[int, int], None]) -> None:
        """読み取りフック追加
        
        Args:
            hook: フック関数 (address, value) -> None
        """
        self._read_hooks.append(hook)
    
    def add_write_hook(self, hook: Callable[[int, int], None]) -> None:
        """書き込みフック追加
        
        Args:
            hook: フック関数 (address, value) -> None
        """
        self._write_hooks.append(hook)
    
    def remove_read_hook(self, hook: Callable[[int, int], None]) -> None:
        """読み取りフック削除"""
        if hook in self._read_hooks:
            self._read_hooks.remove(hook)
    
    def remove_write_hook(self, hook: Callable[[int, int], None]) -> None:
        """書き込みフック削除"""
        if hook in self._write_hooks:
            self._write_hooks.remove(hook)
    
    def get_access_statistics(self) -> Dict[str, Any]:
        """アクセス統計取得
        
        Returns:
            アクセス統計情報
        """
        return {
            'total_reads': self._access_count['read'],
            'total_writes': self._access_count['write'],
            'device_access_count': self._device_access_count.copy(),
            'log_entries': len(self._access_log),
            'logging_enabled': self._access_logging_enabled
        }
    
    def reset_statistics(self) -> None:
        """統計情報リセット"""
        self._access_count = {'read': 0, 'write': 0}
        self._device_access_count.clear()
        self._access_log.clear()
    
    def get_memory_map_info(self) -> Dict[str, Any]:
        """メモリマップ情報取得
        
        Returns:
            メモリマップの詳細情報
        """
        device_mappings = self._device_mapper.get_memory_map()
        unmapped_ranges = self._device_mapper.get_unmapped_ranges()
        
        return {
            'device_mappings': device_mappings,
            'unmapped_ranges': unmapped_ranges,
            'total_mapped_size': self._device_mapper.get_total_mapped_size(),
            'mapping_count': self._device_mapper.get_mapping_count()
        }
    
    def validate_system_integrity(self) -> List[str]:
        """システム整合性チェック
        
        Returns:
            検出された問題のリスト
        """
        issues = []
        
        # デバイスマッピング整合性チェック
        mapping_issues = self._device_mapper.validate_mapping_integrity()
        issues.extend(mapping_issues)
        
        # その他のチェックを追加可能
        
        return issues
    
    def _find_device_mapping(self, address: int) -> Optional[DeviceMapping]:
        """デバイスマッピング検索（キャッシュ付き）"""
        # キャッシュチェック
        if (self._last_mapping and 
            self._last_address_range and
            self._last_address_range[0] <= address <= self._last_address_range[1]):
            return self._last_mapping
        
        # 新規検索
        mapping = self._device_mapper.find_device(address)
        
        # キャッシュ更新
        if mapping:
            self._last_mapping = mapping
            self._last_address_range = (mapping.start_address, mapping.end_address)
        else:
            self._last_mapping = None
            self._last_address_range = None
        
        return mapping
    
    def _validate_address(self, address: int) -> None:
        """アドレス範囲検証"""
        if not (0x0000 <= address <= 0xFFFF):
            raise InvalidAddressError(address)
    
    def _validate_byte_value(self, value: int) -> None:
        """8ビット値範囲検証"""
        if not (0x00 <= value <= 0xFF):
            raise InvalidValueError(value)
    
    def _update_access_stats(self, access_type: str, device_name: Optional[str]) -> None:
        """アクセス統計更新"""
        self._access_count[access_type] += 1
        
        if device_name:
            if device_name not in self._device_access_count:
                self._device_access_count[device_name] = {'read': 0, 'write': 0}
            self._device_access_count[device_name][access_type] += 1
    
    def _log_access(
        self, 
        access_type: AccessType, 
        address: int, 
        value: int, 
        device_name: Optional[str]
    ) -> None:
        """アクセスログ記録"""
        if not self._access_logging_enabled:
            return
        
        # ログエントリ数制限
        if len(self._access_log) >= self._max_log_entries:
            self._access_log.pop(0)  # 古いエントリを削除
        
        log_entry = AccessLog(
            timestamp=time.time(),
            access_type=access_type,
            address=address,
            value=value,
            device_name=device_name
        )
        
        self._access_log.append(log_entry)
