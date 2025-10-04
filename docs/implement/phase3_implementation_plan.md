# Phase3: Memory & I/O 実装作業内容

## 概要

Phase3では、W65C02S Pythonエミュレータのメモリ管理システムと割り込み処理機能を実装します。Phase2で完成したCPUコアを基盤として、64KBアドレス空間の管理、デバイスマッピング、割り込みコントローラを構築します。

## 実装対象プログラムユニット

| PU ID | プログラムユニット名 | 主要責務 | 優先度 |
|-------|---------------------|----------|--------|
| **PU007** | AddressSpace | 64KBアドレス空間管理 | P2 (高) |
| **PU008** | DeviceMapper | デバイスマッピング管理 | P2 (高) |
| **PU009** | MemoryController | メモリアクセス制御 | P2 (高) |
| **PU021** | InterruptController | 割り込み制御 | P2 (高) |

## ファイル単位実装計画

### Week 1: メモリ管理システム

#### 1. `py6502emu/memory/address_space.py` (PU007)

**実装内容**:
- 64KBフラットアドレス空間の実装
- リトルエンディアン16ビット値処理
- ゼロページ・スタックページ特別処理
- アドレス範囲検証機能

**主要クラス**:
```python
class AddressSpace:
    """64KBアドレス空間管理クラス"""
    def __init__(self):
        self._memory = bytearray(65536)  # 64KB
    
    def read_byte(self, address: int) -> int:
        """8ビット読み取り"""
    
    def write_byte(self, address: int, value: int) -> None:
        """8ビット書き込み"""
    
    def read_word(self, address: int) -> int:
        """16ビット読み取り（リトルエンディアン）"""
    
    def write_word(self, address: int, value: int) -> None:
        """16ビット書き込み（リトルエンディアン）"""
    
    def get_zero_page_address(self, offset: int) -> int:
        """ゼロページアドレス計算"""
    
    def get_stack_address(self, sp: int) -> int:
        """スタックアドレス計算"""
```

**工数**: 1.5日

#### 2. `py6502emu/memory/device_mapper.py` (PU008)

**実装内容**:
- デバイスの動的マッピング機能
- アドレス範囲重複検出
- マッピング情報管理
- アドレス変換機能

**主要クラス**:
```python
class DeviceMapper:
    """デバイスマッピング管理クラス"""
    def __init__(self):
        self._mappings: List[DeviceMapping] = []
    
    def map_device(self, device: Device, start: int, end: int, name: str = "") -> None:
        """デバイスマッピング登録"""
    
    def unmap_device(self, start: int, end: int) -> None:
        """デバイスマッピング解除"""
    
    def find_device(self, address: int) -> Optional[DeviceMapping]:
        """アドレスに対応するデバイス検索"""
    
    def get_memory_map(self) -> List[Dict[str, Any]]:
        """メモリマップ情報取得"""
```

**工数**: 1.5日

#### 3. `py6502emu/memory/memory_controller.py` (PU009)

**実装内容**:
- メモリアクセス制御とルーティング
- デバイスアクセス権限チェック
- アクセスログ機能
- パフォーマンス最適化

**主要クラス**:
```python
class MemoryController:
    """メモリアクセス制御クラス"""
    def __init__(self, address_space: AddressSpace, device_mapper: DeviceMapper):
        self._address_space = address_space
        self._device_mapper = device_mapper
    
    def read(self, address: int) -> int:
        """統合メモリ読み取り"""
    
    def write(self, address: int, value: int) -> None:
        """統合メモリ書き込み"""
    
    def read_word(self, address: int) -> int:
        """16ビット読み取り"""
    
    def write_word(self, address: int, value: int) -> None:
        """16ビット書き込み"""
```

**工数**: 2日

### Week 2: 割り込み制御システム

#### 4. `py6502emu/core/interrupt_controller.py` (PU021)

**実装内容**:
- 集中的割り込み管理
- IRQ/NMI/RES優先度制御
- 割り込み要求・承認処理
- 割り込みベクタ管理

**主要クラス**:
```python
class InterruptController:
    """割り込みコントローラクラス"""
    def __init__(self):
        self._irq_sources: Set[str] = set()
        self._nmi_pending = False
        self._reset_pending = False
    
    def assert_irq(self, source_id: str) -> None:
        """IRQ要求アサート"""
    
    def deassert_irq(self, source_id: str) -> None:
        """IRQ要求デアサート"""
    
    def assert_nmi(self) -> None:
        """NMI要求アサート"""
    
    def assert_reset(self) -> None:
        """リセット要求アサート"""
    
    def is_pending(self) -> bool:
        """割り込み保留チェック"""
    
    def acknowledge(self) -> Optional[InterruptVector]:
        """割り込み承認"""
    
    def get_highest_priority_interrupt(self) -> Optional[InterruptType]:
        """最高優先度割り込み取得"""
```

**工数**: 2.5日

#### 5. `py6502emu/core/interrupt_types.py`

**実装内容**:
- 割り込み関連の型定義
- 割り込みベクタ定義
- 優先度定義

**主要定義**:
```python
from enum import Enum, auto
from typing import TypedDict

class InterruptType(Enum):
    """割り込み種別"""
    RESET = auto()
    NMI = auto()
    IRQ = auto()

class InterruptVector(TypedDict):
    """割り込みベクタ情報"""
    vector_address: int
    interrupt_type: InterruptType
    cycles: int

# 割り込みベクタアドレス定義
INTERRUPT_VECTORS = {
    InterruptType.RESET: 0xFFFC,
    InterruptType.NMI: 0xFFFA,
    InterruptType.IRQ: 0xFFFE,
}
```

**工数**: 0.5日

### テストファイル実装

#### 6. `tests/test_memory/test_address_space.py`

**テスト内容**:
- 64KBアドレス空間の全範囲テスト
- リトルエンディアン処理テスト
- ゼロページ・スタック特別処理テスト
- 境界値・異常値テスト

**主要テストケース**:
```python
class TestAddressSpace:
    def test_byte_read_write(self):
        """8ビット読み書きテスト"""
    
    def test_word_read_write_little_endian(self):
        """16ビットリトルエンディアンテスト"""
    
    def test_zero_page_access(self):
        """ゼロページアクセステスト"""
    
    def test_stack_page_access(self):
        """スタックページアクセステスト"""
    
    def test_address_boundary_conditions(self):
        """アドレス境界条件テスト"""
```

**工数**: 1日

#### 7. `tests/test_memory/test_device_mapper.py`

**テスト内容**:
- デバイスマッピング機能テスト
- アドレス重複検出テスト
- マッピング情報管理テスト

**工数**: 1日

#### 8. `tests/test_memory/test_memory_controller.py`

**テスト内容**:
- 統合メモリアクセステスト
- デバイスルーティングテスト
- アクセス権限チェックテスト

**工数**: 1日

#### 9. `tests/test_core/test_interrupt_controller.py`

**テスト内容**:
- 割り込み優先度テスト
- 割り込み要求・承認テスト
- 複数割り込み同時処理テスト

**工数**: 1日

### 統合テスト

#### 10. `tests/integration/test_phase3_integration.py`

**テスト内容**:
- メモリ・割り込みシステム統合テスト
- CPUコアとの連携テスト
- 実際のプログラム実行テスト

**主要テストシナリオ**:
```python
class TestPhase3Integration:
    def test_memory_mapped_io(self):
        """メモリマップドI/Oテスト"""
    
    def test_interrupt_handling_flow(self):
        """割り込み処理フローテスト"""
    
    def test_cpu_memory_integration(self):
        """CPU-メモリ統合テスト"""
    
    def test_device_interrupt_integration(self):
        """デバイス-割り込み統合テスト"""
```

**工数**: 1.5日

## 実装スケジュール

### Week 1: メモリ管理システム (5日間)

| 日 | 作業内容 | 担当ファイル | 工数 |
|----|----------|-------------|------|
| **Day 1** | AddressSpace実装開始 | `address_space.py` | 1日 |
| **Day 2** | AddressSpace完成・DeviceMapper開始 | `address_space.py`, `device_mapper.py` | 1日 |
| **Day 3** | DeviceMapper完成・MemoryController開始 | `device_mapper.py`, `memory_controller.py` | 1日 |
| **Day 4** | MemoryController完成 | `memory_controller.py` | 1日 |
| **Day 5** | メモリ系テスト実装 | `test_address_space.py`, `test_device_mapper.py`, `test_memory_controller.py` | 1日 |

### Week 2: 割り込み制御システム (5日間)

| 日 | 作業内容 | 担当ファイル | 工数 |
|----|----------|-------------|------|
| **Day 6** | 割り込み型定義・InterruptController開始 | `interrupt_types.py`, `interrupt_controller.py` | 1日 |
| **Day 7** | InterruptController実装継続 | `interrupt_controller.py` | 1日 |
| **Day 8** | InterruptController完成 | `interrupt_controller.py` | 1日 |
| **Day 9** | 割り込み系テスト実装 | `test_interrupt_controller.py` | 1日 |
| **Day 10** | 統合テスト・最終調整 | `test_phase3_integration.py` | 1日 |

## 成功基準

### 機能要件
- [ ] 64KBアドレス空間の完全管理
- [ ] デバイスマッピング機能の実装
- [ ] 割り込み処理（IRQ/NMI/RES）の実装
- [ ] CPUコアとの完全統合

### 品質要件
- [ ] 単体テストカバレッジ 90%以上
- [ ] 統合テスト成功率 95%以上
- [ ] メモリアクセス性能目標達成
- [ ] 全静的解析チェック通過

### 技術要件
- [ ] W65C02S仕様準拠のメモリアクセス
- [ ] 正確な割り込み優先度制御
- [ ] リトルエンディアン処理の完全実装
- [ ] デバイスAPI準拠の実装

## 依存関係

### 前提条件
- Phase1 (Foundation) の完了
- Phase2 (CPU Core) の完了
- SystemBus基盤の利用可能性

### 次フェーズへの提供
- 完全なメモリ管理システム
- 割り込み制御システム
- Phase4でのシステム統合基盤

## ファイル構造

```
py6502emu/
├── py6502emu/
│   ├── memory/                    # 🎯 Phase3 メインディレクトリ
│   │   ├── __init__.py
│   │   ├── address_space.py       # PU007: AddressSpace
│   │   ├── device_mapper.py       # PU008: DeviceMapper
│   │   └── memory_controller.py   # PU009: MemoryController
│   └── core/
│       ├── interrupt_controller.py # PU021: InterruptController
│       └── interrupt_types.py     # 割り込み型定義
├── tests/
│   ├── test_memory/               # 🧪 Phase3 テストディレクトリ
│   │   ├── __init__.py
│   │   ├── test_address_space.py
│   │   ├── test_device_mapper.py
│   │   └── test_memory_controller.py
│   ├── test_core/
│   │   └── test_interrupt_controller.py
│   └── integration/
│       └── test_phase3_integration.py
└── examples/
    └── memory_examples/           # 🎮 Phase3 使用例
        ├── memory_mapping_demo.py
        └── interrupt_demo.py
```

## 重要な実装ポイント

### 1. メモリアドレス空間レイアウト

```
$0000-$00FF: Zero Page (ゼロページ)
$0100-$01FF: Stack (スタック)
$0200-$7FFF: RAM (一般RAM)
$8000-$FFFF: ROM/Device (ROM・デバイス領域)
```

### 2. 割り込み優先度

| 優先度 | 割り込み種別 | ベクタアドレス | 処理サイクル |
|--------|-------------|---------------|-------------|
| **1** | RESET | $FFFC-$FFFD | 7サイクル |
| **2** | NMI | $FFFA-$FFFB | 7サイクル |
| **3** | IRQ/BRK | $FFFE-$FFFF | 7サイクル |

### 3. リトルエンディアン処理

```python
def read_word_le(self, address: int) -> int:
    """リトルエンディアン16ビット読み取り"""
    low = self.read_byte(address)
    high = self.read_byte(address + 1)
    return low | (high << 8)

def write_word_le(self, address: int, value: int) -> None:
    """リトルエンディアン16ビット書き込み"""
    self.write_byte(address, value & 0xFF)
    self.write_byte(address + 1, (value >> 8) & 0xFF)
```

## まとめ

Phase3の実装により、W65C02S Pythonエミュレータは完全なメモリ管理システムと割り込み制御機能を獲得し、Phase4のシステム統合に向けた重要な基盤が整います。この段階で、実際のW65C02Sプログラムの実行が可能となり、エミュレータとしての基本機能が完成します。