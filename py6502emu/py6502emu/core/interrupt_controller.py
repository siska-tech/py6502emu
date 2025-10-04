"""
割り込み制御

W65C02S エミュレータの集中的割り込み管理を提供します。
IRQ/NMI/RES優先度制御、割り込み要求・承認処理、割り込みベクタ管理を含みます。
"""

from typing import Set, Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum, auto
import time

from .interrupt_types import (
    InterruptType, 
    InterruptVector, 
    INTERRUPT_VECTORS, 
    INTERRUPT_CYCLES, 
    INTERRUPT_PRIORITY
)


class InterruptState(Enum):
    """割り込み状態"""
    IDLE = auto()       # 割り込みなし
    PENDING = auto()    # 割り込み保留中
    SERVICING = auto()  # 割り込み処理中


@dataclass
class InterruptRequest:
    """割り込み要求情報"""
    interrupt_type: InterruptType
    source_id: str
    timestamp: float
    priority: int
    
    def __post_init__(self) -> None:
        """初期化後処理"""
        if self.priority <= 0:
            raise ValueError("Priority must be positive")


class InterruptController:
    """割り込みコントローラクラス
    
    W65C02Sの割り込み処理を集中管理し、
    IRQ/NMI/RES優先度制御、割り込み要求・承認処理を提供します。
    """
    
    def __init__(self):
        """割り込みコントローラを初期化"""
        # 割り込み要求管理
        self._irq_sources: Set[str] = set()
        self._nmi_pending = False
        self._reset_pending = False
        
        # 割り込み状態
        self._current_state = InterruptState.IDLE
        self._servicing_interrupt: Optional[InterruptType] = None
        
        # 割り込み履歴・統計
        self._interrupt_history: List[InterruptRequest] = []
        self._interrupt_count: Dict[InterruptType, int] = {
            InterruptType.RESET: 0,
            InterruptType.NMI: 0,
            InterruptType.IRQ: 0
        }
        
        # 割り込みフック（デバッグ・トレース用）
        self._interrupt_hooks: List[Callable[[InterruptType, str], None]] = []
        self._acknowledge_hooks: List[Callable[[InterruptType], None]] = []
        
        # 設定
        self._max_history_entries = 1000
        self._enable_history = True
        
        # NMI エッジ検出用
        self._nmi_previous_state = False
    
    def assert_irq(self, source_id: str) -> None:
        """IRQ要求アサート
        
        指定されたソースからのIRQ割り込み要求をアサートします。
        
        Args:
            source_id: 割り込みソースの識別子
        """
        if not source_id:
            raise ValueError("Source ID cannot be empty")
        
        was_pending = bool(self._irq_sources)
        self._irq_sources.add(source_id)
        
        # 新規IRQ要求の場合のみ処理
        if not was_pending:
            self._handle_interrupt_request(InterruptType.IRQ, source_id)
    
    def deassert_irq(self, source_id: str) -> None:
        """IRQ要求デアサート
        
        指定されたソースからのIRQ割り込み要求をデアサートします。
        
        Args:
            source_id: 割り込みソースの識別子
        """
        self._irq_sources.discard(source_id)
    
    def assert_nmi(self, source_id: str = "system") -> None:
        """NMI要求アサート
        
        NMI（Non-Maskable Interrupt）要求をアサートします。
        NMIはエッジトリガーなので、立ち上がりエッジでのみ有効です。
        
        Args:
            source_id: 割り込みソースの識別子
        """
        # エッジ検出（立ち上がりエッジのみ有効）
        if not self._nmi_previous_state and not self._nmi_pending:
            self._nmi_pending = True
            self._handle_interrupt_request(InterruptType.NMI, source_id)
        
        self._nmi_previous_state = True
    
    def deassert_nmi(self) -> None:
        """NMI要求デアサート
        
        NMI信号をデアサートします。
        """
        self._nmi_previous_state = False
    
    def assert_reset(self, source_id: str = "system") -> None:
        """リセット要求アサート
        
        システムリセット要求をアサートします。
        
        Args:
            source_id: 割り込みソースの識別子
        """
        self._reset_pending = True
        self._handle_interrupt_request(InterruptType.RESET, source_id)
    
    def deassert_reset(self) -> None:
        """リセット要求デアサート
        
        リセット信号をデアサートします。
        """
        self._reset_pending = False
    
    def is_pending(self) -> bool:
        """割り込み保留チェック
        
        何らかの割り込みが保留中かどうかをチェックします。
        
        Returns:
            割り込みが保留中の場合True
        """
        return (self._reset_pending or 
                self._nmi_pending or 
                bool(self._irq_sources))
    
    def get_highest_priority_interrupt(self) -> Optional[InterruptType]:
        """最高優先度割り込み取得
        
        現在保留中の割り込みの中で最も優先度の高いものを取得します。
        
        Returns:
            最高優先度の割り込み種別（保留中の割り込みがない場合はNone）
        """
        pending_interrupts = []
        
        if self._reset_pending:
            pending_interrupts.append(InterruptType.RESET)
        
        if self._nmi_pending:
            pending_interrupts.append(InterruptType.NMI)
        
        if self._irq_sources:
            pending_interrupts.append(InterruptType.IRQ)
        
        if not pending_interrupts:
            return None
        
        # 優先度順でソート（数値が小さいほど高優先度）
        pending_interrupts.sort(key=lambda x: INTERRUPT_PRIORITY[x])
        
        return pending_interrupts[0]
    
    def acknowledge(self, interrupt_enabled: bool = True) -> Optional[InterruptVector]:
        """割り込み承認
        
        最高優先度の割り込みを承認し、対応する割り込みベクタ情報を返します。
        
        Args:
            interrupt_enabled: IRQ割り込み許可フラグ（I フラグの逆）
            
        Returns:
            割り込みベクタ情報（承認する割り込みがない場合はNone）
        """
        highest_priority = self.get_highest_priority_interrupt()
        
        if not highest_priority:
            return None
        
        # IRQは割り込み許可フラグをチェック
        if highest_priority == InterruptType.IRQ and not interrupt_enabled:
            return None
        
        # 割り込み承認処理
        vector_info = self._acknowledge_interrupt(highest_priority)
        
        # フック実行
        for hook in self._acknowledge_hooks:
            hook(highest_priority)
        
        return vector_info
    
    def get_interrupt_vector(self, interrupt_type: InterruptType) -> InterruptVector:
        """割り込みベクタ情報取得
        
        Args:
            interrupt_type: 割り込み種別
            
        Returns:
            割り込みベクタ情報
        """
        return {
            'vector_address': INTERRUPT_VECTORS[interrupt_type],
            'interrupt_type': interrupt_type,
            'cycles': INTERRUPT_CYCLES[interrupt_type]
        }
    
    def get_state(self) -> Dict[str, Any]:
        """割り込みコントローラ状態取得
        
        Returns:
            現在の状態情報
        """
        return {
            'current_state': self._current_state.name,
            'servicing_interrupt': self._servicing_interrupt.name if self._servicing_interrupt else None,
            'irq_sources': list(self._irq_sources),
            'nmi_pending': self._nmi_pending,
            'reset_pending': self._reset_pending,
            'interrupt_count': self._interrupt_count.copy(),
            'pending_interrupts': [
                intr.name for intr in self._get_all_pending_interrupts()
            ]
        }
    
    def get_interrupt_statistics(self) -> Dict[str, Any]:
        """割り込み統計取得
        
        Returns:
            割り込み統計情報
        """
        total_interrupts = sum(self._interrupt_count.values())
        
        return {
            'total_interrupts': total_interrupts,
            'interrupt_count_by_type': self._interrupt_count.copy(),
            'history_entries': len(self._interrupt_history),
            'current_state': self._current_state.name,
            'active_irq_sources': len(self._irq_sources)
        }
    
    def get_interrupt_history(self, last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """割り込み履歴取得
        
        Args:
            last_n: 取得する最新エントリ数（Noneの場合は全て）
            
        Returns:
            割り込み履歴のリスト
        """
        if not self._enable_history:
            return []
        
        history = self._interrupt_history
        if last_n is not None and last_n > 0:
            history = history[-last_n:]
        
        return [
            {
                'interrupt_type': req.interrupt_type.name,
                'source_id': req.source_id,
                'timestamp': req.timestamp,
                'priority': req.priority
            }
            for req in history
        ]
    
    def clear_interrupt_history(self) -> None:
        """割り込み履歴クリア"""
        self._interrupt_history.clear()
    
    def reset_statistics(self) -> None:
        """統計情報リセット"""
        self._interrupt_count = {
            InterruptType.RESET: 0,
            InterruptType.NMI: 0,
            InterruptType.IRQ: 0
        }
        self._interrupt_history.clear()
    
    def add_interrupt_hook(self, hook: Callable[[InterruptType, str], None]) -> None:
        """割り込みフック追加
        
        Args:
            hook: フック関数 (interrupt_type, source_id) -> None
        """
        self._interrupt_hooks.append(hook)
    
    def add_acknowledge_hook(self, hook: Callable[[InterruptType], None]) -> None:
        """割り込み承認フック追加
        
        Args:
            hook: フック関数 (interrupt_type) -> None
        """
        self._acknowledge_hooks.append(hook)
    
    def remove_interrupt_hook(self, hook: Callable[[InterruptType, str], None]) -> None:
        """割り込みフック削除"""
        if hook in self._interrupt_hooks:
            self._interrupt_hooks.remove(hook)
    
    def remove_acknowledge_hook(self, hook: Callable[[InterruptType], None]) -> None:
        """割り込み承認フック削除"""
        if hook in self._acknowledge_hooks:
            self._acknowledge_hooks.remove(hook)
    
    def enable_history(self, enabled: bool = True) -> None:
        """履歴機能の有効/無効切り替え"""
        self._enable_history = enabled
        if not enabled:
            self._interrupt_history.clear()
    
    def force_clear_all_interrupts(self) -> None:
        """全割り込み強制クリア（デバッグ用）"""
        self._irq_sources.clear()
        self._nmi_pending = False
        self._reset_pending = False
        self._current_state = InterruptState.IDLE
        self._servicing_interrupt = None
        self._nmi_previous_state = False
    
    def _handle_interrupt_request(self, interrupt_type: InterruptType, source_id: str) -> None:
        """割り込み要求処理"""
        # 統計更新
        self._interrupt_count[interrupt_type] += 1
        
        # 履歴記録
        if self._enable_history:
            self._record_interrupt_history(interrupt_type, source_id)
        
        # 状態更新
        if self._current_state == InterruptState.IDLE:
            self._current_state = InterruptState.PENDING
        
        # フック実行
        for hook in self._interrupt_hooks:
            hook(interrupt_type, source_id)
    
    def _acknowledge_interrupt(self, interrupt_type: InterruptType) -> InterruptVector:
        """割り込み承認処理"""
        # 割り込み要求クリア
        if interrupt_type == InterruptType.RESET:
            self._reset_pending = False
        elif interrupt_type == InterruptType.NMI:
            self._nmi_pending = False
        elif interrupt_type == InterruptType.IRQ:
            # IRQは全ソースをクリア（レベルトリガー）
            self._irq_sources.clear()
        
        # 状態更新
        self._current_state = InterruptState.SERVICING
        self._servicing_interrupt = interrupt_type
        
        # ベクタ情報生成
        return self.get_interrupt_vector(interrupt_type)
    
    def _record_interrupt_history(self, interrupt_type: InterruptType, source_id: str) -> None:
        """割り込み履歴記録"""
        # 履歴エントリ数制限
        if len(self._interrupt_history) >= self._max_history_entries:
            self._interrupt_history.pop(0)
        
        request = InterruptRequest(
            interrupt_type=interrupt_type,
            source_id=source_id,
            timestamp=time.time(),
            priority=INTERRUPT_PRIORITY[interrupt_type]
        )
        
        self._interrupt_history.append(request)
    
    def _get_all_pending_interrupts(self) -> List[InterruptType]:
        """保留中の全割り込み取得"""
        pending = []
        
        if self._reset_pending:
            pending.append(InterruptType.RESET)
        
        if self._nmi_pending:
            pending.append(InterruptType.NMI)
        
        if self._irq_sources:
            pending.append(InterruptType.IRQ)
        
        return pending
    
    def complete_interrupt_service(self) -> None:
        """割り込みサービス完了
        
        現在処理中の割り込みサービスが完了したことを通知します。
        RTI命令実行時などに呼び出されます。
        """
        self._current_state = InterruptState.IDLE
        self._servicing_interrupt = None
