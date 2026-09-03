import pytest
from app.services.query_planner_service import QueryPlannerService, QueryPlannerError

@pytest.fixture
def planner():
    # We don't need a real LLM for AST validation testing
    return QueryPlannerService(llm=None)

def test_valid_select(planner):
    sql = "SELECT id, name FROM authorized_table WHERE score > 90 LIMIT 10"
    allowed = {"authorized_table"}
    result = planner.validate_sql(sql, allowed)
    assert "SELECT" in result.upper()
    assert "LIMIT 10" in result.upper()

def test_missing_limit_injects_100(planner):
    sql = "SELECT id, name FROM authorized_table"
    allowed = {"authorized_table"}
    result = planner.validate_sql(sql, allowed)
    assert "LIMIT 100" in result.upper()

def test_limit_capped_at_100(planner):
    sql = "SELECT id FROM authorized_table LIMIT 500"
    allowed = {"authorized_table"}
    result = planner.validate_sql(sql, allowed)
    assert "LIMIT 100" in result.upper()

def test_dml_rejected(planner):
    allowed = {"authorized_table"}
    with pytest.raises(QueryPlannerError, match="Only SELECT statements are allowed"):
        planner.validate_sql("DELETE FROM authorized_table", allowed)
        
    with pytest.raises(QueryPlannerError, match="Only SELECT statements are allowed"):
        planner.validate_sql("DROP TABLE authorized_table", allowed)
        
    with pytest.raises(QueryPlannerError, match="Multiple SQL statements"):
        planner.validate_sql("SELECT * FROM authorized_table; DROP TABLE authorized_table;", allowed)

def test_unauthorized_table_rejected(planner):
    allowed = {"authorized_table"}
    with pytest.raises(QueryPlannerError, match="Unauthorized or unknown table referenced: secret_table"):
        planner.validate_sql("SELECT * FROM secret_table", allowed)

def test_adversarial_union(planner):
    allowed = {"authorized_table"}
    adversarial_sql = "SELECT id FROM authorized_table UNION SELECT password FROM users"
    with pytest.raises(QueryPlannerError, match="Unauthorized or unknown table referenced: users"):
        planner.validate_sql(adversarial_sql, allowed)

def test_adversarial_subquery(planner):
    allowed = {"authorized_table"}
    adversarial_sql = "SELECT * FROM authorized_table WHERE id IN (SELECT id FROM admin_users)"
    with pytest.raises(QueryPlannerError, match="Unauthorized or unknown table referenced: admin_users"):
        planner.validate_sql(adversarial_sql, allowed)

def test_adversarial_cte(planner):
    allowed = {"authorized_table"}
    adversarial_sql = '''
    WITH secret_data AS (
        SELECT * FROM credit_cards
    )
    SELECT * FROM authorized_table JOIN secret_data ON authorized_table.id = secret_data.id
    '''
    with pytest.raises(QueryPlannerError, match="Unauthorized or unknown table referenced: credit_cards"):
        planner.validate_sql(adversarial_sql, allowed)
