"""
アドレス空間管理

W65C02S エミュレータの64KBアドレス空間管理を提供します。
リトルエンディアン処理、ゼロページ・スタックページの特別処理を含みます。
"""

from typing import Optional


class AddressSpace:
    """64KBアドレス空間管理クラス
    
    W65C02Sの64KBフラットアドレス空間を管理し、
    リトルエンディアン16ビット値処理、ゼロページ・スタックページの
    特別処理を提供します。
    """
    
    # アドレス空間定数
    ADDRESS_SPACE_SIZE = 0x10000  # 64KB
    ZERO_PAGE_START = 0x0000
    ZERO_PAGE_END = 0x00FF
    STACK_PAGE_START = 0x0100
    STACK_PAGE_END = 0x01FF
    STACK_BASE = 0x0100
    
    def __init__(self):
        """アドレス空間を初期化"""
        self._memory = bytearray(self.ADDRESS_SPACE_SIZE)
        self._read_only_regions: set[tuple[int, int]] = set()
    
    def read_byte(self, address: int) -> int:
        """8ビット読み取り
        
        Args:
            address: 読み取りアドレス (0x0000-0xFFFF)
            
        Returns:
            読み取った8ビット値 (0x00-0xFF)
            
        Raises:
            ValueError: アドレスが範囲外の場合
        """
        self._validate_address(address)
        return self._memory[address]
    
    def write_byte(self, address: int, value: int) -> None:
        """8ビット書き込み
        
        Args:
            address: 書き込みアドレス (0x0000-0xFFFF)
            value: 書き込む8ビット値 (0x00-0xFF)
            
        Raises:
            ValueError: アドレスまたは値が範囲外の場合
            PermissionError: 読み取り専用領域への書き込みの場合
        """
        self._validate_address(address)
        self._validate_byte_value(value)
        self._check_write_permission(address)
        
        self._memory[address] = value
    
    def read_word(self, address: int) -> int:
        """16ビット読み取り（リトルエンディアン）
        
        Args:
            address: 読み取りアドレス (0x0000-0xFFFE)
            
        Returns:
            読み取った16ビット値 (0x0000-0xFFFF)
            
        Raises:
            ValueError: アドレスが範囲外の場合
        """
        self._validate_word_address(address)
        
        low_byte = self.read_byte(address)
        high_byte = self.read_byte(address + 1)
        
        return low_byte | (high_byte << 8)
    
    def write_word(self, address: int, value: int) -> None:
        """16ビット書き込み（リトルエンディアン）
        
        Args:
            address: 書き込みアドレス (0x0000-0xFFFE)
            value: 書き込む16ビット値 (0x0000-0xFFFF)
            
        Raises:
            ValueError: アドレスまたは値が範囲外の場合
            PermissionError: 読み取り専用領域への書き込みの場合
        """
        self._validate_word_address(address)
        self._validate_word_value(value)
        
        low_byte = value & 0xFF
        high_byte = (value >> 8) & 0xFF
        
        self.write_byte(address, low_byte)
        self.write_byte(address + 1, high_byte)
    
    def get_zero_page_address(self, offset: int) -> int:
        """ゼロページアドレス計算
        
        Args:
            offset: ゼロページ内オフセット (0x00-0xFF)
            
        Returns:
            ゼロページアドレス (0x0000-0x00FF)
            
        Raises:
            ValueError: オフセットが範囲外の場合
        """
        if not (0x00 <= offset <= 0xFF):
            raise ValueError(f"Zero page offset must be 0x00-0xFF, got 0x{offset:02X}")
        
        return self.ZERO_PAGE_START + offset
    
    def get_stack_address(self, sp: int) -> int:
        """スタックアドレス計算
        
        Args:
            sp: スタックポインタ値 (0x00-0xFF)
            
        Returns:
            スタックアドレス (0x0100-0x01FF)
            
        Raises:
            ValueError: スタックポインタが範囲外の場合
        """
        if not (0x00 <= sp <= 0xFF):
            raise ValueError(f"Stack pointer must be 0x00-0xFF, got 0x{sp:02X}")
        
        return self.STACK_BASE + sp
    
    def is_zero_page(self, address: int) -> bool:
        """ゼロページアドレス判定
        
        Args:
            address: 判定するアドレス
            
        Returns:
            ゼロページアドレスの場合True
        """
        return self.ZERO_PAGE_START <= address <= self.ZERO_PAGE_END
    
    def is_stack_page(self, address: int) -> bool:
        """スタックページアドレス判定
        
        Args:
            address: 判定するアドレス
            
        Returns:
            スタックページアドレスの場合True
        """
        return self.STACK_PAGE_START <= address <= self.STACK_PAGE_END
    
    def set_read_only_region(self, start_address: int, end_address: int) -> None:
        """読み取り専用領域設定
        
        Args:
            start_address: 開始アドレス
            end_address: 終了アドレス（含む）
            
        Raises:
            ValueError: アドレス範囲が不正な場合
        """
        self._validate_address(start_address)
        self._validate_address(end_address)
        
        if start_address > end_address:
            raise ValueError("Start address must be <= end address")
        
        self._read_only_regions.add((start_address, end_address))
    
    def clear_read_only_region(self, start_address: int, end_address: int) -> None:
        """読み取り専用領域解除
        
        Args:
            start_address: 開始アドレス
            end_address: 終了アドレス（含む）
        """
        self._read_only_regions.discard((start_address, end_address))
    
    def fill_memory(self, start_address: int, size: int, value: int) -> None:
        """メモリ領域を指定値で埋める
        
        Args:
            start_address: 開始アドレス
            size: サイズ（バイト数）
            value: 埋める値 (0x00-0xFF)
            
        Raises:
            ValueError: パラメータが範囲外の場合
            PermissionError: 読み取り専用領域への書き込みの場合
        """
        self._validate_address(start_address)
        self._validate_byte_value(value)
        
        if size <= 0:
            raise ValueError("Size must be positive")
        
        end_address = start_address + size - 1
        if end_address >= self.ADDRESS_SPACE_SIZE:
            raise ValueError("Fill operation exceeds address space")
        
        for addr in range(start_address, start_address + size):
            self._check_write_permission(addr)
        
        # 全チェック通過後に実際の書き込み実行
        for addr in range(start_address, start_address + size):
            self._memory[addr] = value
    
    def copy_memory(self, src_address: int, dest_address: int, size: int) -> None:
        """メモリ領域コピー
        
        Args:
            src_address: コピー元アドレス
            dest_address: コピー先アドレス
            size: コピーサイズ（バイト数）
            
        Raises:
            ValueError: パラメータが範囲外の場合
            PermissionError: 読み取り専用領域への書き込みの場合
        """
        self._validate_address(src_address)
        self._validate_address(dest_address)
        
        if size <= 0:
            raise ValueError("Size must be positive")
        
        if src_address + size > self.ADDRESS_SPACE_SIZE:
            raise ValueError("Source copy exceeds address space")
        
        if dest_address + size > self.ADDRESS_SPACE_SIZE:
            raise ValueError("Destination copy exceeds address space")
        
        # 書き込み権限チェック
        for addr in range(dest_address, dest_address + size):
            self._check_write_permission(addr)
        
        # 重複領域を考慮したコピー
        if src_address < dest_address < src_address + size:
            # 後方からコピー（重複領域対応）
            for i in range(size - 1, -1, -1):
                self._memory[dest_address + i] = self._memory[src_address + i]
        else:
            # 前方からコピー
            for i in range(size):
                self._memory[dest_address + i] = self._memory[src_address + i]
    
    def get_memory_dump(self, start_address: int, size: int) -> bytes:
        """メモリダンプ取得
        
        Args:
            start_address: 開始アドレス
            size: ダンプサイズ（バイト数）
            
        Returns:
            メモリ内容のバイト列
            
        Raises:
            ValueError: パラメータが範囲外の場合
        """
        self._validate_address(start_address)
        
        if size <= 0:
            raise ValueError("Size must be positive")
        
        if start_address + size > self.ADDRESS_SPACE_SIZE:
            raise ValueError("Dump exceeds address space")
        
        return bytes(self._memory[start_address:start_address + size])
    
    def _validate_address(self, address: int) -> None:
        """アドレス範囲検証"""
        if not (0x0000 <= address <= 0xFFFF):
            raise ValueError(f"Address must be 0x0000-0xFFFF, got 0x{address:04X}")
    
    def _validate_word_address(self, address: int) -> None:
        """16ビットアクセス用アドレス範囲検証"""
        if not (0x0000 <= address <= 0xFFFE):
            raise ValueError(f"Word address must be 0x0000-0xFFFE, got 0x{address:04X}")
    
    def _validate_byte_value(self, value: int) -> None:
        """8ビット値範囲検証"""
        if not (0x00 <= value <= 0xFF):
            raise ValueError(f"Byte value must be 0x00-0xFF, got 0x{value:02X}")
    
    def _validate_word_value(self, value: int) -> None:
        """16ビット値範囲検証"""
        if not (0x0000 <= value <= 0xFFFF):
            raise ValueError(f"Word value must be 0x0000-0xFFFF, got 0x{value:04X}")
    
    def _check_write_permission(self, address: int) -> None:
        """書き込み権限チェック"""
        for start, end in self._read_only_regions:
            if start <= address <= end:
                raise PermissionError(f"Cannot write to read-only address 0x{address:04X}")
