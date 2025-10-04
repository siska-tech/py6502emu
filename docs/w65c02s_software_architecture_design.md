# W65C02S Pythonエミュレータ ソフトウェア・アーキテクチャ設計書

## 文書管理

| 項目 | 内容 |
| :--- | :--- |
| **バージョン** | 1.0 |
| **関連文書** | W65C02S要件定義書、デバイスIF API要件定義書、ソフトウェア要求仕様書 |

## 目次

1. [設計条件確認メモ](#設計条件確認メモ)
2. [ソフトウェア構成設計書 (SW201)](#sw201-ソフトウェア構成設計書)
3. [機能ユニット設計書 (SW202)](#sw202-機能ユニット設計書)
4. [ソフトウェア動作設計書 (SW203)](#sw203-ソフトウェア動作設計書)
5. [ソフトウェア・インタフェース設計書 (SW204)](#sw204-ソフトウェアインタフェース設計書)
6. [性能試算資料](#性能試算資料)
7. [メモリ使用試算資料](#メモリ使用試算資料)

---

## 設計条件確認メモ

### 機能要求からの設計条件

| 要求ID | 機能要求 | 設計への影響 |
| :--- | :--- | :--- |
| F001-F005 | CPUコアエミュレーション | W65C02Sクラスの詳細設計が必要 |
| F006-F009 | メモリ管理機能 | MMUクラスとアドレス空間管理の設計が必要 |
| F010-F013 | システム制御機能 | Tick駆動アーキテクチャとデバイス管理の設計が必要 |
| F014-F018 | デバッグ機能 | デバッガコンポーネントの設計が必要 |
| F019-F021 | 状態管理機能 | シリアライゼーション機能の設計が必要 |

### 非機能要求からの設計条件

| 要求ID | 非機能要求 | 設計への影響 |
| :--- | :--- | :--- |
| NF001 | 決定論的実行 | 状態管理とイベント処理の厳密な設計が必要 |
| NF005 | 実行速度（実機の10%以上） | 効率的なアルゴリズムとデータ構造の選択が必要 |
| NF009-NF010 | モジュール性・拡張性 | プロトコルベースの疎結合設計が必要 |
| NF013 | クロスプラットフォーム対応 | Python標準ライブラリ中心の実装が必要 |

### 制約条件からの設計条件

| 制約ID | 制約条件 | 設計への影響 |
| :--- | :--- | :--- |
| C001-C002 | 物理ハードウェアとの完全互換性 | サイクル精度の実装が必要 |
| C005-C008 | W65C02S仕様準拠 | 212命令セットとNMOS 6502差異の正確な実装が必要 |
| C020-C021 | Python標準ライブラリ活用 | 外部依存最小化の設計が必要 |
| C023-C025 | 開発・導入環境 | Python 3.8+対応とクロスプラットフォーム設計が必要 |

---

## SW201 ソフトウェア構成設計書

### 1.1 システム全体アーキテクチャ

```mermaid
graph TB
    subgraph "Application Layer (アプリケーション層)"
        APP[Application<br/>アプリケーション]
        DBG[Debugger<br/>デバッガ]
        UI[User Interface<br/>ユーザーインターフェース]
    end
    
    subgraph "Orchestration Layer (オーケストレーション層)"
        ORCH[Orchestrator<br/>オーケストレータ]
        SCHED[Scheduler<br/>スケジューラ]
        SYNC[Synchronizer<br/>同期制御]
    end
    
    subgraph "Device Layer (デバイス層)"
        CPU[W65C02S CPU<br/>CPUデバイス]
        MEM[Memory<br/>メモリデバイス]
        IO[I/O Devices<br/>I/Oデバイス]
    end
    
    subgraph "System Services Layer (システムサービス層)"
        SB[System Bus<br/>システムバス]
        IC[Interrupt Controller<br/>割り込みコントローラ]
        MMU[Memory Management Unit<br/>メモリ管理ユニット]
    end
    
    subgraph "Core Infrastructure Layer (コアインフラ層)"
        PROTO[Device Protocol<br/>デバイスプロトコル]
        STATE[State Manager<br/>状態管理]
        CONFIG[Configuration<br/>設定管理]
    end
    
    %% Layer connections
    APP --> ORCH
    DBG --> ORCH
    UI --> ORCH
    
    ORCH --> SCHED
    ORCH --> SYNC
    SCHED --> CPU
    SCHED --> MEM
    SCHED --> IO
    
    CPU <--> SB
    MEM <--> SB
    IO <--> SB
    
    CPU <--> IC
    IO --> IC
    
    SB <--> MMU
    
    CPU -.-> PROTO
    MEM -.-> PROTO
    IO -.-> PROTO
    
    ORCH --> STATE
    ORCH --> CONFIG
    
    %% Styling
    classDef application fill:#e3f2fd
    classDef orchestration fill:#e8f5e8
    classDef device fill:#fff3e0
    classDef service fill:#f3e5f5
    classDef infrastructure fill:#fce4ec
    
    class APP,DBG,UI application
    class ORCH,SCHED,SYNC orchestration
    class CPU,MEM,IO device
    class SB,IC,MMU service
    class PROTO,STATE,CONFIG infrastructure
```

### 1.2 レイヤー構成と責務

| レイヤー | 構成要素 | 主要責務 |
| :--- | :--- | :--- |
| **Application Layer** | Application, Debugger, UI | ユーザーインターフェース、デバッグ機能の提供 |
| **Orchestration Layer** | Orchestrator, Scheduler, Synchronizer | システム全体の制御、タイムスライス管理、同期制御 |
| **Device Layer** | CPU, Memory, I/O Devices | ハードウェアコンポーネントのエミュレーション |
| **System Services Layer** | System Bus, Interrupt Controller, MMU | デバイス間通信、割り込み管理、メモリ管理 |
| **Core Infrastructure Layer** | Device Protocol, State Manager, Configuration | 基盤プロトコル、状態管理、設定管理 |

### 1.3 主要コンポーネント構成

#### 1.3.1 CPUサブシステム

```mermaid
classDiagram
    class W65C02S {
        +registers: CPURegisters
        +flags: ProcessorFlags
        +instruction_set: InstructionSet
        +addressing_modes: AddressingModes
        +tick(cycles: int) int
        +step() int
        +reset() None
        +get_state() dict
        +set_state(state: dict) None
    }
    
    class CPURegisters {
        +a: int
        +x: int
        +y: int
        +pc: int
        +s: int
        +p: int
    }
    
    class ProcessorFlags {
        +n: bool
        +v: bool
        +b: bool
        +d: bool
        +i: bool
        +z: bool
        +c: bool
        +get_byte() int
        +set_byte(value: int) None
    }
    
    class InstructionSet {
        +opcodes: Dict[int, Instruction]
        +execute(opcode: int) int
        +decode(opcode: int) Instruction
    }
    
    class AddressingModes {
        +immediate(operand: int) int
        +absolute(operand: int) int
        +zero_page(operand: int) int
        +indexed_x(base: int) int
        +indexed_y(base: int) int
        +indirect(pointer: int) int
    }
    
    W65C02S *-- CPURegisters
    W65C02S *-- ProcessorFlags
    W65C02S *-- InstructionSet
    W65C02S *-- AddressingModes
```

#### 1.3.2 メモリサブシステム

```mermaid
classDiagram
    class MemoryManagementUnit {
        +address_space: AddressSpace
        +device_map: DeviceMap
        +read(address: int) int
        +write(address: int, value: int) None
        +map_device(device: Device, start: int, end: int) None
        +unmap_device(start: int, end: int) None
    }
    
    class AddressSpace {
        +size: int = 65536
        +memory: bytearray
        +read_byte(address: int) int
        +write_byte(address: int, value: int) None
        +read_word(address: int) int
        +write_word(address: int, value: int) None
    }
    
    class DeviceMap {
        +mappings: List[DeviceMapping]
        +find_device(address: int) Optional[Device]
        +add_mapping(mapping: DeviceMapping) None
        +remove_mapping(start: int, end: int) None
    }
    
    class DeviceMapping {
        +device: Device
        +start_address: int
        +end_address: int
        +contains(address: int) bool
        +translate_address(address: int) int
    }
    
    MemoryManagementUnit *-- AddressSpace
    MemoryManagementUnit *-- DeviceMap
    DeviceMap *-- DeviceMapping
```

#### 1.3.3 システムサービス

```mermaid
classDiagram
    class SystemBus {
        +mmu: MemoryManagementUnit
        +bus_masters: List[Device]
        +current_master: Optional[Device]
        +read(address: int) int
        +write(address: int, value: int) None
        +request_mastership(device: Device) bool
        +release_mastership(device: Device) None
    }
    
    class InterruptController {
        +interrupt_lines: Dict[InterruptLine, bool]
        +interrupt_enable: Dict[InterruptLine, bool]
        +priority_resolver: PriorityResolver
        +request(line: InterruptLine) None
        +clear(line: InterruptLine) None
        +is_pending() bool
        +acknowledge() Optional[InterruptVector]
    }
    
    class PriorityResolver {
        +scheme: PriorityScheme
        +resolve(pending: List[InterruptLine]) Optional[InterruptLine]
    }
    
    SystemBus *-- MemoryManagementUnit
    InterruptController *-- PriorityResolver
```

---

## SW202 機能ユニット設計書

### 2.1 機能ユニット抽出

#### 2.1.1 主要機能ユニット一覧

| ユニットID | ユニット名 | 機能概要 | 対応要求 |
| :--- | :--- | :--- | :--- |
| FU001 | CPUCore | W65C02S CPU コアの実装 | F001-F005 |
| FU002 | MemoryManager | メモリ管理とアドレス空間制御 | F006-F009 |
| FU003 | SystemOrchestrator | システム全体の制御とスケジューリング | F010-F013 |
| FU004 | DebugEngine | デバッグ機能の実装 | F014-F018 |
| FU005 | StateManager | 状態保存・復元機能 | F019-F021 |
| FU006 | DeviceFramework | 統一デバイスAPIの実装 | C016 |
| FU007 | InterruptSystem | 割り込み管理システム | F004, F012 |
| FU008 | ConfigurationManager | 設定管理システム | C020-C022 |

### 2.2 機能ユニット詳細化

#### 2.2.1 FU001: CPUCore

```mermaid
graph TB
    subgraph "CPUCore (FU001)"
        subgraph "Register Management"
            REG[Register File<br/>レジスタファイル]
            FLAGS[Processor Flags<br/>プロセッサフラグ]
        end
        
        subgraph "Instruction Processing"
            FETCH[Instruction Fetch<br/>命令フェッチ]
            DECODE[Instruction Decode<br/>命令デコード]
            EXECUTE[Instruction Execute<br/>命令実行]
        end
        
        subgraph "Addressing"
            ADDR[Address Calculation<br/>アドレス計算]
            MODES[Addressing Modes<br/>アドレッシングモード]
        end
        
        subgraph "Interrupt Handling"
            INT_CHECK[Interrupt Check<br/>割り込みチェック]
            INT_PROC[Interrupt Processing<br/>割り込み処理]
        end
        
        FETCH --> DECODE
        DECODE --> EXECUTE
        EXECUTE --> ADDR
        ADDR --> MODES
        EXECUTE --> FLAGS
        EXECUTE --> REG
        EXECUTE --> INT_CHECK
        INT_CHECK --> INT_PROC
    end
```

**詳細仕様:**
- **レジスタ管理**: A, X, Y, PC, S, P レジスタの完全実装
- **命令セット**: 212個の有効オペコードの実装
- **アドレッシングモード**: 16種類のモードの実装
- **割り込み処理**: RES/NMI/IRQ/BRK の7サイクルシーケンス
- **サイクル精度**: 各命令の正確なサイクル数の実装

#### 2.2.2 FU002: MemoryManager

```mermaid
graph TB
    subgraph "MemoryManager (FU002)"
        subgraph "Address Space"
            AS[Address Space<br/>64KB アドレス空間]
            ZP[Zero Page<br/>ゼロページ管理]
            STACK[Stack Page<br/>スタックページ管理]
        end
        
        subgraph "Device Mapping"
            MAP[Device Mapping<br/>デバイスマッピング]
            ROUTE[Address Routing<br/>アドレスルーティング]
        end
        
        subgraph "Memory Operations"
            READ[Memory Read<br/>メモリ読み取り]
            WRITE[Memory Write<br/>メモリ書き込み]
            ENDIAN[Endian Handling<br/>エンディアン処理]
        end
        
        AS --> ZP
        AS --> STACK
        MAP --> ROUTE
        ROUTE --> READ
        ROUTE --> WRITE
        READ --> ENDIAN
        WRITE --> ENDIAN
    end
```

**詳細仕様:**
- **アドレス空間**: 64KB フラットアドレス空間
- **特殊領域**: ゼロページ($0000-$00FF)、スタック($0100-$01FF)
- **エンディアン**: リトルエンディアン形式での16ビット値処理
- **デバイスマッピング**: 動的なデバイス登録・解除機能

#### 2.2.3 FU003: SystemOrchestrator

```mermaid
graph TB
    subgraph "SystemOrchestrator (FU003)"
        subgraph "Time Management"
            CLOCK[Master Clock<br/>マスタークロック]
            SLICE[Time Slice<br/>タイムスライス管理]
        end
        
        subgraph "Device Scheduling"
            SCHED[Device Scheduler<br/>デバイススケジューラ]
            SYNC[Synchronization<br/>同期制御]
        end
        
        subgraph "System Control"
            INIT[System Initialize<br/>システム初期化]
            RESET[System Reset<br/>システムリセット]
            SHUTDOWN[System Shutdown<br/>システム終了]
        end
        
        CLOCK --> SLICE
        SLICE --> SCHED
        SCHED --> SYNC
        INIT --> CLOCK
        RESET --> INIT
        SHUTDOWN --> RESET
    end
```

**詳細仕様:**
- **Tick駆動**: 離散時間シミュレーションモデル
- **スケジューリング**: CPU → ペリフェラル → 割り込み処理の順序
- **同期制御**: デバイス間の時間的整合性保証
- **ライフサイクル**: 初期化・実行・リセット・終了の管理

#### 2.2.4 FU004: DebugEngine

```mermaid
graph TB
    subgraph "DebugEngine (FU004)"
        subgraph "Execution Control"
            BP[Breakpoint Manager<br/>ブレークポイント管理]
            STEP[Step Controller<br/>ステップ制御]
        end
        
        subgraph "State Inspection"
            REG_VIEW[Register Viewer<br/>レジスタビューア]
            MEM_VIEW[Memory Viewer<br/>メモリビューア]
            FLAG_VIEW[Flag Viewer<br/>フラグビューア]
        end
        
        subgraph "Code Analysis"
            DISASM[Disassembler<br/>逆アセンブラ]
            SYM_MGR[Symbol Manager<br/>シンボル管理]
            SRC_MAP[Source Mapping<br/>ソースマッピング]
        end
        
        BP --> STEP
        STEP --> REG_VIEW
        REG_VIEW --> MEM_VIEW
        MEM_VIEW --> FLAG_VIEW
        DISASM --> SYM_MGR
        SYM_MGR --> SRC_MAP
    end
```

**詳細仕様:**
- **ブレークポイント**: アドレス指定・条件付きブレーク
- **ステップ実行**: ステップイン・オーバー・アウト
- **状態表示**: レジスタ・メモリ・フラグの表示
- **ソースデバッグ**: .rpt/.lmapファイル解析

#### 2.2.5 FU005: StateManager

```mermaid
graph TB
    subgraph "StateManager (FU005)"
        subgraph "Serialization"
            SAVE[State Save<br/>状態保存]
            LOAD[State Load<br/>状態読み込み]
            VALIDATE[State Validation<br/>状態検証]
        end
        
        subgraph "State Operations"
            SNAPSHOT[Snapshot<br/>スナップショット]
            RESTORE[Restore<br/>復元]
            COMPARE[State Compare<br/>状態比較]
        end
        
        subgraph "Format Support"
            DICT[Dict Format<br/>辞書形式]
            JSON[JSON Format<br/>JSON形式]
            PICKLE[Pickle Format<br/>Pickle形式]
        end
        
        SAVE --> SNAPSHOT
        LOAD --> RESTORE
        VALIDATE --> COMPARE
        SNAPSHOT --> DICT
        RESTORE --> JSON
        COMPARE --> PICKLE
    end
```

**詳細仕様:**
- **シリアライゼーション**: dict形式での状態保存
- **完全復元**: 全デバイス状態の完全復元
- **形式サポート**: JSON, Pickle等の複数形式対応
- **整合性検証**: 状態の整合性チェック機能

---

## SW203 ソフトウェア動作設計書

### 3.1 システム動作フロー

#### 3.1.1 メインエミュレーションループ

```mermaid
sequenceDiagram
    participant APP as Application
    participant ORCH as Orchestrator
    participant CPU as CPU Device
    participant MEM as Memory
    participant IC as Interrupt Controller
    participant IO as I/O Device
    
    APP->>ORCH: start_emulation()
    ORCH->>ORCH: initialize_system()
    
    loop Emulation Loop
        ORCH->>ORCH: calculate_time_slice()
        
        loop Time Slice
            ORCH->>CPU: tick(remaining_cycles)
            CPU-->>ORCH: consumed_cycles
            ORCH->>ORCH: update_system_time(consumed_cycles)
            
            par Peripheral Processing
                ORCH->>MEM: tick(consumed_cycles)
                ORCH->>IO: tick(consumed_cycles)
            end
            
            alt Interrupt Pending
                CPU->>IC: is_pending()
                IC-->>CPU: true
                CPU->>IC: acknowledge()
                IC-->>CPU: interrupt_vector
                CPU->>CPU: setup_interrupt_service()
            end
        end
        
        ORCH->>ORCH: host_synchronization()
        
        alt Stop Condition
            ORCH->>ORCH: shutdown_system()
        end
    end
```

#### 3.1.2 命令実行サイクル

```mermaid
stateDiagram-v2
    [*] --> Fetch
    Fetch --> Decode: オペコード取得
    Decode --> AddressCalc: 命令解析完了
    AddressCalc --> Execute: アドレス計算完了
    Execute --> FlagUpdate: 実行完了
    FlagUpdate --> InterruptCheck: フラグ更新完了
    InterruptCheck --> Fetch: 割り込みなし
    InterruptCheck --> InterruptService: 割り込みあり
    InterruptService --> Fetch: ISR準備完了
    
    state Fetch {
        [*] --> ReadOpcode
        ReadOpcode --> IncrementPC
        IncrementPC --> [*]
    }
    
    state Execute {
        [*] --> ReadOperands
        ReadOperands --> PerformOperation
        PerformOperation --> WriteResult
        WriteResult --> [*]
    }
```

#### 3.1.3 割り込み処理フロー

```mermaid
flowchart TD
    A[割り込み要求発生] --> B{割り込み許可?}
    B -->|No| C[割り込み無視]
    B -->|Yes| D[現在命令完了待ち]
    D --> E[PCをスタックにプッシュ]
    E --> F[Pレジスタをスタックにプッシュ]
    F --> G[Iフラグセット]
    G --> H[Dフラグクリア]
    H --> I[割り込みベクタ読み取り]
    I --> J[PCに割り込みベクタ設定]
    J --> K[ISR実行開始]
    K --> L[ISR処理実行]
    L --> M[RTI命令実行]
    M --> N[Pレジスタをスタックから復帰]
    N --> O[PCをスタックから復帰]
    O --> P[通常実行再開]
    C --> Q[次の命令実行]
    P --> Q
```

### 3.2 デバイス間通信パターン

#### 3.2.1 CPU-メモリ間通信

```mermaid
sequenceDiagram
    participant CPU as W65C02S CPU
    participant SB as System Bus
    participant MMU as Memory Manager
    participant DEV as Device
    participant MEM as Memory
    
    Note over CPU,MEM: メモリ読み取りシーケンス
    CPU->>SB: read(address)
    SB->>MMU: read(address)
    
    alt Device Mapped Address
        MMU->>DEV: read(relative_address)
        DEV-->>MMU: data
        MMU-->>SB: data
    else Memory Address
        MMU->>MEM: read(address)
        MEM-->>MMU: data
        MMU-->>SB: data
    end
    
    SB-->>CPU: data
    
    Note over CPU,MEM: メモリ書き込みシーケンス
    CPU->>SB: write(address, data)
    SB->>MMU: write(address, data)
    
    alt Device Mapped Address
        MMU->>DEV: write(relative_address, data)
    else Memory Address
        MMU->>MEM: write(address, data)
    end
```

#### 3.2.2 DMA転送パターン

```mermaid
sequenceDiagram
    participant CPU as CPU
    participant DMA as DMA Controller
    participant SB as System Bus
    participant SRC as Source Device
    participant DST as Destination Device
    
    CPU->>DMA: configure_transfer(src, dst, length)
    CPU->>DMA: start_transfer()
    
    DMA->>SB: request_mastership()
    SB-->>DMA: mastership_granted
    
    loop Transfer Loop
        DMA->>SB: read(src_address)
        SB->>SRC: read(relative_address)
        SRC-->>SB: data
        SB-->>DMA: data
        
        DMA->>SB: write(dst_address, data)
        SB->>DST: write(relative_address, data)
        
        DMA->>DMA: increment_addresses()
    end
    
    DMA->>SB: release_mastership()
    DMA->>CPU: transfer_complete_interrupt()
```

### 3.3 状態遷移設計

#### 3.3.1 システム状態遷移

```mermaid
stateDiagram-v2
    [*] --> Uninitialized
    Uninitialized --> Initializing: initialize()
    Initializing --> Ready: initialization_complete
    Ready --> Running: start()
    Running --> Paused: pause()
    Paused --> Running: resume()
    Running --> Debugging: breakpoint_hit
    Debugging --> Running: continue()
    Debugging --> Stepping: step()
    Stepping --> Debugging: step_complete
    Running --> Stopped: stop()
    Paused --> Stopped: stop()
    Debugging --> Stopped: stop()
    Stopped --> Ready: reset()
    Ready --> [*]: shutdown()
    
    state Running {
        [*] --> Executing
        Executing --> WaitingForInterrupt: WAI_instruction
        WaitingForInterrupt --> Executing: interrupt_received
        Executing --> Stopped: STP_instruction
    }
```

---

## SW204 ソフトウェア・インタフェース設計書

### 4.1 メモリレイアウト設計

#### 4.1.1 W65C02S アドレス空間レイアウト

```mermaid
graph TB
    subgraph "W65C02S 64KB Address Space"
        subgraph "High Memory ($8000-$FFFF)"
            VECTORS["$FFFA-$FFFF<br/>Interrupt Vectors<br/>6 bytes"]
            ROM["$8000-$FFF9<br/>ROM Area<br/>32KB - 6 bytes"]
        end
        
        subgraph "I/O Space ($2000-$7FFF)"
            IO_EXT["$4000-$7FFF<br/>Extended I/O<br/>16KB"]
            IO_STD["$2000-$3FFF<br/>Standard I/O<br/>8KB"]
        end
        
        subgraph "RAM Space ($0200-$1FFF)"
            RAM_HI["$0800-$1FFF<br/>General RAM<br/>6KB"]
            RAM_LO["$0200-$07FF<br/>General RAM<br/>1.5KB"]
        end
        
        subgraph "System Pages ($0000-$01FF)"
            STACK["$0100-$01FF<br/>Stack Page<br/>256 bytes"]
            ZEROPAGE["$0000-$00FF<br/>Zero Page<br/>256 bytes"]
        end
    end
    
    VECTORS --> ROM
    ROM --> IO_EXT
    IO_EXT --> IO_STD
    IO_STD --> RAM_HI
    RAM_HI --> RAM_LO
    RAM_LO --> STACK
    STACK --> ZEROPAGE
```

#### 4.1.2 メモリ領域詳細仕様

| アドレス範囲 | 領域名 | サイズ | 用途 | アクセス特性 |
| :--- | :--- | :--- | :--- | :--- |
| `$0000-$007F` | Zero Page Low | 128B | 間接ポインタ、高速変数 | 高速アクセス、ラップアラウンド |
| `$0080-$00FF` | Zero Page High | 128B | 高速変数、一時領域 | 高速アクセス、ラップアラウンド |
| `$0100-$01FF` | Stack Page | 256B | ハードウェアスタック | 下方向伸長、S レジスタ制御 |
| `$0200-$07FF` | General RAM Low | 1.5KB | 変数、配列、バッファ | 通常アクセス |
| `$0800-$1FFF` | General RAM High | 6KB | ユーザーデータ、バッファ | 通常アクセス |
| `$2000-$3FFF` | Standard I/O | 8KB | VDP、サウンド、コントローラ | デバイスマップ |
| `$4000-$7FFF` | Extended I/O | 16KB | 拡張デバイス | デバイスマップ |
| `$8000-$FFF9` | ROM Area | 32KB-6B | プログラムコード | 読み取り専用 |
| `$FFFA-$FFFB` | NMI Vector | 2B | NMI 割り込みベクタ | 読み取り専用 |
| `$FFFC-$FFFD` | RES Vector | 2B | リセットベクタ | 読み取り専用 |
| `$FFFE-$FFFF` | IRQ/BRK Vector | 2B | IRQ/BRK 割り込みベクタ | 読み取り専用 |

### 4.2 機能ユニット間インタフェース設計

#### 4.2.1 Device プロトコル仕様

```python
from typing import Protocol, Dict, Any, Optional
from abc import abstractmethod

class Device(Protocol):
    """統一デバイスプロトコル"""
    
    @property
    def name(self) -> str:
        """デバイス名"""
        ...
    
    @abstractmethod
    def reset(self) -> None:
        """デバイスリセット"""
        ...
    
    @abstractmethod
    def tick(self, master_cycles: int) -> int:
        """時間進行処理"""
        ...
    
    @abstractmethod
    def read(self, address: int) -> int:
        """メモリ読み取り"""
        ...
    
    @abstractmethod
    def write(self, address: int, value: int) -> None:
        """メモリ書き込み"""
        ...
    
    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """状態取得"""
        ...
    
    @abstractmethod
    def set_state(self, state: Dict[str, Any]) -> None:
        """状態設定"""
        ...
```

#### 4.2.2 システムバス インタフェース

```python
from typing import List, Optional

class SystemBus:
    """システムバス実装"""
    
    def __init__(self, mmu: MemoryManagementUnit):
        self.mmu = mmu
        self.bus_masters: List[Device] = []
        self.current_master: Optional[Device] = None
    
    def read(self, address: int) -> int:
        """バス読み取り"""
        if not self._validate_address(address):
            raise AddressError(f"Invalid address: ${address:04X}")
        return self.mmu.read(address)
    
    def write(self, address: int, value: int) -> None:
        """バス書き込み"""
        if not self._validate_address(address):
            raise AddressError(f"Invalid address: ${address:04X}")
        if not self._validate_value(value):
            raise ValueError(f"Invalid value: {value}")
        self.mmu.write(address, value)
    
    def request_mastership(self, device: Device) -> bool:
        """バスマスタ権要求"""
        if self.current_master is None:
            self.current_master = device
            return True
        return False
    
    def release_mastership(self, device: Device) -> None:
        """バスマスタ権解放"""
        if self.current_master == device:
            self.current_master = None
    
    def _validate_address(self, address: int) -> bool:
        """アドレス検証"""
        return 0 <= address <= 0xFFFF
    
    def _validate_value(self, value: int) -> bool:
        """値検証"""
        return 0 <= value <= 0xFF
```

#### 4.2.3 割り込みコントローラ インタフェース

```python
from enum import Enum, auto
from typing import Optional, Dict, List
from dataclasses import dataclass

class InterruptLine(Enum):
    """割り込み線定義"""
    IRQ_0 = auto()
    IRQ_1 = auto()
    IRQ_2 = auto()
    NMI = auto()

@dataclass
class InterruptVector:
    """割り込みベクタ情報"""
    vector_address: int
    line: InterruptLine
    priority: int

class InterruptController:
    """割り込みコントローラ実装"""
    
    def __init__(self):
        self.interrupt_lines: Dict[InterruptLine, bool] = {}
        self.interrupt_enable: Dict[InterruptLine, bool] = {}
        self.priority_map: Dict[InterruptLine, int] = {}
        self._initialize_interrupts()
    
    def request(self, line: InterruptLine) -> None:
        """割り込み要求"""
        self.interrupt_lines[line] = True
    
    def clear(self, line: InterruptLine) -> None:
        """割り込みクリア"""
        self.interrupt_lines[line] = False
    
    def is_pending(self) -> bool:
        """割り込み保留確認"""
        for line, requested in self.interrupt_lines.items():
            if requested and self.interrupt_enable.get(line, False):
                return True
        return False
    
    def acknowledge(self) -> Optional[InterruptVector]:
        """割り込み承認"""
        pending_lines = [
            line for line, requested in self.interrupt_lines.items()
            if requested and self.interrupt_enable.get(line, False)
        ]
        
        if not pending_lines:
            return None
        
        # 優先度順にソート
        pending_lines.sort(key=lambda x: self.priority_map.get(x, 0))
        highest_priority = pending_lines[0]
        
        # 割り込みベクタを返す
        vector_address = self._get_vector_address(highest_priority)
        return InterruptVector(
            vector_address=vector_address,
            line=highest_priority,
            priority=self.priority_map.get(highest_priority, 0)
        )
    
    def _initialize_interrupts(self) -> None:
        """割り込み初期化"""
        for line in InterruptLine:
            self.interrupt_lines[line] = False
            self.interrupt_enable[line] = True
            self.priority_map[line] = line.value
    
    def _get_vector_address(self, line: InterruptLine) -> int:
        """ベクタアドレス取得"""
        vector_map = {
            InterruptLine.NMI: 0xFFFA,
            InterruptLine.IRQ_0: 0xFFFE,
            InterruptLine.IRQ_1: 0xFFFE,
            InterruptLine.IRQ_2: 0xFFFE,
        }
        return vector_map.get(line, 0xFFFE)
```

### 4.3 共通情報の一元化

#### 4.3.1 設定管理システム

```python
from dataclasses import dataclass
from typing import Dict, Any, Optional
import json

@dataclass
class SystemConfig:
    """システム設定"""
    cpu_frequency: int = 1000000  # 1MHz
    memory_size: int = 65536      # 64KB
    debug_enabled: bool = False
    log_level: str = "INFO"

@dataclass
class DeviceConfig:
    """デバイス設定基底クラス"""
    device_id: str
    device_type: str
    enabled: bool = True
    
@dataclass
class CPUConfig(DeviceConfig):
    """CPU設定"""
    initial_pc: int = 0x8000
    initial_sp: int = 0xFD
    decimal_mode_enabled: bool = True

class ConfigurationManager:
    """設定管理システム"""
    
    def __init__(self):
        self.system_config = SystemConfig()
        self.device_configs: Dict[str, DeviceConfig] = {}
    
    def load_from_file(self, config_file: str) -> None:
        """設定ファイル読み込み"""
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # システム設定の読み込み
        if 'system' in config_data:
            self._load_system_config(config_data['system'])
        
        # デバイス設定の読み込み
        if 'devices' in config_data:
            self._load_device_configs(config_data['devices'])
    
    def save_to_file(self, config_file: str) -> None:
        """設定ファイル保存"""
        config_data = {
            'system': self._serialize_system_config(),
            'devices': self._serialize_device_configs()
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def get_device_config(self, device_id: str) -> Optional[DeviceConfig]:
        """デバイス設定取得"""
        return self.device_configs.get(device_id)
    
    def set_device_config(self, device_id: str, config: DeviceConfig) -> None:
        """デバイス設定設定"""
        self.device_configs[device_id] = config
    
    def _load_system_config(self, config_data: Dict[str, Any]) -> None:
        """システム設定読み込み"""
        for key, value in config_data.items():
            if hasattr(self.system_config, key):
                setattr(self.system_config, key, value)
    
    def _load_device_configs(self, config_data: Dict[str, Any]) -> None:
        """デバイス設定読み込み"""
        for device_id, device_data in config_data.items():
            device_type = device_data.get('device_type', 'generic')
            
            if device_type == 'cpu':
                config = CPUConfig(
                    device_id=device_id,
                    device_type=device_type,
                    **device_data
                )
            else:
                config = DeviceConfig(
                    device_id=device_id,
                    device_type=device_type,
                    **device_data
                )
            
            self.device_configs[device_id] = config
    
    def _serialize_system_config(self) -> Dict[str, Any]:
        """システム設定シリアライズ"""
        return {
            'cpu_frequency': self.system_config.cpu_frequency,
            'memory_size': self.system_config.memory_size,
            'debug_enabled': self.system_config.debug_enabled,
            'log_level': self.system_config.log_level
        }
    
    def _serialize_device_configs(self) -> Dict[str, Any]:
        """デバイス設定シリアライズ"""
        result = {}
        for device_id, config in self.device_configs.items():
            result[device_id] = {
                'device_type': config.device_type,
                'enabled': config.enabled
            }
            
            # CPU固有設定
            if isinstance(config, CPUConfig):
                result[device_id].update({
                    'initial_pc': config.initial_pc,
                    'initial_sp': config.initial_sp,
                    'decimal_mode_enabled': config.decimal_mode_enabled
                })
        
        return result
```

#### 4.3.2 論理値定義

```python
from enum import Enum, IntEnum

class ProcessorFlag(IntEnum):
    """プロセッサフラグ位置"""
    CARRY = 0
    ZERO = 1
    INTERRUPT_DISABLE = 2
    DECIMAL = 3
    BREAK = 4
    UNUSED = 5
    OVERFLOW = 6
    NEGATIVE = 7

class AddressingMode(Enum):
    """アドレッシングモード"""
    ACCUMULATOR = "acc"
    IMPLIED = "imp"
    IMMEDIATE = "imm"
    ABSOLUTE = "abs"
    ZERO_PAGE = "zp"
    RELATIVE = "rel"
    ABSOLUTE_X = "abs,x"
    ABSOLUTE_Y = "abs,y"
    ZERO_PAGE_X = "zp,x"
    ZERO_PAGE_Y = "zp,y"
    INDIRECT = "(abs)"
    INDIRECT_X = "(abs,x)"
    INDEXED_INDIRECT = "(zp,x)"
    INDIRECT_INDEXED = "(zp),y"
    ZERO_PAGE_INDIRECT = "(zp)"

class InstructionType(Enum):
    """命令タイプ"""
    LOAD_STORE = "load_store"
    ARITHMETIC = "arithmetic"
    LOGICAL = "logical"
    SHIFT_ROTATE = "shift_rotate"
    COMPARE = "compare"
    BRANCH = "branch"
    JUMP = "jump"
    SUBROUTINE = "subroutine"
    INTERRUPT = "interrupt"
    FLAG = "flag"
    TRANSFER = "transfer"
    STACK = "stack"
    INCREMENT = "increment"
    BIT_MANIPULATION = "bit_manipulation"
    SYSTEM = "system"

# システム定数
MEMORY_SIZE = 0x10000  # 64KB
ZERO_PAGE_START = 0x0000
ZERO_PAGE_END = 0x00FF
STACK_PAGE_START = 0x0100
STACK_PAGE_END = 0x01FF
VECTOR_NMI = 0xFFFA
VECTOR_RESET = 0xFFFC
VECTOR_IRQ_BRK = 0xFFFE

# タイミング定数
DEFAULT_CPU_FREQUENCY = 1000000  # 1MHz
CYCLES_PER_SECOND = DEFAULT_CPU_FREQUENCY
FRAME_RATE = 60  # 60 FPS
CYCLES_PER_FRAME = CYCLES_PER_SECOND // FRAME_RATE
```

---

## 性能試算資料

### 性能要求と試算

#### 基準性能要求
- **目標性能**: 実機W65C02S (1MHz) の10%以上の速度
- **最小要求**: 100,000 cycles/second (100kHz相当)
- **推奨性能**: 500,000 cycles/second (500kHz相当)

#### 性能試算

| コンポーネント | 処理時間 (μs/cycle) | 1秒間の処理可能サイクル数 | 備考 |
| :--- | :--- | :--- | :--- |
| **CPU命令実行** | 2.0 | 500,000 | Python関数呼び出しオーバーヘッド含む |
| **メモリアクセス** | 0.5 | 2,000,000 | 配列アクセス + 条件分岐 |
| **デバイスTick** | 0.3 | 3,333,333 | 軽量な状態更新処理 |
| **割り込み処理** | 5.0 | 200,000 | 複雑な状態変更処理 |
| **システム同期** | 1.0 | 1,000,000 | フレーム同期処理 |

#### 総合性能試算

```
総合処理時間 = CPU命令実行 + メモリアクセス + デバイス処理 + システム処理
             = 2.0μs + 0.5μs + 0.3μs + 1.0μs = 3.8μs/cycle

理論最大性能 = 1,000,000μs / 3.8μs = 263,158 cycles/second
実効性能 = 理論最大性能 × 効率係数(0.7) = 184,211 cycles/second
```

**結論**: 目標性能(100kHz)を十分に上回る性能が期待できる。

#### 性能最適化戦略

1. **命令ディスパッチ最適化**
   - 辞書ルックアップからswitch文への変更
   - 頻出命令の最適化

2. **メモリアクセス最適化**
   - キャッシュ機構の導入
   - バルクアクセス処理

3. **タイムスライス最適化**
   - 適応的タイムスライスサイズ
   - 処理負荷に応じた動的調整

---

## メモリ使用試算資料

### メモリ使用量試算

#### 基準メモリ要求
- **最大使用量**: 1GB以下
- **推奨使用量**: 512MB以下
- **最小使用量**: 256MB以下

#### コンポーネント別メモリ使用量

| コンポーネント | 使用量 (MB) | 詳細 |
| :--- | :--- | :--- |
| **CPUコア** | 1.0 | レジスタ、命令テーブル、状態情報 |
| **メモリ空間** | 64.0 | 64KB × 1000倍のPythonオーバーヘッド |
| **デバイス群** | 50.0 | 各種デバイスの状態とバッファ |
| **デバッガ** | 100.0 | シンボルテーブル、ブレークポイント |
| **システムサービス** | 25.0 | バス、割り込みコントローラ等 |
| **Pythonランタイム** | 150.0 | インタープリタ、ガベージコレクタ |
| **その他** | 50.0 | ログ、一時バッファ等 |

#### 総メモリ使用量試算

```
基本使用量 = 1.0 + 64.0 + 50.0 + 25.0 + 150.0 + 50.0 = 340.0 MB
デバッガ有効時 = 基本使用量 + 100.0 = 440.0 MB
最大使用量 = デバッガ有効時 × 安全係数(1.5) = 660.0 MB
```

**結論**: 目標メモリ使用量(1GB)を十分に下回る使用量となる。

#### メモリ最適化戦略

1. **オブジェクトプール**
   - 頻繁に生成/破棄されるオブジェクトの再利用
   - ガベージコレクション負荷の軽減

2. **遅延初期化**
   - 使用されるまでオブジェクトを生成しない
   - メモリ使用量の削減

3. **データ構造最適化**
   - `__slots__`の使用によるメモリ効率化
   - 適切なデータ型の選択

4. **キャッシュ管理**
   - LRUキャッシュによる適切なキャッシュサイズ管理
   - メモリリークの防止

---

## まとめ

本ソフトウェア・アーキテクチャ設計書は、W65C02S Pythonエミュレータの実装において、以下の設計指針を提供している：

1. **階層化アーキテクチャ**: 5層構造による関心の分離と保守性の確保
2. **モジュール化設計**: 8つの機能ユニットによる独立性と再利用性の実現
3. **プロトコルベース**: 統一デバイスAPIによる拡張性の確保
4. **性能・メモリ効率**: 要求仕様を満たす性能とメモリ使用量の実現

この設計により、高品質で保守性の高いW65C02Sエミュレータの実装が可能となる。
