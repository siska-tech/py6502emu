"""
Phase3 統合テスト

メモリ管理システムと割り込み制御システムの統合テスト、
CPUコアとの連携テストを提供します。
"""

import pytest
from unittest.mock import Mock, MagicMock
from py6502emu.memory.address_space import AddressSpace
from py6502emu.memory.device_mapper import DeviceMapper
from py6502emu.memory.memory_controller import MemoryController, MemoryAccessError
from py6502emu.core.interrupt_controller import InterruptController
from py6502emu.core.interrupt_types import InterruptType
from py6502emu.core.device import Device


class MockCPU:
    """テスト用モックCPU"""
    
    def __init__(self):
        self.name = "W65C02S"
        self.registers = {
            'A': 0x00, 'X': 0x00, 'Y': 0x00,
            'PC': 0x8000, 'SP': 0xFF, 'P': 0x20
        }
        self.interrupt_enabled = True
        self.cycles = 0
        
        # 実行履歴
        self.executed_instructions = []
        self.memory_accesses = []
        self.interrupt_services = []
    
    def reset(self) -> None:
        self.registers = {
            'A': 0x00, 'X': 0x00, 'Y': 0x00,
            'PC': 0x8000, 'SP': 0xFF, 'P': 0x20
        }
        self.cycles = 0
    
    def tick(self, master_cycles: int) -> int:
        return 0
    
    def read(self, address: int) -> int:
        # CPUはメモリコントローラ経由でアクセス
        return 0
    
    def write(self, address: int, value: int) -> None:
        # CPUはメモリコントローラ経由でアクセス
        pass
    
    def get_state(self) -> dict:
        return {'registers': self.registers.copy()}
    
    def set_state(self, state: dict) -> None:
        if 'registers' in state:
            self.registers.update(state['registers'])
    
    def step(self) -> int:
        """単一命令実行シミュレーション"""
        self.cycles += 2  # 基本2サイクル
        return 2
    
    def get_registers(self) -> dict:
        return self.registers.copy()
    
    def set_pc(self, address: int) -> None:
        self.registers['PC'] = address
    
    def is_interrupt_enabled(self) -> bool:
        return self.interrupt_enabled
    
    def service_interrupt(self, vector_address: int) -> int:
        """割り込みサービスシミュレーション"""
        self.interrupt_services.append(vector_address)
        # スタックにPC、Pを保存（簡略化）
        self.registers['SP'] = (self.registers['SP'] - 3) & 0xFF
        # 割り込みベクタからPCを読み込み（簡略化）
        self.registers['PC'] = vector_address
        return 7  # 割り込み処理サイクル


class MockROM:
    """テスト用ROMデバイス"""
    
    def __init__(self, size: int = 0x8000):
        self.name = "ROM"
        self._data = bytearray(size)
        self.read_count = 0
        self.write_count = 0
    
    def reset(self) -> None:
        self.read_count = 0
        self.write_count = 0
    
    def tick(self, master_cycles: int) -> int:
        return 0
    
    def read(self, address: int) -> int:
        self.read_count += 1
        if address < len(self._data):
            return self._data[address]
        return 0xFF
    
    def write(self, address: int, value: int) -> None:
        self.write_count += 1
        # ROM is read-only, but we track write attempts
    
    def get_state(self) -> dict:
        return {'data': bytes(self._data)}
    
    def set_state(self, state: dict) -> None:
        if 'data' in state:
            self._data = bytearray(state['data'])
    
    def load_data(self, address: int, data: bytes) -> None:
        """ROMにデータをロード"""
        for i, byte_val in enumerate(data):
            if address + i < len(self._data):
                self._data[address + i] = byte_val


class MockRAM:
    """テスト用RAMデバイス"""
    
    def __init__(self, size: int = 0x8000):
        self.name = "RAM"
        self._data = bytearray(size)
        self.access_count = {'read': 0, 'write': 0}
    
    def reset(self) -> None:
        self._data = bytearray(len(self._data))
        self.access_count = {'read': 0, 'write': 0}
    
    def tick(self, master_cycles: int) -> int:
        return 0
    
    def read(self, address: int) -> int:
        self.access_count['read'] += 1
        if address < len(self._data):
            return self._data[address]
        return 0x00
    
    def write(self, address: int, value: int) -> None:
        self.access_count['write'] += 1
        if address < len(self._data):
            self._data[address] = value
    
    def get_state(self) -> dict:
        return {'data': bytes(self._data)}
    
    def set_state(self, state: dict) -> None:
        if 'data' in state:
            self._data = bytearray(state['data'])


class MockIODevice:
    """テスト用I/Oデバイス"""
    
    def __init__(self):
        self.name = "IO"
        self._registers = bytearray(16)  # 16バイトのレジスタ
        self.interrupt_pending = False
        self.access_log = []
    
    def reset(self) -> None:
        self._registers = bytearray(16)
        self.interrupt_pending = False
        self.access_log.clear()
    
    def tick(self, master_cycles: int) -> int:
        # 定期的に割り込み要求（テスト用）
        if master_cycles % 100 == 0:
            self.interrupt_pending = True
        return 0
    
    def read(self, address: int) -> int:
        self.access_log.append(('read', address))
        if address < len(self._registers):
            return self._registers[address]
        return 0x00
    
    def write(self, address: int, value: int) -> None:
        self.access_log.append(('write', address, value))
        if address < len(self._registers):
            self._registers[address] = value
            # 特定レジスタへの書き込みで割り込みクリア
            if address == 0x0F:
                self.interrupt_pending = False
    
    def get_state(self) -> dict:
        return {'registers': bytes(self._registers)}
    
    def set_state(self, state: dict) -> None:
        if 'registers' in state:
            self._registers = bytearray(state['registers'])


class TestPhase3Integration:
    """Phase3 統合テスト"""
    
    def setup_method(self):
        """各テストメソッド前の初期化"""
        # コンポーネント初期化
        self.address_space = AddressSpace()
        self.device_mapper = DeviceMapper()
        self.memory_controller = MemoryController(self.address_space, self.device_mapper)
        self.interrupt_controller = InterruptController()
        
        # モックデバイス
        self.cpu = MockCPU()
        self.ram = MockRAM(0x8000)  # 32KB RAM
        self.rom = MockROM(0x8000)  # 32KB ROM
        self.io_device = MockIODevice()
        
        # 基本メモリマップ設定
        self.setup_memory_map()
    
    def setup_memory_map(self):
        """基本メモリマップ設定"""
        # RAM: $0000-$7FFF (32KB)
        self.device_mapper.map_device(self.ram, 0x0000, 0x7FFF, "RAM")
        
        # ROM: $8000-$FFFF (32KB, 読み取り専用)
        self.device_mapper.map_device(self.rom, 0x8000, 0xFFFF, "ROM", read_only=True)
        
        # I/O: $C000-$C00F (16バイト)
        self.device_mapper.unmap_device_by_name("ROM")  # 一時的に解除
        self.device_mapper.map_device(self.io_device, 0xC000, 0xC00F, "IO")
        self.device_mapper.map_device(self.rom, 0x8000, 0xBFFF, "ROM_LOW", device_offset=0x0000, read_only=True)
        self.device_mapper.map_device(self.rom, 0xC010, 0xFFFF, "ROM_HIGH", device_offset=0x4010, read_only=True)
    
    def test_memory_mapped_io(self):
        """メモリマップドI/Oテスト"""
        # I/Oデバイスへの書き込み
        self.memory_controller.write(0xC000, 0x42)
        assert self.io_device._registers[0] == 0x42
        
        # I/Oデバイスからの読み取り
        value = self.memory_controller.read(0xC000)
        assert value == 0x42
        
        # アクセスログ確認
        assert ('write', 0, 0x42) in self.io_device.access_log
        assert ('read', 0) in self.io_device.access_log
    
    def test_ram_rom_access(self):
        """RAM・ROMアクセステスト"""
        # RAMへの書き込み・読み取り
        self.memory_controller.write(0x1000, 0xAA)
        assert self.memory_controller.read(0x1000) == 0xAA
        assert self.ram.access_count['write'] == 1
        assert self.ram.access_count['read'] == 1
        
        # ROMデータ設定
        self.rom.load_data(0x0000, bytes([0x55, 0x66, 0x77]))
        
        # ROMからの読み取り
        assert self.memory_controller.read(0x8000) == 0x55
        assert self.memory_controller.read(0x8001) == 0x66
        assert self.memory_controller.read(0x8002) == 0x77
        
        # ROMへの書き込み試行（読み取り専用）
        with pytest.raises(MemoryAccessError):
            self.memory_controller.write(0x8000, 0x99)
    
    def test_interrupt_handling_flow(self):
        """割り込み処理フローテスト"""
        # 割り込みベクタ設定（ROM領域）
        irq_vector = 0xA000
        nmi_vector = 0xB000
        reset_vector = 0xC000
        
        # ベクタテーブル設定（$FFFA-$FFFF）
        # ROMデバイス内の実際のオフセット（device_offsetを考慮）
        vector_offset = 0xFFFA - 0xC010 + 0x4010  # ROM内の実際の位置
        self.rom.load_data(vector_offset, bytes([
            nmi_vector & 0xFF, (nmi_vector >> 8) & 0xFF,    # NMI vector
            reset_vector & 0xFF, (reset_vector >> 8) & 0xFF, # RESET vector
            irq_vector & 0xFF, (irq_vector >> 8) & 0xFF      # IRQ vector
        ]))
        
        # IRQ要求
        self.interrupt_controller.assert_irq("timer")
        assert self.interrupt_controller.is_pending()
        
        # 割り込み承認
        vector_info = self.interrupt_controller.acknowledge(interrupt_enabled=True)
        assert vector_info is not None
        assert vector_info['interrupt_type'] == InterruptType.IRQ
        assert vector_info['vector_address'] == 0xFFFE
        
        # ベクタアドレスからハンドラアドレス読み取り
        handler_low = self.memory_controller.read(0xFFFE)
        handler_high = self.memory_controller.read(0xFFFF)
        handler_address = handler_low | (handler_high << 8)
        assert handler_address == irq_vector
    
    def test_multiple_interrupt_priority(self):
        """複数割り込み優先度テスト"""
        # 複数割り込み同時発生
        self.interrupt_controller.assert_irq("timer")
        self.interrupt_controller.assert_nmi("watchdog")
        self.interrupt_controller.assert_reset("power")
        
        # 最高優先度（RESET）が選択される
        highest = self.interrupt_controller.get_highest_priority_interrupt()
        assert highest == InterruptType.RESET
        
        # RESET承認
        vector = self.interrupt_controller.acknowledge()
        assert vector['interrupt_type'] == InterruptType.RESET
        
        # 次の優先度（NMI）
        highest = self.interrupt_controller.get_highest_priority_interrupt()
        assert highest == InterruptType.NMI
        
        # NMI承認
        vector = self.interrupt_controller.acknowledge()
        assert vector['interrupt_type'] == InterruptType.NMI
        
        # 最後（IRQ）
        highest = self.interrupt_controller.get_highest_priority_interrupt()
        assert highest == InterruptType.IRQ
    
    def test_cpu_memory_integration(self):
        """CPU-メモリ統合テスト"""
        # CPUリセット処理シミュレーション
        self.cpu.reset()
        
        # リセットベクタ設定
        reset_address = 0x8000
        # ROMデバイス内の実際のオフセット（device_offsetを考慮）
        vector_offset = 0xFFFC - 0xC010 + 0x4010  # ROM内の実際の位置
        self.rom.load_data(vector_offset, bytes([
            reset_address & 0xFF, (reset_address >> 8) & 0xFF
        ]))
        
        # リセット割り込み
        self.interrupt_controller.assert_reset("power_on")
        vector = self.interrupt_controller.acknowledge()
        
        # CPUがリセットベクタを読み取り
        vector_low = self.memory_controller.read(vector['vector_address'])
        vector_high = self.memory_controller.read(vector['vector_address'] + 1)
        new_pc = vector_low | (vector_high << 8)
        
        self.cpu.set_pc(new_pc)
        assert self.cpu.get_registers()['PC'] == reset_address
    
    def test_device_interrupt_integration(self):
        """デバイス-割り込み統合テスト"""
        # I/Oデバイスが割り込み要求
        self.io_device.interrupt_pending = True
        
        # 割り込みコントローラに要求
        if self.io_device.interrupt_pending:
            self.interrupt_controller.assert_irq("io_device")
        
        # 割り込み承認
        vector = self.interrupt_controller.acknowledge(interrupt_enabled=True)
        assert vector is not None
        
        # 割り込みハンドラでI/Oデバイスのレジスタをクリア
        self.memory_controller.write(0xC00F, 0x00)  # 割り込みクリアレジスタ
        assert not self.io_device.interrupt_pending
        
        # 割り込み要求デアサート
        self.interrupt_controller.deassert_irq("io_device")
    
    def test_memory_access_logging_integration(self):
        """メモリアクセスログ統合テスト"""
        # アクセスログ有効化
        self.memory_controller.enable_access_logging(True)
        
        # 各種メモリアクセス
        self.memory_controller.write(0x1000, 0xAA)  # RAM
        self.memory_controller.read(0x8000)         # ROM
        self.memory_controller.write(0xC000, 0x55)  # I/O
        
        # ログ確認
        log = self.memory_controller.get_access_log()
        assert len(log) == 3
        
        # RAM書き込みログ
        ram_log = next(l for l in log if l.address == 0x1000)
        assert ram_log.device_name == "RAM"
        assert ram_log.value == 0xAA
        
        # ROM読み取りログ
        rom_log = next(l for l in log if l.address == 0x8000)
        assert rom_log.device_name == "ROM_LOW"
        
        # I/O書き込みログ
        io_log = next(l for l in log if l.address == 0xC000)
        assert io_log.device_name == "IO"
        assert io_log.value == 0x55
    
    def test_system_performance_integration(self):
        """システム性能統合テスト"""
        # 大量のメモリアクセス
        access_count = 1000
        
        for i in range(access_count):
            # RAMアクセス
            self.memory_controller.write(0x1000 + (i % 0x100), i & 0xFF)
            self.memory_controller.read(0x1000 + (i % 0x100))
            
            # ROMアクセス
            self.memory_controller.read(0x8000 + (i % 0x100))
        
        # 統計確認
        stats = self.memory_controller.get_access_statistics()
        assert stats['total_reads'] == access_count * 2  # RAM read + ROM read
        assert stats['total_writes'] == access_count     # RAM write only
        
        # デバイス別統計
        assert stats['device_access_count']['RAM']['read'] == access_count
        assert stats['device_access_count']['RAM']['write'] == access_count
        assert stats['device_access_count']['ROM_LOW']['read'] == access_count
    
    def test_memory_map_validation(self):
        """メモリマップ検証テスト"""
        # メモリマップ情報取得
        memory_map = self.memory_controller.get_memory_map_info()
        
        # マッピング数確認
        assert memory_map['mapping_count'] == 4  # RAM, ROM_LOW, IO, ROM_HIGH
        
        # 未マッピング領域確認
        unmapped = memory_map['unmapped_ranges']
        # 全領域がマッピングされているはず
        total_unmapped = sum(r['size'] for r in unmapped)
        assert total_unmapped == 0
        
        # 整合性チェック
        issues = self.memory_controller.validate_system_integrity()
        assert len(issues) == 0
    
    def test_interrupt_statistics_integration(self):
        """割り込み統計統合テスト"""
        # 各種割り込み発生
        interrupts = [
            (InterruptType.RESET, "power_on"),
            (InterruptType.NMI, "watchdog"),
            (InterruptType.IRQ, "timer"),
            (InterruptType.IRQ, "uart"),
            (InterruptType.IRQ, "keyboard")
        ]
        
        for interrupt_type, source in interrupts:
            if interrupt_type == InterruptType.RESET:
                self.interrupt_controller.assert_reset(source)
            elif interrupt_type == InterruptType.NMI:
                self.interrupt_controller.assert_nmi(source)
            else:
                self.interrupt_controller.assert_irq(source)
            
            # 承認
            self.interrupt_controller.acknowledge(interrupt_enabled=True)
        
        # 統計確認
        stats = self.interrupt_controller.get_interrupt_statistics()
        assert stats['total_interrupts'] == len(interrupts)
        assert stats['interrupt_count_by_type'][InterruptType.RESET] == 1
        assert stats['interrupt_count_by_type'][InterruptType.NMI] == 1
        assert stats['interrupt_count_by_type'][InterruptType.IRQ] == 3
    
    def test_full_system_reset(self):
        """システム全体リセットテスト"""
        # システム状態設定
        self.memory_controller.write(0x1000, 0xAA)
        self.memory_controller.enable_access_logging(True)
        self.interrupt_controller.assert_irq("timer")
        
        # 各コンポーネントリセット
        self.cpu.reset()
        self.ram.reset()
        self.rom.reset()
        self.io_device.reset()
        self.interrupt_controller.force_clear_all_interrupts()
        self.memory_controller.reset_statistics()
        
        # リセット後状態確認
        assert self.memory_controller.read(0x1000) == 0x00  # RAMクリア
        assert not self.interrupt_controller.is_pending()
        assert self.memory_controller.get_access_statistics()['total_reads'] == 1  # 上記read分
        assert len(self.io_device.access_log) == 0
    
    def test_complex_memory_operations(self):
        """複雑なメモリ操作テスト"""
        # 16ビットデータ操作
        test_word = 0x1234
        self.memory_controller.write_word(0x1000, test_word)
        assert self.memory_controller.read_word(0x1000) == test_word
        
        # バルク操作
        test_data = bytes(range(0x00, 0x100))
        self.memory_controller.bulk_write(0x2000, test_data)
        read_data = self.memory_controller.bulk_read(0x2000, len(test_data))
        assert read_data == test_data
        
        # クロスデバイス操作（RAMからROMへのコピー試行）
        with pytest.raises(MemoryAccessError):
            # ROMは読み取り専用なので書き込み不可
            self.memory_controller.bulk_write(0x8000, test_data[:16])
    
    def test_interrupt_nesting_simulation(self):
        """割り込みネスト処理シミュレーション"""
        # 低優先度割り込み処理中に高優先度割り込み発生
        self.interrupt_controller.assert_irq("low_priority")
        
        # IRQ承認・処理開始
        vector = self.interrupt_controller.acknowledge(interrupt_enabled=True)
        assert vector['interrupt_type'] == InterruptType.IRQ
        
        # 処理中にNMI発生
        self.interrupt_controller.assert_nmi("high_priority")
        
        # NMIは即座に処理される（マスク不可）
        vector = self.interrupt_controller.acknowledge(interrupt_enabled=False)
        assert vector['interrupt_type'] == InterruptType.NMI
        
        # NMI処理完了
        self.interrupt_controller.complete_interrupt_service()
        
        # 元のIRQ処理に戻る（実際のCPUでは自動的に復帰）
        assert self.interrupt_controller._current_state.name in ['IDLE', 'PENDING']
