import sys, os
sys.path.insert(0, os.path.abspath("."))

cmd = sys.argv[1] if len(sys.argv) > 1 else ""

if cmd == "schema":
    from graph.schema import run_setup
    run_setup()

elif cmd == "ingest":
    from graph.ingest import ingest_all
    ingest_all()

elif cmd == "embed":
    from embeddings.embed_nodes import run_embeddings
    run_embeddings()

elif cmd == "test":
    from tests.test_queries import run_all_tests
    run_all_tests()

elif cmd == "check":
    from graph.schema import get_driver
    d = get_driver()
    with d.session() as s:
        print("CostRecords:     ", s.run("MATCH (n:CostRecord) RETURN count(n) as c").single()["c"])
        print("Services:        ", s.run("MATCH (n:Service) RETURN count(n) as c").single()["c"])
        print("With embeddings: ", s.run("MATCH (n:Service) WHERE n.embedding IS NOT NULL RETURN count(n) as c").single()["c"])
        print("FOCUSColumns:    ", s.run("MATCH (n:FOCUSColumn) RETURN count(n) as c").single()["c"])
        print("Relationships:   ", s.run("MATCH ()-[r]->() RETURN count(r) as c").single()["c"])
    d.close()
    print("Done.")

else:
    print("Usage: python run.py [schema|ingest|embed|test|check]")