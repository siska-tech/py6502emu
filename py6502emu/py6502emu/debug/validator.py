"""
State validation system for W65C02S emulator debugging.

This module implements PU018: StateValidator functionality including:
- State data integrity checking
- Register value range validation
- Memory access validity confirmation
- Device state validation
- Validation error report generation
"""

from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
import re

from .serializer import StateFormat, StateMetadata


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = auto()       # Informational message
    WARNING = auto()    # Potential issue
    ERROR = auto()      # Definite problem
    CRITICAL = auto()   # System-breaking issue


class ValidationCategory(Enum):
    """Categories of validation checks."""
    CPU_REGISTERS = auto()
    CPU_FLAGS = auto()
    MEMORY = auto()
    DEVICES = auto()
    METADATA = auto()
    CONSISTENCY = auto()


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    category: ValidationCategory
    severity: ValidationSeverity
    message: str
    details: Optional[str] = None
    location: Optional[str] = None  # e.g., "register A", "memory 0x1000"
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    suggestion: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation of the issue."""
        parts = [f"[{self.severity.name}] {self.category.name}: {self.message}"]
        
        if self.location:
            parts.append(f"Location: {self.location}")
        
        if self.expected is not None and self.actual is not None:
            parts.append(f"Expected: {self.expected}, Actual: {self.actual}")
        
        if self.details:
            parts.append(f"Details: {self.details}")
        
        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")
        
        return "\n  ".join(parts)


@dataclass
class ValidationReport:
    """Complete validation report with all issues found."""
    timestamp: float
    state_checksum: Optional[str] = None
    issues: List[ValidationIssue] = field(default_factory=list)
    statistics: Dict[str, int] = field(default_factory=dict)
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """Add an issue to the report."""
        self.issues.append(issue)
        
        # Update statistics
        severity_key = f"{issue.severity.name.lower()}_count"
        category_key = f"{issue.category.name.lower()}_issues"
        
        self.statistics[severity_key] = self.statistics.get(severity_key, 0) + 1
        self.statistics[category_key] = self.statistics.get(category_key, 0) + 1
    
    def has_errors(self) -> bool:
        """Check if report contains any errors or critical issues."""
        return any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] 
                  for issue in self.issues)
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get all issues of a specific severity."""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def get_issues_by_category(self, category: ValidationCategory) -> List[ValidationIssue]:
        """Get all issues of a specific category."""
        return [issue for issue in self.issues if issue.category == category]
    
    def get_summary(self) -> str:
        """Get a summary of the validation report."""
        total_issues = len(self.issues)
        if total_issues == 0:
            return "Validation passed: No issues found."
        
        critical = len(self.get_issues_by_severity(ValidationSeverity.CRITICAL))
        errors = len(self.get_issues_by_severity(ValidationSeverity.ERROR))
        warnings = len(self.get_issues_by_severity(ValidationSeverity.WARNING))
        info = len(self.get_issues_by_severity(ValidationSeverity.INFO))
        
        parts = [f"Validation completed: {total_issues} issues found"]
        
        if critical > 0:
            parts.append(f"{critical} critical")
        if errors > 0:
            parts.append(f"{errors} errors")
        if warnings > 0:
            parts.append(f"{warnings} warnings")
        if info > 0:
            parts.append(f"{info} info")
        
        return ", ".join(parts)


class ValidationRule(ABC):
    """Abstract base class for validation rules."""
    
    def __init__(self, name: str, category: ValidationCategory, 
                 severity: ValidationSeverity = ValidationSeverity.ERROR):
        self.name = name
        self.category = category
        self.severity = severity
    
    @abstractmethod
    def validate(self, state: StateFormat) -> List[ValidationIssue]:
        """Validate the state and return any issues found."""
        pass


class RegisterRangeRule(ValidationRule):
    """Validates that CPU registers are within valid ranges."""
    
    def __init__(self):
        super().__init__("Register Range Check", ValidationCategory.CPU_REGISTERS)
    
    def validate(self, state: StateFormat) -> List[ValidationIssue]:
        issues = []
        registers = state.cpu_registers
        
        # 8-bit register checks
        for reg_name in ['A', 'X', 'Y', 'S', 'P']:
            if reg_name in registers:
                value = registers[reg_name]
                if not (0 <= value <= 255):
                    issues.append(ValidationIssue(
                        category=self.category,
                        severity=self.severity,
                        message=f"Register {reg_name} value out of range",
                        location=f"register {reg_name}",
                        expected="0-255",
                        actual=value,
                        suggestion=f"Ensure {reg_name} register is properly masked to 8 bits"
                    ))
        
        # 16-bit register checks
        if 'PC' in registers:
            pc_value = registers['PC']
            if not (0 <= pc_value <= 65535):
                issues.append(ValidationIssue(
                    category=self.category,
                    severity=self.severity,
                    message="Program Counter (PC) value out of range",
                    location="register PC",
                    expected="0-65535",
                    actual=pc_value,
                    suggestion="Ensure PC register is properly masked to 16 bits"
                ))
        
        return issues


class FlagConsistencyRule(ValidationRule):
    """Validates CPU flag consistency."""
    
    def __init__(self):
        super().__init__("Flag Consistency Check", ValidationCategory.CPU_FLAGS)
    
    def validate(self, state: StateFormat) -> List[ValidationIssue]:
        issues = []
        flags = state.cpu_flags
        registers = state.cpu_registers
        
        # Check that unused bit (U) is always true for W65C02S
        if 'U' in flags and not flags['U']:
            issues.append(ValidationIssue(
                category=self.category,
                severity=ValidationSeverity.WARNING,
                message="Unused flag bit should always be set for W65C02S",
                location="flag U",
                expected=True,
                actual=flags['U'],
                suggestion="Set unused bit (bit 5) to 1 in processor status register"
            ))
        
        # Check flag consistency with P register if both are present
        if 'P' in registers and len(flags) >= 8:
            p_value = registers['P']
            expected_flags = {
                'N': bool(p_value & 0x80),
                'V': bool(p_value & 0x40),
                'U': bool(p_value & 0x20),
                'B': bool(p_value & 0x10),
                'D': bool(p_value & 0x08),
                'I': bool(p_value & 0x04),
                'Z': bool(p_value & 0x02),
                'C': bool(p_value & 0x01)
            }
            
            for flag_name, expected_value in expected_flags.items():
                if flag_name in flags and flags[flag_name] != expected_value:
                    issues.append(ValidationIssue(
                        category=self.category,
                        severity=self.severity,
                        message=f"Flag {flag_name} inconsistent with P register",
                        location=f"flag {flag_name}",
                        expected=expected_value,
                        actual=flags[flag_name],
                        details=f"P register value: 0x{p_value:02X}",
                        suggestion="Ensure flags are synchronized with P register"
                    ))
        
        return issues


class MemoryValidityRule(ValidationRule):
    """Validates memory data integrity."""
    
    def __init__(self):
        super().__init__("Memory Validity Check", ValidationCategory.MEMORY)
    
    def validate(self, state: StateFormat) -> List[ValidationIssue]:
        issues = []
        
        for i, memory_range in enumerate(state.memory_ranges):
            # Check required fields
            if 'start' not in memory_range or 'end' not in memory_range or 'data' not in memory_range:
                issues.append(ValidationIssue(
                    category=self.category,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Memory range {i} missing required fields",
                    location=f"memory_range[{i}]",
                    details="Required fields: start, end, data",
                    suggestion="Ensure all memory ranges have start, end, and data fields"
                ))
                continue
            
            start_addr = memory_range['start']
            end_addr = memory_range['end']
            data = memory_range['data']
            
            # Validate address range
            if not (0 <= start_addr <= 65535):
                issues.append(ValidationIssue(
                    category=self.category,
                    severity=self.severity,
                    message=f"Memory range {i} start address out of bounds",
                    location=f"memory_range[{i}].start",
                    expected="0-65535",
                    actual=start_addr
                ))
            
            if not (0 <= end_addr <= 65535):
                issues.append(ValidationIssue(
                    category=self.category,
                    severity=self.severity,
                    message=f"Memory range {i} end address out of bounds",
                    location=f"memory_range[{i}].end",
                    expected="0-65535",
                    actual=end_addr
                ))
            
            if start_addr > end_addr:
                issues.append(ValidationIssue(
                    category=self.category,
                    severity=self.severity,
                    message=f"Memory range {i} start address greater than end address",
                    location=f"memory_range[{i}]",
                    details=f"Start: 0x{start_addr:04X}, End: 0x{end_addr:04X}",
                    suggestion="Ensure start address is less than or equal to end address"
                ))
            
            # Validate data length
            expected_length = end_addr - start_addr + 1
            if len(data) != expected_length:
                issues.append(ValidationIssue(
                    category=self.category,
                    severity=self.severity,
                    message=f"Memory range {i} data length mismatch",
                    location=f"memory_range[{i}].data",
                    expected=expected_length,
                    actual=len(data),
                    details=f"Range: 0x{start_addr:04X}-0x{end_addr:04X}",
                    suggestion="Ensure data array length matches address range"
                ))
            
            # Validate data values
            for j, byte_value in enumerate(data):
                if not isinstance(byte_value, int) or not (0 <= byte_value <= 255):
                    issues.append(ValidationIssue(
                        category=self.category,
                        severity=self.severity,
                        message=f"Invalid byte value in memory range {i}",
                        location=f"memory_range[{i}].data[{j}]",
                        expected="0-255",
                        actual=byte_value,
                        details=f"Address: 0x{start_addr + j:04X}",
                        suggestion="Ensure all memory bytes are integers in range 0-255"
                    ))
        
        return issues


class DeviceStateRule(ValidationRule):
    """Validates device state data."""
    
    def __init__(self):
        super().__init__("Device State Check", ValidationCategory.DEVICES)
    
    def validate(self, state: StateFormat) -> List[ValidationIssue]:
        issues = []
        
        for device_name, device_data in state.devices.items():
            # Check device type
            if 'type' not in device_data:
                issues.append(ValidationIssue(
                    category=self.category,
                    severity=ValidationSeverity.WARNING,
                    message=f"Device '{device_name}' missing type information",
                    location=f"devices[{device_name}]",
                    suggestion="Include device type in serialized state"
                ))
            
            # Check for error states
            if 'error' in device_data:
                issues.append(ValidationIssue(
                    category=self.category,
                    severity=ValidationSeverity.WARNING,
                    message=f"Device '{device_name}' reported error during serialization",
                    location=f"devices[{device_name}]",
                    details=device_data['error'],
                    suggestion="Check device implementation and state access methods"
                ))
            
            # Validate device state structure
            if 'state' in device_data:
                device_state = device_data['state']
                if not isinstance(device_state, dict):
                    issues.append(ValidationIssue(
                        category=self.category,
                        severity=ValidationSeverity.WARNING,
                        message=f"Device '{device_name}' state is not a dictionary",
                        location=f"devices[{device_name}].state",
                        actual=type(device_state).__name__,
                        suggestion="Device state should be serializable as dictionary"
                    ))
        
        return issues


class MetadataValidityRule(ValidationRule):
    """Validates state metadata."""
    
    def __init__(self):
        super().__init__("Metadata Validity Check", ValidationCategory.METADATA)
    
    def validate(self, state: StateFormat) -> List[ValidationIssue]:
        issues = []
        metadata = state.metadata
        
        # Check version format
        if not re.match(r'^\d+\.\d+(\.\d+)?$', metadata.version):
            issues.append(ValidationIssue(
                category=self.category,
                severity=ValidationSeverity.WARNING,
                message="Metadata version format invalid",
                location="metadata.version",
                actual=metadata.version,
                suggestion="Use semantic versioning format (e.g., '1.0.0')"
            ))
        
        # Check timestamp validity
        if metadata.timestamp <= 0:
            issues.append(ValidationIssue(
                category=self.category,
                severity=ValidationSeverity.WARNING,
                message="Invalid timestamp in metadata",
                location="metadata.timestamp",
                actual=metadata.timestamp,
                suggestion="Use valid Unix timestamp"
            ))
        
        # Check checksum if present
        if metadata.checksum:
            calculated_checksum = state.calculate_checksum()
            if metadata.checksum != calculated_checksum:
                issues.append(ValidationIssue(
                    category=self.category,
                    severity=ValidationSeverity.ERROR,
                    message="State checksum mismatch",
                    location="metadata.checksum",
                    expected=calculated_checksum,
                    actual=metadata.checksum,
                    suggestion="Recalculate checksum or verify state integrity"
                ))
        
        return issues


class IntegrityChecker:
    """Performs comprehensive integrity checks on state data."""
    
    def __init__(self):
        self._rules: List[ValidationRule] = []
        self._custom_validators: List[Callable[[StateFormat], List[ValidationIssue]]] = []
    
    def add_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule."""
        self._rules.append(rule)
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a validation rule by name."""
        for i, rule in enumerate(self._rules):
            if rule.name == rule_name:
                del self._rules[i]
                return True
        return False
    
    def add_custom_validator(self, validator: Callable[[StateFormat], List[ValidationIssue]]) -> None:
        """Add a custom validation function."""
        self._custom_validators.append(validator)
    
    def check_integrity(self, state: StateFormat) -> ValidationReport:
        """Perform comprehensive integrity check."""
        import time
        
        report = ValidationReport(timestamp=time.time())
        
        if state.metadata.checksum:
            report.state_checksum = state.metadata.checksum
        
        # Run all validation rules
        for rule in self._rules:
            try:
                issues = rule.validate(state)
                for issue in issues:
                    report.add_issue(issue)
            except Exception as e:
                # If a rule fails, report it as a critical issue
                report.add_issue(ValidationIssue(
                    category=ValidationCategory.CONSISTENCY,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Validation rule '{rule.name}' failed",
                    details=str(e),
                    suggestion="Check validation rule implementation"
                ))
        
        # Run custom validators
        for validator in self._custom_validators:
            try:
                issues = validator(state)
                for issue in issues:
                    report.add_issue(issue)
            except Exception as e:
                report.add_issue(ValidationIssue(
                    category=ValidationCategory.CONSISTENCY,
                    severity=ValidationSeverity.CRITICAL,
                    message="Custom validator failed",
                    details=str(e),
                    suggestion="Check custom validator implementation"
                ))
        
        return report


class StateValidator:
    """
    Main state validation interface providing comprehensive validation capabilities.
    
    Validates state data integrity, register ranges, memory validity,
    and device states to ensure emulator state consistency.
    """
    
    def __init__(self):
        self._integrity_checker = IntegrityChecker()
        self._setup_default_rules()
    
    def _setup_default_rules(self) -> None:
        """Setup default validation rules."""
        self._integrity_checker.add_rule(RegisterRangeRule())
        self._integrity_checker.add_rule(FlagConsistencyRule())
        self._integrity_checker.add_rule(MemoryValidityRule())
        self._integrity_checker.add_rule(DeviceStateRule())
        self._integrity_checker.add_rule(MetadataValidityRule())
    
    def validate_state(self, state: StateFormat) -> ValidationReport:
        """
        Perform complete state validation.
        
        Args:
            state: State to validate
            
        Returns:
            ValidationReport with all issues found
        """
        return self._integrity_checker.check_integrity(state)
    
    def quick_validate(self, state: StateFormat) -> bool:
        """
        Perform quick validation check.
        
        Args:
            state: State to validate
            
        Returns:
            True if state is valid (no errors or critical issues)
        """
        report = self.validate_state(state)
        return not report.has_errors()
    
    def validate_registers(self, registers: Dict[str, int]) -> List[ValidationIssue]:
        """Validate CPU registers only."""
        # Create minimal state for register validation
        from .serializer import StateMetadata
        temp_state = StateFormat(
            metadata=StateMetadata(),
            cpu_registers=registers,
            cpu_flags={},
            memory_ranges=[],
            devices={}
        )
        
        rule = RegisterRangeRule()
        return rule.validate(temp_state)
    
    def validate_memory_range(self, start: int, end: int, data: List[int]) -> List[ValidationIssue]:
        """Validate a single memory range."""
        # Create minimal state for memory validation
        from .serializer import StateMetadata
        temp_state = StateFormat(
            metadata=StateMetadata(),
            cpu_registers={},
            cpu_flags={},
            memory_ranges=[{'start': start, 'end': end, 'data': data}],
            devices={}
        )
        
        rule = MemoryValidityRule()
        return rule.validate(temp_state)
    
    def add_validation_rule(self, rule: ValidationRule) -> None:
        """Add a custom validation rule."""
        self._integrity_checker.add_rule(rule)
    
    def add_custom_validator(self, validator: Callable[[StateFormat], List[ValidationIssue]]) -> None:
        """Add a custom validation function."""
        self._integrity_checker.add_custom_validator(validator)
    
    def get_validation_statistics(self, report: ValidationReport) -> Dict[str, Any]:
        """Get detailed statistics from a validation report."""
        return {
            'total_issues': len(report.issues),
            'by_severity': {
                'critical': len(report.get_issues_by_severity(ValidationSeverity.CRITICAL)),
                'error': len(report.get_issues_by_severity(ValidationSeverity.ERROR)),
                'warning': len(report.get_issues_by_severity(ValidationSeverity.WARNING)),
                'info': len(report.get_issues_by_severity(ValidationSeverity.INFO))
            },
            'by_category': {
                'cpu_registers': len(report.get_issues_by_category(ValidationCategory.CPU_REGISTERS)),
                'cpu_flags': len(report.get_issues_by_category(ValidationCategory.CPU_FLAGS)),
                'memory': len(report.get_issues_by_category(ValidationCategory.MEMORY)),
                'devices': len(report.get_issues_by_category(ValidationCategory.DEVICES)),
                'metadata': len(report.get_issues_by_category(ValidationCategory.METADATA)),
                'consistency': len(report.get_issues_by_category(ValidationCategory.CONSISTENCY))
            },
            'has_errors': report.has_errors(),
            'timestamp': report.timestamp,
            'checksum': report.state_checksum
        }
