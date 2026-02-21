"""
Part B – Knowledge Graph Construction in Neo4j
Steps 2 & 3: Relationships & Data Ingestion
============================================
Loads AWS and Azure FOCUS 1.0 CSV data into Neo4j.

Raw billing data stays in-memory (pandas DataFrame).
Only metadata / structural nodes go into Neo4j as per assignment spec.

What this script does:
  1. Reads AWS and Azure CSV files
  2. Parses tags from TagsKV JSON
  3. Creates all Neo4j nodes (CostRecord, Service, Resource, etc.)
  4. Creates all relationships
  5. Prints a summary of what was ingested
"""

import os
import json
import hashlib
import pandas as pd
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        total = kwargs.get('total', None)
        desc = kwargs.get('desc', '')
        for i, item in enumerate(iterable):
            if i % 100 == 0:
                print(f"  {desc}: {i}...")
            yield item

from dotenv import load_dotenv
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from graph.schema import get_driver

load_dotenv()

AWS_PATH = os.getenv("AWS_DATA_PATH", "data/aws_focus.csv")
AZURE_PATH = os.getenv("AZURE_DATA_PATH", "data/azure_focus.csv")


# ─────────────────────────────────────────────
# Utility Helpers
# ─────────────────────────────────────────────

def safe_str(val):
    """Convert any value to string, returning None for NaN/empty."""
    if pd.isna(val) or val == "" or val is None:
        return None
    return str(val).strip()


def safe_float(val):
    """Convert any value to float, returning 0.0 for invalid."""
    try:
        if pd.isna(val):
            return 0.0
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def make_id(*parts):
    """Create a stable hash-based ID from multiple parts."""
    combined = "|".join(str(p) for p in parts if p)
    return hashlib.md5(combined.encode()).hexdigest()[:16]


def parse_tags(tags_str):
    """
    Parse the TagsKV JSON string into a dict.
    Handles both AWS and Azure tag formats.
    """
    if not tags_str or pd.isna(tags_str):
        return {}
    try:
        if isinstance(tags_str, str):
            tags = json.loads(tags_str.replace("'", '"'))
            if isinstance(tags, dict):
                return tags
        return {}
    except (json.JSONDecodeError, ValueError):
        return {}


# ─────────────────────────────────────────────
# Load & Normalize Data
# ─────────────────────────────────────────────

def load_aws_data(path):
    """Load AWS FOCUS CSV and normalize column names."""
    df = pd.read_csv(path)
    # AWS columns are already in proper case — map to our standard names
    df["_source"] = "aws"
    df["_provider"] = "Amazon Web Services"
    # Normalize tags column
    df["_tags"] = df["Tags"].apply(parse_tags) if "Tags" in df.columns else [{}] * len(df)
    return df


def load_azure_data(path):
    """Load Azure FOCUS CSV and normalize column names to match AWS naming."""
    df = pd.read_csv(path)
    df["_source"] = "azure"
    df["_provider"] = "Microsoft Azure"
    # Azure uses lowercase column names — rename to match AWS FOCUS standard
    rename_map = {col: col.title().replace("_", "") if "_" not in col else col
                  for col in df.columns}
    # Specific renames for FOCUS standard fields
    focus_renames = {
        "billedcost": "BilledCost",
        "billingaccountid": "BillingAccountId",
        "billingaccountname": "BillingAccountName",
        "billingcurrency": "BillingCurrency",
        "billingperiodend": "BillingPeriodEnd",
        "billingperiodstart": "BillingPeriodStart",
        "chargecategory": "ChargeCategory",
        "chargeclass": "ChargeClass",
        "chargedescription": "ChargeDescription",
        "chargefrequency": "ChargeFrequency",
        "chargeperiodend": "ChargePeriodEnd",
        "chargeperiodstart": "ChargePeriodStart",
        "consumedquantity": "ConsumedQuantity",
        "consumedunit": "ConsumedUnit",
        "contractedcost": "ContractedCost",
        "contractedunitprice": "ContractedUnitPrice",
        "effectivecost": "EffectiveCost",
        "listcost": "ListCost",
        "listunitprice": "ListUnitPrice",
        "pricingcategory": "PricingCategory",
        "pricingquantity": "PricingQuantity",
        "pricingunit": "PricingUnit",
        "providername": "ProviderName",
        "regionid": "RegionId",
        "regionname": "RegionName",
        "resourceid": "ResourceId",
        "resourcename": "ResourceName",
        "resourcetype": "ResourceType",
        "servicecategory": "ServiceCategory",
        "servicename": "ServiceName",
        "subaccountid": "SubAccountId",
        "subaccountname": "SubAccountName",
        "tags": "Tags",
        "skuid": "SkuId",
        "skupriceid": "SkuPriceId",
        "invoiceissuername": "InvoiceIssuerName",
        "publishername": "PublisherName",
    }
    df.rename(columns=focus_renames, inplace=True)
    df["_tags"] = df["Tags"].apply(parse_tags) if "Tags" in df.columns else [{}] * len(df)
    return df


# ─────────────────────────────────────────────
# Node Creation Queries (Cypher)
# ─────────────────────────────────────────────

def create_billing_account(session, row):
    acct_id = safe_str(row.get("BillingAccountId"))
    if not acct_id:
        return None
    cypher = """
    MERGE (a:BillingAccount {billingAccountId: $id})
    SET a.billingAccountName = $name,
        a.provider = $provider,
        a.description = 'Billing account: ' + $name
    RETURN a
    """
    session.run(cypher, id=acct_id,
                name=safe_str(row.get("BillingAccountName")) or acct_id,
                provider=row.get("_source", "unknown"))
    return acct_id


def create_sub_account(session, row):
    sub_id = safe_str(row.get("SubAccountId"))
    if not sub_id:
        return None
    cypher = """
    MERGE (s:SubAccount {subAccountId: $id})
    SET s.subAccountName = $name,
        s.description = 'Sub-account: ' + $name
    RETURN s
    """
    session.run(cypher, id=sub_id,
                name=safe_str(row.get("SubAccountName")) or sub_id)
    return sub_id


def create_billing_period(session, row):
    period_start = safe_str(row.get("BillingPeriodStart"))
    if not period_start:
        return None
    cypher = """
    MERGE (p:BillingPeriod {start: $start})
    SET p.end = $end,
        p.description = 'Billing period: ' + $start + ' to ' + $end
    RETURN p
    """
    session.run(cypher, start=period_start,
                end=safe_str(row.get("BillingPeriodEnd")) or "")
    return period_start


def create_service(session, row):
    svc_name = safe_str(row.get("ServiceName"))
    if not svc_name:
        svc_name = "Unknown Service"
    cypher = """
    MERGE (s:Service {serviceName: $name})
    SET s.serviceCategory = $category,
        s.provider = $provider,
        s.description = $name + ' (' + $category + ') — ' + $provider
    RETURN s
    """
    session.run(cypher, name=svc_name,
                category=safe_str(row.get("ServiceCategory")) or "Other",
                provider=row.get("_source", "unknown"))
    return svc_name


def create_location(session, row):
    region_id = safe_str(row.get("RegionId"))
    if not region_id:
        return None
    cypher = """
    MERGE (l:Location {regionId: $rid})
    SET l.regionName = $rname,
        l.availabilityZone = $az,
        l.description = 'Region: ' + $rname
    RETURN l
    """
    session.run(cypher, rid=region_id,
                rname=safe_str(row.get("RegionName")) or region_id,
                az=safe_str(row.get("AvailabilityZone")))
    return region_id


def create_resource(session, row):
    resource_id = safe_str(row.get("ResourceId"))
    if not resource_id:
        resource_id = make_id(row.get("ResourceName"), row.get("ServiceName"), row.get("_source"))
    cypher = """
    MERGE (r:Resource {resourceId: $rid})
    SET r.resourceName = $rname,
        r.resourceType = $rtype,
        r.description = $rtype + ': ' + $rname
    RETURN r
    """
    session.run(cypher, rid=resource_id,
                rname=safe_str(row.get("ResourceName")) or "unnamed",
                rtype=safe_str(row.get("ResourceType")) or "unknown")
    return resource_id


def create_charge(session, row, record_id):
    charge_id = make_id(record_id, row.get("ChargeCategory"), row.get("ChargeFrequency"))
    desc = safe_str(row.get("ChargeDescription")) or ""
    cypher = """
    MERGE (c:Charge {chargeId: $cid})
    SET c.chargeCategory = $category,
        c.chargeFrequency = $frequency,
        c.chargeDescription = $description,
        c.chargeClass = $class,
        c.description = $description
    RETURN c
    """
    session.run(cypher, cid=charge_id,
                category=safe_str(row.get("ChargeCategory")) or "Usage",
                frequency=safe_str(row.get("ChargeFrequency")) or "Usage-Based",
                description=desc[:500] if desc else "",
                **{"class": safe_str(row.get("ChargeClass"))})
    return charge_id


def create_vendor_attrs(session, row, record_id, source):
    attr_id = make_id("vendor", record_id, source)
    if source == "aws":
        cypher = """
        MERGE (v:VendorAttrsAWS {attrId: $aid})
        SET v.x_ServiceCode = $service_code,
            v.x_UsageType = $usage_type,
            v.x_Operation = $operation,
            v.provider = 'aws',
            v.description = 'AWS vendor attrs: ' + $service_code
        RETURN v
        """
        session.run(cypher, aid=attr_id,
                    service_code=safe_str(row.get("x_ServiceCode")) or "",
                    usage_type=safe_str(row.get("x_UsageType")) or "",
                    operation=safe_str(row.get("x_Operation")) or "")
    else:
        cypher = """
        MERGE (v:VendorAttrsAzure {attrId: $aid})
        SET v.x_skuMeterCategory = $meter_cat,
            v.x_skuDescription = $sku_desc,
            v.x_resourceGroupName = $rg_name,
            v.x_costCenter = $cost_center,
            v.x_costAllocationRuleName = $alloc_rule,
            v.provider = 'azure',
            v.description = 'Azure vendor attrs: ' + $meter_cat
        RETURN v
        """
        session.run(cypher, aid=attr_id,
                    meter_cat=safe_str(row.get("x_skumetercategory")) or safe_str(row.get("x_skuMeterCategory")) or "",
                    sku_desc=safe_str(row.get("x_skudescription")) or safe_str(row.get("x_skuDescription")) or "",
                    rg_name=safe_str(row.get("x_resourcegroupname")) or "",
                    cost_center=safe_str(row.get("x_costcenter")) or safe_str(row.get("x_costCenter")) or "",
                    alloc_rule=safe_str(row.get("x_costallocationrulename")) or "")
    return attr_id


def create_tags(session, tags_dict, record_id):
    """Create Tag nodes from the parsed tags dictionary."""
    tag_ids = []
    for key, value in tags_dict.items():
        tag_id = make_id("tag", key, str(value))
        cypher = """
        MERGE (t:Tag {tagId: $tid})
        SET t.key = $key, t.value = $val,
            t.description = $key + '=' + $val
        """
        session.run(cypher, tid=tag_id, key=str(key), val=str(value))
        tag_ids.append((tag_id, key, value))
    return tag_ids


def create_cost_allocation(session, row):
    """Create CostAllocation node if allocation data is present."""
    alloc_rule = safe_str(row.get("x_costallocationrulename")) or safe_str(row.get("x_CostCategories"))
    if not alloc_rule:
        return None
    alloc_id = make_id("alloc", alloc_rule)
    cypher = """
    MERGE (ca:CostAllocation {allocationId: $aid})
    SET ca.allocationRuleName = $rule,
        ca.allocationMethod = $method,
        ca.isSharedCost = $shared,
        ca.description = 'Cost allocation: ' + $rule
    RETURN ca
    """
    session.run(cypher, aid=alloc_id, rule=alloc_rule,
                method="Proportional", shared=True)
    return alloc_id


# ─────────────────────────────────────────────
# Main Cost Record Creation + Relationships
# ─────────────────────────────────────────────

def create_cost_record_with_relationships(session, row, idx):
    """
    Core ingestion function — creates one CostRecord node
    and all its relationships in a single transaction.
    """
    source = row.get("_source", "unknown")
    record_id = make_id(source, idx,
                        row.get("BillingAccountId"),
                        row.get("ChargePeriodStart"),
                        row.get("ResourceId"))

    # ── Create the CostRecord node
    tags_dict = row.get("_tags", {})
    cypher_record = """
    MERGE (cr:CostRecord {recordId: $rid})
    SET cr.effectiveCost = $eff_cost,
        cr.billedCost = $billed_cost,
        cr.listCost = $list_cost,
        cr.contractedCost = $contracted_cost,
        cr.currency = $currency,
        cr.consumedQuantity = $consumed_qty,
        cr.consumedUnit = $consumed_unit,
        cr.pricingQuantity = $pricing_qty,
        cr.pricingUnit = $pricing_unit,
        cr.chargePeriodStart = $cp_start,
        cr.chargePeriodEnd = $cp_end,
        cr.source = $source,
        cr.tagApplication = $tag_app,
        cr.tagEnvironment = $tag_env,
        cr.tagCostCentre = $tag_cc,
        cr.description = $description
    RETURN cr
    """
    description = (
        f"{source.upper()} {safe_str(row.get('ServiceName'))} "
        f"{safe_str(row.get('ChargeCategory'))} "
        f"${safe_float(row.get('EffectiveCost')):.4f}"
    )
    session.run(cypher_record,
        rid=record_id,
        eff_cost=safe_float(row.get("EffectiveCost")),
        billed_cost=safe_float(row.get("BilledCost")),
        list_cost=safe_float(row.get("ListCost")),
        contracted_cost=safe_float(row.get("ContractedCost")),
        currency=safe_str(row.get("BillingCurrency")) or "USD",
        consumed_qty=safe_float(row.get("ConsumedQuantity")),
        consumed_unit=safe_str(row.get("ConsumedUnit")),
        pricing_qty=safe_float(row.get("PricingQuantity")),
        pricing_unit=safe_str(row.get("PricingUnit")),
        cp_start=safe_str(row.get("ChargePeriodStart")),
        cp_end=safe_str(row.get("ChargePeriodEnd")),
        source=source,
        tag_app=str(tags_dict.get("application", tags_dict.get("Application", ""))),
        tag_env=str(tags_dict.get("environment", tags_dict.get("Environment", ""))),
        tag_cc=str(tags_dict.get("cost_center", tags_dict.get("CostCentre", ""))),
        description=description
    )

    # ── Create dimension nodes
    acct_id = create_billing_account(session, row)
    sub_id = create_sub_account(session, row)
    period_start = create_billing_period(session, row)
    svc_name = create_service(session, row)
    region_id = create_location(session, row)
    resource_id = create_resource(session, row)
    charge_id = create_charge(session, row, record_id)
    attr_id = create_vendor_attrs(session, row, record_id, source)
    tag_ids = create_tags(session, tags_dict, record_id)
    alloc_id = create_cost_allocation(session, row)

    # ── Create relationships (Part B Step 2)
    if acct_id:
        session.run("""
            MATCH (cr:CostRecord {recordId: $rid}), (a:BillingAccount {billingAccountId: $aid})
            MERGE (cr)-[:BELONGS_TO_BILLING_ACCOUNT]->(a)
        """, rid=record_id, aid=acct_id)

    if sub_id:
        session.run("""
            MATCH (cr:CostRecord {recordId: $rid}), (s:SubAccount {subAccountId: $sid})
            MERGE (cr)-[:BELONGS_TO_SUBACCOUNT]->(s)
        """, rid=record_id, sid=sub_id)

    if period_start:
        session.run("""
            MATCH (cr:CostRecord {recordId: $rid}), (p:BillingPeriod {start: $pstart})
            MERGE (cr)-[:IN_BILLING_PERIOD]->(p)
        """, rid=record_id, pstart=period_start)

    if charge_id:
        session.run("""
            MATCH (cr:CostRecord {recordId: $rid}), (c:Charge {chargeId: $cid})
            MERGE (cr)-[:HAS_CHARGE]->(c)
        """, rid=record_id, cid=charge_id)

    if resource_id:
        session.run("""
            MATCH (cr:CostRecord {recordId: $rid}), (r:Resource {resourceId: $rrid})
            MERGE (cr)-[:INCURRED_BY]->(r)
        """, rid=record_id, rrid=resource_id)

        if svc_name:
            session.run("""
                MATCH (r:Resource {resourceId: $rrid}), (s:Service {serviceName: $sname})
                MERGE (r)-[:USES_SERVICE]->(s)
            """, rrid=resource_id, sname=svc_name)

        if region_id:
            session.run("""
                MATCH (r:Resource {resourceId: $rrid}), (l:Location {regionId: $lid})
                MERGE (r)-[:DEPLOYED_IN]->(l)
            """, rrid=resource_id, lid=region_id)

    if attr_id:
        label = "VendorAttrsAWS" if source == "aws" else "VendorAttrsAzure"
        session.run(f"""
            MATCH (cr:CostRecord {{recordId: $rid}}), (v:{label} {{attrId: $aid}})
            MERGE (cr)-[:HAS_VENDOR_ATTRS]->(v)
        """, rid=record_id, aid=attr_id)

    for tag_id, key, value in tag_ids:
        session.run("""
            MATCH (cr:CostRecord {recordId: $rid}), (t:Tag {tagId: $tid})
            MERGE (cr)-[:HAS_TAG]->(t)
        """, rid=record_id, tid=tag_id)

    if alloc_id:
        session.run("""
            MATCH (cr:CostRecord {recordId: $rid}), (ca:CostAllocation {allocationId: $aid})
            MERGE (cr)-[:ALLOCATED_VIA]->(ca)
        """, rid=record_id, aid=alloc_id)

    return record_id


# ─────────────────────────────────────────────
# Main Ingestion Runner
# ─────────────────────────────────────────────

def ingest_all():
    print(" Starting data ingestion into Neo4j...")
    driver = get_driver()

    try:
        driver.verify_connectivity()
        print("✓ Neo4j connected")
    except Exception as e:
        print(f"✗ Cannot connect to Neo4j: {e}")
        return

    # Load datasets
    print(f"\n Loading AWS data from {AWS_PATH}...")
    aws_df = load_aws_data(AWS_PATH)
    print(f"  → {len(aws_df)} records")

    print(f" Loading Azure data from {AZURE_PATH}...")
    azure_df = load_azure_data(AZURE_PATH)
    print(f"  → {len(azure_df)} records")

    all_rows = []
    for _, row in aws_df.iterrows():
        all_rows.append(row.to_dict())
    for _, row in azure_df.iterrows():
        all_rows.append(row.to_dict())

    print(f"\n Ingesting {len(all_rows)} total records into Neo4j...")
    success = 0
    errors = 0

    with driver.session() as session:
        for idx, row in enumerate(tqdm(all_rows, desc="Ingesting records")):
            try:
                create_cost_record_with_relationships(session, row, idx)
                success += 1
            except Exception as e:
                errors += 1
                if errors <= 5:  # Only show first 5 errors
                    print(f"\n  Error at row {idx}: {e}")

    print(f"\n Ingestion complete!")
    print(f"   ✓ {success} records ingested")
    print(f"   ✗ {errors} errors")

    # Print graph stats
    with driver.session() as session:
        print("\n Graph Statistics:")
        result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(n) as count ORDER BY count DESC")
        for record in result:
            print(f"   {record['label']}: {record['count']} nodes")
        result = session.run("MATCH ()-[r]->() RETURN type(r) as rel, count(r) as count ORDER BY count DESC")
        print("   Relationships:")
        for record in result:
            print(f"   [{record['rel']}]: {record['count']}")

    driver.close()
    print("\n Done! Next: python embeddings/embed_nodes.py")


if __name__ == "__main__":
    ingest_all()
