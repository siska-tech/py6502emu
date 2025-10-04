"""
アドレッシングモード計算
PU005: AddressingModes

W65C02S CPUの16種類のアドレッシングモードの計算を行います。
"""

from typing import Tuple, Optional, Protocol
from enum import Enum, auto
from .registers import CPURegisters


class AddressingMode(Enum):
    """アドレッシングモード定義"""
    IMPLICIT = auto()           # 暗黙
    ACCUMULATOR = auto()        # アキュムレータ
    IMMEDIATE = auto()          # 即値 #$nn
    ZERO_PAGE = auto()          # ゼロページ $nn
    ZERO_PAGE_X = auto()        # ゼロページ,X $nn,X
    ZERO_PAGE_Y = auto()        # ゼロページ,Y $nn,Y
    ABSOLUTE = auto()           # 絶対 $nnnn
    ABSOLUTE_X = auto()         # 絶対,X $nnnn,X
    ABSOLUTE_Y = auto()         # 絶対,Y $nnnn,Y
    INDIRECT = auto()           # 間接 ($nnnn)
    INDIRECT_X = auto()         # 間接,X ($nn,X)
    INDIRECT_Y = auto()         # 間接,Y ($nn),Y
    INDIRECT_ZP = auto()        # ゼロページ間接 ($nn) - W65C02S拡張
    INDIRECT_ABS_X = auto()     # 絶対間接,X ($nnnn,X) - W65C02S拡張
    RELATIVE = auto()           # 相対 $nn
    STACK = auto()              # スタック


class MemoryInterface(Protocol):
    """メモリインターフェイス"""
    
    def read(self, address: int) -> int:
        """メモリ読み取り"""
        ...
    
    def write(self, address: int, value: int) -> None:
        """メモリ書き込み"""
        ...


class AddressingResult:
    """アドレッシング結果
    
    アドレッシングモード計算の結果を格納するクラス。
    """
    
    def __init__(self, 
                 address: Optional[int] = None,
                 value: Optional[int] = None,
                 page_crossed: bool = False,
                 extra_cycles: int = 0) -> None:
        """初期化
        
        Args:
            address: 計算されたアドレス
            value: 即値の場合の値
            page_crossed: ページクロスが発生したか
            extra_cycles: 追加サイクル数
        """
        self.address = address
        self.value = value
        self.page_crossed = page_crossed
        self.extra_cycles = extra_cycles
    
    def __repr__(self) -> str:
        address_str = f"{self.address:#06x}" if self.address is not None else "None"
        value_str = f"{self.value:#04x}" if self.value is not None else "None"
        return (f"AddressingResult(address={address_str}, "
                f"value={value_str}, "
                f"page_crossed={self.page_crossed}, extra_cycles={self.extra_cycles})")


class AddressingModes:
    """W65C02S アドレッシングモード計算クラス
    
    W65C02Sの16種類のアドレッシングモードの計算を行います。
    ページクロスペナルティの検出も含みます。
    """
    
    def __init__(self, registers: CPURegisters, memory: MemoryInterface) -> None:
        """初期化
        
        Args:
            registers: CPUレジスタ管理オブジェクト
            memory: メモリインターフェイス
        """
        self._registers = registers
        self._memory = memory
    
    def _check_page_cross(self, base_address: int, offset: int) -> bool:
        """ページクロスチェック
        
        Args:
            base_address: ベースアドレス
            offset: オフセット
            
        Returns:
            bool: ページクロスが発生したか
        """
        return (base_address & 0xFF00) != ((base_address + offset) & 0xFF00)
    
    def _read_word(self, address: int) -> int:
        """16ビット値読み取り
        
        指定されたアドレスから16ビット値をリトルエンディアンで読み取ります。
        
        Args:
            address: 読み取りアドレス
            
        Returns:
            int: 読み取った16ビット値
        """
        low = self._memory.read(address & 0xFFFF)
        high = self._memory.read((address + 1) & 0xFFFF)
        return low | (high << 8)
    
    def _read_word_bug(self, address: int) -> int:
        """16ビット値読み取り（JMP間接バグ対応）
        
        NMOS 6502のJMP間接命令のページ境界バグを再現します。
        W65C02Sではこのバグは修正されていますが、互換性のため残しています。
        
        Args:
            address: 読み取りアドレス
            
        Returns:
            int: 読み取った16ビット値
        """
        low = self._memory.read(address)
        # ページ境界でのバグ: 上位バイトは同一ページ内から読み取り
        high_addr = (address & 0xFF00) | ((address + 1) & 0x00FF)
        high = self._memory.read(high_addr)
        return low | (high << 8)
    
    def implicit(self) -> AddressingResult:
        """暗黙アドレッシング
        
        オペランドを持たない命令用。
        
        Returns:
            AddressingResult: 結果（アドレス・値なし）
        """
        return AddressingResult()
    
    def accumulator(self) -> AddressingResult:
        """アキュムレータアドレッシング
        
        アキュムレータを対象とする命令用。
        
        Returns:
            AddressingResult: 結果（アキュムレータの値）
        """
        return AddressingResult(value=self._registers.a)
    
    def immediate(self, operand: int) -> AddressingResult:
        """即値アドレッシング #$nn
        
        Args:
            operand: 即値オペランド
            
        Returns:
            AddressingResult: 結果（即値）
        """
        return AddressingResult(value=operand & 0xFF)
    
    def zero_page(self, operand: int) -> AddressingResult:
        """ゼロページアドレッシング $nn
        
        Args:
            operand: ゼロページアドレス
            
        Returns:
            AddressingResult: 結果（ゼロページアドレス）
        """
        address = operand & 0xFF
        return AddressingResult(address=address)
    
    def zero_page_x(self, operand: int) -> AddressingResult:
        """ゼロページ,X アドレッシング $nn,X
        
        Args:
            operand: ベースゼロページアドレス
            
        Returns:
            AddressingResult: 結果（インデックス付きゼロページアドレス）
        """
        address = (operand + self._registers.x) & 0xFF
        return AddressingResult(address=address)
    
    def zero_page_y(self, operand: int) -> AddressingResult:
        """ゼロページ,Y アドレッシング $nn,Y
        
        Args:
            operand: ベースゼロページアドレス
            
        Returns:
            AddressingResult: 結果（インデックス付きゼロページアドレス）
        """
        address = (operand + self._registers.y) & 0xFF
        return AddressingResult(address=address)
    
    def absolute(self, operand: int) -> AddressingResult:
        """絶対アドレッシング $nnnn
        
        Args:
            operand: 絶対アドレス
            
        Returns:
            AddressingResult: 結果（絶対アドレス）
        """
        address = operand & 0xFFFF
        return AddressingResult(address=address)
    
    def absolute_x(self, operand: int) -> AddressingResult:
        """絶対,X アドレッシング $nnnn,X
        
        Args:
            operand: ベース絶対アドレス
            
        Returns:
            AddressingResult: 結果（インデックス付き絶対アドレス、ページクロス情報含む）
        """
        base_address = operand & 0xFFFF
        address = (base_address + self._registers.x) & 0xFFFF
        page_crossed = self._check_page_cross(base_address, self._registers.x)
        extra_cycles = 1 if page_crossed else 0
        
        return AddressingResult(address=address, page_crossed=page_crossed, extra_cycles=extra_cycles)
    
    def absolute_y(self, operand: int) -> AddressingResult:
        """絶対,Y アドレッシング $nnnn,Y
        
        Args:
            operand: ベース絶対アドレス
            
        Returns:
            AddressingResult: 結果（インデックス付き絶対アドレス、ページクロス情報含む）
        """
        base_address = operand & 0xFFFF
        address = (base_address + self._registers.y) & 0xFFFF
        page_crossed = self._check_page_cross(base_address, self._registers.y)
        extra_cycles = 1 if page_crossed else 0
        
        return AddressingResult(address=address, page_crossed=page_crossed, extra_cycles=extra_cycles)
    
    def indirect(self, operand: int) -> AddressingResult:
        """間接アドレッシング ($nnnn)
        
        JMP命令専用。W65C02Sではページ境界バグが修正されています。
        
        Args:
            operand: 間接アドレス
            
        Returns:
            AddressingResult: 結果（間接アドレス）
        """
        indirect_address = operand & 0xFFFF
        # W65C02Sではページ境界バグが修正されている
        address = self._read_word(indirect_address)
        return AddressingResult(address=address)
    
    def indirect_x(self, operand: int) -> AddressingResult:
        """間接,X アドレッシング ($nn,X)
        
        Args:
            operand: ベースゼロページアドレス
            
        Returns:
            AddressingResult: 結果（間接アドレス）
        """
        zp_address = (operand + self._registers.x) & 0xFF
        address = self._read_word(zp_address)
        return AddressingResult(address=address)
    
    def indirect_y(self, operand: int) -> AddressingResult:
        """間接,Y アドレッシング ($nn),Y
        
        Args:
            operand: ゼロページアドレス
            
        Returns:
            AddressingResult: 結果（間接インデックスアドレス、ページクロス情報含む）
        """
        zp_address = operand & 0xFF
        base_address = self._read_word(zp_address)
        address = (base_address + self._registers.y) & 0xFFFF
        page_crossed = self._check_page_cross(base_address, self._registers.y)
        extra_cycles = 1 if page_crossed else 0
        
        return AddressingResult(address=address, page_crossed=page_crossed, extra_cycles=extra_cycles)
    
    def indirect_zp(self, operand: int) -> AddressingResult:
        """ゼロページ間接アドレッシング ($nn) - W65C02S拡張
        
        Args:
            operand: ゼロページアドレス
            
        Returns:
            AddressingResult: 結果（間接アドレス）
        """
        zp_address = operand & 0xFF
        address = self._read_word(zp_address)
        return AddressingResult(address=address)
    
    def indirect_abs_x(self, operand: int) -> AddressingResult:
        """絶対間接,X アドレッシング ($nnnn,X) - W65C02S拡張
        
        JMP命令専用の新しいアドレッシングモード。
        
        Args:
            operand: ベース絶対アドレス
            
        Returns:
            AddressingResult: 結果（間接インデックスアドレス）
        """
        base_address = operand & 0xFFFF
        indirect_address = (base_address + self._registers.x) & 0xFFFF
        address = self._read_word(indirect_address)
        return AddressingResult(address=address)
    
    def relative(self, operand: int) -> AddressingResult:
        """相対アドレッシング $nn
        
        分岐命令用。符号付き8ビットオフセットを現在のPCに加算します。
        
        Args:
            operand: 符号付きオフセット
            
        Returns:
            AddressingResult: 結果（分岐先アドレス、ページクロス情報含む）
        """
        # 符号付き8ビット値として解釈
        offset = operand if operand < 0x80 else operand - 0x100
        base_address = self._registers.pc
        address = (base_address + offset) & 0xFFFF
        page_crossed = self._check_page_cross(base_address, offset)
        extra_cycles = 1 if page_crossed else 0
        
        return AddressingResult(address=address, page_crossed=page_crossed, extra_cycles=extra_cycles)
    
    def stack(self) -> AddressingResult:
        """スタックアドレッシング
        
        スタック操作用。現在のスタックポインタに基づくアドレスを返します。
        
        Returns:
            AddressingResult: 結果（スタックアドレス）
        """
        address = self._registers.get_stack_address()
        return AddressingResult(address=address)
    
    def calculate_address(self, mode: AddressingMode, operand: Optional[int] = None) -> AddressingResult:
        """アドレッシングモード計算
        
        指定されたアドレッシングモードに基づいてアドレスまたは値を計算します。
        
        Args:
            mode: アドレッシングモード
            operand: オペランド（必要な場合）
            
        Returns:
            AddressingResult: 計算結果
            
        Raises:
            ValueError: 無効なアドレッシングモードまたはオペランド不足
        """
        if mode == AddressingMode.IMPLICIT:
            return self.implicit()
        elif mode == AddressingMode.ACCUMULATOR:
            return self.accumulator()
        elif mode == AddressingMode.IMMEDIATE:
            if operand is None:
                raise ValueError("Immediate addressing requires operand")
            return self.immediate(operand)
        elif mode == AddressingMode.ZERO_PAGE:
            if operand is None:
                raise ValueError("Zero page addressing requires operand")
            return self.zero_page(operand)
        elif mode == AddressingMode.ZERO_PAGE_X:
            if operand is None:
                raise ValueError("Zero page,X addressing requires operand")
            return self.zero_page_x(operand)
        elif mode == AddressingMode.ZERO_PAGE_Y:
            if operand is None:
                raise ValueError("Zero page,Y addressing requires operand")
            return self.zero_page_y(operand)
        elif mode == AddressingMode.ABSOLUTE:
            if operand is None:
                raise ValueError("Absolute addressing requires operand")
            return self.absolute(operand)
        elif mode == AddressingMode.ABSOLUTE_X:
            if operand is None:
                raise ValueError("Absolute,X addressing requires operand")
            return self.absolute_x(operand)
        elif mode == AddressingMode.ABSOLUTE_Y:
            if operand is None:
                raise ValueError("Absolute,Y addressing requires operand")
            return self.absolute_y(operand)
        elif mode == AddressingMode.INDIRECT:
            if operand is None:
                raise ValueError("Indirect addressing requires operand")
            return self.indirect(operand)
        elif mode == AddressingMode.INDIRECT_X:
            if operand is None:
                raise ValueError("Indirect,X addressing requires operand")
            return self.indirect_x(operand)
        elif mode == AddressingMode.INDIRECT_Y:
            if operand is None:
                raise ValueError("Indirect,Y addressing requires operand")
            return self.indirect_y(operand)
        elif mode == AddressingMode.INDIRECT_ZP:
            if operand is None:
                raise ValueError("Indirect zero page addressing requires operand")
            return self.indirect_zp(operand)
        elif mode == AddressingMode.INDIRECT_ABS_X:
            if operand is None:
                raise ValueError("Indirect absolute,X addressing requires operand")
            return self.indirect_abs_x(operand)
        elif mode == AddressingMode.RELATIVE:
            if operand is None:
                raise ValueError("Relative addressing requires operand")
            return self.relative(operand)
        elif mode == AddressingMode.STACK:
            return self.stack()
        else:
            raise ValueError(f"Unknown addressing mode: {mode}")
    
    def get_instruction_length(self, mode: AddressingMode) -> int:
        """命令長取得
        
        アドレッシングモードに基づいて命令の長さ（バイト数）を返します。
        
        Args:
            mode: アドレッシングモード
            
        Returns:
            int: 命令長（1-3バイト）
        """
        if mode in (AddressingMode.IMPLICIT, AddressingMode.ACCUMULATOR, AddressingMode.STACK):
            return 1
        elif mode in (AddressingMode.IMMEDIATE, AddressingMode.ZERO_PAGE, 
                     AddressingMode.ZERO_PAGE_X, AddressingMode.ZERO_PAGE_Y,
                     AddressingMode.INDIRECT_X, AddressingMode.INDIRECT_Y,
                     AddressingMode.INDIRECT_ZP, AddressingMode.RELATIVE):
            return 2
        elif mode in (AddressingMode.ABSOLUTE, AddressingMode.ABSOLUTE_X,
                     AddressingMode.ABSOLUTE_Y, AddressingMode.INDIRECT,
                     AddressingMode.INDIRECT_ABS_X):
            return 3
        else:
            raise ValueError(f"Unknown addressing mode: {mode}")
