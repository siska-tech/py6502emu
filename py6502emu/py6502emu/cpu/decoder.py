"""
命令デコーダ
PU003: InstructionDecoder

W65C02S CPUの212個の有効オペコードのデコード処理を行います。
"""

from typing import Dict, Tuple, Optional, NamedTuple
from enum import Enum, auto
from .addressing import AddressingMode


class InstructionType(Enum):
    """命令タイプ定義"""
    # Load/Store
    LDA = auto()
    STA = auto()
    LDX = auto()
    STX = auto()
    LDY = auto()
    STY = auto()
    STZ = auto()  # W65C02S拡張
    
    # Transfer
    TAX = auto()
    TAY = auto()
    TXA = auto()
    TYA = auto()
    TSX = auto()
    TXS = auto()
    
    # Stack
    PHA = auto()
    PLA = auto()
    PHP = auto()
    PLP = auto()
    PHX = auto()  # W65C02S拡張
    PHY = auto()  # W65C02S拡張
    PLX = auto()  # W65C02S拡張
    PLY = auto()  # W65C02S拡張
    
    # Arithmetic
    ADC = auto()
    SBC = auto()
    INC = auto()
    DEC = auto()
    INX = auto()
    DEX = auto()
    INY = auto()
    DEY = auto()
    
    # Logic
    AND = auto()
    ORA = auto()
    EOR = auto()
    BIT = auto()
    TRB = auto()  # W65C02S拡張
    TSB = auto()  # W65C02S拡張
    
    # Shift/Rotate
    ASL = auto()
    LSR = auto()
    ROL = auto()
    ROR = auto()
    
    # Compare
    CMP = auto()
    CPX = auto()
    CPY = auto()
    
    # Branch
    BCC = auto()
    BCS = auto()
    BEQ = auto()
    BNE = auto()
    BMI = auto()
    BPL = auto()
    BVC = auto()
    BVS = auto()
    BRA = auto()  # W65C02S拡張
    
    # Jump
    JMP = auto()
    JSR = auto()
    RTS = auto()
    RTI = auto()
    
    # Flag Control
    CLC = auto()
    SEC = auto()
    CLI = auto()
    SEI = auto()
    CLD = auto()
    SED = auto()
    CLV = auto()
    
    # System
    BRK = auto()
    NOP = auto()
    WAI = auto()  # W65C02S拡張
    STP = auto()  # W65C02S拡張
    
    # W65C02S Bit Operations
    BBR0 = auto()
    BBR1 = auto()
    BBR2 = auto()
    BBR3 = auto()
    BBR4 = auto()
    BBR5 = auto()
    BBR6 = auto()
    BBR7 = auto()
    BBS0 = auto()
    BBS1 = auto()
    BBS2 = auto()
    BBS3 = auto()
    BBS4 = auto()
    BBS5 = auto()
    BBS6 = auto()
    BBS7 = auto()
    RMB0 = auto()
    RMB1 = auto()
    RMB2 = auto()
    RMB3 = auto()
    RMB4 = auto()
    RMB5 = auto()
    RMB6 = auto()
    RMB7 = auto()
    SMB0 = auto()
    SMB1 = auto()
    SMB2 = auto()
    SMB3 = auto()
    SMB4 = auto()
    SMB5 = auto()
    SMB6 = auto()
    SMB7 = auto()


class InstructionInfo(NamedTuple):
    """命令情報"""
    opcode: int
    instruction: InstructionType
    addressing_mode: AddressingMode
    cycles: int
    length: int


class InstructionDecoder:
    """W65C02S 命令デコーダクラス
    
    212個の有効オペコードを解析し、命令タイプ、アドレッシングモード、
    サイクル数、命令長を決定します。
    """
    
    def __init__(self) -> None:
        """初期化"""
        self._instruction_table = self._build_instruction_table()
    
    def _build_instruction_table(self) -> Dict[int, InstructionInfo]:
        """命令テーブル構築
        
        Returns:
            Dict[int, InstructionInfo]: オペコード -> 命令情報のマッピング
        """
        table = {}
        
        # Load/Store Instructions
        # LDA
        table[0xA9] = InstructionInfo(0xA9, InstructionType.LDA, AddressingMode.IMMEDIATE, 2, 2)
        table[0xA5] = InstructionInfo(0xA5, InstructionType.LDA, AddressingMode.ZERO_PAGE, 3, 2)
        table[0xB5] = InstructionInfo(0xB5, InstructionType.LDA, AddressingMode.ZERO_PAGE_X, 4, 2)
        table[0xAD] = InstructionInfo(0xAD, InstructionType.LDA, AddressingMode.ABSOLUTE, 4, 3)
        table[0xBD] = InstructionInfo(0xBD, InstructionType.LDA, AddressingMode.ABSOLUTE_X, 4, 3)  # +1 if page crossed
        table[0xB9] = InstructionInfo(0xB9, InstructionType.LDA, AddressingMode.ABSOLUTE_Y, 4, 3)  # +1 if page crossed
        table[0xA1] = InstructionInfo(0xA1, InstructionType.LDA, AddressingMode.INDIRECT_X, 6, 2)
        table[0xB1] = InstructionInfo(0xB1, InstructionType.LDA, AddressingMode.INDIRECT_Y, 5, 2)  # +1 if page crossed
        table[0xB2] = InstructionInfo(0xB2, InstructionType.LDA, AddressingMode.INDIRECT_ZP, 5, 2)  # W65C02S
        
        # STA
        table[0x85] = InstructionInfo(0x85, InstructionType.STA, AddressingMode.ZERO_PAGE, 3, 2)
        table[0x95] = InstructionInfo(0x95, InstructionType.STA, AddressingMode.ZERO_PAGE_X, 4, 2)
        table[0x8D] = InstructionInfo(0x8D, InstructionType.STA, AddressingMode.ABSOLUTE, 4, 3)
        table[0x9D] = InstructionInfo(0x9D, InstructionType.STA, AddressingMode.ABSOLUTE_X, 5, 3)
        table[0x99] = InstructionInfo(0x99, InstructionType.STA, AddressingMode.ABSOLUTE_Y, 5, 3)
        table[0x81] = InstructionInfo(0x81, InstructionType.STA, AddressingMode.INDIRECT_X, 6, 2)
        table[0x91] = InstructionInfo(0x91, InstructionType.STA, AddressingMode.INDIRECT_Y, 6, 2)
        table[0x92] = InstructionInfo(0x92, InstructionType.STA, AddressingMode.INDIRECT_ZP, 5, 2)  # W65C02S
        
        # LDX
        table[0xA2] = InstructionInfo(0xA2, InstructionType.LDX, AddressingMode.IMMEDIATE, 2, 2)
        table[0xA6] = InstructionInfo(0xA6, InstructionType.LDX, AddressingMode.ZERO_PAGE, 3, 2)
        table[0xB6] = InstructionInfo(0xB6, InstructionType.LDX, AddressingMode.ZERO_PAGE_Y, 4, 2)
        table[0xAE] = InstructionInfo(0xAE, InstructionType.LDX, AddressingMode.ABSOLUTE, 4, 3)
        table[0xBE] = InstructionInfo(0xBE, InstructionType.LDX, AddressingMode.ABSOLUTE_Y, 4, 3)  # +1 if page crossed
        
        # STX
        table[0x86] = InstructionInfo(0x86, InstructionType.STX, AddressingMode.ZERO_PAGE, 3, 2)
        table[0x96] = InstructionInfo(0x96, InstructionType.STX, AddressingMode.ZERO_PAGE_Y, 4, 2)
        table[0x8E] = InstructionInfo(0x8E, InstructionType.STX, AddressingMode.ABSOLUTE, 4, 3)
        
        # LDY
        table[0xA0] = InstructionInfo(0xA0, InstructionType.LDY, AddressingMode.IMMEDIATE, 2, 2)
        table[0xA4] = InstructionInfo(0xA4, InstructionType.LDY, AddressingMode.ZERO_PAGE, 3, 2)
        table[0xB4] = InstructionInfo(0xB4, InstructionType.LDY, AddressingMode.ZERO_PAGE_X, 4, 2)
        table[0xAC] = InstructionInfo(0xAC, InstructionType.LDY, AddressingMode.ABSOLUTE, 4, 3)
        table[0xBC] = InstructionInfo(0xBC, InstructionType.LDY, AddressingMode.ABSOLUTE_X, 4, 3)  # +1 if page crossed
        
        # STY
        table[0x84] = InstructionInfo(0x84, InstructionType.STY, AddressingMode.ZERO_PAGE, 3, 2)
        table[0x94] = InstructionInfo(0x94, InstructionType.STY, AddressingMode.ZERO_PAGE_X, 4, 2)
        table[0x8C] = InstructionInfo(0x8C, InstructionType.STY, AddressingMode.ABSOLUTE, 4, 3)
        
        # STZ (W65C02S)
        table[0x64] = InstructionInfo(0x64, InstructionType.STZ, AddressingMode.ZERO_PAGE, 3, 2)
        table[0x74] = InstructionInfo(0x74, InstructionType.STZ, AddressingMode.ZERO_PAGE_X, 4, 2)
        table[0x9C] = InstructionInfo(0x9C, InstructionType.STZ, AddressingMode.ABSOLUTE, 4, 3)
        table[0x9E] = InstructionInfo(0x9E, InstructionType.STZ, AddressingMode.ABSOLUTE_X, 5, 3)
        
        # Transfer Instructions
        table[0xAA] = InstructionInfo(0xAA, InstructionType.TAX, AddressingMode.IMPLICIT, 2, 1)
        table[0xA8] = InstructionInfo(0xA8, InstructionType.TAY, AddressingMode.IMPLICIT, 2, 1)
        table[0x8A] = InstructionInfo(0x8A, InstructionType.TXA, AddressingMode.IMPLICIT, 2, 1)
        table[0x98] = InstructionInfo(0x98, InstructionType.TYA, AddressingMode.IMPLICIT, 2, 1)
        table[0xBA] = InstructionInfo(0xBA, InstructionType.TSX, AddressingMode.IMPLICIT, 2, 1)
        table[0x9A] = InstructionInfo(0x9A, InstructionType.TXS, AddressingMode.IMPLICIT, 2, 1)
        
        # Stack Instructions
        table[0x48] = InstructionInfo(0x48, InstructionType.PHA, AddressingMode.IMPLICIT, 3, 1)
        table[0x68] = InstructionInfo(0x68, InstructionType.PLA, AddressingMode.IMPLICIT, 4, 1)
        table[0x08] = InstructionInfo(0x08, InstructionType.PHP, AddressingMode.IMPLICIT, 3, 1)
        table[0x28] = InstructionInfo(0x28, InstructionType.PLP, AddressingMode.IMPLICIT, 4, 1)
        table[0xDA] = InstructionInfo(0xDA, InstructionType.PHX, AddressingMode.IMPLICIT, 3, 1)  # W65C02S
        table[0xFA] = InstructionInfo(0xFA, InstructionType.PLX, AddressingMode.IMPLICIT, 4, 1)  # W65C02S
        table[0x5A] = InstructionInfo(0x5A, InstructionType.PHY, AddressingMode.IMPLICIT, 3, 1)  # W65C02S
        table[0x7A] = InstructionInfo(0x7A, InstructionType.PLY, AddressingMode.IMPLICIT, 4, 1)  # W65C02S
        
        # Arithmetic Instructions
        # ADC
        table[0x69] = InstructionInfo(0x69, InstructionType.ADC, AddressingMode.IMMEDIATE, 2, 2)
        table[0x65] = InstructionInfo(0x65, InstructionType.ADC, AddressingMode.ZERO_PAGE, 3, 2)
        table[0x75] = InstructionInfo(0x75, InstructionType.ADC, AddressingMode.ZERO_PAGE_X, 4, 2)
        table[0x6D] = InstructionInfo(0x6D, InstructionType.ADC, AddressingMode.ABSOLUTE, 4, 3)
        table[0x7D] = InstructionInfo(0x7D, InstructionType.ADC, AddressingMode.ABSOLUTE_X, 4, 3)  # +1 if page crossed
        table[0x79] = InstructionInfo(0x79, InstructionType.ADC, AddressingMode.ABSOLUTE_Y, 4, 3)  # +1 if page crossed
        table[0x61] = InstructionInfo(0x61, InstructionType.ADC, AddressingMode.INDIRECT_X, 6, 2)
        table[0x71] = InstructionInfo(0x71, InstructionType.ADC, AddressingMode.INDIRECT_Y, 5, 2)  # +1 if page crossed
        table[0x72] = InstructionInfo(0x72, InstructionType.ADC, AddressingMode.INDIRECT_ZP, 5, 2)  # W65C02S
        
        # SBC
        table[0xE9] = InstructionInfo(0xE9, InstructionType.SBC, AddressingMode.IMMEDIATE, 2, 2)
        table[0xE5] = InstructionInfo(0xE5, InstructionType.SBC, AddressingMode.ZERO_PAGE, 3, 2)
        table[0xF5] = InstructionInfo(0xF5, InstructionType.SBC, AddressingMode.ZERO_PAGE_X, 4, 2)
        table[0xED] = InstructionInfo(0xED, InstructionType.SBC, AddressingMode.ABSOLUTE, 4, 3)
        table[0xFD] = InstructionInfo(0xFD, InstructionType.SBC, AddressingMode.ABSOLUTE_X, 4, 3)  # +1 if page crossed
        table[0xF9] = InstructionInfo(0xF9, InstructionType.SBC, AddressingMode.ABSOLUTE_Y, 4, 3)  # +1 if page crossed
        table[0xE1] = InstructionInfo(0xE1, InstructionType.SBC, AddressingMode.INDIRECT_X, 6, 2)
        table[0xF1] = InstructionInfo(0xF1, InstructionType.SBC, AddressingMode.INDIRECT_Y, 5, 2)  # +1 if page crossed
        table[0xF2] = InstructionInfo(0xF2, InstructionType.SBC, AddressingMode.INDIRECT_ZP, 5, 2)  # W65C02S
        
        # INC/DEC
        table[0xE6] = InstructionInfo(0xE6, InstructionType.INC, AddressingMode.ZERO_PAGE, 5, 2)
        table[0xF6] = InstructionInfo(0xF6, InstructionType.INC, AddressingMode.ZERO_PAGE_X, 6, 2)
        table[0xEE] = InstructionInfo(0xEE, InstructionType.INC, AddressingMode.ABSOLUTE, 6, 3)
        table[0xFE] = InstructionInfo(0xFE, InstructionType.INC, AddressingMode.ABSOLUTE_X, 7, 3)
        table[0x1A] = InstructionInfo(0x1A, InstructionType.INC, AddressingMode.ACCUMULATOR, 2, 1)  # W65C02S
        
        table[0xC6] = InstructionInfo(0xC6, InstructionType.DEC, AddressingMode.ZERO_PAGE, 5, 2)
        table[0xD6] = InstructionInfo(0xD6, InstructionType.DEC, AddressingMode.ZERO_PAGE_X, 6, 2)
        table[0xCE] = InstructionInfo(0xCE, InstructionType.DEC, AddressingMode.ABSOLUTE, 6, 3)
        table[0xDE] = InstructionInfo(0xDE, InstructionType.DEC, AddressingMode.ABSOLUTE_X, 7, 3)
        table[0x3A] = InstructionInfo(0x3A, InstructionType.DEC, AddressingMode.ACCUMULATOR, 2, 1)  # W65C02S
        
        table[0xE8] = InstructionInfo(0xE8, InstructionType.INX, AddressingMode.IMPLICIT, 2, 1)
        table[0xCA] = InstructionInfo(0xCA, InstructionType.DEX, AddressingMode.IMPLICIT, 2, 1)
        table[0xC8] = InstructionInfo(0xC8, InstructionType.INY, AddressingMode.IMPLICIT, 2, 1)
        table[0x88] = InstructionInfo(0x88, InstructionType.DEY, AddressingMode.IMPLICIT, 2, 1)
        
        # Logic Instructions
        # AND
        table[0x29] = InstructionInfo(0x29, InstructionType.AND, AddressingMode.IMMEDIATE, 2, 2)
        table[0x25] = InstructionInfo(0x25, InstructionType.AND, AddressingMode.ZERO_PAGE, 3, 2)
        table[0x35] = InstructionInfo(0x35, InstructionType.AND, AddressingMode.ZERO_PAGE_X, 4, 2)
        table[0x2D] = InstructionInfo(0x2D, InstructionType.AND, AddressingMode.ABSOLUTE, 4, 3)
        table[0x3D] = InstructionInfo(0x3D, InstructionType.AND, AddressingMode.ABSOLUTE_X, 4, 3)  # +1 if page crossed
        table[0x39] = InstructionInfo(0x39, InstructionType.AND, AddressingMode.ABSOLUTE_Y, 4, 3)  # +1 if page crossed
        table[0x21] = InstructionInfo(0x21, InstructionType.AND, AddressingMode.INDIRECT_X, 6, 2)
        table[0x31] = InstructionInfo(0x31, InstructionType.AND, AddressingMode.INDIRECT_Y, 5, 2)  # +1 if page crossed
        table[0x32] = InstructionInfo(0x32, InstructionType.AND, AddressingMode.INDIRECT_ZP, 5, 2)  # W65C02S
        
        # ORA
        table[0x09] = InstructionInfo(0x09, InstructionType.ORA, AddressingMode.IMMEDIATE, 2, 2)
        table[0x05] = InstructionInfo(0x05, InstructionType.ORA, AddressingMode.ZERO_PAGE, 3, 2)
        table[0x15] = InstructionInfo(0x15, InstructionType.ORA, AddressingMode.ZERO_PAGE_X, 4, 2)
        table[0x0D] = InstructionInfo(0x0D, InstructionType.ORA, AddressingMode.ABSOLUTE, 4, 3)
        table[0x1D] = InstructionInfo(0x1D, InstructionType.ORA, AddressingMode.ABSOLUTE_X, 4, 3)  # +1 if page crossed
        table[0x19] = InstructionInfo(0x19, InstructionType.ORA, AddressingMode.ABSOLUTE_Y, 4, 3)  # +1 if page crossed
        table[0x01] = InstructionInfo(0x01, InstructionType.ORA, AddressingMode.INDIRECT_X, 6, 2)
        table[0x11] = InstructionInfo(0x11, InstructionType.ORA, AddressingMode.INDIRECT_Y, 5, 2)  # +1 if page crossed
        table[0x12] = InstructionInfo(0x12, InstructionType.ORA, AddressingMode.INDIRECT_ZP, 5, 2)  # W65C02S
        
        # EOR
        table[0x49] = InstructionInfo(0x49, InstructionType.EOR, AddressingMode.IMMEDIATE, 2, 2)
        table[0x45] = InstructionInfo(0x45, InstructionType.EOR, AddressingMode.ZERO_PAGE, 3, 2)
        table[0x55] = InstructionInfo(0x55, InstructionType.EOR, AddressingMode.ZERO_PAGE_X, 4, 2)
        table[0x4D] = InstructionInfo(0x4D, InstructionType.EOR, AddressingMode.ABSOLUTE, 4, 3)
        table[0x5D] = InstructionInfo(0x5D, InstructionType.EOR, AddressingMode.ABSOLUTE_X, 4, 3)  # +1 if page crossed
        table[0x59] = InstructionInfo(0x59, InstructionType.EOR, AddressingMode.ABSOLUTE_Y, 4, 3)  # +1 if page crossed
        table[0x41] = InstructionInfo(0x41, InstructionType.EOR, AddressingMode.INDIRECT_X, 6, 2)
        table[0x51] = InstructionInfo(0x51, InstructionType.EOR, AddressingMode.INDIRECT_Y, 5, 2)  # +1 if page crossed
        table[0x52] = InstructionInfo(0x52, InstructionType.EOR, AddressingMode.INDIRECT_ZP, 5, 2)  # W65C02S
        
        # BIT
        table[0x24] = InstructionInfo(0x24, InstructionType.BIT, AddressingMode.ZERO_PAGE, 3, 2)
        table[0x2C] = InstructionInfo(0x2C, InstructionType.BIT, AddressingMode.ABSOLUTE, 4, 3)
        table[0x34] = InstructionInfo(0x34, InstructionType.BIT, AddressingMode.ZERO_PAGE_X, 4, 2)  # W65C02S
        table[0x3C] = InstructionInfo(0x3C, InstructionType.BIT, AddressingMode.ABSOLUTE_X, 4, 3)  # W65C02S
        table[0x89] = InstructionInfo(0x89, InstructionType.BIT, AddressingMode.IMMEDIATE, 2, 2)  # W65C02S
        
        # TRB/TSB (W65C02S)
        table[0x14] = InstructionInfo(0x14, InstructionType.TRB, AddressingMode.ZERO_PAGE, 5, 2)
        table[0x1C] = InstructionInfo(0x1C, InstructionType.TRB, AddressingMode.ABSOLUTE, 6, 3)
        table[0x04] = InstructionInfo(0x04, InstructionType.TSB, AddressingMode.ZERO_PAGE, 5, 2)
        table[0x0C] = InstructionInfo(0x0C, InstructionType.TSB, AddressingMode.ABSOLUTE, 6, 3)
        
        # Shift/Rotate Instructions
        # ASL
        table[0x0A] = InstructionInfo(0x0A, InstructionType.ASL, AddressingMode.ACCUMULATOR, 2, 1)
        table[0x06] = InstructionInfo(0x06, InstructionType.ASL, AddressingMode.ZERO_PAGE, 5, 2)
        table[0x16] = InstructionInfo(0x16, InstructionType.ASL, AddressingMode.ZERO_PAGE_X, 6, 2)
        table[0x0E] = InstructionInfo(0x0E, InstructionType.ASL, AddressingMode.ABSOLUTE, 6, 3)
        table[0x1E] = InstructionInfo(0x1E, InstructionType.ASL, AddressingMode.ABSOLUTE_X, 7, 3)
        
        # LSR
        table[0x4A] = InstructionInfo(0x4A, InstructionType.LSR, AddressingMode.ACCUMULATOR, 2, 1)
        table[0x46] = InstructionInfo(0x46, InstructionType.LSR, AddressingMode.ZERO_PAGE, 5, 2)
        table[0x56] = InstructionInfo(0x56, InstructionType.LSR, AddressingMode.ZERO_PAGE_X, 6, 2)
        table[0x4E] = InstructionInfo(0x4E, InstructionType.LSR, AddressingMode.ABSOLUTE, 6, 3)
        table[0x5E] = InstructionInfo(0x5E, InstructionType.LSR, AddressingMode.ABSOLUTE_X, 7, 3)
        
        # ROL
        table[0x2A] = InstructionInfo(0x2A, InstructionType.ROL, AddressingMode.ACCUMULATOR, 2, 1)
        table[0x26] = InstructionInfo(0x26, InstructionType.ROL, AddressingMode.ZERO_PAGE, 5, 2)
        table[0x36] = InstructionInfo(0x36, InstructionType.ROL, AddressingMode.ZERO_PAGE_X, 6, 2)
        table[0x2E] = InstructionInfo(0x2E, InstructionType.ROL, AddressingMode.ABSOLUTE, 6, 3)
        table[0x3E] = InstructionInfo(0x3E, InstructionType.ROL, AddressingMode.ABSOLUTE_X, 7, 3)
        
        # ROR
        table[0x6A] = InstructionInfo(0x6A, InstructionType.ROR, AddressingMode.ACCUMULATOR, 2, 1)
        table[0x66] = InstructionInfo(0x66, InstructionType.ROR, AddressingMode.ZERO_PAGE, 5, 2)
        table[0x76] = InstructionInfo(0x76, InstructionType.ROR, AddressingMode.ZERO_PAGE_X, 6, 2)
        table[0x6E] = InstructionInfo(0x6E, InstructionType.ROR, AddressingMode.ABSOLUTE, 6, 3)
        table[0x7E] = InstructionInfo(0x7E, InstructionType.ROR, AddressingMode.ABSOLUTE_X, 7, 3)
        
        # Compare Instructions
        # CMP
        table[0xC9] = InstructionInfo(0xC9, InstructionType.CMP, AddressingMode.IMMEDIATE, 2, 2)
        table[0xC5] = InstructionInfo(0xC5, InstructionType.CMP, AddressingMode.ZERO_PAGE, 3, 2)
        table[0xD5] = InstructionInfo(0xD5, InstructionType.CMP, AddressingMode.ZERO_PAGE_X, 4, 2)
        table[0xCD] = InstructionInfo(0xCD, InstructionType.CMP, AddressingMode.ABSOLUTE, 4, 3)
        table[0xDD] = InstructionInfo(0xDD, InstructionType.CMP, AddressingMode.ABSOLUTE_X, 4, 3)  # +1 if page crossed
        table[0xD9] = InstructionInfo(0xD9, InstructionType.CMP, AddressingMode.ABSOLUTE_Y, 4, 3)  # +1 if page crossed
        table[0xC1] = InstructionInfo(0xC1, InstructionType.CMP, AddressingMode.INDIRECT_X, 6, 2)
        table[0xD1] = InstructionInfo(0xD1, InstructionType.CMP, AddressingMode.INDIRECT_Y, 5, 2)  # +1 if page crossed
        table[0xD2] = InstructionInfo(0xD2, InstructionType.CMP, AddressingMode.INDIRECT_ZP, 5, 2)  # W65C02S
        
        # CPX
        table[0xE0] = InstructionInfo(0xE0, InstructionType.CPX, AddressingMode.IMMEDIATE, 2, 2)
        table[0xE4] = InstructionInfo(0xE4, InstructionType.CPX, AddressingMode.ZERO_PAGE, 3, 2)
        table[0xEC] = InstructionInfo(0xEC, InstructionType.CPX, AddressingMode.ABSOLUTE, 4, 3)
        
        # CPY
        table[0xC0] = InstructionInfo(0xC0, InstructionType.CPY, AddressingMode.IMMEDIATE, 2, 2)
        table[0xC4] = InstructionInfo(0xC4, InstructionType.CPY, AddressingMode.ZERO_PAGE, 3, 2)
        table[0xCC] = InstructionInfo(0xCC, InstructionType.CPY, AddressingMode.ABSOLUTE, 4, 3)
        
        # Branch Instructions
        table[0x90] = InstructionInfo(0x90, InstructionType.BCC, AddressingMode.RELATIVE, 2, 2)  # +1 if branch taken, +1 if page crossed
        table[0xB0] = InstructionInfo(0xB0, InstructionType.BCS, AddressingMode.RELATIVE, 2, 2)
        table[0xF0] = InstructionInfo(0xF0, InstructionType.BEQ, AddressingMode.RELATIVE, 2, 2)
        table[0xD0] = InstructionInfo(0xD0, InstructionType.BNE, AddressingMode.RELATIVE, 2, 2)
        table[0x30] = InstructionInfo(0x30, InstructionType.BMI, AddressingMode.RELATIVE, 2, 2)
        table[0x10] = InstructionInfo(0x10, InstructionType.BPL, AddressingMode.RELATIVE, 2, 2)
        table[0x50] = InstructionInfo(0x50, InstructionType.BVC, AddressingMode.RELATIVE, 2, 2)
        table[0x70] = InstructionInfo(0x70, InstructionType.BVS, AddressingMode.RELATIVE, 2, 2)
        table[0x80] = InstructionInfo(0x80, InstructionType.BRA, AddressingMode.RELATIVE, 3, 2)  # W65C02S, always taken
        
        # Jump Instructions
        table[0x4C] = InstructionInfo(0x4C, InstructionType.JMP, AddressingMode.ABSOLUTE, 3, 3)
        table[0x6C] = InstructionInfo(0x6C, InstructionType.JMP, AddressingMode.INDIRECT, 5, 3)
        table[0x7C] = InstructionInfo(0x7C, InstructionType.JMP, AddressingMode.INDIRECT_ABS_X, 6, 3)  # W65C02S
        table[0x20] = InstructionInfo(0x20, InstructionType.JSR, AddressingMode.ABSOLUTE, 6, 3)
        table[0x60] = InstructionInfo(0x60, InstructionType.RTS, AddressingMode.IMPLICIT, 6, 1)
        table[0x40] = InstructionInfo(0x40, InstructionType.RTI, AddressingMode.IMPLICIT, 6, 1)
        
        # Flag Control Instructions
        table[0x18] = InstructionInfo(0x18, InstructionType.CLC, AddressingMode.IMPLICIT, 2, 1)
        table[0x38] = InstructionInfo(0x38, InstructionType.SEC, AddressingMode.IMPLICIT, 2, 1)
        table[0x58] = InstructionInfo(0x58, InstructionType.CLI, AddressingMode.IMPLICIT, 2, 1)
        table[0x78] = InstructionInfo(0x78, InstructionType.SEI, AddressingMode.IMPLICIT, 2, 1)
        table[0xD8] = InstructionInfo(0xD8, InstructionType.CLD, AddressingMode.IMPLICIT, 2, 1)
        table[0xF8] = InstructionInfo(0xF8, InstructionType.SED, AddressingMode.IMPLICIT, 2, 1)
        table[0xB8] = InstructionInfo(0xB8, InstructionType.CLV, AddressingMode.IMPLICIT, 2, 1)
        
        # System Instructions
        table[0x00] = InstructionInfo(0x00, InstructionType.BRK, AddressingMode.IMPLICIT, 7, 1)
        table[0xEA] = InstructionInfo(0xEA, InstructionType.NOP, AddressingMode.IMPLICIT, 2, 1)
        table[0xCB] = InstructionInfo(0xCB, InstructionType.WAI, AddressingMode.IMPLICIT, 3, 1)  # W65C02S
        table[0xDB] = InstructionInfo(0xDB, InstructionType.STP, AddressingMode.IMPLICIT, 3, 1)  # W65C02S
        
        # W65C02S Bit Branch Instructions (BBR/BBS)
        # BBR (Branch on Bit Reset)
        table[0x0F] = InstructionInfo(0x0F, InstructionType.BBR0, AddressingMode.RELATIVE, 5, 3)
        table[0x1F] = InstructionInfo(0x1F, InstructionType.BBR1, AddressingMode.RELATIVE, 5, 3)
        table[0x2F] = InstructionInfo(0x2F, InstructionType.BBR2, AddressingMode.RELATIVE, 5, 3)
        table[0x3F] = InstructionInfo(0x3F, InstructionType.BBR3, AddressingMode.RELATIVE, 5, 3)
        table[0x4F] = InstructionInfo(0x4F, InstructionType.BBR4, AddressingMode.RELATIVE, 5, 3)
        table[0x5F] = InstructionInfo(0x5F, InstructionType.BBR5, AddressingMode.RELATIVE, 5, 3)
        table[0x6F] = InstructionInfo(0x6F, InstructionType.BBR6, AddressingMode.RELATIVE, 5, 3)
        table[0x7F] = InstructionInfo(0x7F, InstructionType.BBR7, AddressingMode.RELATIVE, 5, 3)
        
        # BBS (Branch on Bit Set)
        table[0x8F] = InstructionInfo(0x8F, InstructionType.BBS0, AddressingMode.RELATIVE, 5, 3)
        table[0x9F] = InstructionInfo(0x9F, InstructionType.BBS1, AddressingMode.RELATIVE, 5, 3)
        table[0xAF] = InstructionInfo(0xAF, InstructionType.BBS2, AddressingMode.RELATIVE, 5, 3)
        table[0xBF] = InstructionInfo(0xBF, InstructionType.BBS3, AddressingMode.RELATIVE, 5, 3)
        table[0xCF] = InstructionInfo(0xCF, InstructionType.BBS4, AddressingMode.RELATIVE, 5, 3)
        table[0xDF] = InstructionInfo(0xDF, InstructionType.BBS5, AddressingMode.RELATIVE, 5, 3)
        table[0xEF] = InstructionInfo(0xEF, InstructionType.BBS6, AddressingMode.RELATIVE, 5, 3)
        table[0xFF] = InstructionInfo(0xFF, InstructionType.BBS7, AddressingMode.RELATIVE, 5, 3)
        
        # W65C02S Bit Manipulation Instructions (RMB/SMB)
        # RMB (Reset Memory Bit)
        table[0x07] = InstructionInfo(0x07, InstructionType.RMB0, AddressingMode.ZERO_PAGE, 5, 2)
        table[0x17] = InstructionInfo(0x17, InstructionType.RMB1, AddressingMode.ZERO_PAGE, 5, 2)
        table[0x27] = InstructionInfo(0x27, InstructionType.RMB2, AddressingMode.ZERO_PAGE, 5, 2)
        table[0x37] = InstructionInfo(0x37, InstructionType.RMB3, AddressingMode.ZERO_PAGE, 5, 2)
        table[0x47] = InstructionInfo(0x47, InstructionType.RMB4, AddressingMode.ZERO_PAGE, 5, 2)
        table[0x57] = InstructionInfo(0x57, InstructionType.RMB5, AddressingMode.ZERO_PAGE, 5, 2)
        table[0x67] = InstructionInfo(0x67, InstructionType.RMB6, AddressingMode.ZERO_PAGE, 5, 2)
        table[0x77] = InstructionInfo(0x77, InstructionType.RMB7, AddressingMode.ZERO_PAGE, 5, 2)
        
        # SMB (Set Memory Bit)
        table[0x87] = InstructionInfo(0x87, InstructionType.SMB0, AddressingMode.ZERO_PAGE, 5, 2)
        table[0x97] = InstructionInfo(0x97, InstructionType.SMB1, AddressingMode.ZERO_PAGE, 5, 2)
        table[0xA7] = InstructionInfo(0xA7, InstructionType.SMB2, AddressingMode.ZERO_PAGE, 5, 2)
        table[0xB7] = InstructionInfo(0xB7, InstructionType.SMB3, AddressingMode.ZERO_PAGE, 5, 2)
        table[0xC7] = InstructionInfo(0xC7, InstructionType.SMB4, AddressingMode.ZERO_PAGE, 5, 2)
        table[0xD7] = InstructionInfo(0xD7, InstructionType.SMB5, AddressingMode.ZERO_PAGE, 5, 2)
        table[0xE7] = InstructionInfo(0xE7, InstructionType.SMB6, AddressingMode.ZERO_PAGE, 5, 2)
        table[0xF7] = InstructionInfo(0xF7, InstructionType.SMB7, AddressingMode.ZERO_PAGE, 5, 2)
        
        return table
    
    def decode(self, opcode: int) -> Optional[InstructionInfo]:
        """命令デコード
        
        Args:
            opcode: オペコード (0x00-0xFF)
            
        Returns:
            Optional[InstructionInfo]: 命令情報、無効オペコードの場合はNone
        """
        return self._instruction_table.get(opcode & 0xFF)
    
    def is_valid_opcode(self, opcode: int) -> bool:
        """有効オペコード判定
        
        Args:
            opcode: オペコード (0x00-0xFF)
            
        Returns:
            bool: 有効オペコードかどうか
        """
        return (opcode & 0xFF) in self._instruction_table
    
    def get_instruction_count(self) -> int:
        """実装済み命令数取得
        
        Returns:
            int: 実装済み命令数
        """
        return len(self._instruction_table)
    
    def get_all_opcodes(self) -> Tuple[int, ...]:
        """全オペコード取得
        
        Returns:
            Tuple[int, ...]: 実装済み全オペコードのタプル
        """
        return tuple(sorted(self._instruction_table.keys()))
    
    def get_instructions_by_type(self, instruction_type: InstructionType) -> Tuple[InstructionInfo, ...]:
        """命令タイプ別命令取得
        
        Args:
            instruction_type: 命令タイプ
            
        Returns:
            Tuple[InstructionInfo, ...]: 該当する命令情報のタプル
        """
        return tuple(
            info for info in self._instruction_table.values()
            if info.instruction == instruction_type
        )
    
    def get_instructions_by_addressing_mode(self, addressing_mode: AddressingMode) -> Tuple[InstructionInfo, ...]:
        """アドレッシングモード別命令取得
        
        Args:
            addressing_mode: アドレッシングモード
            
        Returns:
            Tuple[InstructionInfo, ...]: 該当する命令情報のタプル
        """
        return tuple(
            info for info in self._instruction_table.values()
            if info.addressing_mode == addressing_mode
        )
    
    def __str__(self) -> str:
        """文字列表現
        
        Returns:
            str: デコーダの状態を表す文字列
        """
        return f"InstructionDecoder({self.get_instruction_count()} instructions)"
    
    def __repr__(self) -> str:
        """詳細文字列表現
        
        Returns:
            str: デコーダの詳細状態を表す文字列
        """
        return f"InstructionDecoder(instructions={self.get_instruction_count()})"
