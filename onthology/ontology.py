"""
Part A – Ontology Design & Schema Modeling
==========================================
This module defines the full FOCUS 1.0-aligned ontology as Python dataclasses.
Think of this as the "blueprint" of our knowledge base — every concept and
relationship is formally defined here before anything is built in Neo4j.

FOCUS 1.0 spec: https://focus.finops.org/focus-specification/v1-0/
"""

from dataclasses import dataclass, field
from typing import Optional, List, Literal
from enum import Enum


# ─────────────────────────────────────────────
# Enumerations (Allowed Value Sets per FOCUS spec)
# ─────────────────────────────────────────────

class ChargeCategory(str, Enum):
    USAGE = "Usage"
    PURCHASE = "Purchase"
    TAX = "Tax"
    CREDIT = "Credit"
    ADJUSTMENT = "Adjustment"

class ChargeFrequency(str, Enum):
    ONE_TIME = "One-Time"
    RECURRING = "Recurring"
    USAGE_BASED = "Usage-Based"

class ChargeClass(str, Enum):
    REGULAR = "Regular"
    CORRECTION = "Correction"

class PricingCategory(str, Enum):
    STANDARD = "Standard"
    COMMITTED = "Committed"
    DYNAMIC = "Dynamic"
    OTHER = "Other"

class CommitmentDiscountStatus(str, Enum):
    USED = "Used"
    UNUSED = "Unused"

class AllocationMethod(str, Enum):
    PROPORTIONAL = "Proportional"
    EVEN_SPLIT = "EvenSplit"
    WEIGHTED = "Weighted"

class AllocationTargetType(str, Enum):
    APPLICATION = "Application"
    COST_CENTRE = "CostCentre"
    ENVIRONMENT = "Environment"

class AllocationBasis(str, Enum):
    USAGE = "Usage"
    COST = "Cost"
    TAG = "Tag"
    MANUAL = "Manual"


# ─────────────────────────────────────────────
# Ontology Classes (FOCUS 1.0 aligned)
# ─────────────────────────────────────────────

@dataclass
class OntologyClass:
    """Base class for all ontology concepts."""
    label: str
    description: str
    embedding: Optional[List[float]] = field(default=None, repr=False)


@dataclass
class CostRecord(OntologyClass):
    """
    Central fact class. Represents a single billing line item.
    FOCUS columns: EffectiveCost, BilledCost, ListCost, ContractedCost, etc.

    Validation rules:
      - billedCost >= 0
      - effectiveCost >= 0
      - listCost >= 0
      - contractedCost >= 0
      - currency: ISO 4217 3-letter code (e.g. USD, AUD)

    Derivation rule (FOCUS spec):
      effectiveCost = billedCost - discounts + amortizedUpfrontFees
    """
    # Data Properties
    effective_cost: float = 0.0           # FOCUS: EffectiveCost (required, ≥ 0)
    billed_cost: float = 0.0             # FOCUS: BilledCost (required, ≥ 0)
    list_cost: float = 0.0               # FOCUS: ListCost (optional, ≥ 0)
    contracted_cost: float = 0.0         # FOCUS: ContractedCost (optional, ≥ 0)
    currency: str = "USD"                # FOCUS: BillingCurrency (ISO 4217)
    consumed_quantity: Optional[float] = None   # FOCUS: ConsumedQuantity
    consumed_unit: Optional[str] = None         # FOCUS: ConsumedUnit
    pricing_quantity: Optional[float] = None    # FOCUS: PricingQuantity
    pricing_unit: Optional[str] = None          # FOCUS: PricingUnit
    list_unit_price: Optional[float] = None     # FOCUS: ListUnitPrice
    contracted_unit_price: Optional[float] = None  # FOCUS: ContractedUnitPrice
    tags_kv: Optional[str] = None               # FOCUS: Tags (JSON string)
    # Derived from TagsKV
    tag_application: Optional[str] = None
    tag_environment: Optional[str] = None
    tag_cost_centre: Optional[str] = None
    # Source tracking
    source: str = "unknown"              # "aws" or "azure"
    record_id: Optional[str] = None


@dataclass
class Account(OntologyClass):
    """
    Billing account / sub-account hierarchy.
    FOCUS columns: BillingAccountId, BillingAccountName, SubAccountId, SubAccountName
    Cardinality: one CostRecord → one BillingAccount; one BillingAccount → many SubAccounts
    """
    billing_account_id: str = ""          # FOCUS: BillingAccountId (required, unique)
    billing_account_name: str = ""        # FOCUS: BillingAccountName
    sub_account_id: Optional[str] = None  # FOCUS: SubAccountId
    sub_account_name: Optional[str] = None  # FOCUS: SubAccountName
    provider: str = ""                    # "aws" or "azure"


@dataclass
class TimeFrame(OntologyClass):
    """
    Billing and charge period dimensions.
    FOCUS columns: ChargePeriodStart/End, BillingPeriodStart/End

    Validation rules:
      - ChargePeriodEnd > ChargePeriodStart
      - BillingPeriodEnd > BillingPeriodStart
      - ChargePeriod must fall within BillingPeriod
    """
    charge_period_start: Optional[str] = None   # FOCUS: ChargePeriodStart (ISO 8601)
    charge_period_end: Optional[str] = None     # FOCUS: ChargePeriodEnd (ISO 8601)
    billing_period_start: Optional[str] = None  # FOCUS: BillingPeriodStart (ISO 8601)
    billing_period_end: Optional[str] = None    # FOCUS: BillingPeriodEnd (ISO 8601)


@dataclass
class Charge(OntologyClass):
    """
    Charge classification metadata.
    FOCUS columns: ChargeCategory, ChargeFrequency, ChargeDescription, ChargeClass

    Validation rules:
      - chargeCategory ∈ {Usage, Purchase, Tax, Credit, Adjustment}
      - chargeFrequency ∈ {One-Time, Recurring, Usage-Based}
      - chargeClass ∈ {Regular, Correction} — if null, treat as Regular
    """
    charge_category: Optional[str] = None    # FOCUS: ChargeCategory (required)
    charge_frequency: Optional[str] = None   # FOCUS: ChargeFrequency (required)
    charge_description: Optional[str] = None # FOCUS: ChargeDescription
    charge_class: Optional[str] = None       # FOCUS: ChargeClass


@dataclass
class Resource(OntologyClass):
    """
    Cloud resource that incurred a cost.
    FOCUS columns: ResourceId, ResourceName, ResourceType

    Cardinality: one CostRecord → one Resource; one Resource → many Tags
    """
    resource_id: Optional[str] = None    # FOCUS: ResourceId
    resource_name: Optional[str] = None  # FOCUS: ResourceName
    resource_type: Optional[str] = None  # FOCUS: ResourceType


@dataclass
class Service(OntologyClass):
    """
    Cloud service consumed.
    FOCUS columns: ServiceName, ServiceCategory

    Cardinality: one Resource → one Service; one Service → many Resources
    """
    service_name: str = ""              # FOCUS: ServiceName (required)
    service_category: Optional[str] = None  # FOCUS: ServiceCategory


@dataclass
class Location(OntologyClass):
    """
    Geographic deployment location.
    FOCUS columns: RegionId, RegionName

    Cardinality: one Resource → one Location; one Location → many Resources
    """
    region_id: Optional[str] = None    # FOCUS: RegionId
    region_name: Optional[str] = None  # FOCUS: RegionName
    availability_zone: Optional[str] = None


@dataclass
class VendorSpecificAttributes(OntologyClass):
    """
    Base class for vendor-specific (x_*) fields not covered by FOCUS standard.
    Subclassed into AWSAttributes and AzureAttributes.
    """
    provider: str = ""


@dataclass
class AWSAttributes(VendorSpecificAttributes):
    """
    AWS-specific extended fields.
    SubClass of: VendorSpecificAttributes
    """
    x_service_code: Optional[str] = None    # e.g. "AmazonEC2"
    x_usage_type: Optional[str] = None      # e.g. "APS2-DataTransfer-Regional-Bytes"
    x_operation: Optional[str] = None       # e.g. "RunInstances"
    x_cost_categories: Optional[str] = None
    x_discounts: Optional[str] = None
    sku_id: Optional[str] = None
    sku_price_id: Optional[str] = None


@dataclass
class AzureAttributes(VendorSpecificAttributes):
    """
    Azure-specific extended fields.
    SubClass of: VendorSpecificAttributes
    """
    x_sku_meter_category: Optional[str] = None    # e.g. "Virtual Machines"
    x_sku_description: Optional[str] = None        # e.g. "D2s v3 Windows"
    x_resource_group_name: Optional[str] = None
    x_billing_profile_name: Optional[str] = None
    x_invoice_section_name: Optional[str] = None
    x_cost_allocation_rule_name: Optional[str] = None
    x_cost_center: Optional[str] = None
    x_pricing_subcategory: Optional[str] = None
    x_sku_meter_name: Optional[str] = None
    x_sku_service_family: Optional[str] = None


@dataclass
class CostAllocation(OntologyClass):
    """
    Represents a cost allocation rule applied to shared costs.

    Example:
      CostAllocation(A1)
        --> allocationMethod = "Proportional"
        --> allocationTargetType = "Application"
        --> isSharedCost = True

    Allocation rules:
      - If isSharedCost=True, allocatedCost is derived
      - allocationMethod determines how sourceCostPool is split
      - allocationBasis determines the metric used for weighting
    """
    allocation_rule_name: Optional[str] = None
    allocation_method: Optional[str] = None          # Proportional/EvenSplit/Weighted
    is_shared_cost: bool = False
    allocation_target_type: Optional[str] = None     # Application/CostCentre
    allocation_basis: Optional[str] = None           # Usage/Cost/Tag/Manual
    # Derived fields
    allocated_cost: Optional[float] = None
    source_cost_pool: Optional[str] = None


@dataclass
class Tag(OntologyClass):
    """
    Key-value tag applied to a resource or cost record.
    Derived from FOCUS TagsKV field.
    Cardinality: one CostRecord → many Tags
    """
    key: str = ""
    value: str = ""


# ─────────────────────────────────────────────
# Object Properties (Relationships)
# ─────────────────────────────────────────────

OBJECT_PROPERTIES = {
    "BELONGS_TO_BILLING_ACCOUNT": {
        "domain": "CostRecord",
        "range": "BillingAccount",
        "cardinality": "many-to-one",
        "description": "Each cost record belongs to exactly one billing account"
    },
    "BELONGS_TO_SUBACCOUNT": {
        "domain": "CostRecord",
        "range": "SubAccount",
        "cardinality": "many-to-one",
        "description": "Each cost record is scoped to one sub-account"
    },
    "IN_BILLING_PERIOD": {
        "domain": "CostRecord",
        "range": "BillingPeriod",
        "cardinality": "many-to-one",
        "description": "A cost record falls within one billing period"
    },
    "HAS_CHARGE": {
        "domain": "CostRecord",
        "range": "Charge",
        "cardinality": "one-to-one",
        "description": "Each cost record has one charge classification"
    },
    "INCURRED_BY": {
        "domain": "CostRecord",
        "range": "Resource",
        "cardinality": "many-to-one",
        "description": "A cost is incurred by a specific cloud resource"
    },
    "USES_SERVICE": {
        "domain": "Resource",
        "range": "Service",
        "cardinality": "many-to-one",
        "description": "A resource uses a specific cloud service"
    },
    "DEPLOYED_IN": {
        "domain": "Resource",
        "range": "Location",
        "cardinality": "many-to-one",
        "description": "A resource is deployed in a geographic location"
    },
    "HAS_VENDOR_ATTRS": {
        "domain": "CostRecord",
        "range": "VendorSpecificAttributes",
        "cardinality": "one-to-one",
        "description": "Vendor-specific fields attached to a cost record"
    },
    "ALLOCATED_VIA": {
        "domain": "CostRecord",
        "range": "CostAllocation",
        "cardinality": "many-to-many",
        "description": "A cost record may be split via an allocation rule"
    },
    "ALLOCATED_TO": {
        "domain": "CostAllocation",
        "range": "Tag",
        "cardinality": "many-to-many",
        "description": "Allocation targets (application, cost centre, environment)"
    },
    "HAS_TAG": {
        "domain": "CostRecord",
        "range": "Tag",
        "cardinality": "many-to-many",
        "description": "Tags applied to a cost record from the TagsKV field"
    },
}

# ─────────────────────────────────────────────
# Validation Rules (FOCUS spec compliance)
# ─────────────────────────────────────────────

VALIDATION_RULES = {
    "billedCost": {"type": "float", "nullable": False, "min": 0},
    "effectiveCost": {"type": "float", "nullable": False, "min": 0},
    "listCost": {"type": "float", "nullable": True, "min": 0},
    "contractedCost": {"type": "float", "nullable": True, "min": 0},
    "currency": {"type": "str", "nullable": False, "pattern": r"^[A-Z]{3}$"},
    "chargeCategory": {
        "type": "str", "nullable": False,
        "allowed": ["Usage", "Purchase", "Tax", "Credit", "Adjustment"]
    },
    "chargeFrequency": {
        "type": "str", "nullable": False,
        "allowed": ["One-Time", "Recurring", "Usage-Based"]
    },
    "chargeClass": {
        "type": "str", "nullable": True,
        "allowed": ["Regular", "Correction", None]
    },
    "billingAccountId": {"type": "str", "nullable": False, "unique": True},
    "chargePeriodStart": {"type": "datetime", "nullable": False},
    "chargePeriodEnd": {"type": "datetime", "nullable": False},
}

# ─────────────────────────────────────────────
# Derivation Rules
# ─────────────────────────────────────────────

DERIVATION_RULES = {
    "effectiveCost": "billedCost - sum(discounts) + amortizedUpfrontFees",
    "allocatedCost": "sourceCostPool * allocationWeight / totalWeight",
    "allocationWeight_proportional": "resourceUsage / totalUsage",
    "allocationWeight_evenSplit": "1 / numberOfTargets",
    "allocationWeight_weighted": "customWeight / sum(customWeights)",
    # ContractedCost derivation note
    "contractedCost_note": (
        "ContractedCost MAY differ from ContractedUnitPrice × PricingQuantity "
        "when negotiated enterprise discounts, tiered pricing, or bundled rates apply. "
        "Use EffectiveCost (not ContractedCost) for actual spend analysis."
    ),
}


if __name__ == "__main__":
    # Print ontology summary
    print("=" * 60)
    print("FOCUS 1.0 Cloud Cost Ontology — Class Hierarchy")
    print("=" * 60)
    classes = [
        CostRecord, Account, TimeFrame, Charge, Resource,
        Service, Location, VendorSpecificAttributes,
        AWSAttributes, AzureAttributes, CostAllocation, Tag
    ]
    for cls in classes:
        parent = cls.__bases__[0].__name__
        print(f"  {cls.__name__} (extends {parent})")

    print("\nObject Properties:")
    for prop, meta in OBJECT_PROPERTIES.items():
        print(f"  ({meta['domain']}) -[:{prop}]-> ({meta['range']})  [{meta['cardinality']}]")

    print("\nValidation Rules (sample):")
    for field, rule in list(VALIDATION_RULES.items())[:4]:
        print(f"  {field}: {rule}")
