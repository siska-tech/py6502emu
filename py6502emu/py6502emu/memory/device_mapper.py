"""
デバイスマッピング管理

W65C02S エミュレータのデバイス動的マッピング機能を提供します。
アドレス範囲重複検出、マッピング情報管理、アドレス変換機能を含みます。
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from ..core.device import Device, DeviceError


class DeviceMappingError(DeviceError):
    """デバイスマッピング例外"""
    pass


class AddressOverlapError(DeviceMappingError):
    """アドレス重複例外"""
    
    def __init__(self, start: int, end: int, existing_name: str) -> None:
        self.start = start
        self.end = end
        self.existing_name = existing_name
        super().__init__(
            f"Address range ${start:04X}-${end:04X} overlaps with existing device '{existing_name}'"
        )


@dataclass
class DeviceMapping:
    """デバイスマッピング情報"""
    device: Device
    start_address: int
    end_address: int
    name: str
    device_offset: int = 0  # デバイス内アドレスオフセット
    read_only: bool = False
    
    def __post_init__(self) -> None:
        """初期化後処理"""
        if self.start_address > self.end_address:
            raise ValueError("Start address must be <= end address")
        
        if not (0x0000 <= self.start_address <= 0xFFFF):
            raise ValueError(f"Start address must be 0x0000-0xFFFF, got 0x{self.start_address:04X}")
        
        if not (0x0000 <= self.end_address <= 0xFFFF):
            raise ValueError(f"End address must be 0x0000-0xFFFF, got 0x{self.end_address:04X}")
    
    @property
    def size(self) -> int:
        """マッピングサイズ（バイト数）"""
        return self.end_address - self.start_address + 1
    
    def contains_address(self, address: int) -> bool:
        """アドレスがマッピング範囲内かチェック"""
        return self.start_address <= address <= self.end_address
    
    def overlaps_with(self, start: int, end: int) -> bool:
        """指定範囲との重複チェック"""
        return not (end < self.start_address or start > self.end_address)
    
    def get_device_address(self, system_address: int) -> int:
        """システムアドレスをデバイスアドレスに変換"""
        if not self.contains_address(system_address):
            raise ValueError(f"Address 0x{system_address:04X} is not in mapping range")
        
        return (system_address - self.start_address) + self.device_offset


class DeviceMapper:
    """デバイスマッピング管理クラス
    
    システム内のデバイスの動的マッピングを管理し、
    アドレス範囲重複検出、マッピング情報管理、アドレス変換機能を提供します。
    """
    
    def __init__(self):
        """デバイスマッパーを初期化"""
        self._mappings: List[DeviceMapping] = []
        self._name_to_mapping: Dict[str, DeviceMapping] = {}
    
    def map_device(
        self, 
        device: Device, 
        start_address: int, 
        end_address: int, 
        name: str = "",
        device_offset: int = 0,
        read_only: bool = False
    ) -> None:
        """デバイスマッピング登録
        
        Args:
            device: マッピングするデバイス
            start_address: 開始アドレス
            end_address: 終了アドレス（含む）
            name: マッピング名（空の場合はデバイス名を使用）
            device_offset: デバイス内アドレスオフセット
            read_only: 読み取り専用フラグ
            
        Raises:
            AddressOverlapError: アドレス範囲が重複している場合
            ValueError: パラメータが不正な場合
        """
        if not name:
            name = device.name
        
        # 重複チェック
        existing_mapping = self._find_overlapping_mapping(start_address, end_address)
        if existing_mapping:
            raise AddressOverlapError(start_address, end_address, existing_mapping.name)
        
        # 名前重複チェック
        if name in self._name_to_mapping:
            raise DeviceMappingError(f"Device name '{name}' already exists")
        
        # マッピング作成・登録
        mapping = DeviceMapping(
            device=device,
            start_address=start_address,
            end_address=end_address,
            name=name,
            device_offset=device_offset,
            read_only=read_only
        )
        
        self._mappings.append(mapping)
        self._name_to_mapping[name] = mapping
        
        # アドレス順でソート（検索効率化）
        self._mappings.sort(key=lambda m: m.start_address)
    
    def unmap_device(self, start_address: int, end_address: int) -> None:
        """デバイスマッピング解除（アドレス範囲指定）
        
        Args:
            start_address: 開始アドレス
            end_address: 終了アドレス（含む）
            
        Raises:
            DeviceMappingError: 指定範囲にマッピングが存在しない場合
        """
        mapping = self._find_exact_mapping(start_address, end_address)
        if not mapping:
            raise DeviceMappingError(
                f"No mapping found for range ${start_address:04X}-${end_address:04X}"
            )
        
        self._remove_mapping(mapping)
    
    def unmap_device_by_name(self, name: str) -> None:
        """デバイスマッピング解除（名前指定）
        
        Args:
            name: マッピング名
            
        Raises:
            DeviceMappingError: 指定名のマッピングが存在しない場合
        """
        mapping = self._name_to_mapping.get(name)
        if not mapping:
            raise DeviceMappingError(f"No mapping found with name '{name}'")
        
        self._remove_mapping(mapping)
    
    def find_device(self, address: int) -> Optional[DeviceMapping]:
        """アドレスに対応するデバイス検索
        
        Args:
            address: 検索するアドレス
            
        Returns:
            対応するデバイスマッピング（見つからない場合はNone）
        """
        # バイナリサーチで効率的に検索
        left, right = 0, len(self._mappings) - 1
        
        while left <= right:
            mid = (left + right) // 2
            mapping = self._mappings[mid]
            
            if mapping.contains_address(address):
                return mapping
            elif address < mapping.start_address:
                right = mid - 1
            else:
                left = mid + 1
        
        return None
    
    def get_device_by_name(self, name: str) -> Optional[DeviceMapping]:
        """名前でデバイスマッピング取得
        
        Args:
            name: マッピング名
            
        Returns:
            対応するデバイスマッピング（見つからない場合はNone）
        """
        return self._name_to_mapping.get(name)
    
    def get_memory_map(self) -> List[Dict[str, Any]]:
        """メモリマップ情報取得
        
        Returns:
            メモリマップ情報のリスト
        """
        memory_map = []
        
        for mapping in self._mappings:
            memory_map.append({
                'name': mapping.name,
                'start_address': mapping.start_address,
                'end_address': mapping.end_address,
                'size': mapping.size,
                'device_offset': mapping.device_offset,
                'read_only': mapping.read_only,
                'device_name': mapping.device.name
            })
        
        return memory_map
    
    def get_unmapped_ranges(self) -> List[Dict[str, int]]:
        """未マッピング領域取得
        
        Returns:
            未マッピング領域のリスト
        """
        unmapped_ranges = []
        current_address = 0x0000
        
        for mapping in self._mappings:
            if current_address < mapping.start_address:
                unmapped_ranges.append({
                    'start_address': current_address,
                    'end_address': mapping.start_address - 1,
                    'size': mapping.start_address - current_address
                })
            
            current_address = max(current_address, mapping.end_address + 1)
        
        # 最後の未マッピング領域
        if current_address <= 0xFFFF:
            unmapped_ranges.append({
                'start_address': current_address,
                'end_address': 0xFFFF,
                'size': 0x10000 - current_address
            })
        
        return unmapped_ranges
    
    def validate_mapping_integrity(self) -> List[str]:
        """マッピング整合性チェック
        
        Returns:
            検出された問題のリスト（問題がない場合は空リスト）
        """
        issues = []
        
        # 重複チェック
        for i, mapping1 in enumerate(self._mappings):
            for j, mapping2 in enumerate(self._mappings[i + 1:], i + 1):
                if mapping1.overlaps_with(mapping2.start_address, mapping2.end_address):
                    issues.append(
                        f"Overlap detected: '{mapping1.name}' and '{mapping2.name}'"
                    )
        
        # 名前マッピング整合性チェック
        for name, mapping in self._name_to_mapping.items():
            if mapping not in self._mappings:
                issues.append(f"Name mapping inconsistency for '{name}'")
        
        # ソート順チェック
        for i in range(len(self._mappings) - 1):
            if self._mappings[i].start_address > self._mappings[i + 1].start_address:
                issues.append("Mapping list is not properly sorted")
                break
        
        return issues
    
    def clear_all_mappings(self) -> None:
        """全マッピング削除"""
        self._mappings.clear()
        self._name_to_mapping.clear()
    
    def get_mapping_count(self) -> int:
        """マッピング数取得"""
        return len(self._mappings)
    
    def get_total_mapped_size(self) -> int:
        """総マッピングサイズ取得"""
        return sum(mapping.size for mapping in self._mappings)
    
    def _find_overlapping_mapping(self, start: int, end: int) -> Optional[DeviceMapping]:
        """重複するマッピングを検索"""
        for mapping in self._mappings:
            if mapping.overlaps_with(start, end):
                return mapping
        return None
    
    def _find_exact_mapping(self, start: int, end: int) -> Optional[DeviceMapping]:
        """完全一致するマッピングを検索"""
        for mapping in self._mappings:
            if mapping.start_address == start and mapping.end_address == end:
                return mapping
        return None
    
    def _remove_mapping(self, mapping: DeviceMapping) -> None:
        """マッピング削除"""
        self._mappings.remove(mapping)
        del self._name_to_mapping[mapping.name]
