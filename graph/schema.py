"""
Part B – Knowledge Graph Construction in Neo4j
Step 1: Schema Setup — Constraints & Indexes
============================================
"""

import os
from dotenv import load_dotenv

load_dotenv()


def get_driver():
    """Create and return a Neo4j driver instance."""
    from neo4j import GraphDatabase
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    driver = GraphDatabase.driver(
        uri,
        auth=(user, password),
        encrypted=False                 
    )
    return driver


def setup_constraints(driver):
    """Create uniqueness constraints per FOCUS spec requirements."""
    constraints = [
        # BillingAccount — billingAccountId must be unique
        """CREATE CONSTRAINT billing_account_id IF NOT EXISTS
           FOR (n:BillingAccount) REQUIRE n.billingAccountId IS UNIQUE""",

        # SubAccount
        """CREATE CONSTRAINT sub_account_id IF NOT EXISTS
           FOR (n:SubAccount) REQUIRE n.subAccountId IS UNIQUE""",

        # Service
        """CREATE CONSTRAINT service_name IF NOT EXISTS
           FOR (n:Service) REQUIRE n.serviceName IS UNIQUE""",

        # Location / Region
        """CREATE CONSTRAINT region_id IF NOT EXISTS
           FOR (n:Location) REQUIRE n.regionId IS UNIQUE""",

        # Charge class unique by (category, frequency, description hash)
        # Resource unique by resourceId
        """CREATE CONSTRAINT resource_id IF NOT EXISTS
           FOR (n:Resource) REQUIRE n.resourceId IS UNIQUE""",

        # BillingPeriod unique by start date
        """CREATE CONSTRAINT billing_period_start IF NOT EXISTS
           FOR (n:BillingPeriod) REQUIRE n.start IS UNIQUE""",
    ]

    with driver.session() as session:
        for cypher in constraints:
            try:
                session.run(cypher)
                print(f"✓ Constraint: {cypher[:60]}...")
            except Exception as e:
                print(f"  (skipped) {e}")


def setup_indexes(driver):
    """Create standard and full-text search indexes."""
    indexes = [
        # Standard indexes for common query patterns
        """CREATE INDEX service_name_idx IF NOT EXISTS
           FOR (n:Service) ON (n.serviceName)""",

        """CREATE INDEX charge_period_idx IF NOT EXISTS
           FOR (n:BillingPeriod) ON (n.start)""",

        """CREATE INDEX service_category_idx IF NOT EXISTS
           FOR (n:Service) ON (n.serviceCategory)""",

        """CREATE INDEX resource_type_idx IF NOT EXISTS
           FOR (n:Resource) ON (n.resourceType)""",

        """CREATE INDEX charge_category_idx IF NOT EXISTS
           FOR (n:Charge) ON (n.chargeCategory)""",

        """CREATE INDEX cost_record_source_idx IF NOT EXISTS
           FOR (n:CostRecord) ON (n.source)""",

        """CREATE INDEX tag_key_idx IF NOT EXISTS
           FOR (n:Tag) ON (n.key)""",
    ]

    full_text_indexes = [
        # Full-text search indexes for semantic queries
        """CREATE FULLTEXT INDEX charge_description_ft IF NOT EXISTS
           FOR (n:Charge) ON EACH [n.chargeDescription]""",

        """CREATE FULLTEXT INDEX service_fulltext IF NOT EXISTS
           FOR (n:Service) ON EACH [n.serviceName, n.serviceCategory]""",

        """CREATE FULLTEXT INDEX resource_fulltext IF NOT EXISTS
           FOR (n:Resource) ON EACH [n.resourceName, n.resourceType]""",
    ]

    with driver.session() as session:
        for cypher in indexes + full_text_indexes:
            try:
                session.run(cypher)
                print(f"✓ Index: {cypher[:60]}...")
            except Exception as e:
                print(f"  (skipped) {e}")


def setup_vector_indexes(driver):
    """
    Create Neo4j vector indexes for semantic similarity search.
    Requires Neo4j 5.x with vector index support.
    Embedding dimension: 384 (all-MiniLM-L6-v2)
    """
    vector_indexes = [
        """CREATE VECTOR INDEX cost_record_embedding IF NOT EXISTS
           FOR (n:CostRecord) ON (n.embedding)
           OPTIONS {indexConfig: {
             `vector.dimensions`: 384,
             `vector.similarity_function`: 'cosine'
           }}""",

        """CREATE VECTOR INDEX service_embedding IF NOT EXISTS
           FOR (n:Service) ON (n.embedding)
           OPTIONS {indexConfig: {
             `vector.dimensions`: 384,
             `vector.similarity_function`: 'cosine'
           }}""",

        """CREATE VECTOR INDEX charge_embedding IF NOT EXISTS
           FOR (n:Charge) ON (n.embedding)
           OPTIONS {indexConfig: {
             `vector.dimensions`: 384,
             `vector.similarity_function`: 'cosine'
           }}""",

        """CREATE VECTOR INDEX location_embedding IF NOT EXISTS
           FOR (n:Location) ON (n.embedding)
           OPTIONS {indexConfig: {
             `vector.dimensions`: 384,
             `vector.similarity_function`: 'cosine'
           }}""",
    ]

    with driver.session() as session:
        for cypher in vector_indexes:
            try:
                session.run(cypher)
                print(f"✓ Vector index: {cypher[:60]}...")
            except Exception as e:
                print(f"  Vector index skipped (OK if Neo4j < 5.x): {e}")


def clear_database(driver, confirm=False):
    """  DANGER: Deletes ALL nodes and relationships. Use only for dev reset."""
    if not confirm:
        print("Pass confirm=True to actually clear the database.")
        return
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("  Database cleared.")


def run_setup():
    print(" Setting up Neo4j schema for Cloud Cost Knowledge Graph...")
    driver = get_driver()
    try:
        driver.verify_connectivity()
        print("✓ Neo4j connection successful")
    except Exception as e:
        print(f"✗ Cannot connect to Neo4j: {e}")
        print("  Make sure Neo4j Desktop is running and check your .env file")
        return

    setup_constraints(driver)
    setup_indexes(driver)
    setup_vector_indexes(driver)
    driver.close()
    print("\n Schema setup complete! You can now run: python graph/ingest.py")


if __name__ == "__main__":
    run_setup()
