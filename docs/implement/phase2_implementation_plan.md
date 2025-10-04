# Phase2: CPU Core Implementation Plan
# W65C02S Pythonエミュレータ Phase2実装計画書

## 文書管理

| 項目 | 内容 |
| :--- | :--- |
| **バージョン** | 1.0 |
| **関連文書** | W65C02Sソフトウェア詳細設計書、実装計画書 |

---

## 目次

1. [Phase2概要](#phase2概要)
2. [実装対象コンポーネント](#実装対象コンポーネント)
3. [ファイル構造](#ファイル構造)
4. [実装スケジュール](#実装スケジュール)
5. [成功基準](#成功基準)
6. [重要な実装ポイント](#重要な実装ポイント)

---

## Phase2概要

### 基本情報

| 項目 | 内容 |
|------|------|
| **フェーズ名** | CPU Core (CPUコア) |
| **期間** | 3週間 (Week 3-5) |
| **目標** | W65C02S CPUコアの完全実装 |
| **依存関係** | Phase 1 (Foundation) の完了が前提 |
| **主要成果物** | 212命令セット、16種アドレッシングモード、サイクル精度実装 |

### 実装目標

- ✅ W65C02S CPUコアの完全実装
- ✅ 212個の有効オペコード実装
- ✅ 16種類のアドレッシングモード実装
- ✅ サイクル精度の実現
- ✅ NMOS 6502からの差異点の正確な実装
- ✅ 包括的なテストスイート (90%+カバレッジ)

---

## 実装対象コンポーネント

### プログラムユニット (PU) 一覧

| PU ID | プログラムユニット名 | 主要責務 | 優先度 | 実装週 |
|-------|---------------------|----------|--------|--------|
| **PU001** | CPURegisters | A,X,Y,PC,S,Pレジスタの管理 | P2 (高) | Week 1 |
| **PU002** | ProcessorFlags | N,V,B,D,I,Z,Cフラグの管理 | P2 (高) | Week 1 |
| **PU003** | InstructionDecoder | 212命令のデコード処理 | P2 (高) | Week 2 |
| **PU004** | InstructionExecutor | 命令実行エンジン | P2 (高) | Week 3 |
| **PU005** | AddressingModes | 16種アドレッシングモード計算 | P2 (高) | Week 1 |

### 命令セット実装優先順位

#### Priority 1: Core Instructions (コア命令)
- **Load/Store**: LDA, STA, LDX, STX, LDY, STY
- **Transfer**: TAX, TAY, TXA, TYA, TSX, TXS
- **Stack**: PHA, PLA, PHP, PLP

#### Priority 2: Arithmetic (算術演算)
- **Addition**: ADC, SBC
- **Increment/Decrement**: INC, DEC, INX, DEX, INY, DEY
- **Compare**: CMP, CPX, CPY

#### Priority 3: Logic & Bit (論理・ビット)
- **Logic**: AND, ORA, EOR
- **Shift**: ASL, LSR, ROL, ROR
- **Bit Test**: BIT, TRB, TSB

#### Priority 4: Control Flow (制御フロー)
- **Jump**: JMP, JSR, RTS, RTI
- **Branch**: BCC, BCS, BEQ, BNE, BMI, BPL, BVC, BVS, BRA
- **Flag Control**: CLC, SEC, CLI, SEI, CLD, SED, CLV

#### Priority 5: System & Special (システム・特殊)
- **System**: BRK, NOP, WAI, STP
- **W65C02S Specific**: BBR, BBS, RMB, SMB
- **Enhanced**: PHX, PHY, PLX, PLY

### アドレッシングモード実装順序

| 優先度 | アドレッシングモード | 実装理由 |
|--------|---------------------|----------|
| **1** | Immediate (imm) | 最も単純、テスト容易 |
| **2** | Zero Page (zp) | 基本的なメモリアクセス |
| **3** | Absolute (abs) | 16ビットアドレッシング |
| **4** | Zero Page,X (zp,x) | インデックス付きアクセス |
| **5** | Absolute,X (abs,x) | ページクロス処理 |
| **6** | Absolute,Y (abs,y) | Y インデックス |
| **7** | (Zero Page,X) (zp,x) | 間接アドレッシング |
| **8** | (Zero Page),Y (zp),y | 間接インデックス |
| **9** | (Zero Page) (zp) | W65C02S 拡張 |
| **10** | Relative (rel) | 分岐命令用 |

---

## ファイル構造

### 推奨ディレクトリ構造

```
py6502emu/
├── py6502emu/
│   ├── __init__.py
│   ├── cpu/                    # 🎯 Phase2 メインディレクトリ
│   │   ├── __init__.py
│   │   ├── registers.py        # PU001: CPURegisters
│   │   ├── flags.py            # PU002: ProcessorFlags  
│   │   ├── decoder.py          # PU003: InstructionDecoder
│   │   ├── executor.py         # PU004: InstructionExecutor
│   │   ├── addressing.py       # PU005: AddressingModes
│   │   ├── instructions/       # 命令実装ディレクトリ
│   │   │   ├── __init__.py
│   │   │   ├── load_store.py   # LDA, STA, LDX, STX, LDY, STY
│   │   │   ├── arithmetic.py   # ADC, SBC, INC, DEC, INX, DEX, INY, DEY
│   │   │   ├── logical.py      # AND, ORA, EOR, BIT
│   │   │   ├── shift.py        # ASL, LSR, ROL, ROR
│   │   │   ├── transfer.py     # TAX, TAY, TXA, TYA, TSX, TXS
│   │   │   ├── stack.py        # PHA, PLA, PHP, PLP, PHX, PHY, PLX, PLY
│   │   │   ├── compare.py      # CMP, CPX, CPY
│   │   │   ├── branch.py       # BCC, BCS, BEQ, BNE, BMI, BPL, BVC, BVS, BRA
│   │   │   ├── jump.py         # JMP, JSR, RTS, RTI
│   │   │   ├── flag_ops.py     # CLC, SEC, CLI, SEI, CLD, SED, CLV
│   │   │   ├── system.py       # BRK, NOP, WAI, STP
│   │   │   └── w65c02s.py      # BBR, BBS, RMB, SMB, TRB, TSB, STZ
│   │   └── cpu_core.py         # メインCPUクラス統合
│   └── core/                   # Phase1で作成済み (依存)
│       ├── __init__.py
│       ├── protocols.py        # Device プロトコル定義
│       └── bus.py              # SystemBus実装
├── tests/
│   ├── test_cpu/              # 🧪 Phase2 テストディレクトリ
│   │   ├── __init__.py
│   │   ├── test_registers.py   # PU001テスト
│   │   ├── test_flags.py       # PU002テスト
│   │   ├── test_decoder.py     # PU003テスト
│   │   ├── test_executor.py    # PU004テスト
│   │   ├── test_addressing.py  # PU005テスト
│   │   ├── test_instructions/  # 命令別テスト
│   │   │   ├── test_load_store.py
│   │   │   ├── test_arithmetic.py
│   │   │   ├── test_logical.py
│   │   │   ├── test_shift.py
│   │   │   ├── test_transfer.py
│   │   │   ├── test_stack.py
│   │   │   ├── test_compare.py
│   │   │   ├── test_branch.py
│   │   │   ├── test_jump.py
│   │   │   ├── test_flag_ops.py
│   │   │   ├── test_system.py
│   │   │   └── test_w65c02s.py
│   │   ├── test_cpu_integration.py  # CPU統合テスト
│   │   └── fixtures/           # テストデータ
│   │       ├── instruction_tests.json
│   │       └── cycle_tests.json
│   └── test_core/             # Phase1テスト (既存)
└── examples/
    └── cpu_examples/          # 🎮 Phase2 使用例
        ├── basic_cpu_usage.py
        ├── instruction_demo.py
        └── register_demo.py
```

### 主要ファイルの責務

| ファイル | 責務 | 依存関係 |
|----------|------|----------|
| `registers.py` | CPUレジスタ管理 (A,X,Y,PC,S,P) | なし |
| `flags.py` | プロセッサフラグ管理 (N,V,B,D,I,Z,C) | registers.py |
| `addressing.py` | 16種アドレッシングモード計算 | registers.py |
| `decoder.py` | 212命令のデコード処理 | addressing.py |
| `executor.py` | 命令実行エンジン | decoder.py, instructions/ |
| `cpu_core.py` | メインCPUクラス統合 | 全PU |

---

## 実装スケジュール

### Week 1 (Day 11-17): 基盤コンポーネント

| 優先度 | ファイル | 実装内容 | 工数 | 依存関係 |
|--------|----------|----------|------|----------|
| **1** | `py6502emu/cpu/registers.py` | PU001: CPURegisters実装 | 1日 | なし |
| **2** | `py6502emu/cpu/flags.py` | PU002: ProcessorFlags実装 | 1日 | registers.py |
| **3** | `py6502emu/cpu/addressing.py` | PU005: AddressingModes実装 | 2日 | registers.py |
| **4** | `tests/test_cpu/test_registers.py` | レジスタテスト | 0.5日 | registers.py |
| **5** | `tests/test_cpu/test_flags.py` | フラグテスト | 0.5日 | flags.py |
| **6** | `tests/test_cpu/test_addressing.py` | アドレッシングテスト | 1日 | addressing.py |

#### Week 1 成果物
- ✅ CPUレジスタ管理システム
- ✅ プロセッサフラグ管理システム
- ✅ 16種アドレッシングモード実装
- ✅ 基盤コンポーネントテスト (90%+カバレッジ)

### Week 2 (Day 18-24): 命令デコーダ

| 優先度 | ファイル | 実装内容 | 工数 | 依存関係 |
|--------|----------|----------|------|----------|
| **7** | `py6502emu/cpu/decoder.py` | PU003: InstructionDecoder基盤 | 2日 | addressing.py |
| **8** | `py6502emu/cpu/instructions/__init__.py` | 命令カテゴリ定義 | 0.5日 | decoder.py |
| **9** | `py6502emu/cpu/instructions/load_store.py` | Priority 1命令群 | 1日 | decoder.py |
| **10** | `py6502emu/cpu/instructions/transfer.py` | Priority 1命令群 | 0.5日 | load_store.py |
| **11** | `py6502emu/cpu/instructions/stack.py` | Priority 1命令群 | 1日 | transfer.py |
| **12** | `tests/test_cpu/test_decoder.py` | デコーダテスト | 1日 | decoder.py |

#### Week 2 成果物
- ✅ 命令デコーダシステム
- ✅ Priority 1命令群実装 (Load/Store, Transfer, Stack)
- ✅ 命令テーブル構築
- ✅ デコーダテスト (90%+カバレッジ)

### Week 3 (Day 25-35): 命令実行器と統合

| 優先度 | ファイル | 実装内容 | 工数 | 依存関係 |
|--------|----------|----------|------|----------|
| **13** | `py6502emu/cpu/executor.py` | PU004: InstructionExecutor基盤 | 2日 | decoder.py, instructions/ |
| **14** | `py6502emu/cpu/instructions/arithmetic.py` | Priority 2命令群 | 1.5日 | executor.py |
| **15** | `py6502emu/cpu/instructions/logical.py` | Priority 3命令群 | 1日 | arithmetic.py |
| **16** | `py6502emu/cpu/instructions/branch.py` | Priority 4命令群 | 1.5日 | logical.py |
| **17** | `py6502emu/cpu/instructions/jump.py` | Priority 4命令群 | 1日 | branch.py |
| **18** | `py6502emu/cpu/cpu_core.py` | メインCPUクラス統合 | 2日 | 全PU完成後 |
| **19** | `tests/test_cpu/test_cpu_integration.py` | CPU統合テスト | 1日 | cpu_core.py |

#### Week 3 成果物
- ✅ 命令実行エンジン
- ✅ 全212命令実装完了
- ✅ メインCPUクラス統合
- ✅ CPU統合テスト (95%+成功率)

---

## 成功基準

### 技術的成功基準

| 項目 | 目標 | 測定方法 |
|------|------|----------|
| **命令セット実装** | 212個の命令完全実装 | 命令テスト100%通過 |
| **アドレッシングモード** | 16種類完全実装 | アドレッシングテスト100%通過 |
| **サイクル精度** | W65C02S仕様準拠 | サイクル数テスト100%通過 |
| **単体テストカバレッジ** | 90%以上 | pytest-cov測定 |
| **統合テスト成功率** | 95%以上 | 自動テスト結果 |

### 品質基準

| 項目 | 基準 | 検証方法 |
|------|------|----------|
| **型チェック** | mypy エラー0件 | 静的解析 |
| **コード品質** | pylint A評価以上 | 静的解析 |
| **ドキュメント** | 全パブリックAPI文書化 | docstring 100% |
| **性能** | 基本命令 < 2μs/cycle | ベンチマーク |

### 機能検証項目

#### ✅ CPUレジスタ (PU001)
- [ ] A, X, Y レジスタの8ビット操作
- [ ] PC レジスタの16ビット操作
- [ ] S レジスタのスタック管理
- [ ] P レジスタのフラグ管理
- [ ] レジスタ間転送操作
- [ ] 状態保存・復元機能

#### ✅ プロセッサフラグ (PU002)
- [ ] N, V, B, D, I, Z, C フラグの個別制御
- [ ] 演算結果によるフラグ自動更新
- [ ] 条件分岐でのフラグ判定
- [ ] スタック操作でのフラグ処理
- [ ] 割り込み処理でのフラグ制御

#### ✅ アドレッシングモード (PU005)
- [ ] Immediate (imm) - 即値
- [ ] Zero Page (zp) - ゼロページ
- [ ] Absolute (abs) - 絶対アドレス
- [ ] Zero Page,X/Y (zp,x/y) - ゼロページインデックス
- [ ] Absolute,X/Y (abs,x/y) - 絶対アドレスインデックス
- [ ] (Zero Page,X) (zp,x) - ゼロページ間接インデックス
- [ ] (Zero Page),Y (zp),y - ゼロページ間接ポストインデックス
- [ ] (Zero Page) (zp) - ゼロページ間接 (W65C02S拡張)
- [ ] (Absolute) (abs) - 絶対間接
- [ ] (Absolute,X) (abs,x) - 絶対間接インデックス (W65C02S拡張)
- [ ] Relative (rel) - 相対アドレス
- [ ] ページクロスペナルティ処理

#### ✅ 命令デコーダ (PU003)
- [ ] 212個の有効オペコード認識
- [ ] 命令長の正確な判定 (1-3バイト)
- [ ] アドレッシングモードの正確な判定
- [ ] サイクル数の正確な計算
- [ ] 無効オペコードの適切な処理

#### ✅ 命令実行器 (PU004)
- [ ] Load/Store命令群 (LDA, STA, LDX, STX, LDY, STY, STZ)
- [ ] 算術演算命令群 (ADC, SBC, INC, DEC, INX, DEX, INY, DEY)
- [ ] 論理演算命令群 (AND, ORA, EOR, BIT, TRB, TSB)
- [ ] シフト/ローテート命令群 (ASL, LSR, ROL, ROR)
- [ ] 転送命令群 (TAX, TAY, TXA, TYA, TSX, TXS)
- [ ] スタック命令群 (PHA, PLA, PHP, PLP, PHX, PHY, PLX, PLY)
- [ ] 比較命令群 (CMP, CPX, CPY)
- [ ] 分岐命令群 (BCC, BCS, BEQ, BNE, BMI, BPL, BVC, BVS, BRA)
- [ ] ジャンプ命令群 (JMP, JSR, RTS, RTI)
- [ ] フラグ制御命令群 (CLC, SEC, CLI, SEI, CLD, SED, CLV)
- [ ] システム命令群 (BRK, NOP, WAI, STP)
- [ ] W65C02S専用命令群 (BBR, BBS, RMB, SMB)

---

## 重要な実装ポイント

### 1. W65C02S固有機能の実装

#### 新命令の実装
- **BBR/BBS**: ビット分岐命令 (8命令 × 2 = 16命令)
- **RMB/SMB**: ビット操作命令 (8命令 × 2 = 16命令)
- **TRB/TSB**: テスト・リセット/セット・ビット命令
- **STZ**: ゼロストア命令
- **BRA**: 無条件分岐命令

#### 拡張アドレッシングモード
- **(zp)**: ゼロページ間接
- **(abs,x)**: 絶対間接インデックス

#### 改善された動作
- **JMP ($xxFF)バグ修正**: ページ境界での正しい間接ジャンプ
- **デシマルモード改善**: ADC/SBC でのN,V,Zフラグ正常動作
- **割り込み時Dフラグクリア**: 全割り込みでDフラグを自動クリア

### 2. サイクル精度の実現

#### 基本サイクル数
```python
# 例: LDA命令のサイクル数
INSTRUCTION_CYCLES = {
    0xA9: 2,  # LDA #imm
    0xA5: 3,  # LDA zp
    0xB5: 4,  # LDA zp,x
    0xAD: 4,  # LDA abs
    0xBD: 4,  # LDA abs,x (+1 if page crossed)
    0xB9: 4,  # LDA abs,y (+1 if page crossed)
    0xA1: 6,  # LDA (zp,x)
    0xB1: 5,  # LDA (zp),y (+1 if page crossed)
    0xB2: 5,  # LDA (zp)
}
```

#### ページクロスペナルティ
```python
def check_page_cross(base_addr: int, offset: int) -> bool:
    """ページクロスチェック"""
    return (base_addr & 0xFF00) != ((base_addr + offset) & 0xFF00)
```

#### デシマルモード追加サイクル
```python
def decimal_mode_penalty(is_decimal: bool) -> int:
    """デシマルモード時の追加サイクル"""
    return 1 if is_decimal else 0
```

### 3. NMOS 6502からの差異

#### 未定義オペコードの処理
```python
# NMOS 6502の不正オペコードは全てNOPとして処理
INVALID_OPCODES = {
    0x02, 0x12, 0x22, 0x32, 0x42, 0x52, 0x62, 0x72,
    0x92, 0xB2, 0xD2, 0xF2, 0x1A, 0x3A, 0x5A, 0x7A,
    # ... 他の無効オペコード
}
```

#### RMW命令の正しい動作
```python
def rmw_instruction(self, address: int, operation):
    """Read-Modify-Write命令の正しい実装"""
    # W65C02S: Read, Read, Write (NMOS: Read, Write, Write)
    value = self.bus.read(address)  # 1st read
    value = self.bus.read(address)  # 2nd read (dummy)
    result = operation(value)
    self.bus.write(address, result)  # write
```

### 4. テスト戦略

#### 単体テスト
- 各PUの全パブリックメソッド
- 境界値・異常値テスト
- エラーハンドリング検証

#### 統合テスト
- PU間インタフェース検証
- 命令実行フロー確認
- サイクル精度検証

#### 命令レベルテスト
```python
# 命令テストの例
def test_lda_immediate():
    cpu = W65C02S()
    cpu.memory[0x8000] = 0xA9  # LDA #$42
    cpu.memory[0x8001] = 0x42
    cpu.pc = 0x8000
    
    cycles = cpu.step()
    
    assert cpu.a == 0x42
    assert cpu.pc == 0x8002
    assert cycles == 2
    assert cpu.flags.zero == False
    assert cpu.flags.negative == False
```

---

## Phase2完了時の成果物

### 1. 完全なCPUコア実装
- ✅ 5つのプログラムユニット (PU001-PU005)
- ✅ W65C02S仕様完全準拠
- ✅ サイクル精度実装

### 2. 212命令セット完全実装
- ✅ 全有効オペコード実装
- ✅ W65C02S固有命令実装
- ✅ NMOS 6502差異点対応

### 3. 包括的なテストスイート
- ✅ 単体テスト (90%+カバレッジ)
- ✅ 統合テスト (95%+成功率)
- ✅ 命令レベルテスト (100%通過)

### 4. API文書
- ✅ 全パブリック関数のdocstring
- ✅ 使用例とサンプルコード
- ✅ 実装ノート

### 5. 使用例とデモ
- ✅ 基本的なCPU使用例
- ✅ 命令実行デモ
- ✅ レジスタ操作例

---

## 次フェーズへの準備

Phase2完了により、以下が実現される：

1. **完全なCPUコア**: Phase3のメモリ・I/O実装で使用可能
2. **統一インタフェース**: Device プロトコル準拠
3. **テスト基盤**: Phase3以降のテスト拡張基盤
4. **性能基準**: 実機の10%以上の実行速度達成

Phase3では、このCPUコアを基盤として、メモリ管理システムと割り込みコントローラの実装に進む。

---

## 付録

### A. 参考資料
- W65C02Sソフトウェア詳細設計書
- W65C02S Data Sheet (Western Design Center)
- 6502 Instruction Set Reference

### B. 開発ツール
- Python 3.8+
- pytest (テストフレームワーク)
- mypy (型チェック)
- pylint (コード品質)
- black (コードフォーマット)

### C. 品質管理
- コードレビュー (2名以上承認)
- 継続的インテグレーション
- 自動テスト実行
- 性能監視

---

*本文書は、W65C02S Pythonエミュレータ Phase2実装の完全なガイドラインを提供し、高品質なCPUコア実装の実現を目指します。*
