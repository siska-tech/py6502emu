"""
CPUレジスタ管理
PU001: CPURegisters

W65C02S CPUの全レジスタ（A, X, Y, PC, S, P）の管理を行います。
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class CPURegisters:
    """W65C02S CPUレジスタ管理クラス
    
    W65C02S CPUの全レジスタを管理し、レジスタ間の転送操作や
    状態の保存・復元機能を提供します。
    
    Attributes:
        a: アキュムレータ (8ビット)
        x: Xインデックスレジスタ (8ビット)
        y: Yインデックスレジスタ (8ビット)
        pc: プログラムカウンタ (16ビット)
        s: スタックポインタ (8ビット)
        p: プロセッサステータスレジスタ (8ビット)
    """
    
    # 8ビットレジスタ
    a: int = 0x00    # アキュムレータ
    x: int = 0x00    # Xインデックスレジスタ
    y: int = 0x00    # Yインデックスレジスタ
    s: int = 0xFF    # スタックポインタ (初期値: 0xFF)
    
    # 16ビットレジスタ
    pc: int = 0x0000  # プログラムカウンタ
    
    # プロセッサステータスレジスタ (8ビット)
    p: int = 0x34    # 初期値: 0x34 (未使用ビット5=1, B=1, I=1)
    
    def __post_init__(self) -> None:
        """初期化後処理
        
        レジスタ値の範囲チェックを行います。
        """
        self._validate_registers()
    
    def _validate_registers(self) -> None:
        """レジスタ値の妥当性チェック
        
        Raises:
            ValueError: レジスタ値が範囲外の場合
        """
        # 8ビットレジスタの範囲チェック
        for name, value in [('A', self.a), ('X', self.x), ('Y', self.y), ('S', self.s), ('P', self.p)]:
            if not (0 <= value <= 0xFF):
                raise ValueError(f"Register {name} value {value:02X} out of range (0x00-0xFF)")
        
        # 16ビットレジスタの範囲チェック
        if not (0 <= self.pc <= 0xFFFF):
            raise ValueError(f"Register PC value {self.pc:04X} out of range (0x0000-0xFFFF)")
    
    def reset(self) -> None:
        """レジスタリセット
        
        全レジスタを初期状態にリセットします。
        W65C02Sのリセット仕様に準拠します。
        """
        self.a = 0x00
        self.x = 0x00
        self.y = 0x00
        self.s = 0xFF
        self.pc = 0x0000  # 実際のリセットベクタは後でロードされる
        self.p = 0x34     # N=0, V=0, -=1, B=1, D=0, I=1, Z=0, C=0
    
    def get_a(self) -> int:
        """アキュムレータ取得
        
        Returns:
            int: アキュムレータの値 (0x00-0xFF)
        """
        return self.a
    
    def set_a(self, value: int) -> None:
        """アキュムレータ設定
        
        Args:
            value: 設定する値 (0x00-0xFF)
            
        Raises:
            ValueError: 値が範囲外の場合
        """
        if not (0 <= value <= 0xFF):
            raise ValueError(f"Accumulator value {value:02X} out of range (0x00-0xFF)")
        self.a = value
    
    def get_x(self) -> int:
        """Xレジスタ取得
        
        Returns:
            int: Xレジスタの値 (0x00-0xFF)
        """
        return self.x
    
    def set_x(self, value: int) -> None:
        """Xレジスタ設定
        
        Args:
            value: 設定する値 (0x00-0xFF)
            
        Raises:
            ValueError: 値が範囲外の場合
        """
        if not (0 <= value <= 0xFF):
            raise ValueError(f"X register value {value:02X} out of range (0x00-0xFF)")
        self.x = value
    
    def get_y(self) -> int:
        """Yレジスタ取得
        
        Returns:
            int: Yレジスタの値 (0x00-0xFF)
        """
        return self.y
    
    def set_y(self, value: int) -> None:
        """Yレジスタ設定
        
        Args:
            value: 設定する値 (0x00-0xFF)
            
        Raises:
            ValueError: 値が範囲外の場合
        """
        if not (0 <= value <= 0xFF):
            raise ValueError(f"Y register value {value:02X} out of range (0x00-0xFF)")
        self.y = value
    
    def get_pc(self) -> int:
        """プログラムカウンタ取得
        
        Returns:
            int: プログラムカウンタの値 (0x0000-0xFFFF)
        """
        return self.pc
    
    def set_pc(self, value: int) -> None:
        """プログラムカウンタ設定
        
        Args:
            value: 設定する値 (0x0000-0xFFFF)
            
        Raises:
            ValueError: 値が範囲外の場合
        """
        if not (0 <= value <= 0xFFFF):
            raise ValueError(f"PC value {value:04X} out of range (0x0000-0xFFFF)")
        self.pc = value
    
    def get_s(self) -> int:
        """スタックポインタ取得
        
        Returns:
            int: スタックポインタの値 (0x00-0xFF)
        """
        return self.s
    
    def set_s(self, value: int) -> None:
        """スタックポインタ設定
        
        Args:
            value: 設定する値 (0x00-0xFF)
            
        Raises:
            ValueError: 値が範囲外の場合
        """
        if not (0 <= value <= 0xFF):
            raise ValueError(f"Stack pointer value {value:02X} out of range (0x00-0xFF)")
        self.s = value
    
    def get_p(self) -> int:
        """プロセッサステータスレジスタ取得
        
        Returns:
            int: プロセッサステータスレジスタの値 (0x00-0xFF)
        """
        return self.p
    
    def set_p(self, value: int) -> None:
        """プロセッサステータスレジスタ設定
        
        Args:
            value: 設定する値 (0x00-0xFF)
            
        Raises:
            ValueError: 値が範囲外の場合
        """
        if not (0 <= value <= 0xFF):
            raise ValueError(f"Processor status value {value:02X} out of range (0x00-0xFF)")
        self.p = value
    
    def increment_pc(self, amount: int = 1) -> None:
        """プログラムカウンタインクリメント
        
        Args:
            amount: インクリメント量 (デフォルト: 1)
        """
        self.pc = (self.pc + amount) & 0xFFFF
    
    def decrement_s(self) -> None:
        """スタックポインタデクリメント
        
        スタック操作時のスタックポインタ減算を行います。
        """
        self.s = (self.s - 1) & 0xFF
    
    def increment_s(self) -> None:
        """スタックポインタインクリメント
        
        スタック操作時のスタックポインタ加算を行います。
        """
        self.s = (self.s + 1) & 0xFF
    
    def get_stack_address(self) -> int:
        """スタックアドレス取得
        
        現在のスタックポインタに対応する実際のメモリアドレスを取得します。
        6502ファミリーではスタックは0x0100-0x01FFの範囲に配置されます。
        
        Returns:
            int: スタックアドレス (0x0100-0x01FF)
        """
        return 0x0100 + self.s
    
    # レジスタ間転送操作
    def transfer_a_to_x(self) -> None:
        """A → X 転送 (TAX命令)"""
        self.x = self.a
    
    def transfer_a_to_y(self) -> None:
        """A → Y 転送 (TAY命令)"""
        self.y = self.a
    
    def transfer_x_to_a(self) -> None:
        """X → A 転送 (TXA命令)"""
        self.a = self.x
    
    def transfer_y_to_a(self) -> None:
        """Y → A 転送 (TYA命令)"""
        self.a = self.y
    
    def transfer_s_to_x(self) -> None:
        """S → X 転送 (TSX命令)"""
        self.x = self.s
    
    def transfer_x_to_s(self) -> None:
        """X → S 転送 (TXS命令)"""
        self.s = self.x
    
    def get_state(self) -> Dict[str, Any]:
        """レジスタ状態取得
        
        全レジスタの現在の状態を辞書形式で取得します。
        
        Returns:
            Dict[str, Any]: レジスタ状態
        """
        return {
            'A': self.a,
            'X': self.x,
            'Y': self.y,
            'PC': self.pc,
            'S': self.s,
            'P': self.p
        }
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """レジスタ状態設定
        
        レジスタの状態を一括設定します。
        
        Args:
            state: 設定するレジスタ状態
        """
        if 'A' in state:
            self.set_a(state['A'])
        if 'X' in state:
            self.set_x(state['X'])
        if 'Y' in state:
            self.set_y(state['Y'])
        if 'PC' in state:
            self.set_pc(state['PC'])
        if 'S' in state:
            self.set_s(state['S'])
        if 'P' in state:
            self.set_p(state['P'])
    
    def __str__(self) -> str:
        """文字列表現
        
        Returns:
            str: レジスタの状態を表す文字列
        """
        return (f"A:{self.a:02X} X:{self.x:02X} Y:{self.y:02X} "
                f"PC:{self.pc:04X} S:{self.s:02X} P:{self.p:02X}")
    
    def __repr__(self) -> str:
        """詳細文字列表現
        
        Returns:
            str: レジスタの詳細状態を表す文字列
        """
        return (f"CPURegisters(A=0x{self.a:02X}, X=0x{self.x:02X}, Y=0x{self.y:02X}, "
                f"PC=0x{self.pc:04X}, S=0x{self.s:02X}, P=0x{self.p:02X})")
