"""
割り込みハンドラ
PU006: InterruptHandler

W65C02S CPUの割り込み処理ロジックを提供します。
7サイクル割り込みシーケンスの実装、割り込み優先度処理、RES/NMI/IRQ/BRKの処理を含みます。
"""

from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import time
import logging

from ..core.interrupt_types import InterruptType, InterruptVector, INTERRUPT_VECTORS, INTERRUPT_CYCLES
from ..core.interrupt_controller import InterruptController


class InterruptSequenceState(Enum):
    """割り込みシーケンス状態"""
    IDLE = auto()           # アイドル状態
    FETCH_VECTOR = auto()   # ベクタフェッチ
    PUSH_PCH = auto()       # PCH プッシュ
    PUSH_PCL = auto()       # PCL プッシュ
    PUSH_STATUS = auto()    # ステータスプッシュ
    SET_FLAGS = auto()      # フラグ設定
    LOAD_VECTOR = auto()    # ベクタロード
    JUMP_VECTOR = auto()    # ベクタジャンプ
    COMPLETED = auto()      # 完了


@dataclass
class InterruptSequence:
    """割り込みシーケンス管理
    
    W65C02Sの7サイクル割り込みシーケンスを管理します。
    """
    interrupt_type: InterruptType
    vector_address: int
    current_cycle: int = 0
    total_cycles: int = 7
    state: InterruptSequenceState = InterruptSequenceState.IDLE
    
    # CPU状態保存
    saved_pc: int = 0
    saved_status: int = 0
    
    # シーケンス実行履歴
    cycle_history: List[Tuple[int, InterruptSequenceState, str]] = field(default_factory=list)
    
    def is_completed(self) -> bool:
        """シーケンス完了チェック"""
        return self.state == InterruptSequenceState.COMPLETED
    
    def get_progress_percent(self) -> float:
        """進行率取得"""
        if self.total_cycles == 0:
            return 100.0
        return (self.current_cycle / self.total_cycles) * 100.0


@dataclass
class InterruptContext:
    """割り込みコンテキスト
    
    割り込み処理中のCPU状態とコンテキスト情報を管理します。
    """
    interrupt_type: InterruptType
    source_id: str
    start_cycle: int
    start_timestamp_ns: int
    
    # CPU状態
    pc_before: int = 0
    status_before: int = 0
    stack_pointer_before: int = 0
    
    # 割り込み処理状態
    vector_fetched: bool = False
    context_saved: bool = False
    flags_set: bool = False
    
    # 統計情報
    total_cycles_taken: int = 0
    actual_execution_time_ns: int = 0
    
    def get_duration_ns(self) -> int:
        """実行時間取得（ナノ秒）"""
        return time.time_ns() - self.start_timestamp_ns


class InterruptHandler:
    """割り込みハンドラ
    
    W65C02S CPUの割り込み処理を管理し、
    7サイクル割り込みシーケンスの実行を制御します。
    """
    
    def __init__(self, interrupt_controller: InterruptController):
        """割り込みハンドラを初期化
        
        Args:
            interrupt_controller: 割り込みコントローラ
        """
        self._interrupt_controller = interrupt_controller
        
        # 現在の割り込み処理
        self._current_sequence: Optional[InterruptSequence] = None
        self._current_context: Optional[InterruptContext] = None
        
        # 割り込み処理履歴
        self._interrupt_history: List[InterruptContext] = []
        self._max_history_entries = 100
        
        # CPU状態アクセス（外部から設定される）
        self._cpu_state_accessor: Optional[Callable[[], Dict[str, Any]]] = None
        self._cpu_state_modifier: Optional[Callable[[Dict[str, Any]], None]] = None
        self._memory_accessor: Optional[Callable[[int], int]] = None
        self._memory_modifier: Optional[Callable[[int, int], None]] = None
        
        # 統計情報
        self._interrupt_stats: Dict[InterruptType, Dict[str, Any]] = {
            interrupt_type: {
                'total_count': 0,
                'total_cycles': 0,
                'total_time_ns': 0,
                'average_cycles': 0.0,
                'average_time_ns': 0.0,
                'min_cycles': float('inf'),
                'max_cycles': 0,
                'last_execution_cycles': 0
            }
            for interrupt_type in InterruptType
        }
        
        # フック
        self._pre_interrupt_hooks: List[Callable[[InterruptType, str], None]] = []
        self._post_interrupt_hooks: List[Callable[[InterruptType, int], None]] = []
        self._sequence_step_hooks: List[Callable[[InterruptSequenceState, int], None]] = []
        
        self._logger = logging.getLogger(__name__)
    
    def set_cpu_accessors(
        self,
        state_accessor: Callable[[], Dict[str, Any]],
        state_modifier: Callable[[Dict[str, Any]], None],
        memory_accessor: Callable[[int], int],
        memory_modifier: Callable[[int, int], None]
    ) -> None:
        """CPU状態アクセサ設定
        
        Args:
            state_accessor: CPU状態取得関数
            state_modifier: CPU状態変更関数
            memory_accessor: メモリ読み取り関数
            memory_modifier: メモリ書き込み関数
        """
        self._cpu_state_accessor = state_accessor
        self._cpu_state_modifier = state_modifier
        self._memory_accessor = memory_accessor
        self._memory_modifier = memory_modifier
    
    def check_and_handle_interrupts(self, current_cycle: int) -> bool:
        """割り込みチェックと処理
        
        Args:
            current_cycle: 現在のサイクル数
            
        Returns:
            割り込み処理を開始した場合True
        """
        # 既に割り込み処理中の場合は継続
        if self._current_sequence is not None:
            return self._continue_interrupt_sequence(current_cycle)
        
        # 新しい割り込みチェック
        if not self._interrupt_controller.is_pending():
            return False
        
        # CPU状態取得
        if not self._cpu_state_accessor:
            self._logger.error("CPU state accessor not set")
            return False
        
        cpu_state = self._cpu_state_accessor()
        interrupt_enabled = not cpu_state.get('interrupt_disable_flag', False)
        
        # 割り込み承認
        vector_info = self._interrupt_controller.acknowledge(interrupt_enabled)
        if vector_info is None:
            return False
        
        # 割り込み処理開始
        return self._start_interrupt_sequence(vector_info, current_cycle)
    
    def force_interrupt(self, interrupt_type: InterruptType, source_id: str = "forced") -> bool:
        """強制割り込み実行
        
        Args:
            interrupt_type: 割り込み種別
            source_id: 割り込みソースID
            
        Returns:
            割り込み処理を開始した場合True
        """
        if self._current_sequence is not None:
            self._logger.warning("Interrupt already in progress, cannot force new interrupt")
            return False
        
        # ベクタ情報作成
        vector_info = {
            'vector_address': INTERRUPT_VECTORS[interrupt_type],
            'interrupt_type': interrupt_type,
            'cycles': INTERRUPT_CYCLES[interrupt_type]
        }
        
        return self._start_interrupt_sequence(vector_info, 0, source_id)
    
    def is_interrupt_in_progress(self) -> bool:
        """割り込み処理中チェック"""
        return self._current_sequence is not None
    
    def get_current_interrupt_info(self) -> Optional[Dict[str, Any]]:
        """現在の割り込み情報取得"""
        if self._current_sequence is None or self._current_context is None:
            return None
        
        return {
            'interrupt_type': self._current_sequence.interrupt_type.name,
            'source_id': self._current_context.source_id,
            'current_cycle': self._current_sequence.current_cycle,
            'total_cycles': self._current_sequence.total_cycles,
            'state': self._current_sequence.state.name,
            'progress_percent': self._current_sequence.get_progress_percent(),
            'vector_address': self._current_sequence.vector_address
        }
    
    def get_interrupt_statistics(self) -> Dict[str, Any]:
        """割り込み統計取得"""
        return {
            'interrupt_stats': self._interrupt_stats.copy(),
            'history_count': len(self._interrupt_history),
            'current_interrupt': self.get_current_interrupt_info(),
            'controller_stats': self._interrupt_controller.get_interrupt_statistics()
        }
    
    def get_interrupt_history(self, last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """割り込み履歴取得
        
        Args:
            last_n: 取得する最新エントリ数
            
        Returns:
            割り込み履歴のリスト
        """
        history = self._interrupt_history
        if last_n is not None and last_n > 0:
            history = history[-last_n:]
        
        return [
            {
                'interrupt_type': ctx.interrupt_type.name,
                'source_id': ctx.source_id,
                'start_cycle': ctx.start_cycle,
                'total_cycles_taken': ctx.total_cycles_taken,
                'execution_time_ns': ctx.actual_execution_time_ns,
                'pc_before': ctx.pc_before,
                'status_before': ctx.status_before
            }
            for ctx in history
        ]
    
    def add_pre_interrupt_hook(self, hook: Callable[[InterruptType, str], None]) -> None:
        """割り込み前フック追加"""
        self._pre_interrupt_hooks.append(hook)
    
    def add_post_interrupt_hook(self, hook: Callable[[InterruptType, int], None]) -> None:
        """割り込み後フック追加"""
        self._post_interrupt_hooks.append(hook)
    
    def add_sequence_step_hook(self, hook: Callable[[InterruptSequenceState, int], None]) -> None:
        """シーケンスステップフック追加"""
        self._sequence_step_hooks.append(hook)
    
    def reset_statistics(self) -> None:
        """統計リセット"""
        for stats in self._interrupt_stats.values():
            stats.update({
                'total_count': 0,
                'total_cycles': 0,
                'total_time_ns': 0,
                'average_cycles': 0.0,
                'average_time_ns': 0.0,
                'min_cycles': float('inf'),
                'max_cycles': 0,
                'last_execution_cycles': 0
            })
        
        self._interrupt_history.clear()
    
    def _start_interrupt_sequence(
        self, 
        vector_info: InterruptVector, 
        current_cycle: int, 
        source_id: str = "unknown"
    ) -> bool:
        """割り込みシーケンス開始"""
        try:
            interrupt_type = vector_info['interrupt_type']
            vector_address = vector_info['vector_address']
            
            # CPU状態取得
            cpu_state = self._cpu_state_accessor()
            
            # 割り込みシーケンス作成
            self._current_sequence = InterruptSequence(
                interrupt_type=interrupt_type,
                vector_address=vector_address,
                total_cycles=vector_info['cycles'],
                saved_pc=cpu_state.get('program_counter', 0),
                saved_status=cpu_state.get('status_register', 0)
            )
            
            # 割り込みコンテキスト作成
            self._current_context = InterruptContext(
                interrupt_type=interrupt_type,
                source_id=source_id,
                start_cycle=current_cycle,
                start_timestamp_ns=time.time_ns(),
                pc_before=cpu_state.get('program_counter', 0),
                status_before=cpu_state.get('status_register', 0),
                stack_pointer_before=cpu_state.get('stack_pointer', 0xFF)
            )
            
            # プリ割り込みフック実行
            for hook in self._pre_interrupt_hooks:
                hook(interrupt_type, source_id)
            
            self._logger.info(
                f"Interrupt sequence started: {interrupt_type.name} "
                f"from {source_id} at cycle {current_cycle}"
            )
            
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to start interrupt sequence: {e}")
            self._current_sequence = None
            self._current_context = None
            return False
    
    def _continue_interrupt_sequence(self, current_cycle: int) -> bool:
        """割り込みシーケンス継続"""
        if self._current_sequence is None or self._current_context is None:
            return False
        
        try:
            # シーケンスステップ実行
            step_completed = self._execute_sequence_step(current_cycle)
            
            if step_completed:
                self._current_sequence.current_cycle += 1
                
                # シーケンス完了チェック
                if self._current_sequence.is_completed():
                    self._complete_interrupt_sequence(current_cycle)
                    return False  # 割り込み処理完了
            
            return True  # 継続中
            
        except Exception as e:
            self._logger.error(f"Interrupt sequence execution error: {e}")
            self._abort_interrupt_sequence()
            return False
    
    def _execute_sequence_step(self, current_cycle: int) -> bool:
        """シーケンスステップ実行
        
        Returns:
            ステップが完了した場合True
        """
        sequence = self._current_sequence
        context = self._current_context
        
        # 現在のサイクルに基づいてステート決定
        cycle_in_sequence = sequence.current_cycle
        
        if cycle_in_sequence == 0:
            # サイクル1: ベクタフェッチ開始
            sequence.state = InterruptSequenceState.FETCH_VECTOR
            action = "Fetch interrupt vector"
            
        elif cycle_in_sequence == 1:
            # サイクル2: PCH をスタックにプッシュ
            sequence.state = InterruptSequenceState.PUSH_PCH
            action = self._push_pch_to_stack()
            
        elif cycle_in_sequence == 2:
            # サイクル3: PCL をスタックにプッシュ
            sequence.state = InterruptSequenceState.PUSH_PCL
            action = self._push_pcl_to_stack()
            
        elif cycle_in_sequence == 3:
            # サイクル4: ステータスレジスタをスタックにプッシュ
            sequence.state = InterruptSequenceState.PUSH_STATUS
            action = self._push_status_to_stack()
            
        elif cycle_in_sequence == 4:
            # サイクル5: 割り込みフラグ設定
            sequence.state = InterruptSequenceState.SET_FLAGS
            action = self._set_interrupt_flags()
            
        elif cycle_in_sequence == 5:
            # サイクル6: ベクタアドレスからPCL読み込み
            sequence.state = InterruptSequenceState.LOAD_VECTOR
            action = self._load_vector_low()
            
        elif cycle_in_sequence == 6:
            # サイクル7: ベクタアドレス+1からPCH読み込み、ジャンプ
            sequence.state = InterruptSequenceState.JUMP_VECTOR
            action = self._load_vector_high_and_jump()
            sequence.state = InterruptSequenceState.COMPLETED
            
        else:
            action = "Invalid cycle"
        
        # 履歴記録
        sequence.cycle_history.append((cycle_in_sequence, sequence.state, action))
        
        # フック実行
        for hook in self._sequence_step_hooks:
            hook(sequence.state, current_cycle)
        
        return True
    
    def _push_pch_to_stack(self) -> str:
        """PCH をスタックにプッシュ"""
        if not self._cpu_state_accessor or not self._cpu_state_modifier or not self._memory_modifier:
            return "CPU accessors not available"
        
        cpu_state = self._cpu_state_accessor()
        stack_pointer = cpu_state.get('stack_pointer', 0xFF)
        pc = self._current_sequence.saved_pc
        
        # PCH (上位バイト) をスタックに書き込み
        pch = (pc >> 8) & 0xFF
        stack_address = 0x0100 + stack_pointer
        self._memory_modifier(stack_address, pch)
        
        # スタックポインタデクリメント
        stack_pointer = (stack_pointer - 1) & 0xFF
        cpu_state['stack_pointer'] = stack_pointer
        self._cpu_state_modifier(cpu_state)
        
        return f"Pushed PCH (${pch:02X}) to stack at ${stack_address:04X}"
    
    def _push_pcl_to_stack(self) -> str:
        """PCL をスタックにプッシュ"""
        if not self._cpu_state_accessor or not self._cpu_state_modifier or not self._memory_modifier:
            return "CPU accessors not available"
        
        cpu_state = self._cpu_state_accessor()
        stack_pointer = cpu_state.get('stack_pointer', 0xFF)
        pc = self._current_sequence.saved_pc
        
        # PCL (下位バイト) をスタックに書き込み
        pcl = pc & 0xFF
        stack_address = 0x0100 + stack_pointer
        self._memory_modifier(stack_address, pcl)
        
        # スタックポインタデクリメント
        stack_pointer = (stack_pointer - 1) & 0xFF
        cpu_state['stack_pointer'] = stack_pointer
        self._cpu_state_modifier(cpu_state)
        
        return f"Pushed PCL (${pcl:02X}) to stack at ${stack_address:04X}"
    
    def _push_status_to_stack(self) -> str:
        """ステータスレジスタをスタックにプッシュ"""
        if not self._cpu_state_accessor or not self._cpu_state_modifier or not self._memory_modifier:
            return "CPU accessors not available"
        
        cpu_state = self._cpu_state_accessor()
        stack_pointer = cpu_state.get('stack_pointer', 0xFF)
        status = self._current_sequence.saved_status
        
        # ステータスレジスタをスタックに書き込み
        # BRK命令の場合はBフラグをセット、それ以外はクリア
        if self._current_sequence.interrupt_type == InterruptType.IRQ:
            # BRK命令かIRQかの判別は実装依存
            status_to_push = status & 0xEF  # Bフラグクリア（IRQの場合）
        else:
            status_to_push = status
        
        stack_address = 0x0100 + stack_pointer
        self._memory_modifier(stack_address, status_to_push)
        
        # スタックポインタデクリメント
        stack_pointer = (stack_pointer - 1) & 0xFF
        cpu_state['stack_pointer'] = stack_pointer
        self._cpu_state_modifier(cpu_state)
        
        self._current_context.context_saved = True
        
        return f"Pushed status (${status_to_push:02X}) to stack at ${stack_address:04X}"
    
    def _set_interrupt_flags(self) -> str:
        """割り込みフラグ設定"""
        if not self._cpu_state_accessor or not self._cpu_state_modifier:
            return "CPU accessors not available"
        
        cpu_state = self._cpu_state_accessor()
        status = cpu_state.get('status_register', 0)
        
        # 割り込み禁止フラグ (I) をセット
        status |= 0x04  # I フラグセット
        
        # デシマルモードフラグ (D) をクリア（W65C02Sの場合）
        status &= 0xF7  # D フラグクリア
        
        cpu_state['status_register'] = status
        self._cpu_state_modifier(cpu_state)
        
        self._current_context.flags_set = True
        
        return f"Set interrupt flags: I=1, D=0 (status=${status:02X})"
    
    def _load_vector_low(self) -> str:
        """ベクタ下位バイト読み込み"""
        if not self._memory_accessor:
            return "Memory accessor not available"
        
        vector_address = self._current_sequence.vector_address
        vector_low = self._memory_accessor(vector_address)
        
        # 一時的に保存（次のサイクルで使用）
        self._current_sequence.saved_pc = (self._current_sequence.saved_pc & 0xFF00) | vector_low
        
        return f"Loaded vector low byte (${vector_low:02X}) from ${vector_address:04X}"
    
    def _load_vector_high_and_jump(self) -> str:
        """ベクタ上位バイト読み込みとジャンプ"""
        if not self._memory_accessor or not self._cpu_state_accessor or not self._cpu_state_modifier:
            return "CPU/Memory accessors not available"
        
        vector_address = self._current_sequence.vector_address + 1
        vector_high = self._memory_accessor(vector_address)
        
        # 新しいPC計算
        new_pc = (vector_high << 8) | (self._current_sequence.saved_pc & 0xFF)
        
        # PCを新しいアドレスに設定
        cpu_state = self._cpu_state_accessor()
        cpu_state['program_counter'] = new_pc
        self._cpu_state_modifier(cpu_state)
        
        self._current_context.vector_fetched = True
        
        return f"Loaded vector high byte (${vector_high:02X}), jumped to ${new_pc:04X}"
    
    def _complete_interrupt_sequence(self, current_cycle: int) -> None:
        """割り込みシーケンス完了"""
        if self._current_sequence is None or self._current_context is None:
            return
        
        # 統計更新
        interrupt_type = self._current_sequence.interrupt_type
        cycles_taken = self._current_sequence.current_cycle + 1
        execution_time_ns = self._current_context.get_duration_ns()
        
        self._current_context.total_cycles_taken = cycles_taken
        self._current_context.actual_execution_time_ns = execution_time_ns
        
        # 統計情報更新
        stats = self._interrupt_stats[interrupt_type]
        stats['total_count'] += 1
        stats['total_cycles'] += cycles_taken
        stats['total_time_ns'] += execution_time_ns
        stats['last_execution_cycles'] = cycles_taken
        
        # 平均値更新
        stats['average_cycles'] = stats['total_cycles'] / stats['total_count']
        stats['average_time_ns'] = stats['total_time_ns'] / stats['total_count']
        
        # 最小・最大値更新
        stats['min_cycles'] = min(stats['min_cycles'], cycles_taken)
        stats['max_cycles'] = max(stats['max_cycles'], cycles_taken)
        
        # 履歴に追加
        if len(self._interrupt_history) >= self._max_history_entries:
            self._interrupt_history.pop(0)
        self._interrupt_history.append(self._current_context)
        
        # ポスト割り込みフック実行
        for hook in self._post_interrupt_hooks:
            hook(interrupt_type, cycles_taken)
        
        # 割り込みコントローラに完了通知
        self._interrupt_controller.complete_interrupt_service()
        
        self._logger.info(
            f"Interrupt sequence completed: {interrupt_type.name} "
            f"in {cycles_taken} cycles ({execution_time_ns/1000:.1f} μs)"
        )
        
        # クリーンアップ
        self._current_sequence = None
        self._current_context = None
    
    def _abort_interrupt_sequence(self) -> None:
        """割り込みシーケンス中断"""
        if self._current_sequence is not None:
            self._logger.error(
                f"Interrupt sequence aborted: {self._current_sequence.interrupt_type.name}"
            )
        
        self._current_sequence = None
        self._current_context = None
