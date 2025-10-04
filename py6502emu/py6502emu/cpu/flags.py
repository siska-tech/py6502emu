"""
プロセッサフラグ管理
PU002: ProcessorFlags

W65C02S CPUのプロセッサステータスレジスタ（P）の各フラグビットを管理します。
"""

from typing import Dict, Any
from .registers import CPURegisters


class ProcessorFlags:
    """W65C02S プロセッサフラグ管理クラス
    
    プロセッサステータスレジスタ（P）の各フラグビットを個別に管理し、
    演算結果による自動更新や条件分岐での判定機能を提供します。
    
    フラグビット構成 (P レジスタ):
    Bit 7: N (Negative) - 負数フラグ
    Bit 6: V (Overflow) - オーバーフローフラグ  
    Bit 5: - (未使用) - 常に1
    Bit 4: B (Break) - ブレークフラグ
    Bit 3: D (Decimal) - デシマルモードフラグ
    Bit 2: I (Interrupt) - 割り込み禁止フラグ
    Bit 1: Z (Zero) - ゼロフラグ
    Bit 0: C (Carry) - キャリーフラグ
    """
    
    def __init__(self, registers: CPURegisters) -> None:
        """初期化
        
        Args:
            registers: CPUレジスタ管理オブジェクト
        """
        self._registers = registers
    
    # フラグビット定数
    FLAG_N = 0x80  # Negative (bit 7)
    FLAG_V = 0x40  # Overflow (bit 6)
    FLAG_U = 0x20  # Unused (bit 5) - 常に1
    FLAG_B = 0x10  # Break (bit 4)
    FLAG_D = 0x08  # Decimal (bit 3)
    FLAG_I = 0x04  # Interrupt (bit 2)
    FLAG_Z = 0x02  # Zero (bit 1)
    FLAG_C = 0x01  # Carry (bit 0)
    
    @property
    def negative(self) -> bool:
        """負数フラグ (N) 取得
        
        Returns:
            bool: 負数フラグの状態
        """
        return bool(self._registers.p & self.FLAG_N)
    
    @negative.setter
    def negative(self, value: bool) -> None:
        """負数フラグ (N) 設定
        
        Args:
            value: 設定する値
        """
        if value:
            self._registers.p |= self.FLAG_N
        else:
            self._registers.p &= ~self.FLAG_N
    
    @property
    def overflow(self) -> bool:
        """オーバーフローフラグ (V) 取得
        
        Returns:
            bool: オーバーフローフラグの状態
        """
        return bool(self._registers.p & self.FLAG_V)
    
    @overflow.setter
    def overflow(self, value: bool) -> None:
        """オーバーフローフラグ (V) 設定
        
        Args:
            value: 設定する値
        """
        if value:
            self._registers.p |= self.FLAG_V
        else:
            self._registers.p &= ~self.FLAG_V
    
    @property
    def break_flag(self) -> bool:
        """ブレークフラグ (B) 取得
        
        Returns:
            bool: ブレークフラグの状態
        """
        return bool(self._registers.p & self.FLAG_B)
    
    @break_flag.setter
    def break_flag(self, value: bool) -> None:
        """ブレークフラグ (B) 設定
        
        Args:
            value: 設定する値
        """
        if value:
            self._registers.p |= self.FLAG_B
        else:
            self._registers.p &= ~self.FLAG_B
    
    @property
    def decimal(self) -> bool:
        """デシマルモードフラグ (D) 取得
        
        Returns:
            bool: デシマルモードフラグの状態
        """
        return bool(self._registers.p & self.FLAG_D)
    
    @decimal.setter
    def decimal(self, value: bool) -> None:
        """デシマルモードフラグ (D) 設定
        
        Args:
            value: 設定する値
        """
        if value:
            self._registers.p |= self.FLAG_D
        else:
            self._registers.p &= ~self.FLAG_D
    
    @property
    def interrupt(self) -> bool:
        """割り込み禁止フラグ (I) 取得
        
        Returns:
            bool: 割り込み禁止フラグの状態
        """
        return bool(self._registers.p & self.FLAG_I)
    
    @interrupt.setter
    def interrupt(self, value: bool) -> None:
        """割り込み禁止フラグ (I) 設定
        
        Args:
            value: 設定する値
        """
        if value:
            self._registers.p |= self.FLAG_I
        else:
            self._registers.p &= ~self.FLAG_I
    
    @property
    def zero(self) -> bool:
        """ゼロフラグ (Z) 取得
        
        Returns:
            bool: ゼロフラグの状態
        """
        return bool(self._registers.p & self.FLAG_Z)
    
    @zero.setter
    def zero(self, value: bool) -> None:
        """ゼロフラグ (Z) 設定
        
        Args:
            value: 設定する値
        """
        if value:
            self._registers.p |= self.FLAG_Z
        else:
            self._registers.p &= ~self.FLAG_Z
    
    @property
    def carry(self) -> bool:
        """キャリーフラグ (C) 取得
        
        Returns:
            bool: キャリーフラグの状態
        """
        return bool(self._registers.p & self.FLAG_C)
    
    @carry.setter
    def carry(self, value: bool) -> None:
        """キャリーフラグ (C) 設定
        
        Args:
            value: 設定する値
        """
        if value:
            self._registers.p |= self.FLAG_C
        else:
            self._registers.p &= ~self.FLAG_C
    
    def update_nz(self, value: int) -> None:
        """N, Z フラグ更新
        
        演算結果に基づいてNegativeとZeroフラグを更新します。
        
        Args:
            value: 演算結果の値 (0x00-0xFF)
        """
        value &= 0xFF  # 8ビットに制限
        self.negative = bool(value & 0x80)
        self.zero = (value == 0)
    
    def update_nzc(self, value: int, carry_in: bool = False) -> None:
        """N, Z, C フラグ更新
        
        演算結果に基づいてNegative, Zero, Carryフラグを更新します。
        
        Args:
            value: 演算結果の値
            carry_in: キャリー入力
        """
        self.carry = (value > 0xFF) or carry_in
        self.update_nz(value)
    
    def update_overflow_add(self, operand1: int, operand2: int, result: int) -> None:
        """加算時のオーバーフローフラグ更新
        
        符号付き加算でのオーバーフロー検出を行います。
        
        Args:
            operand1: 第1オペランド
            operand2: 第2オペランド
            result: 演算結果
        """
        # 符号付き演算でのオーバーフロー検出
        # 同符号同士の加算で異符号の結果が出た場合にオーバーフロー
        operand1 &= 0xFF
        operand2 &= 0xFF
        result &= 0xFF
        
        # 両オペランドが同符号で、結果が異符号の場合にオーバーフロー
        op1_sign = operand1 & 0x80
        op2_sign = operand2 & 0x80
        result_sign = result & 0x80
        
        # 正 + 正 = 負 または 負 + 負 = 正 の場合にオーバーフロー
        overflow = (op1_sign == op2_sign) and (op1_sign != result_sign)
        self.overflow = overflow
    
    def update_overflow_sub(self, operand1: int, operand2: int, result: int) -> None:
        """減算時のオーバーフローフラグ更新
        
        符号付き減算でのオーバーフロー検出を行います。
        
        Args:
            operand1: 第1オペランド (被減数)
            operand2: 第2オペランド (減数)
            result: 演算結果
        """
        # 符号付き演算でのオーバーフロー検出
        # 異符号同士の減算で被減数と異符号の結果が出た場合にオーバーフロー
        operand1 &= 0xFF
        operand2 &= 0xFF
        result &= 0xFF
        
        op1_sign = operand1 & 0x80
        op2_sign = operand2 & 0x80
        result_sign = result & 0x80
        
        # 被減数と減数が異符号で、被減数と結果が異符号の場合にオーバーフロー
        overflow = (op1_sign != op2_sign) and (op1_sign != result_sign)
        self.overflow = overflow
    
    def clear_carry(self) -> None:
        """キャリーフラグクリア (CLC命令)"""
        self.carry = False
    
    def set_carry(self) -> None:
        """キャリーフラグセット (SEC命令)"""
        self.carry = True
    
    def clear_interrupt(self) -> None:
        """割り込み禁止フラグクリア (CLI命令)"""
        self.interrupt = False
    
    def set_interrupt(self) -> None:
        """割り込み禁止フラグセット (SEI命令)"""
        self.interrupt = True
    
    def clear_decimal(self) -> None:
        """デシマルモードフラグクリア (CLD命令)"""
        self.decimal = False
    
    def set_decimal(self) -> None:
        """デシマルモードフラグセット (SED命令)"""
        self.decimal = True
    
    def clear_overflow(self) -> None:
        """オーバーフローフラグクリア (CLV命令)"""
        self.overflow = False
    
    def get_flags_byte(self) -> int:
        """フラグバイト取得
        
        プロセッサステータスレジスタの値を取得します。
        未使用ビット（bit 5）は常に1に設定されます。
        
        Returns:
            int: プロセッサステータスレジスタの値
        """
        # 未使用ビット（bit 5）を常に1に設定
        return self._registers.p | self.FLAG_U
    
    def set_flags_byte(self, value: int) -> None:
        """フラグバイト設定
        
        プロセッサステータスレジスタの値を設定します。
        
        Args:
            value: 設定する値 (0x00-0xFF)
        """
        # 未使用ビット（bit 5）を常に1に設定
        self._registers.p = (value | self.FLAG_U) & 0xFF
    
    def push_flags(self, with_break: bool = True) -> int:
        """フラグをスタック用に準備
        
        スタックプッシュ用のフラグバイトを準備します。
        
        Args:
            with_break: ブレークフラグを設定するか
            
        Returns:
            int: スタック用フラグバイト
        """
        flags = self.get_flags_byte()
        if with_break:
            flags |= self.FLAG_B
        else:
            flags &= ~self.FLAG_B
        return flags
    
    def pop_flags(self, value: int) -> None:
        """スタックからフラグを復元
        
        スタックからポップしたフラグバイトを設定します。
        
        Args:
            value: スタックからの値
        """
        self.set_flags_byte(value)
    
    # 条件分岐用のフラグ判定メソッド
    def branch_on_carry_clear(self) -> bool:
        """BCC: キャリークリア時分岐"""
        return not self.carry
    
    def branch_on_carry_set(self) -> bool:
        """BCS: キャリーセット時分岐"""
        return self.carry
    
    def branch_on_equal(self) -> bool:
        """BEQ: ゼロフラグセット時分岐（等しい）"""
        return self.zero
    
    def branch_on_not_equal(self) -> bool:
        """BNE: ゼロフラグクリア時分岐（等しくない）"""
        return not self.zero
    
    def branch_on_minus(self) -> bool:
        """BMI: 負数フラグセット時分岐（負）"""
        return self.negative
    
    def branch_on_plus(self) -> bool:
        """BPL: 負数フラグクリア時分岐（正）"""
        return not self.negative
    
    def branch_on_overflow_clear(self) -> bool:
        """BVC: オーバーフローフラグクリア時分岐"""
        return not self.overflow
    
    def branch_on_overflow_set(self) -> bool:
        """BVS: オーバーフローフラグセット時分岐"""
        return self.overflow
    
    def get_state(self) -> Dict[str, Any]:
        """フラグ状態取得
        
        Returns:
            Dict[str, Any]: フラグ状態
        """
        return {
            'N': self.negative,
            'V': self.overflow,
            'B': self.break_flag,
            'D': self.decimal,
            'I': self.interrupt,
            'Z': self.zero,
            'C': self.carry,
            'P': self.get_flags_byte()
        }
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """フラグ状態設定
        
        Args:
            state: 設定するフラグ状態
        """
        if 'P' in state:
            self.set_flags_byte(state['P'])
        else:
            # 個別フラグ設定
            if 'N' in state:
                self.negative = state['N']
            if 'V' in state:
                self.overflow = state['V']
            if 'B' in state:
                self.break_flag = state['B']
            if 'D' in state:
                self.decimal = state['D']
            if 'I' in state:
                self.interrupt = state['I']
            if 'Z' in state:
                self.zero = state['Z']
            if 'C' in state:
                self.carry = state['C']
    
    def __str__(self) -> str:
        """文字列表現
        
        Returns:
            str: フラグの状態を表す文字列
        """
        flags = []
        flags.append('N' if self.negative else 'n')
        flags.append('V' if self.overflow else 'v')
        flags.append('-')  # 未使用ビット
        flags.append('B' if self.break_flag else 'b')
        flags.append('D' if self.decimal else 'd')
        flags.append('I' if self.interrupt else 'i')
        flags.append('Z' if self.zero else 'z')
        flags.append('C' if self.carry else 'c')
        return ''.join(flags)
    
    def __repr__(self) -> str:
        """詳細文字列表現
        
        Returns:
            str: フラグの詳細状態を表す文字列
        """
        return f"ProcessorFlags({self})"
