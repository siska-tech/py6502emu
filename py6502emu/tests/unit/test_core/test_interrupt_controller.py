"""
InterruptController テスト

割り込み優先度制御、割り込み要求・承認処理、
複数割り込み同時処理のテストを提供します。
"""

import pytest
from unittest.mock import Mock, patch
import time
from py6502emu.core.interrupt_controller import (
    InterruptController,
    InterruptState,
    InterruptRequest
)
from py6502emu.core.interrupt_types import (
    InterruptType,
    INTERRUPT_VECTORS,
    INTERRUPT_CYCLES,
    INTERRUPT_PRIORITY
)


class TestInterruptRequest:
    """InterruptRequest クラステスト"""
    
    def test_interrupt_request_creation(self):
        """割り込み要求作成テスト"""
        request = InterruptRequest(
            interrupt_type=InterruptType.IRQ,
            source_id="timer",
            timestamp=time.time(),
            priority=3
        )
        
        assert request.interrupt_type == InterruptType.IRQ
        assert request.source_id == "timer"
        assert request.priority == 3
        assert request.timestamp > 0
    
    def test_interrupt_request_invalid_priority(self):
        """無効優先度テスト"""
        with pytest.raises(ValueError, match="Priority must be positive"):
            InterruptRequest(
                interrupt_type=InterruptType.IRQ,
                source_id="test",
                timestamp=time.time(),
                priority=0
            )


class TestInterruptController:
    """InterruptController クラステスト"""
    
    def setup_method(self):
        """各テストメソッド前の初期化"""
        self.controller = InterruptController()
    
    def test_initialization(self):
        """初期化テスト"""
        assert len(self.controller._irq_sources) == 0
        assert not self.controller._nmi_pending
        assert not self.controller._reset_pending
        assert self.controller._current_state == InterruptState.IDLE
        assert self.controller._servicing_interrupt is None
        
        # 統計初期化確認
        for interrupt_type in InterruptType:
            assert self.controller._interrupt_count[interrupt_type] == 0
    
    def test_irq_assert_deassert(self):
        """IRQ要求アサート・デアサートテスト"""
        # IRQ要求なし
        assert not self.controller.is_pending()
        assert self.controller.get_highest_priority_interrupt() is None
        
        # IRQ要求アサート
        self.controller.assert_irq("timer")
        assert self.controller.is_pending()
        assert self.controller.get_highest_priority_interrupt() == InterruptType.IRQ
        assert "timer" in self.controller._irq_sources
        
        # 同じソースから再度アサート（重複なし）
        self.controller.assert_irq("timer")
        assert len(self.controller._irq_sources) == 1
        
        # 別ソースからアサート
        self.controller.assert_irq("uart")
        assert len(self.controller._irq_sources) == 2
        assert "uart" in self.controller._irq_sources
        
        # 一つのソースをデアサート
        self.controller.deassert_irq("timer")
        assert len(self.controller._irq_sources) == 1
        assert "timer" not in self.controller._irq_sources
        assert "uart" in self.controller._irq_sources
        assert self.controller.is_pending()  # まだuartが残っている
        
        # 全ソースをデアサート
        self.controller.deassert_irq("uart")
        assert len(self.controller._irq_sources) == 0
        assert not self.controller.is_pending()
    
    def test_nmi_assert_deassert(self):
        """NMI要求アサート・デアサートテスト"""
        # NMI要求なし
        assert not self.controller._nmi_pending
        assert not self.controller.is_pending()
        
        # NMI要求アサート（エッジトリガー）
        self.controller.assert_nmi("system")
        assert self.controller._nmi_pending
        assert self.controller.is_pending()
        assert self.controller.get_highest_priority_interrupt() == InterruptType.NMI
        
        # 同じNMI信号を再度アサート（エッジトリガーなので無効）
        self.controller.assert_nmi("system")
        assert self.controller._nmi_pending  # 状態変わらず
        
        # NMI信号をデアサート
        self.controller.deassert_nmi()
        assert not self.controller._nmi_previous_state
        # NMI要求は承認されるまで保留状態
        assert self.controller._nmi_pending
        
        # 再度NMIアサート（立ち上がりエッジ）
        self.controller.assert_nmi("system2")
        # 既にNMI保留中なので新しい要求は無視される
        assert self.controller._nmi_pending
    
    def test_reset_assert_deassert(self):
        """リセット要求アサート・デアサートテスト"""
        # リセット要求なし
        assert not self.controller._reset_pending
        
        # リセット要求アサート
        self.controller.assert_reset("power_on")
        assert self.controller._reset_pending
        assert self.controller.is_pending()
        assert self.controller.get_highest_priority_interrupt() == InterruptType.RESET
        
        # リセット要求デアサート
        self.controller.deassert_reset()
        assert not self.controller._reset_pending
    
    def test_interrupt_priority(self):
        """割り込み優先度テスト"""
        # 全ての割り込みを同時にアサート
        self.controller.assert_reset("system")
        self.controller.assert_nmi("system")
        self.controller.assert_irq("timer")
        
        # 最高優先度はRESET
        assert self.controller.get_highest_priority_interrupt() == InterruptType.RESET
        
        # RESETを承認
        vector = self.controller.acknowledge()
        assert vector['interrupt_type'] == InterruptType.RESET
        assert not self.controller._reset_pending
        
        # 次の最高優先度はNMI
        assert self.controller.get_highest_priority_interrupt() == InterruptType.NMI
        
        # NMIを承認
        vector = self.controller.acknowledge()
        assert vector['interrupt_type'] == InterruptType.NMI
        assert not self.controller._nmi_pending
        
        # 最後はIRQ
        assert self.controller.get_highest_priority_interrupt() == InterruptType.IRQ
        
        # IRQを承認（割り込み許可状態）
        vector = self.controller.acknowledge(interrupt_enabled=True)
        assert vector['interrupt_type'] == InterruptType.IRQ
        assert len(self.controller._irq_sources) == 0
    
    def test_irq_interrupt_disabled(self):
        """IRQ割り込み禁止状態テスト"""
        self.controller.assert_irq("timer")
        
        # 割り込み禁止状態での承認試行
        vector = self.controller.acknowledge(interrupt_enabled=False)
        assert vector is None  # IRQは承認されない
        assert len(self.controller._irq_sources) == 1  # 要求は残る
        
        # 割り込み許可状態での承認
        vector = self.controller.acknowledge(interrupt_enabled=True)
        assert vector is not None
        assert vector['interrupt_type'] == InterruptType.IRQ
    
    def test_nmi_reset_always_acknowledged(self):
        """NMI・RESETは常に承認されることのテスト"""
        # NMI
        self.controller.assert_nmi("system")
        vector = self.controller.acknowledge(interrupt_enabled=False)
        assert vector is not None
        assert vector['interrupt_type'] == InterruptType.NMI
        
        # RESET
        self.controller.assert_reset("system")
        vector = self.controller.acknowledge(interrupt_enabled=False)
        assert vector is not None
        assert vector['interrupt_type'] == InterruptType.RESET
    
    def test_interrupt_vector_information(self):
        """割り込みベクタ情報テスト"""
        for interrupt_type in InterruptType:
            vector = self.controller.get_interrupt_vector(interrupt_type)
            
            assert vector['interrupt_type'] == interrupt_type
            assert vector['vector_address'] == INTERRUPT_VECTORS[interrupt_type]
            assert vector['cycles'] == INTERRUPT_CYCLES[interrupt_type]
    
    def test_interrupt_state_management(self):
        """割り込み状態管理テスト"""
        # 初期状態
        assert self.controller._current_state == InterruptState.IDLE
        
        # 割り込み要求
        self.controller.assert_irq("timer")
        assert self.controller._current_state == InterruptState.PENDING
        
        # 割り込み承認
        self.controller.acknowledge(interrupt_enabled=True)
        assert self.controller._current_state == InterruptState.SERVICING
        assert self.controller._servicing_interrupt == InterruptType.IRQ
        
        # 割り込みサービス完了
        self.controller.complete_interrupt_service()
        assert self.controller._current_state == InterruptState.IDLE
        assert self.controller._servicing_interrupt is None
    
    def test_interrupt_statistics(self):
        """割り込み統計テスト"""
        # 各種割り込み実行
        self.controller.assert_reset("power_on")
        self.controller.acknowledge()
        
        self.controller.assert_nmi("watchdog")
        self.controller.acknowledge()
        
        self.controller.assert_irq("timer")
        self.controller.acknowledge(interrupt_enabled=True)
        
        self.controller.assert_irq("uart")
        self.controller.acknowledge(interrupt_enabled=True)
        
        # 統計確認
        stats = self.controller.get_interrupt_statistics()
        assert stats['total_interrupts'] == 4
        assert stats['interrupt_count_by_type'][InterruptType.RESET] == 1
        assert stats['interrupt_count_by_type'][InterruptType.NMI] == 1
        assert stats['interrupt_count_by_type'][InterruptType.IRQ] == 2
    
    def test_interrupt_history(self):
        """割り込み履歴テスト"""
        # 履歴有効化
        self.controller.enable_history(True)
        
        # 割り込み実行
        self.controller.assert_irq("timer")
        self.controller.assert_nmi("watchdog")
        
        # 履歴確認
        history = self.controller.get_interrupt_history()
        assert len(history) == 2
        
        irq_entry = next(h for h in history if h['interrupt_type'] == 'IRQ')
        assert irq_entry['source_id'] == 'timer'
        assert irq_entry['priority'] == INTERRUPT_PRIORITY[InterruptType.IRQ]
        
        nmi_entry = next(h for h in history if h['interrupt_type'] == 'NMI')
        assert nmi_entry['source_id'] == 'watchdog'
        assert nmi_entry['priority'] == INTERRUPT_PRIORITY[InterruptType.NMI]
        
        # 履歴制限テスト
        original_limit = self.controller._max_history_entries
        self.controller._max_history_entries = 2
        
        try:
            # 制限を超える履歴
            for i in range(5):
                self.controller.assert_irq(f"source_{i}")
            
            history = self.controller.get_interrupt_history()
            assert len(history) == 2  # 制限内
            
        finally:
            self.controller._max_history_entries = original_limit
    
    def test_interrupt_history_disabled(self):
        """割り込み履歴無効化テスト"""
        # 履歴無効化
        self.controller.enable_history(False)
        
        # 割り込み実行
        self.controller.assert_irq("timer")
        
        # 履歴が記録されないことを確認
        history = self.controller.get_interrupt_history()
        assert len(history) == 0
    
    def test_interrupt_hooks(self):
        """割り込みフックテスト"""
        interrupt_hook_calls = []
        acknowledge_hook_calls = []
        
        def interrupt_hook(interrupt_type, source_id):
            interrupt_hook_calls.append((interrupt_type, source_id))
        
        def acknowledge_hook(interrupt_type):
            acknowledge_hook_calls.append(interrupt_type)
        
        # フック追加
        self.controller.add_interrupt_hook(interrupt_hook)
        self.controller.add_acknowledge_hook(acknowledge_hook)
        
        # 割り込み実行
        self.controller.assert_irq("timer")
        self.controller.acknowledge(interrupt_enabled=True)
        
        # フック呼び出し確認
        assert len(interrupt_hook_calls) == 1
        assert interrupt_hook_calls[0] == (InterruptType.IRQ, "timer")
        
        assert len(acknowledge_hook_calls) == 1
        assert acknowledge_hook_calls[0] == InterruptType.IRQ
        
        # フック削除
        self.controller.remove_interrupt_hook(interrupt_hook)
        self.controller.remove_acknowledge_hook(acknowledge_hook)
        
        # 新しい割り込み
        self.controller.assert_nmi("system")
        self.controller.acknowledge()
        
        # フック呼び出しされないことを確認
        assert len(interrupt_hook_calls) == 1
        assert len(acknowledge_hook_calls) == 1
    
    def test_get_state(self):
        """状態取得テスト"""
        # 複数の割り込み要求
        self.controller.assert_irq("timer")
        self.controller.assert_irq("uart")
        self.controller.assert_nmi("watchdog")
        
        state = self.controller.get_state()
        
        assert state['current_state'] == 'PENDING'
        assert state['servicing_interrupt'] is None
        assert set(state['irq_sources']) == {'timer', 'uart'}
        assert state['nmi_pending'] is True
        assert state['reset_pending'] is False
        assert 'NMI' in state['pending_interrupts']
        assert 'IRQ' in state['pending_interrupts']
    
    def test_force_clear_all_interrupts(self):
        """全割り込み強制クリアテスト"""
        # 全種類の割り込み要求
        self.controller.assert_reset("system")
        self.controller.assert_nmi("watchdog")
        self.controller.assert_irq("timer")
        self.controller.assert_irq("uart")
        
        assert self.controller.is_pending()
        
        # 強制クリア
        self.controller.force_clear_all_interrupts()
        
        # 全てクリアされることを確認
        assert not self.controller.is_pending()
        assert len(self.controller._irq_sources) == 0
        assert not self.controller._nmi_pending
        assert not self.controller._reset_pending
        assert self.controller._current_state == InterruptState.IDLE
        assert self.controller._servicing_interrupt is None
    
    def test_multiple_irq_sources(self):
        """複数IRQソーステスト"""
        sources = ["timer", "uart", "keyboard", "disk"]
        
        # 複数ソースからIRQ要求
        for source in sources:
            self.controller.assert_irq(source)
        
        assert len(self.controller._irq_sources) == len(sources)
        assert self.controller.is_pending()
        
        # IRQ承認（全ソースがクリアされる）
        vector = self.controller.acknowledge(interrupt_enabled=True)
        assert vector['interrupt_type'] == InterruptType.IRQ
        assert len(self.controller._irq_sources) == 0
        
        # 個別にデアサート（既にクリアされているので効果なし）
        for source in sources:
            self.controller.deassert_irq(source)
        
        assert len(self.controller._irq_sources) == 0
    
    def test_nmi_edge_detection(self):
        """NMIエッジ検出テスト"""
        # 初期状態でNMIアサート
        self.controller.assert_nmi("test")
        assert self.controller._nmi_pending
        
        # NMI承認
        self.controller.acknowledge()
        assert not self.controller._nmi_pending
        
        # NMI信号がアサート状態のまま再度アサート（エッジなし）
        self.controller.assert_nmi("test")
        assert not self.controller._nmi_pending  # 新しい要求なし
        
        # NMI信号をデアサート
        self.controller.deassert_nmi()
        
        # 再度アサート（立ち上がりエッジ）
        self.controller.assert_nmi("test")
        assert self.controller._nmi_pending  # 新しい要求
    
    def test_empty_source_id_validation(self):
        """空のソースID検証テスト"""
        with pytest.raises(ValueError, match="Source ID cannot be empty"):
            self.controller.assert_irq("")
    
    def test_statistics_reset(self):
        """統計リセットテスト"""
        # 履歴有効化
        self.controller.enable_history(True)
        
        # 割り込み実行
        self.controller.assert_irq("timer")
        self.controller.assert_nmi("watchdog")
        
        # 統計・履歴確認
        stats = self.controller.get_interrupt_statistics()
        assert stats['total_interrupts'] > 0
        assert len(self.controller.get_interrupt_history()) > 0
        
        # リセット
        self.controller.reset_statistics()
        
        # リセット後確認
        stats = self.controller.get_interrupt_statistics()
        assert stats['total_interrupts'] == 0
        for interrupt_type in InterruptType:
            assert stats['interrupt_count_by_type'][interrupt_type] == 0
        assert len(self.controller.get_interrupt_history()) == 0
    
    def test_no_pending_interrupts_acknowledge(self):
        """保留中割り込みなしでの承認テスト"""
        # 保留中の割り込みなし
        assert not self.controller.is_pending()
        
        # 承認試行
        vector = self.controller.acknowledge(interrupt_enabled=True)
        assert vector is None
        
        # 状態変化なし
        assert self.controller._current_state == InterruptState.IDLE
