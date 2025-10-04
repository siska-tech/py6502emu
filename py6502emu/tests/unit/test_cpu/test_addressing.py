"""
AddressingModes テストモジュール
PU005: AddressingModes のユニットテスト
"""

import pytest
from py6502emu.cpu.registers import CPURegisters
from py6502emu.cpu.addressing import AddressingModes, AddressingMode, AddressingResult


class MockMemory:
    """テスト用メモリモック"""
    
    def __init__(self):
        self.memory = {}
    
    def read(self, address: int) -> int:
        return self.memory.get(address & 0xFFFF, 0x00)
    
    def write(self, address: int, value: int) -> None:
        self.memory[address & 0xFFFF] = value & 0xFF
    
    def setup_word(self, address: int, value: int) -> None:
        """16ビット値をリトルエンディアンで設定"""
        self.write(address, value & 0xFF)
        self.write(address + 1, (value >> 8) & 0xFF)


class TestAddressingModes:
    """AddressingModes クラスのテスト"""
    
    def setup_method(self):
        """各テストメソッド実行前のセットアップ"""
        self.registers = CPURegisters()
        self.memory = MockMemory()
        self.addressing = AddressingModes(self.registers, self.memory)
    
    def test_implicit(self):
        """暗黙アドレッシングテスト"""
        result = self.addressing.implicit()
        
        assert result.address is None
        assert result.value is None
        assert not result.page_crossed
        assert result.extra_cycles == 0
    
    def test_accumulator(self):
        """アキュムレータアドレッシングテスト"""
        self.registers.set_a(0x42)
        result = self.addressing.accumulator()
        
        assert result.address is None
        assert result.value == 0x42
        assert not result.page_crossed
        assert result.extra_cycles == 0
    
    def test_immediate(self):
        """即値アドレッシングテスト"""
        result = self.addressing.immediate(0x42)
        
        assert result.address is None
        assert result.value == 0x42
        assert not result.page_crossed
        assert result.extra_cycles == 0
        
        # 9ビット値は8ビットに制限される
        result = self.addressing.immediate(0x142)
        assert result.value == 0x42
    
    def test_zero_page(self):
        """ゼロページアドレッシングテスト"""
        result = self.addressing.zero_page(0x42)
        
        assert result.address == 0x42
        assert result.value is None
        assert not result.page_crossed
        assert result.extra_cycles == 0
        
        # 9ビット値は8ビットに制限される
        result = self.addressing.zero_page(0x142)
        assert result.address == 0x42
    
    def test_zero_page_x(self):
        """ゼロページ,X アドレッシングテスト"""
        self.registers.set_x(0x10)
        result = self.addressing.zero_page_x(0x42)
        
        assert result.address == 0x52
        assert result.value is None
        assert not result.page_crossed
        assert result.extra_cycles == 0
        
        # ゼロページ境界でのラップアラウンド
        self.registers.set_x(0x10)
        result = self.addressing.zero_page_x(0xF8)
        assert result.address == 0x08  # (0xF8 + 0x10) & 0xFF
    
    def test_zero_page_y(self):
        """ゼロページ,Y アドレッシングテスト"""
        self.registers.set_y(0x20)
        result = self.addressing.zero_page_y(0x42)
        
        assert result.address == 0x62
        assert result.value is None
        assert not result.page_crossed
        assert result.extra_cycles == 0
        
        # ゼロページ境界でのラップアラウンド
        self.registers.set_y(0x20)
        result = self.addressing.zero_page_y(0xF0)
        assert result.address == 0x10  # (0xF0 + 0x20) & 0xFF
    
    def test_absolute(self):
        """絶対アドレッシングテスト"""
        result = self.addressing.absolute(0x8000)
        
        assert result.address == 0x8000
        assert result.value is None
        assert not result.page_crossed
        assert result.extra_cycles == 0
        
        # 17ビット値は16ビットに制限される
        result = self.addressing.absolute(0x18000)
        assert result.address == 0x8000
    
    def test_absolute_x(self):
        """絶対,X アドレッシングテスト"""
        self.registers.set_x(0x10)
        
        # ページクロスなし
        result = self.addressing.absolute_x(0x8000)
        assert result.address == 0x8010
        assert not result.page_crossed
        assert result.extra_cycles == 0
        
        # ページクロスあり
        result = self.addressing.absolute_x(0x80FF)
        assert result.address == 0x810F
        assert result.page_crossed
        assert result.extra_cycles == 1
        
        # 16ビット境界でのラップアラウンド
        self.registers.set_x(0x01)
        result = self.addressing.absolute_x(0xFFFF)
        assert result.address == 0x0000
    
    def test_absolute_y(self):
        """絶対,Y アドレッシングテスト"""
        self.registers.set_y(0x20)
        
        # ページクロスなし
        result = self.addressing.absolute_y(0x8000)
        assert result.address == 0x8020
        assert not result.page_crossed
        assert result.extra_cycles == 0
        
        # ページクロスあり
        result = self.addressing.absolute_y(0x80F0)
        assert result.address == 0x8110
        assert result.page_crossed
        assert result.extra_cycles == 1
    
    def test_indirect(self):
        """間接アドレッシングテスト"""
        # メモリ設定: 0x2000に0x8000を格納
        self.memory.setup_word(0x2000, 0x8000)
        
        result = self.addressing.indirect(0x2000)
        assert result.address == 0x8000
        assert result.value is None
        assert not result.page_crossed
        assert result.extra_cycles == 0
        
        # ページ境界テスト（W65C02Sではバグ修正済み）
        self.memory.setup_word(0x20FF, 0x1234)
        result = self.addressing.indirect(0x20FF)
        assert result.address == 0x1234
    
    def test_indirect_x(self):
        """間接,X アドレッシングテスト"""
        self.registers.set_x(0x04)
        
        # ゼロページ 0x20 + X(0x04) = 0x24 に 0x8000 を格納
        self.memory.setup_word(0x24, 0x8000)
        
        result = self.addressing.indirect_x(0x20)
        assert result.address == 0x8000
        assert result.value is None
        assert not result.page_crossed
        assert result.extra_cycles == 0
        
        # ゼロページ境界でのラップアラウンド
        self.registers.set_x(0x10)
        self.memory.setup_word(0x08, 0x1234)  # (0xF8 + 0x10) & 0xFF = 0x08
        result = self.addressing.indirect_x(0xF8)
        assert result.address == 0x1234
    
    def test_indirect_y(self):
        """間接,Y アドレッシングテスト"""
        self.registers.set_y(0x10)
        
        # ゼロページ 0x20 に 0x8000 を格納
        self.memory.setup_word(0x20, 0x8000)
        
        # ページクロスなし
        result = self.addressing.indirect_y(0x20)
        assert result.address == 0x8010  # 0x8000 + 0x10
        assert not result.page_crossed
        assert result.extra_cycles == 0
        
        # ページクロスあり
        self.memory.setup_word(0x30, 0x80FF)
        result = self.addressing.indirect_y(0x30)
        assert result.address == 0x810F  # 0x80FF + 0x10
        assert result.page_crossed
        assert result.extra_cycles == 1
    
    def test_indirect_zp(self):
        """ゼロページ間接アドレッシングテスト（W65C02S拡張）"""
        # ゼロページ 0x20 に 0x8000 を格納
        self.memory.setup_word(0x20, 0x8000)
        
        result = self.addressing.indirect_zp(0x20)
        assert result.address == 0x8000
        assert result.value is None
        assert not result.page_crossed
        assert result.extra_cycles == 0
        
        # 9ビット値は8ビットに制限される
        result = self.addressing.indirect_zp(0x120)
        # 0x20のメモリ内容を読む
        assert result.address == 0x8000
    
    def test_indirect_abs_x(self):
        """絶対間接,X アドレッシングテスト（W65C02S拡張）"""
        self.registers.set_x(0x02)
        
        # 0x2000 + X(0x02) = 0x2002 に 0x8000 を格納
        self.memory.setup_word(0x2002, 0x8000)
        
        result = self.addressing.indirect_abs_x(0x2000)
        assert result.address == 0x8000
        assert result.value is None
        assert not result.page_crossed
        assert result.extra_cycles == 0
    
    def test_relative(self):
        """相対アドレッシングテスト"""
        self.registers.set_pc(0x8000)
        
        # 正のオフセット
        result = self.addressing.relative(0x10)
        assert result.address == 0x8010
        assert not result.page_crossed
        assert result.extra_cycles == 0
        
        # 負のオフセット
        result = self.addressing.relative(0xF0)  # -16
        assert result.address == 0x7FF0
        assert result.page_crossed
        assert result.extra_cycles == 1
        
        # ページクロスあり（正方向）
        self.registers.set_pc(0x80FF)
        result = self.addressing.relative(0x02)
        assert result.address == 0x8101
        assert result.page_crossed
        assert result.extra_cycles == 1
        
        # 16ビット境界でのラップアラウンド
        self.registers.set_pc(0x0002)
        result = self.addressing.relative(0xFC)  # -4
        assert result.address == 0xFFFE
    
    def test_stack(self):
        """スタックアドレッシングテスト"""
        # 初期スタックポインタ
        result = self.addressing.stack()
        assert result.address == 0x01FF
        assert result.value is None
        assert not result.page_crossed
        assert result.extra_cycles == 0
        
        # スタックポインタ変更
        self.registers.set_s(0x80)
        result = self.addressing.stack()
        assert result.address == 0x0180
    
    def test_calculate_address(self):
        """アドレッシングモード計算統合テスト"""
        # 即値
        result = self.addressing.calculate_address(AddressingMode.IMMEDIATE, 0x42)
        assert result.value == 0x42
        
        # ゼロページ
        result = self.addressing.calculate_address(AddressingMode.ZERO_PAGE, 0x80)
        assert result.address == 0x80
        
        # 絶対
        result = self.addressing.calculate_address(AddressingMode.ABSOLUTE, 0x8000)
        assert result.address == 0x8000
        
        # オペランド不要なモード
        result = self.addressing.calculate_address(AddressingMode.IMPLICIT)
        assert result.address is None
        assert result.value is None
    
    def test_calculate_address_errors(self):
        """アドレッシングモード計算エラーテスト"""
        # オペランド必須なのに未指定
        with pytest.raises(ValueError, match="requires operand"):
            self.addressing.calculate_address(AddressingMode.IMMEDIATE)
        
        with pytest.raises(ValueError, match="requires operand"):
            self.addressing.calculate_address(AddressingMode.ZERO_PAGE)
        
        with pytest.raises(ValueError, match="requires operand"):
            self.addressing.calculate_address(AddressingMode.ABSOLUTE)
        
        # 無効なアドレッシングモード
        with pytest.raises(ValueError, match="Unknown addressing mode"):
            # 存在しない値を直接作成
            invalid_mode = 999
            self.addressing.calculate_address(invalid_mode)
    
    def test_get_instruction_length(self):
        """命令長取得テスト"""
        # 1バイト命令
        assert self.addressing.get_instruction_length(AddressingMode.IMPLICIT) == 1
        assert self.addressing.get_instruction_length(AddressingMode.ACCUMULATOR) == 1
        assert self.addressing.get_instruction_length(AddressingMode.STACK) == 1
        
        # 2バイト命令
        assert self.addressing.get_instruction_length(AddressingMode.IMMEDIATE) == 2
        assert self.addressing.get_instruction_length(AddressingMode.ZERO_PAGE) == 2
        assert self.addressing.get_instruction_length(AddressingMode.ZERO_PAGE_X) == 2
        assert self.addressing.get_instruction_length(AddressingMode.ZERO_PAGE_Y) == 2
        assert self.addressing.get_instruction_length(AddressingMode.INDIRECT_X) == 2
        assert self.addressing.get_instruction_length(AddressingMode.INDIRECT_Y) == 2
        assert self.addressing.get_instruction_length(AddressingMode.INDIRECT_ZP) == 2
        assert self.addressing.get_instruction_length(AddressingMode.RELATIVE) == 2
        
        # 3バイト命令
        assert self.addressing.get_instruction_length(AddressingMode.ABSOLUTE) == 3
        assert self.addressing.get_instruction_length(AddressingMode.ABSOLUTE_X) == 3
        assert self.addressing.get_instruction_length(AddressingMode.ABSOLUTE_Y) == 3
        assert self.addressing.get_instruction_length(AddressingMode.INDIRECT) == 3
        assert self.addressing.get_instruction_length(AddressingMode.INDIRECT_ABS_X) == 3
    
    def test_get_instruction_length_error(self):
        """命令長取得エラーテスト"""
        with pytest.raises(ValueError, match="Unknown addressing mode"):
            # 存在しない値を直接作成
            invalid_mode = 999
            self.addressing.get_instruction_length(invalid_mode)
    
    def test_page_cross_detection(self):
        """ページクロス検出テスト"""
        # ページクロスなし
        assert not self.addressing._check_page_cross(0x8000, 0x10)
        assert not self.addressing._check_page_cross(0x8000, 0xFF)
        
        # ページクロスあり
        assert self.addressing._check_page_cross(0x80FF, 0x01)
        assert self.addressing._check_page_cross(0x8000, 0x100)
        
        # 負のオフセット
        assert self.addressing._check_page_cross(0x8000, -1)
        assert not self.addressing._check_page_cross(0x8010, -0x10)
    
    def test_read_word(self):
        """16ビット読み取りテスト"""
        # リトルエンディアン
        self.memory.write(0x1000, 0x34)
        self.memory.write(0x1001, 0x12)
        
        word = self.addressing._read_word(0x1000)
        assert word == 0x1234
        
        # 16ビット境界でのラップアラウンド
        self.memory.write(0xFFFF, 0x78)
        self.memory.write(0x0000, 0x56)
        
        word = self.addressing._read_word(0xFFFF)
        assert word == 0x5678
    
    def test_read_word_bug(self):
        """16ビット読み取り（バグ版）テスト"""
        # 通常のケース
        self.memory.write(0x1000, 0x34)
        self.memory.write(0x1001, 0x12)
        
        word = self.addressing._read_word_bug(0x1000)
        assert word == 0x1234
        
        # ページ境界バグのケース
        self.memory.write(0x10FF, 0x34)
        self.memory.write(0x1100, 0x12)  # 実際のアドレス
        self.memory.write(0x1000, 0x56)  # バグでアクセスされるアドレス
        
        word = self.addressing._read_word_bug(0x10FF)
        assert word == 0x5634  # バグにより0x1000から上位バイトを読む
    
    def test_addressing_result_repr(self):
        """AddressingResult文字列表現テスト"""
        result = AddressingResult(address=0x8000, value=0x42, page_crossed=True, extra_cycles=1)
        repr_str = repr(result)
        
        assert "0x8000" in repr_str
        assert "0x42" in repr_str
        assert "page_crossed=True" in repr_str
        assert "extra_cycles=1" in repr_str
    
    def test_complex_addressing_scenarios(self):
        """複合アドレッシングシナリオテスト"""
        # 複雑な間接アドレッシング
        self.registers.set_x(0x05)
        self.registers.set_y(0x10)
        
        # ($20,X) -> ($25) -> $3000 + Y -> $3010
        self.memory.setup_word(0x25, 0x3000)
        
        result = self.addressing.indirect_x(0x20)
        assert result.address == 0x3000
        
        # indirect_y は ($20),Y なので、$20のメモリ内容（$3000）+ Y（$10）= $3010
        self.memory.setup_word(0x20, 0x3000)
        result = self.addressing.indirect_y(0x20)
        assert result.address == 0x3010
        
        # ページクロスの複合パターン
        self.memory.setup_word(0x30, 0x80F0)
        result = self.addressing.indirect_y(0x30)
        assert result.address == 0x8100  # 0x80F0 + 0x10
        assert result.page_crossed
        assert result.extra_cycles == 1
