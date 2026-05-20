def pre_init_hook(env):
    env.cr.execute(
        """
        SELECT
            child.relname AS rel_table,
            child_att.attname AS rel_column,
            parent.relname AS parent_table,
            parent_att.attname AS parent_column
        FROM pg_constraint fk
        JOIN pg_class child ON child.oid = fk.conrelid
        JOIN pg_class parent ON parent.oid = fk.confrelid
        JOIN pg_attribute child_att
            ON child_att.attrelid = child.oid
            AND child_att.attnum = ANY (fk.conkey)
        JOIN pg_attribute parent_att
            ON parent_att.attrelid = parent.oid
            AND parent_att.attnum = ANY (fk.confkey)
        WHERE fk.contype = 'f'
          AND fk.connamespace = 'public'::regnamespace
          AND child.relname LIKE '%rel%'
        """
    )
    for rel_table, rel_column, parent_table, parent_column in env.cr.fetchall():
        env.cr.execute(
            f"""
            DELETE FROM "{rel_table}" rel
            WHERE NOT EXISTS (
                SELECT 1
                FROM "{parent_table}" parent
                WHERE parent."{parent_column}" = rel."{rel_column}"
            )
            """
        )
