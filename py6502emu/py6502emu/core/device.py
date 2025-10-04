"""
統一デバイスプロトコル実装
PU019: DeviceProtocol

W65C02S エミュレータで使用される全デバイスが準拠すべき統一プロトコルを定義します。
"""

from typing import Protocol, Dict, Any, Optional, runtime_checkable
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DeviceConfig:
    """デバイス設定基底クラス"""
    device_id: str
    name: str = ""
    
    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.device_id


@runtime_checkable
class Device(Protocol):
    """統一デバイスプロトコル
    
    全てのエミュレートされるデバイスが実装すべき基本インターフェイス。
    CPUやメモリ、I/Oデバイスなど、システム内の全コンポーネントが
    このプロトコルに準拠することで統一的な管理が可能になります。
    """
    
    @property
    def name(self) -> str:
        """デバイス名を取得
        
        Returns:
            str: デバイスの識別名
        """
        ...
    
    def reset(self) -> None:
        """デバイスリセット
        
        デバイスを初期状態にリセットします。
        システム起動時やリセット信号受信時に呼び出されます。
        """
        ...
    
    def tick(self, master_cycles: int) -> int:
        """時間進行処理
        
        マスタークロックサイクルに基づいてデバイスの状態を更新します。
        
        Args:
            master_cycles: 経過したマスタークロックサイクル数
            
        Returns:
            int: デバイスが消費したサイクル数
        """
        ...
    
    def read(self, address: int) -> int:
        """メモリ読み取り
        
        指定されたアドレスからデータを読み取ります。
        
        Args:
            address: 読み取りアドレス (0x0000-0xFFFF)
            
        Returns:
            int: 読み取った値 (0x00-0xFF)
            
        Raises:
            InvalidAddressError: 無効なアドレスが指定された場合
        """
        ...
    
    def write(self, address: int, value: int) -> None:
        """メモリ書き込み
        
        指定されたアドレスにデータを書き込みます。
        
        Args:
            address: 書き込みアドレス (0x0000-0xFFFF)
            value: 書き込み値 (0x00-0xFF)
            
        Raises:
            InvalidAddressError: 無効なアドレスが指定された場合
            InvalidValueError: 無効な値が指定された場合
        """
        ...
    
    def get_state(self) -> Dict[str, Any]:
        """状態取得
        
        デバイスの現在の内部状態を辞書形式で取得します。
        デバッグやセーブ/ロード機能で使用されます。
        
        Returns:
            Dict[str, Any]: デバイスの状態情報
        """
        ...
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """状態設定
        
        デバイスの内部状態を設定します。
        ロード機能やテスト時の状態設定で使用されます。
        
        Args:
            state: 設定する状態情報
        """
        ...


@runtime_checkable
class CPUDevice(Device, Protocol):
    """CPU専用プロトコル
    
    CPUデバイス固有の機能を定義するプロトコル。
    基本のDeviceプロトコルに加えて、命令実行やレジスタ操作など
    CPU特有の機能を提供します。
    """
    
    def step(self) -> int:
        """単一命令実行
        
        次の命令を1つ実行します。
        
        Returns:
            int: 実行に要したサイクル数
        """
        ...
    
    def get_registers(self) -> Dict[str, int]:
        """レジスタ状態取得
        
        CPUの全レジスタの現在値を取得します。
        
        Returns:
            Dict[str, int]: レジスタ名と値のマッピング
                例: {'A': 0x42, 'X': 0x00, 'Y': 0x01, 'PC': 0x8000, ...}
        """
        ...
    
    def set_pc(self, address: int) -> None:
        """プログラムカウンタ設定
        
        プログラムカウンタ(PC)を指定されたアドレスに設定します。
        
        Args:
            address: 設定するアドレス (0x0000-0xFFFF)
            
        Raises:
            InvalidAddressError: 無効なアドレスが指定された場合
        """
        ...
    
    def is_interrupt_enabled(self) -> bool:
        """割り込み許可状態取得
        
        IRQ割り込みが許可されているかを確認します。
        
        Returns:
            bool: 割り込み許可状態 (True: 許可, False: 禁止)
        """
        ...


@runtime_checkable
class VideoDevice(Device, Protocol):
    """ビデオデバイスプロトコル
    
    ビデオ出力デバイス用のプロトコル。
    フレームバッファの管理や画面更新機能を提供します。
    """
    
    def get_framebuffer(self) -> bytes:
        """フレームバッファ取得
        
        現在のフレームバッファの内容を取得します。
        
        Returns:
            bytes: フレームバッファデータ
        """
        ...


@runtime_checkable
class AudioDevice(Device, Protocol):
    """オーディオデバイスプロトコル
    
    オーディオ出力デバイス用のプロトコル。
    音声データの生成と出力機能を提供します。
    """
    
    def get_audio_buffer(self, samples: int) -> bytes:
        """オーディオバッファ取得
        
        指定されたサンプル数分のオーディオデータを取得します。
        
        Args:
            samples: 取得するサンプル数
            
        Returns:
            bytes: オーディオサンプルデータ
        """
        ...


# 例外クラス
class DeviceError(Exception):
    """デバイス基底例外
    
    デバイス関連の全ての例外の基底クラス。
    """
    pass


class InvalidAddressError(DeviceError):
    """無効アドレス例外
    
    無効なメモリアドレスが指定された場合に発生する例外。
    """
    
    def __init__(self, address: int) -> None:
        self.address = address
        super().__init__(f"Invalid address: ${address:04X}")


class InvalidValueError(DeviceError):
    """無効値例外
    
    無効な値が指定された場合に発生する例外。
    """
    
    def __init__(self, value: int) -> None:
        self.value = value
        super().__init__(f"Invalid value: {value}")
