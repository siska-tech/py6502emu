"""
ProcessorFlags テストモジュール
PU002: ProcessorFlags のユニットテスト
"""

import pytest
from py6502emu.cpu.registers import CPURegisters
from py6502emu.cpu.flags import ProcessorFlags


class TestProcessorFlags:
    """ProcessorFlags クラスのテスト"""
    
    def setup_method(self):
        """各テストメソッド実行前のセットアップ"""
        self.registers = CPURegisters()
        self.flags = ProcessorFlags(self.registers)
    
    def test_init(self):
        """初期化テスト"""
        # 初期状態のフラグ確認 (P = 0x34 = 00110100)
        assert not self.flags.negative      # bit 7 = 0
        assert not self.flags.overflow     # bit 6 = 0
        assert self.flags.break_flag       # bit 4 = 1
        assert not self.flags.decimal      # bit 3 = 0
        assert self.flags.interrupt        # bit 2 = 1
        assert not self.flags.zero         # bit 1 = 0
        assert not self.flags.carry        # bit 0 = 0
    
    def test_negative_flag(self):
        """負数フラグ (N) テスト"""
        # 初期状態
        assert not self.flags.negative
        
        # セット
        self.flags.negative = True
        assert self.flags.negative
        assert self.registers.p & ProcessorFlags.FLAG_N
        
        # クリア
        self.flags.negative = False
        assert not self.flags.negative
        assert not (self.registers.p & ProcessorFlags.FLAG_N)
    
    def test_overflow_flag(self):
        """オーバーフローフラグ (V) テスト"""
        # 初期状態
        assert not self.flags.overflow
        
        # セット
        self.flags.overflow = True
        assert self.flags.overflow
        assert self.registers.p & ProcessorFlags.FLAG_V
        
        # クリア
        self.flags.overflow = False
        assert not self.flags.overflow
        assert not (self.registers.p & ProcessorFlags.FLAG_V)
    
    def test_break_flag(self):
        """ブレークフラグ (B) テスト"""
        # 初期状態（初期値で設定済み）
        assert self.flags.break_flag
        
        # クリア
        self.flags.break_flag = False
        assert not self.flags.break_flag
        assert not (self.registers.p & ProcessorFlags.FLAG_B)
        
        # セット
        self.flags.break_flag = True
        assert self.flags.break_flag
        assert self.registers.p & ProcessorFlags.FLAG_B
    
    def test_decimal_flag(self):
        """デシマルモードフラグ (D) テスト"""
        # 初期状態
        assert not self.flags.decimal
        
        # セット
        self.flags.decimal = True
        assert self.flags.decimal
        assert self.registers.p & ProcessorFlags.FLAG_D
        
        # クリア
        self.flags.decimal = False
        assert not self.flags.decimal
        assert not (self.registers.p & ProcessorFlags.FLAG_D)
    
    def test_interrupt_flag(self):
        """割り込み禁止フラグ (I) テスト"""
        # 初期状態（初期値で設定済み）
        assert self.flags.interrupt
        
        # クリア
        self.flags.interrupt = False
        assert not self.flags.interrupt
        assert not (self.registers.p & ProcessorFlags.FLAG_I)
        
        # セット
        self.flags.interrupt = True
        assert self.flags.interrupt
        assert self.registers.p & ProcessorFlags.FLAG_I
    
    def test_zero_flag(self):
        """ゼロフラグ (Z) テスト"""
        # 初期状態
        assert not self.flags.zero
        
        # セット
        self.flags.zero = True
        assert self.flags.zero
        assert self.registers.p & ProcessorFlags.FLAG_Z
        
        # クリア
        self.flags.zero = False
        assert not self.flags.zero
        assert not (self.registers.p & ProcessorFlags.FLAG_Z)
    
    def test_carry_flag(self):
        """キャリーフラグ (C) テスト"""
        # 初期状態
        assert not self.flags.carry
        
        # セット
        self.flags.carry = True
        assert self.flags.carry
        assert self.registers.p & ProcessorFlags.FLAG_C
        
        # クリア
        self.flags.carry = False
        assert not self.flags.carry
        assert not (self.registers.p & ProcessorFlags.FLAG_C)
    
    def test_update_nz(self):
        """N, Z フラグ更新テスト"""
        # ゼロ値
        self.flags.update_nz(0x00)
        assert not self.flags.negative
        assert self.flags.zero
        
        # 正の値
        self.flags.update_nz(0x42)
        assert not self.flags.negative
        assert not self.flags.zero
        
        # 負の値（bit 7 = 1）
        self.flags.update_nz(0x80)
        assert self.flags.negative
        assert not self.flags.zero
        
        # 9ビット値（8ビットに制限される）
        self.flags.update_nz(0x180)  # 0x80
        assert self.flags.negative
        assert not self.flags.zero
    
    def test_update_nzc(self):
        """N, Z, C フラグ更新テスト"""
        # 8ビット範囲内
        self.flags.update_nzc(0x42)
        assert not self.flags.negative
        assert not self.flags.zero
        assert not self.flags.carry
        
        # 9ビット値（キャリー発生）
        self.flags.update_nzc(0x100)
        assert not self.flags.negative
        assert self.flags.zero  # 0x100 & 0xFF = 0x00
        assert self.flags.carry
        
        # キャリー入力あり
        self.flags.update_nzc(0x42, carry_in=True)
        assert not self.flags.negative
        assert not self.flags.zero
        assert self.flags.carry
    
    def test_update_overflow_add(self):
        """加算時オーバーフロー更新テスト"""
        # 正 + 正 = 正（オーバーフローなし）
        self.flags.update_overflow_add(0x40, 0x30, 0x70)
        assert not self.flags.overflow
        
        # 正 + 正 = 負（オーバーフローあり）
        self.flags.update_overflow_add(0x7F, 0x01, 0x80)
        assert self.flags.overflow
        
        # 負 + 負 = 正（オーバーフローあり）
        self.flags.update_overflow_add(0x80, 0x80, 0x00)
        assert self.flags.overflow
        
        # 負 + 負 = 正（オーバーフローあり）
        self.flags.update_overflow_add(0x80, 0x80, 0x00)
        # 実際は 0x100 だが 0x00 になる（オーバーフロー）
        self.flags.update_overflow_add(0xFF, 0xFF, 0xFE)
        assert not self.flags.overflow  # 負 + 負 = 負なのでオーバーフローなし
        
        # 正 + 負（オーバーフローなし）
        self.flags.update_overflow_add(0x40, 0x80, 0xC0)
        assert not self.flags.overflow
    
    def test_update_overflow_sub(self):
        """減算時オーバーフロー更新テスト"""
        # 正 - 負 = 正（オーバーフローなし）
        self.flags.update_overflow_sub(0x40, 0x80, 0x40)
        assert not self.flags.overflow
        
        # 正 - 負 = 負（オーバーフローあり）
        self.flags.update_overflow_sub(0x40, 0x80, 0xC0)
        assert self.flags.overflow
        
        # 負 - 正 = 正（オーバーフローあり）
        self.flags.update_overflow_sub(0x80, 0x40, 0x40)
        assert self.flags.overflow
        
        # 負 - 正 = 正（オーバーフローあり）
        self.flags.update_overflow_sub(0x80, 0x01, 0x7F)
        assert self.flags.overflow
        
        # 同符号同士（オーバーフローなし）
        self.flags.update_overflow_sub(0x40, 0x30, 0x10)
        assert not self.flags.overflow
    
    def test_flag_control_instructions(self):
        """フラグ制御命令テスト"""
        # CLC/SEC
        self.flags.set_carry()
        assert self.flags.carry
        self.flags.clear_carry()
        assert not self.flags.carry
        
        # CLI/SEI
        self.flags.clear_interrupt()
        assert not self.flags.interrupt
        self.flags.set_interrupt()
        assert self.flags.interrupt
        
        # CLD/SED
        self.flags.clear_decimal()
        assert not self.flags.decimal
        self.flags.set_decimal()
        assert self.flags.decimal
        
        # CLV
        self.flags.overflow = True
        self.flags.clear_overflow()
        assert not self.flags.overflow
    
    def test_flags_byte_operations(self):
        """フラグバイト操作テスト"""
        # 初期状態のフラグバイト取得
        flags_byte = self.flags.get_flags_byte()
        assert flags_byte == 0x34  # 未使用ビット5が1に設定される
        
        # フラグバイト設定
        self.flags.set_flags_byte(0xFF)
        assert self.flags.negative
        assert self.flags.overflow
        assert self.flags.break_flag
        assert self.flags.decimal
        assert self.flags.interrupt
        assert self.flags.zero
        assert self.flags.carry
        
        # 未使用ビット5は常に1
        self.flags.set_flags_byte(0x00)
        flags_byte = self.flags.get_flags_byte()
        assert flags_byte & ProcessorFlags.FLAG_U  # bit 5 = 1
    
    def test_stack_operations(self):
        """スタック操作テスト"""
        # フラグプッシュ（ブレークフラグあり）
        self.flags.negative = True
        self.flags.carry = True
        
        push_flags = self.flags.push_flags(with_break=True)
        assert push_flags & ProcessorFlags.FLAG_N
        assert push_flags & ProcessorFlags.FLAG_B
        assert push_flags & ProcessorFlags.FLAG_C
        assert push_flags & ProcessorFlags.FLAG_U  # 未使用ビット
        
        # フラグプッシュ（ブレークフラグなし）
        push_flags = self.flags.push_flags(with_break=False)
        assert push_flags & ProcessorFlags.FLAG_N
        assert not (push_flags & ProcessorFlags.FLAG_B)
        assert push_flags & ProcessorFlags.FLAG_C
        
        # フラグポップ
        self.flags.pop_flags(0x81)  # N=1, C=1
        assert self.flags.negative
        assert not self.flags.overflow
        assert not self.flags.zero
        assert self.flags.carry
    
    def test_branch_conditions(self):
        """分岐条件テスト"""
        # BCC/BCS
        self.flags.carry = False
        assert self.flags.branch_on_carry_clear()
        assert not self.flags.branch_on_carry_set()
        
        self.flags.carry = True
        assert not self.flags.branch_on_carry_clear()
        assert self.flags.branch_on_carry_set()
        
        # BEQ/BNE
        self.flags.zero = False
        assert not self.flags.branch_on_equal()
        assert self.flags.branch_on_not_equal()
        
        self.flags.zero = True
        assert self.flags.branch_on_equal()
        assert not self.flags.branch_on_not_equal()
        
        # BMI/BPL
        self.flags.negative = False
        assert not self.flags.branch_on_minus()
        assert self.flags.branch_on_plus()
        
        self.flags.negative = True
        assert self.flags.branch_on_minus()
        assert not self.flags.branch_on_plus()
        
        # BVC/BVS
        self.flags.overflow = False
        assert self.flags.branch_on_overflow_clear()
        assert not self.flags.branch_on_overflow_set()
        
        self.flags.overflow = True
        assert not self.flags.branch_on_overflow_clear()
        assert self.flags.branch_on_overflow_set()
    
    def test_state_management(self):
        """状態管理テスト"""
        # フラグ設定
        self.flags.negative = True
        self.flags.overflow = True
        self.flags.break_flag = False
        self.flags.decimal = True
        self.flags.interrupt = False
        self.flags.zero = True
        self.flags.carry = True
        
        # 状態取得
        state = self.flags.get_state()
        expected_state = {
            'N': True,
            'V': True,
            'B': False,
            'D': True,
            'I': False,
            'Z': True,
            'C': True,
            'P': self.flags.get_flags_byte()
        }
        assert state == expected_state
        
        # 新しいフラグで状態復元
        new_registers = CPURegisters()
        new_flags = ProcessorFlags(new_registers)
        new_flags.set_state(state)
        
        assert new_flags.negative == True
        assert new_flags.overflow == True
        assert new_flags.break_flag == False
        assert new_flags.decimal == True
        assert new_flags.interrupt == False
        assert new_flags.zero == True
        assert new_flags.carry == True
    
    def test_state_management_with_p_register(self):
        """Pレジスタ経由の状態管理テスト"""
        # Pレジスタ値で状態設定
        state = {'P': 0xFF}
        self.flags.set_state(state)
        
        assert self.flags.negative
        assert self.flags.overflow
        assert self.flags.break_flag
        assert self.flags.decimal
        assert self.flags.interrupt
        assert self.flags.zero
        assert self.flags.carry
    
    def test_partial_state_setting(self):
        """部分状態設定テスト"""
        # 部分的なフラグ設定
        partial_state = {'N': True, 'C': True}
        self.flags.set_state(partial_state)
        
        assert self.flags.negative
        assert self.flags.carry
        # 他のフラグは初期値のまま
        assert not self.flags.overflow
        assert not self.flags.zero
    
    def test_string_representations(self):
        """文字列表現テスト"""
        # 全フラグクリア状態
        self.flags.set_flags_byte(0x20)  # 未使用ビットのみ
        str_repr = str(self.flags)
        assert str_repr == "nv-bdizc"
        
        # 全フラグセット状態
        self.flags.set_flags_byte(0xFF)
        str_repr = str(self.flags)
        assert str_repr == "NV-BDIZC"
        
        # __repr__
        repr_str = repr(self.flags)
        assert "ProcessorFlags" in repr_str
    
    def test_flag_constants(self):
        """フラグ定数テスト"""
        assert ProcessorFlags.FLAG_N == 0x80
        assert ProcessorFlags.FLAG_V == 0x40
        assert ProcessorFlags.FLAG_U == 0x20
        assert ProcessorFlags.FLAG_B == 0x10
        assert ProcessorFlags.FLAG_D == 0x08
        assert ProcessorFlags.FLAG_I == 0x04
        assert ProcessorFlags.FLAG_Z == 0x02
        assert ProcessorFlags.FLAG_C == 0x01
    
    def test_complex_flag_operations(self):
        """複合フラグ操作テスト"""
        # 複数フラグの同時操作
        self.flags.negative = True
        self.flags.zero = True
        self.flags.carry = True
        
        # ビットマスクでの確認
        p_value = self.registers.p
        assert p_value & ProcessorFlags.FLAG_N
        assert p_value & ProcessorFlags.FLAG_Z
        assert p_value & ProcessorFlags.FLAG_C
        
        # フラグクリア
        self.flags.negative = False
        self.flags.zero = False
        self.flags.carry = False
        
        p_value = self.registers.p
        assert not (p_value & ProcessorFlags.FLAG_N)
        assert not (p_value & ProcessorFlags.FLAG_Z)
        assert not (p_value & ProcessorFlags.FLAG_C)
