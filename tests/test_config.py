from django_migrate_sql.config import SQLItem


def test_dedent_simple_string():
    """Test that dedent works on a simple indented string."""
    item = SQLItem(
        "test_func",
        """
        CREATE FUNCTION test() RETURNS int AS $$
          BEGIN
            RETURN 1;
          END;
        $$ LANGUAGE plpgsql;
        """,
        reverse_sql="DROP FUNCTION test();",
    )
    # Should remove common leading whitespace
    assert item.sql.startswith("\nCREATE FUNCTION")
    assert "  BEGIN" in item.sql
    assert item.reverse_sql == "DROP FUNCTION test();"


def test_dedent_reverse_sql():
    """Test that dedent works on reverse_sql."""
    item = SQLItem(
        "test_func",
        "CREATE FUNCTION test() RETURNS int AS $$ BEGIN RETURN 1; END; $$ LANGUAGE plpgsql;",
        reverse_sql="""
            DROP FUNCTION test();
        """,
    )
    assert item.reverse_sql.strip() == "DROP FUNCTION test();"


def test_dedent_with_tuple_sql():
    """Test that dedent works with tuple format (sql with parameters)."""
    item = SQLItem(
        "test_func",
        [
            (
                """
                CREATE FUNCTION test(min_val int) RETURNS int AS $$
                  BEGIN
                    RETURN min_val + %s;
                  END;
                $$ LANGUAGE plpgsql;
                """,
                [5],
            )
        ],
    )
    # Should dedent the SQL string in the tuple
    assert isinstance(item.sql, list)
    assert len(item.sql) == 1
    sql_text, params = item.sql[0]
    assert sql_text.startswith("\nCREATE FUNCTION")
    assert params == [5]


def test_dedent_preserves_single_line():
    """Test that single-line SQL strings work correctly."""
    item = SQLItem(
        "test_func",
        "CREATE FUNCTION test() RETURNS int AS $$ BEGIN RETURN 1; END; $$ LANGUAGE plpgsql;",
        reverse_sql="DROP FUNCTION test();",
    )
    assert item.sql == "CREATE FUNCTION test() RETURNS int AS $$ BEGIN RETURN 1; END; $$ LANGUAGE plpgsql;"
    assert item.reverse_sql == "DROP FUNCTION test();"


def test_dedent_with_no_indentation():
    """Test that SQL without indentation is not affected."""
    sql = "CREATE FUNCTION test() RETURNS int AS $$ BEGIN RETURN 1; END; $$ LANGUAGE plpgsql;"
    item = SQLItem("test_func", sql, reverse_sql="DROP FUNCTION test();")
    assert item.sql == sql


def test_dedent_with_dependencies():
    """Test that dedent works with dependencies specified."""
    item = SQLItem(
        "test_func",
        """
        CREATE FUNCTION test() RETURNS mytype AS $$
          BEGIN
            RETURN (1, 'test')::mytype;
          END;
        $$ LANGUAGE plpgsql;
        """,
        reverse_sql="DROP FUNCTION test();",
        dependencies=[("test_app", "mytype")],
    )
    assert item.sql.startswith("\nCREATE FUNCTION")
    assert item.dependencies == [("test_app", "mytype")]


def test_dedent_with_replace_flag():
    """Test that dedent works with replace flag."""
    item = SQLItem(
        "test_func",
        """
        CREATE OR REPLACE FUNCTION test() RETURNS int AS $$
          BEGIN
            RETURN 1;
          END;
        $$ LANGUAGE plpgsql;
        """,
        reverse_sql="DROP FUNCTION test();",
        replace=True,
    )
    assert item.sql.startswith("\nCREATE OR REPLACE FUNCTION")
    assert item.replace is True


def test_dedent_with_list_of_strings():
    """Test that dedent works with a list containing plain strings (not tuples)."""
    item = SQLItem(
        "test_func",
        [
            """
            CREATE FUNCTION test() RETURNS int AS $$
              BEGIN
                RETURN 1;
              END;
            $$ LANGUAGE plpgsql;
            """
        ],
    )
    assert isinstance(item.sql, list)
    assert len(item.sql) == 1
    assert item.sql[0].startswith("\nCREATE FUNCTION")


def test_dedent_with_none_sql():
    """Test that None sql is handled correctly."""
    # This tests the edge case where sql might be None
    # In practice, this shouldn't happen but we test the return sql path
    item = SQLItem(
        "test_func",
        "CREATE FUNCTION test() RETURNS int AS $$ BEGIN RETURN 1; END; $$ LANGUAGE plpgsql;",
        reverse_sql=None,
    )
    assert item.reverse_sql is None

    # Test with integer - should be returned unchanged
    item = SQLItem(
        "test_func",
        123,
    )
    assert item.sql == 123
