# Phase5: Debug & Tools (デバッグ・ツール) 実装計画

## Phase5 概要

**期間**: 2週間  
**目標**: デバッグ機能と解析ツールの実装  
**主要成果物**: 完全なデバッグ機能、状態保存・復元機能、解析ツール

## Phase5 実装対象コンポーネント

### 主要プログラムユニット (PU)
- **PU013**: BreakpointManager (ブレークポイント管理)
- **PU014**: StepController (ステップ制御)
- **PU015**: StateInspector (状態検査)
- **PU016**: Disassembler (逆アセンブラ)
- **PU017**: StateSerializer (状態シリアライザ)
- **PU018**: StateValidator (状態検証)

## ファイル構造と実装内容

### 1. ブレークポイント管理 (`py6502emu/debug/breakpoint.py`)

```python
# PU013: BreakpointManager の実装
class BreakpointManager:
    """ブレークポイント管理システム"""
    
class Breakpoint:
    """個別ブレークポイント"""
    
class ConditionalBreakpoint:
    """条件付きブレークポイント"""
    
class BreakpointHitInfo:
    """ブレークポイントヒット情報"""
```

**実装内容**:
- アドレス指定ブレークポイント設定・解除
- 条件付きブレークポイント (Python式評価)
- ブレークポイントヒット検出
- ブレークポイント状態管理
- 一時的ブレークポイント機能

### 2. ステップ実行制御 (`py6502emu/debug/step_controller.py`)

```python
# PU014: StepController の実装
class StepController:
    """ステップ実行制御"""
    
class StepMode:
    """ステップモード定義"""
    
class CallStack:
    """コールスタック管理"""
    
class StepContext:
    """ステップ実行コンテキスト"""
```

**実装内容**:
- ステップイン (s): 次の単一命令実行
- ステップオーバー (n): サブルーチンをスキップ
- ステップアウト (o): 現在のサブルーチンから抜ける
- コールスタック追跡
- 実行制御状態管理

### 3. 状態検査機能 (`py6502emu/debug/inspector.py`)

```python
# PU015: StateInspector の実装
class StateInspector:
    """システム状態検査"""
    
class RegisterInspector:
    """レジスタ検査"""
    
class MemoryInspector:
    """メモリ検査"""
    
class FlagInspector:
    """フラグ状態検査"""
```

**実装内容**:
- CPUレジスタ状態表示 (A, X, Y, PC, S, P)
- プロセッサフラグのニーモニック表現
- メモリ範囲の16進ダンプ表示
- ASCII表現付きメモリダンプ
- デバイス状態検査機能

### 4. 逆アセンブラ (`py6502emu/debug/disassembler.py`)

```python
# PU016: Disassembler の実装
class Disassembler:
    """W65C02S逆アセンブラ"""
    
class InstructionFormatter:
    """命令フォーマッタ"""
    
class SymbolResolver:
    """シンボル解決"""
    
class SourceMapper:
    """ソースマッピング"""
```

**実装内容**:
- メモリ範囲の逆アセンブル
- W65C02Sニーモニック変換
- オペランドフォーマット
- シンボリックラベル表示
- アドレスとソースコードの対応

### 5. 状態シリアライザ (`py6502emu/debug/serializer.py`)

```python
# PU017: StateSerializer の実装
class StateSerializer:
    """システム状態シリアライズ"""
    
class StateFormat:
    """状態フォーマット定義"""
    
class CompressionHandler:
    """圧縮処理"""
    
class StateMetadata:
    """状態メタデータ"""
```

**実装内容**:
- 全システム状態のdict形式保存
- CPU・メモリ・デバイス状態の統合
- 状態データ圧縮機能
- バージョン管理対応
- メタデータ付与機能

### 6. 状態検証 (`py6502emu/debug/validator.py`)

```python
# PU018: StateValidator の実装
class StateValidator:
    """状態データ検証"""
    
class ValidationRule:
    """検証ルール"""
    
class IntegrityChecker:
    """整合性チェッカー"""
    
class ValidationReport:
    """検証レポート"""
```

**実装内容**:
- 状態データ整合性チェック
- レジスタ値範囲検証
- メモリアクセス妥当性確認
- デバイス状態検証
- 検証エラーレポート生成

### 7. デバッガコアインターフェース (`py6502emu/debug/debugger.py`)

```python
# デバッガ統合インターフェース
class Debugger:
    """統合デバッガインターフェース"""
    
class DebugSession:
    """デバッグセッション管理"""
    
class CommandInterface:
    """コマンドラインインターフェース"""
    
class DebugContext:
    """デバッグコンテキスト"""
```

**実装内容**:
- 統合デバッガインターフェース
- pdb風コマンドラインUI
- デバッグセッション管理
- コマンド履歴機能
- ヘルプシステム

### 8. ソースレベルデバッグ (`py6502emu/debug/source_debug.py`)

```python
# ソースレベルデバッグ機能
class SourceDebugger:
    """ソースレベルデバッグ"""
    
class ReportParser:
    """.rptファイル解析"""
    
class MapParser:
    """.lmapファイル解析"""
    
class SymbolManager:
    """シンボル管理"""
```

**実装内容**:
- .rptアセンブラレポート解析
- .lmapリンカマップ解析
- アドレス→ソース行マッピング
- シンボル名解決
- ソースコード表示機能

## テストファイル構造

### 単体テスト (`tests/debug/`)

```
tests/debug/
├── test_breakpoint.py          # ブレークポイント管理テスト
├── test_step_controller.py     # ステップ実行テスト
├── test_inspector.py           # 状態検査テスト
├── test_disassembler.py        # 逆アセンブラテスト
├── test_serializer.py          # 状態シリアライザテスト
├── test_validator.py           # 状態検証テスト
├── test_debugger.py            # デバッガ統合テスト
└── test_source_debug.py        # ソースデバッグテスト
```

### 統合テスト (`tests/integration/debug/`)

```
tests/integration/debug/
├── test_debug_session.py       # デバッグセッション統合テスト
├── test_step_execution.py      # ステップ実行統合テスト
├── test_state_management.py    # 状態管理統合テスト
└── test_source_mapping.py      # ソースマッピング統合テスト
```

## 実装スケジュール

### Week 1: コアデバッグ機能

| 日 | 作業内容 | 担当PU | 成果物 | 時間 |
|:---|:---------|:-------|:-------|:-----|
| **Day 1-2** | ブレークポイント管理 | PU013 | BreakpointManager | 16h |
| **Day 3-4** | ステップ実行制御 | PU014 | StepController | 16h |
| **Day 5** | 状態検査機能 | PU015 | StateInspector | 8h |

### Week 2: 解析ツール・統合

| 日 | 作業内容 | 担当PU | 成果物 | 時間 |
|:---|:---------|:-------|:-------|:-----|
| **Day 6-7** | 逆アセンブラ | PU016 | Disassembler | 16h |
| **Day 8** | 状態シリアライザ | PU017 | StateSerializer | 8h |
| **Day 9** | 状態検証 | PU018 | StateValidator | 8h |
| **Day 10** | 統合・最終テスト | 全PU | 統合デバッガ | 8h |

## 成功基準

### 機能要件
- [ ] ブレークポイント設定・解除機能
- [ ] 条件付きブレークポイント機能
- [ ] ステップイン・オーバー・アウト機能
- [ ] レジスタ・メモリ状態表示
- [ ] 逆アセンブル機能
- [ ] 状態保存・復元機能
- [ ] 状態整合性検証機能

### 品質要件
- [ ] 単体テストカバレッジ 90%以上
- [ ] 統合テスト 100%通過
- [ ] エンドツーエンドテスト 100%通過
- [ ] 性能要件達成 (デバッグ機能使用時)
- [ ] メモリ使用量制限内

### ユーザビリティ要件
- [ ] pdb風コマンドインターフェース
- [ ] 直感的なコマンド体系
- [ ] 適切なエラーメッセージ
- [ ] ヘルプシステム完備
- [ ] コマンド履歴機能

## 依存関係

### Phase4からの依存
- SystemOrchestrator (システム制御)
- SystemBus (バス監視)
- CPUコア (状態アクセス)
- MemoryController (メモリアクセス)

### 外部ライブラリ依存
- `typing`: 型ヒント
- `dataclasses`: データクラス
- `enum`: 列挙型
- `abc`: 抽象基底クラス
- `pickle`: 状態シリアライズ
- `zlib`: データ圧縮
- `re`: 正規表現 (ファイル解析用)

## リスク要因と対策

### 主要リスク
1. **デバッグ機能の複雑化**: 段階的実装で対応
2. **性能への影響**: プロファイリングで最適化
3. **ソースデバッグの実装困難**: 簡易版から開始
4. **状態管理の複雑性**: 明確なインターフェース設計

### 軽減策
- 基本機能から段階的実装
- 継続的な性能測定
- 豊富な単体テスト
- 明確な責任分離

この実装計画により、Phase5では完全なデバッグ・解析ツール群を構築し、W65C02Sエミュレータの開発・利用を強力に支援する環境を提供します。