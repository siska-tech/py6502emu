"""
AddressSpace テスト

64KBアドレス空間管理、リトルエンディアン処理、
ゼロページ・スタック特別処理のテストを提供します。
"""

import pytest
from py6502emu.memory.address_space import AddressSpace


class TestAddressSpace:
    """AddressSpace クラステスト"""
    
    def setup_method(self):
        """各テストメソッド前の初期化"""
        self.address_space = AddressSpace()
    
    def test_initialization(self):
        """初期化テスト"""
        assert self.address_space.ADDRESS_SPACE_SIZE == 0x10000
        assert self.address_space.ZERO_PAGE_START == 0x0000
        assert self.address_space.ZERO_PAGE_END == 0x00FF
        assert self.address_space.STACK_PAGE_START == 0x0100
        assert self.address_space.STACK_PAGE_END == 0x01FF
        assert self.address_space.STACK_BASE == 0x0100
    
    def test_byte_read_write(self):
        """8ビット読み書きテスト"""
        # 基本的な読み書き
        self.address_space.write_byte(0x1000, 0x42)
        assert self.address_space.read_byte(0x1000) == 0x42
        
        # 境界値テスト
        self.address_space.write_byte(0x0000, 0x00)
        assert self.address_space.read_byte(0x0000) == 0x00
        
        self.address_space.write_byte(0xFFFF, 0xFF)
        assert self.address_space.read_byte(0xFFFF) == 0xFF
        
        # 複数アドレスへの書き込み
        test_data = [(0x0080, 0xAA), (0x0200, 0x55), (0x8000, 0xCC)]
        for addr, value in test_data:
            self.address_space.write_byte(addr, value)
        
        for addr, expected in test_data:
            assert self.address_space.read_byte(addr) == expected
    
    def test_byte_read_write_invalid_address(self):
        """無効アドレス例外テスト"""
        # 無効な読み取りアドレス
        with pytest.raises(ValueError, match="Address must be 0x0000-0xFFFF"):
            self.address_space.read_byte(-1)
        
        with pytest.raises(ValueError, match="Address must be 0x0000-0xFFFF"):
            self.address_space.read_byte(0x10000)
        
        # 無効な書き込みアドレス
        with pytest.raises(ValueError, match="Address must be 0x0000-0xFFFF"):
            self.address_space.write_byte(-1, 0x00)
        
        with pytest.raises(ValueError, match="Address must be 0x0000-0xFFFF"):
            self.address_space.write_byte(0x10000, 0x00)
    
    def test_byte_write_invalid_value(self):
        """無効値例外テスト"""
        with pytest.raises(ValueError, match="Byte value must be 0x00-0xFF"):
            self.address_space.write_byte(0x1000, -1)
        
        with pytest.raises(ValueError, match="Byte value must be 0x00-0xFF"):
            self.address_space.write_byte(0x1000, 0x100)
    
    def test_word_read_write_little_endian(self):
        """16ビットリトルエンディアンテスト"""
        # 基本的なリトルエンディアン処理
        self.address_space.write_word(0x1000, 0x1234)
        assert self.address_space.read_word(0x1000) == 0x1234
        
        # バイト単位で確認
        assert self.address_space.read_byte(0x1000) == 0x34  # Low byte
        assert self.address_space.read_byte(0x1001) == 0x12  # High byte
        
        # 境界値テスト
        self.address_space.write_word(0x0000, 0x0000)
        assert self.address_space.read_word(0x0000) == 0x0000
        
        self.address_space.write_word(0xFFFE, 0xFFFF)
        assert self.address_space.read_word(0xFFFE) == 0xFFFF
        
        # 複数の値でテスト
        test_values = [0x0001, 0x00FF, 0xFF00, 0xABCD, 0x5555, 0xAAAA]
        for i, value in enumerate(test_values):
            addr = 0x2000 + (i * 2)
            self.address_space.write_word(addr, value)
            assert self.address_space.read_word(addr) == value
    
    def test_word_read_write_invalid_address(self):
        """16ビットアクセス無効アドレステスト"""
        # 無効な読み取りアドレス
        with pytest.raises(ValueError, match="Word address must be 0x0000-0xFFFE"):
            self.address_space.read_word(0xFFFF)
        
        with pytest.raises(ValueError, match="Word address must be 0x0000-0xFFFE"):
            self.address_space.read_word(-1)
        
        # 無効な書き込みアドレス
        with pytest.raises(ValueError, match="Word address must be 0x0000-0xFFFE"):
            self.address_space.write_word(0xFFFF, 0x1234)
    
    def test_word_write_invalid_value(self):
        """16ビット無効値テスト"""
        with pytest.raises(ValueError, match="Word value must be 0x0000-0xFFFF"):
            self.address_space.write_word(0x1000, -1)
        
        with pytest.raises(ValueError, match="Word value must be 0x0000-0xFFFF"):
            self.address_space.write_word(0x1000, 0x10000)
    
    def test_zero_page_access(self):
        """ゼロページアクセステスト"""
        # ゼロページアドレス計算
        for offset in range(0x00, 0x100):
            addr = self.address_space.get_zero_page_address(offset)
            assert addr == offset
            assert self.address_space.is_zero_page(addr)
        
        # 無効オフセット
        with pytest.raises(ValueError, match="Zero page offset must be 0x00-0xFF"):
            self.address_space.get_zero_page_address(-1)
        
        with pytest.raises(ValueError, match="Zero page offset must be 0x00-0xFF"):
            self.address_space.get_zero_page_address(0x100)
        
        # ゼロページ判定テスト
        assert self.address_space.is_zero_page(0x0000)
        assert self.address_space.is_zero_page(0x00FF)
        assert not self.address_space.is_zero_page(0x0100)
        assert not self.address_space.is_zero_page(0x1000)
    
    def test_stack_page_access(self):
        """スタックページアクセステスト"""
        # スタックアドレス計算
        for sp in range(0x00, 0x100):
            addr = self.address_space.get_stack_address(sp)
            expected = 0x0100 + sp
            assert addr == expected
            assert self.address_space.is_stack_page(addr)
        
        # 無効スタックポインタ
        with pytest.raises(ValueError, match="Stack pointer must be 0x00-0xFF"):
            self.address_space.get_stack_address(-1)
        
        with pytest.raises(ValueError, match="Stack pointer must be 0x00-0xFF"):
            self.address_space.get_stack_address(0x100)
        
        # スタックページ判定テスト
        assert self.address_space.is_stack_page(0x0100)
        assert self.address_space.is_stack_page(0x01FF)
        assert not self.address_space.is_stack_page(0x00FF)
        assert not self.address_space.is_stack_page(0x0200)
    
    def test_address_boundary_conditions(self):
        """アドレス境界条件テスト"""
        # 全アドレス空間の境界
        self.address_space.write_byte(0x0000, 0xAA)
        self.address_space.write_byte(0xFFFF, 0x55)
        assert self.address_space.read_byte(0x0000) == 0xAA
        assert self.address_space.read_byte(0xFFFF) == 0x55
        
        # ページ境界
        page_boundaries = [0x00FF, 0x0100, 0x01FF, 0x0200, 0x7FFF, 0x8000, 0xFFFE, 0xFFFF]
        for i, addr in enumerate(page_boundaries):
            value = 0x10 + i
            self.address_space.write_byte(addr, value)
            assert self.address_space.read_byte(addr) == value
    
    def test_read_only_regions(self):
        """読み取り専用領域テスト"""
        # ROM領域設定
        rom_start, rom_end = 0x8000, 0xFFFF
        self.address_space.set_read_only_region(rom_start, rom_end)
        
        # 読み取り専用領域への書き込み試行
        with pytest.raises(PermissionError, match="Cannot write to read-only address"):
            self.address_space.write_byte(0x8000, 0x42)
        
        with pytest.raises(PermissionError, match="Cannot write to read-only address"):
            self.address_space.write_byte(0xFFFF, 0x42)
        
        # 読み取り専用領域外は書き込み可能
        self.address_space.write_byte(0x7FFF, 0x42)
        assert self.address_space.read_byte(0x7FFF) == 0x42
        
        # 読み取り専用領域解除
        self.address_space.clear_read_only_region(rom_start, rom_end)
        self.address_space.write_byte(0x8000, 0x42)
        assert self.address_space.read_byte(0x8000) == 0x42
    
    def test_fill_memory(self):
        """メモリ埋めテスト"""
        # 基本的なメモリ埋め
        self.address_space.fill_memory(0x1000, 0x100, 0xAA)
        for addr in range(0x1000, 0x1100):
            assert self.address_space.read_byte(addr) == 0xAA
        
        # 境界値テスト
        self.address_space.fill_memory(0x0000, 1, 0x55)
        assert self.address_space.read_byte(0x0000) == 0x55
        
        # 無効パラメータ
        with pytest.raises(ValueError, match="Size must be positive"):
            self.address_space.fill_memory(0x1000, 0, 0x00)
        
        with pytest.raises(ValueError, match="Fill operation exceeds address space"):
            self.address_space.fill_memory(0xFFFF, 2, 0x00)
        
        # 読み取り専用領域への埋め込み試行
        self.address_space.set_read_only_region(0x2000, 0x2FFF)
        with pytest.raises(PermissionError):
            self.address_space.fill_memory(0x2000, 0x100, 0x00)
    
    def test_copy_memory(self):
        """メモリコピーテスト"""
        # テストデータ準備
        test_data = bytes(range(0x00, 0x100))
        for i, byte_val in enumerate(test_data):
            self.address_space.write_byte(0x1000 + i, byte_val)
        
        # 基本的なコピー
        self.address_space.copy_memory(0x1000, 0x2000, 0x100)
        for i in range(0x100):
            expected = self.address_space.read_byte(0x1000 + i)
            actual = self.address_space.read_byte(0x2000 + i)
            assert actual == expected
        
        # 重複領域コピー（前方重複）
        self.address_space.copy_memory(0x1000, 0x1080, 0x80)
        # 検証は省略（実装の詳細に依存）
        
        # 無効パラメータ
        with pytest.raises(ValueError, match="Size must be positive"):
            self.address_space.copy_memory(0x1000, 0x2000, 0)
        
        with pytest.raises(ValueError, match="Source copy exceeds address space"):
            self.address_space.copy_memory(0xFFFF, 0x1000, 2)
        
        with pytest.raises(ValueError, match="Destination copy exceeds address space"):
            self.address_space.copy_memory(0x1000, 0xFFFF, 2)
    
    def test_memory_dump(self):
        """メモリダンプテスト"""
        # テストデータ準備
        test_data = bytes([0xAA, 0x55, 0xCC, 0x33, 0xFF, 0x00])
        for i, byte_val in enumerate(test_data):
            self.address_space.write_byte(0x1000 + i, byte_val)
        
        # ダンプ取得
        dump = self.address_space.get_memory_dump(0x1000, len(test_data))
        assert dump == test_data
        
        # 境界値テスト
        single_byte = self.address_space.get_memory_dump(0x1000, 1)
        assert single_byte == bytes([0xAA])
        
        # 無効パラメータ
        with pytest.raises(ValueError, match="Size must be positive"):
            self.address_space.get_memory_dump(0x1000, 0)
        
        with pytest.raises(ValueError, match="Dump exceeds address space"):
            self.address_space.get_memory_dump(0xFFFF, 2)
    
    def test_memory_initialization(self):
        """メモリ初期化状態テスト"""
        # 初期状態は全て0
        for addr in [0x0000, 0x0080, 0x0100, 0x1000, 0x8000, 0xFFFF]:
            assert self.address_space.read_byte(addr) == 0x00
        
        # 16ビット読み取りも0
        for addr in [0x0000, 0x1000, 0x8000, 0xFFFE]:
            assert self.address_space.read_word(addr) == 0x0000
