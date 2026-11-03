"""Host-side validation of role handoffs; never mounted in the agent sandbox."""

from .validate import ContractError, load_json, validate_contract

__all__ = ["ContractError", "load_json", "validate_contract"]
