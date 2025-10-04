"""
CPURegisters テストモジュール
PU001: CPURegisters のユニットテスト
"""

import pytest
from py6502emu.cpu.registers import CPURegisters


class TestCPURegisters:
    """CPURegisters クラスのテスト"""
    
    def test_init_default_values(self):
        """デフォルト値での初期化テスト"""
        registers = CPURegisters()
        
        assert registers.a == 0x00
        assert registers.x == 0x00
        assert registers.y == 0x00
        assert registers.s == 0xFF
        assert registers.pc == 0x0000
        assert registers.p == 0x34  # 未使用ビット5=1, B=1, I=1
    
    def test_init_custom_values(self):
        """カスタム値での初期化テスト"""
        registers = CPURegisters(
            a=0x42, x=0x10, y=0x20, s=0x80, pc=0x8000, p=0xFF
        )
        
        assert registers.a == 0x42
        assert registers.x == 0x10
        assert registers.y == 0x20
        assert registers.s == 0x80
        assert registers.pc == 0x8000
        assert registers.p == 0xFF
    
    def test_init_invalid_values(self):
        """無効値での初期化エラーテスト"""
        # 8ビットレジスタの範囲外
        with pytest.raises(ValueError, match="Register A value"):
            CPURegisters(a=0x100)
        
        with pytest.raises(ValueError, match="Register X value"):
            CPURegisters(x=-1)
        
        with pytest.raises(ValueError, match="Register Y value"):
            CPURegisters(y=0x100)
        
        with pytest.raises(ValueError, match="Register S value"):
            CPURegisters(s=0x100)
        
        with pytest.raises(ValueError, match="Register P value"):
            CPURegisters(p=0x100)
        
        # 16ビットレジスタの範囲外
        with pytest.raises(ValueError, match="Register PC value"):
            CPURegisters(pc=0x10000)
        
        with pytest.raises(ValueError, match="Register PC value"):
            CPURegisters(pc=-1)
    
    def test_reset(self):
        """リセット機能テスト"""
        registers = CPURegisters(
            a=0x42, x=0x10, y=0x20, s=0x80, pc=0x8000, p=0xFF
        )
        
        registers.reset()
        
        assert registers.a == 0x00
        assert registers.x == 0x00
        assert registers.y == 0x00
        assert registers.s == 0xFF
        assert registers.pc == 0x0000
        assert registers.p == 0x34
    
    def test_accumulator_operations(self):
        """アキュムレータ操作テスト"""
        registers = CPURegisters()
        
        # 取得
        assert registers.get_a() == 0x00
        
        # 設定
        registers.set_a(0x42)
        assert registers.get_a() == 0x42
        assert registers.a == 0x42
        
        # 範囲外エラー
        with pytest.raises(ValueError, match="Accumulator value"):
            registers.set_a(0x100)
        
        with pytest.raises(ValueError, match="Accumulator value"):
            registers.set_a(-1)
    
    def test_x_register_operations(self):
        """Xレジスタ操作テスト"""
        registers = CPURegisters()
        
        # 取得
        assert registers.get_x() == 0x00
        
        # 設定
        registers.set_x(0x10)
        assert registers.get_x() == 0x10
        assert registers.x == 0x10
        
        # 範囲外エラー
        with pytest.raises(ValueError, match="X register value"):
            registers.set_x(0x100)
    
    def test_y_register_operations(self):
        """Yレジスタ操作テスト"""
        registers = CPURegisters()
        
        # 取得
        assert registers.get_y() == 0x00
        
        # 設定
        registers.set_y(0x20)
        assert registers.get_y() == 0x20
        assert registers.y == 0x20
        
        # 範囲外エラー
        with pytest.raises(ValueError, match="Y register value"):
            registers.set_y(0x100)
    
    def test_pc_operations(self):
        """プログラムカウンタ操作テスト"""
        registers = CPURegisters()
        
        # 取得
        assert registers.get_pc() == 0x0000
        
        # 設定
        registers.set_pc(0x8000)
        assert registers.get_pc() == 0x8000
        assert registers.pc == 0x8000
        
        # 範囲外エラー
        with pytest.raises(ValueError, match="PC value"):
            registers.set_pc(0x10000)
    
    def test_stack_pointer_operations(self):
        """スタックポインタ操作テスト"""
        registers = CPURegisters()
        
        # 取得
        assert registers.get_s() == 0xFF
        
        # 設定
        registers.set_s(0x80)
        assert registers.get_s() == 0x80
        assert registers.s == 0x80
        
        # 範囲外エラー
        with pytest.raises(ValueError, match="Stack pointer value"):
            registers.set_s(0x100)
    
    def test_processor_status_operations(self):
        """プロセッサステータス操作テスト"""
        registers = CPURegisters()
        
        # 取得
        assert registers.get_p() == 0x34
        
        # 設定
        registers.set_p(0xFF)
        assert registers.get_p() == 0xFF
        assert registers.p == 0xFF
        
        # 範囲外エラー
        with pytest.raises(ValueError, match="Processor status value"):
            registers.set_p(0x100)
    
    def test_pc_increment(self):
        """プログラムカウンタインクリメントテスト"""
        registers = CPURegisters()
        registers.set_pc(0x8000)
        
        # デフォルト（+1）
        registers.increment_pc()
        assert registers.pc == 0x8001
        
        # カスタム量
        registers.increment_pc(2)
        assert registers.pc == 0x8003
        
        # オーバーフロー処理
        registers.set_pc(0xFFFF)
        registers.increment_pc()
        assert registers.pc == 0x0000
    
    def test_stack_pointer_operations_detailed(self):
        """スタックポインタ詳細操作テスト"""
        registers = CPURegisters()
        
        # 初期値
        assert registers.s == 0xFF
        assert registers.get_stack_address() == 0x01FF
        
        # デクリメント
        registers.decrement_s()
        assert registers.s == 0xFE
        assert registers.get_stack_address() == 0x01FE
        
        # インクリメント
        registers.increment_s()
        assert registers.s == 0xFF
        assert registers.get_stack_address() == 0x01FF
        
        # アンダーフロー処理
        registers.set_s(0x00)
        registers.decrement_s()
        assert registers.s == 0xFF
        
        # オーバーフロー処理
        registers.set_s(0xFF)
        registers.increment_s()
        assert registers.s == 0x00
    
    def test_register_transfers(self):
        """レジスタ間転送テスト"""
        registers = CPURegisters()
        
        # A → X (TAX)
        registers.set_a(0x42)
        registers.transfer_a_to_x()
        assert registers.x == 0x42
        
        # A → Y (TAY)
        registers.set_a(0x33)
        registers.transfer_a_to_y()
        assert registers.y == 0x33
        
        # X → A (TXA)
        registers.set_x(0x55)
        registers.transfer_x_to_a()
        assert registers.a == 0x55
        
        # Y → A (TYA)
        registers.set_y(0x77)
        registers.transfer_y_to_a()
        assert registers.a == 0x77
        
        # S → X (TSX)
        registers.set_s(0x80)
        registers.transfer_s_to_x()
        assert registers.x == 0x80
        
        # X → S (TXS)
        registers.set_x(0x90)
        registers.transfer_x_to_s()
        assert registers.s == 0x90
    
    def test_state_management(self):
        """状態管理テスト"""
        registers = CPURegisters()
        
        # 状態設定
        registers.set_a(0x42)
        registers.set_x(0x10)
        registers.set_y(0x20)
        registers.set_pc(0x8000)
        registers.set_s(0x80)
        registers.set_p(0xFF)
        
        # 状態取得
        state = registers.get_state()
        expected_state = {
            'A': 0x42,
            'X': 0x10,
            'Y': 0x20,
            'PC': 0x8000,
            'S': 0x80,
            'P': 0xFF
        }
        assert state == expected_state
        
        # 新しいレジスタで状態復元
        new_registers = CPURegisters()
        new_registers.set_state(state)
        
        assert new_registers.a == 0x42
        assert new_registers.x == 0x10
        assert new_registers.y == 0x20
        assert new_registers.pc == 0x8000
        assert new_registers.s == 0x80
        assert new_registers.p == 0xFF
    
    def test_partial_state_setting(self):
        """部分状態設定テスト"""
        registers = CPURegisters()
        
        # 部分的な状態設定
        partial_state = {'A': 0x42, 'PC': 0x8000}
        registers.set_state(partial_state)
        
        assert registers.a == 0x42
        assert registers.pc == 0x8000
        # 他のレジスタは初期値のまま
        assert registers.x == 0x00
        assert registers.y == 0x00
        assert registers.s == 0xFF
        assert registers.p == 0x34
    
    def test_string_representations(self):
        """文字列表現テスト"""
        registers = CPURegisters(
            a=0x42, x=0x10, y=0x20, pc=0x8000, s=0x80, p=0xFF
        )
        
        # __str__
        str_repr = str(registers)
        assert "A:42" in str_repr
        assert "X:10" in str_repr
        assert "Y:20" in str_repr
        assert "PC:8000" in str_repr
        assert "S:80" in str_repr
        assert "P:FF" in str_repr
        
        # __repr__
        repr_str = repr(registers)
        assert "CPURegisters" in repr_str
        assert "A=0x42" in repr_str
        assert "PC=0x8000" in repr_str
    
    def test_edge_cases(self):
        """エッジケーステスト"""
        registers = CPURegisters()
        
        # 境界値テスト
        registers.set_a(0x00)
        assert registers.a == 0x00
        
        registers.set_a(0xFF)
        assert registers.a == 0xFF
        
        registers.set_pc(0x0000)
        assert registers.pc == 0x0000
        
        registers.set_pc(0xFFFF)
        assert registers.pc == 0xFFFF
        
        # スタックアドレス境界値
        registers.set_s(0x00)
        assert registers.get_stack_address() == 0x0100
        
        registers.set_s(0xFF)
        assert registers.get_stack_address() == 0x01FF
