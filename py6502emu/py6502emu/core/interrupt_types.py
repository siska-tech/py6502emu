"""
割り込み関連型定義

W65C02S エミュレータの割り込み処理で使用される型定義とベクタアドレス定義を提供します。
"""

from enum import Enum, auto
from typing import TypedDict, Dict


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


# 割り込みベクタアドレス定義（W65C02S仕様準拠）
INTERRUPT_VECTORS: Dict[InterruptType, int] = {
    InterruptType.RESET: 0xFFFC,  # RESET vector
    InterruptType.NMI: 0xFFFA,    # NMI vector
    InterruptType.IRQ: 0xFFFE,    # IRQ/BRK vector
}

# 割り込み処理サイクル数
INTERRUPT_CYCLES: Dict[InterruptType, int] = {
    InterruptType.RESET: 7,
    InterruptType.NMI: 7,
    InterruptType.IRQ: 7,
}

# 割り込み優先度（数値が小さいほど高優先度）
INTERRUPT_PRIORITY: Dict[InterruptType, int] = {
    InterruptType.RESET: 1,  # 最高優先度
    InterruptType.NMI: 2,
    InterruptType.IRQ: 3,
}
