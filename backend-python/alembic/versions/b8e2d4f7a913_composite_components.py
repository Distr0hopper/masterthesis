"""composite components: tools and workflows as children of components

Turns the two parallel stacks into one composite hierarchy - CWL's Process with its
CommandLineTool/ExpressionTool and Workflow subclasses:

- `components` becomes the shared base of both kinds (discriminated by `kind`); the
  tool-only columns move to the new 1:1 detail table `tools`.
- every workflow gets a `components` row - same uuid, so URLs, the builder-draft link and
  every step FK stay valid - and `workflows` is reduced to its 1:1 detail row.
- `workflow_domains`/`workflow_files` fold into `component_domains`/`component_files`,
  and workflows gain `parameters` (their ports), parsed from the stored pipeline CWL.
- workflows join the name+version lineage (all existing ones become version 1), and
  their status maps onto the shared one: validated -> published, pending -> draft.
- `workflow_steps.workflow_id` now references the workflow detail row, while
  `component_id` may reference either kind - which is what makes nesting possible.
- favorites always reference a component lineage name; the entity_type column goes.

Data-preserving: converts in place, never drops a populated table before its rows are
copied.

Revision ID: b8e2d4f7a913
Revises: f3a8d61c9b27
Create Date: 2026-10-02 00:00:00.000000

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b8e2d4f7a913'
down_revision: Union[str, Sequence[str], None] = 'f3a8d61c9b27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    _split_tool_columns()
    _move_workflows_into_components()
    _backfill_workflow_ports()
    _key_favorites_by_component_name()


def _split_tool_columns() -> None:
    op.add_column('components', sa.Column('kind', sa.String(), nullable=False, server_default='tool'))
    # every existing row was a tool; new rows must always say what they are
    op.alter_column('components', 'kind', server_default=None)

    op.create_table(
        'tools',
        sa.Column('component_id', sa.Uuid(), sa.ForeignKey('components.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('cwl_type', sa.String(), nullable=True),
        sa.Column('dockerfile_content', sa.Text(), nullable=True),
        sa.Column('docker_pull_reference', sa.String(), nullable=True),
    )
    op.execute(
        """
        INSERT INTO tools (component_id, cwl_type, dockerfile_content, docker_pull_reference)
        SELECT id, cwl_type, dockerfile_content, docker_pull_reference FROM components
        """
    )
    op.drop_column('components', 'cwl_type')
    op.drop_column('components', 'dockerfile_content')
    op.drop_column('components', 'docker_pull_reference')


def _move_workflows_into_components() -> None:
    # the old table steps aside so the detail table can take its name. Renaming a table
    # keeps its index names, so the two that would collide are renamed/dropped first.
    op.execute('ALTER INDEX workflows_pkey RENAME TO workflows_old_pkey')
    op.drop_index('ix_workflows_draft_id', table_name='workflows')
    op.drop_constraint('uq_workflows_name', 'workflows', type_='unique')
    op.rename_table('workflows', 'workflows_old')

    # names are one lineage key across both kinds now - a workflow that shares its name
    # with a tool lineage is renamed rather than silently merged into it
    op.execute(
        """
        UPDATE workflows_old w SET name = w.name || ' (workflow)'
        WHERE EXISTS (SELECT 1 FROM components c WHERE c.name = w.name)
        """
    )
    op.execute(
        """
        INSERT INTO components (
            id, kind, name, version, description, created_by_id, cwl_content,
            source, status, created_at, updated_at
        )
        SELECT
            id, 'workflow', name, 1, description, created_by_id, cwl_content, source,
            CASE status WHEN 'validated' THEN 'published' ELSE 'draft' END,
            created_at, updated_at
        FROM workflows_old
        """
    )

    op.create_table(
        'workflows',
        sa.Column('component_id', sa.Uuid(), sa.ForeignKey('components.id', ondelete='CASCADE'), primary_key=True),
        sa.Column(
            'draft_id',
            sa.Uuid(),
            sa.ForeignKey('workflow_drafts.id', ondelete='SET NULL', name='fk_workflows_draft_id_workflow_drafts'),
            nullable=True,
        ),
    )
    op.create_index('ix_workflows_draft_id', 'workflows', ['draft_id'])
    op.execute('INSERT INTO workflows (component_id, draft_id) SELECT id, draft_id FROM workflows_old')

    op.execute(
        """
        INSERT INTO component_domains (component_id, domain)
        SELECT workflow_id, domain FROM workflow_domains
        """
    )
    op.execute(
        """
        INSERT INTO component_files (component_id, path, content)
        SELECT workflow_id, path, content FROM workflow_files
        """
    )
    op.drop_table('workflow_domains')
    op.drop_table('workflow_files')

    # the parent of a step is the workflow detail row now; the child (component_id) stays
    # pointed at components and so may be a tool or, nested, another workflow
    op.drop_constraint('workflow_steps_workflow_id_fkey', 'workflow_steps', type_='foreignkey')
    op.create_foreign_key(
        'workflow_steps_workflow_id_fkey',
        'workflow_steps',
        'workflows',
        ['workflow_id'],
        ['component_id'],
        ondelete='CASCADE',
    )
    op.drop_table('workflows_old')


def _backfill_workflow_ports() -> None:
    """Workflows had no parameters until now - parse them from each stored pipeline, with
    the same extractor every new component goes through. Format labels are left unresolved:
    that needs the format service, which a migration must not depend on."""
    # imported here, not at module level: alembic loads every revision file, and only this
    # data step needs the app
    from app.infrastructure.cwl.cwl_parser import extract_parameters, extract_schema_url
    from app.infrastructure.format_service.ontology import resolve_ontology_url

    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, cwl_content FROM components WHERE kind = 'workflow'")).all()
    parameters = sa.table(
        'parameters',
        sa.column('id', sa.Uuid()),
        sa.column('component_id', sa.Uuid()),
        sa.column('name', sa.String()),
        sa.column('cwl_type', sa.String()),
        sa.column('default_value', sa.String()),
        sa.column('description', sa.String()),
        sa.column('format', sa.String()),
        sa.column('direction', sa.String()),
    )
    for component_id, cwl_content in rows:
        try:
            extracted = extract_parameters(cwl_content)
        except ValueError:
            # an unreadable pipeline simply has no ports - it was stored before, so it must
            # not block the migration now
            continue
        if extracted:
            op.bulk_insert(
                parameters,
                [
                    {
                        'id': uuid.uuid4(),
                        'component_id': component_id,
                        'name': p.name,
                        'cwl_type': p.cwl_type,
                        'default_value': p.default_value,
                        'description': p.description,
                        'format': p.format,
                        'direction': p.direction.value,
                    }
                    for p in extracted
                ],
            )
        connection.execute(
            sa.text('UPDATE components SET ontology_url = :url WHERE id = :id'),
            {'url': resolve_ontology_url(extract_schema_url(cwl_content)), 'id': component_id},
        )


def _key_favorites_by_component_name() -> None:
    # workflow favorites pointed at the workflow's uuid; a lineage name is what both kinds use now
    op.execute(
        """
        UPDATE favorites f SET entity_ref = c.name
        FROM components c
        WHERE f.entity_type = 'WORKFLOW' AND c.id::text = f.entity_ref
        """
    )
    op.execute("DELETE FROM favorites WHERE entity_type = 'WORKFLOW' AND entity_ref NOT IN (SELECT name FROM components)")
    # a user may now hold the same name twice (once per old entity type) - keep one
    op.execute(
        """
        DELETE FROM favorites f USING favorites g
        WHERE f.user_id = g.user_id AND f.entity_ref = g.entity_ref
          AND f.entity_type = 'WORKFLOW' AND g.entity_type = 'COMPONENT'
        """
    )
    op.drop_constraint('favorites_pkey', 'favorites', type_='primary')
    op.drop_column('favorites', 'entity_type')
    op.alter_column('favorites', 'entity_ref', new_column_name='component_name')
    op.create_primary_key('favorites_pkey', 'favorites', ['user_id', 'component_name'])


def downgrade() -> None:
    """Best effort: workflows go back to their own table, but only the latest version of
    each lineage survives - the old schema has no versions, and its names are unique."""
    op.drop_constraint('favorites_pkey', 'favorites', type_='primary')
    op.alter_column('favorites', 'component_name', new_column_name='entity_ref')
    op.add_column('favorites', sa.Column('entity_type', sa.String(), nullable=False, server_default='COMPONENT'))
    op.alter_column('favorites', 'entity_type', server_default=None)
    op.execute(
        """
        UPDATE favorites f SET entity_type = 'WORKFLOW', entity_ref = c.id::text
        FROM (
            SELECT DISTINCT ON (name) id, name FROM components
            WHERE kind = 'workflow' ORDER BY name, version DESC
        ) c
        WHERE c.name = f.entity_ref
        """
    )
    op.create_primary_key('favorites_pkey', 'favorites', ['user_id', 'entity_type', 'entity_ref'])

    # nested steps (a workflow running a workflow) cannot exist in the old schema
    op.execute(
        """
        DELETE FROM workflow_steps s USING components c
        WHERE c.id = s.component_id AND c.kind = 'workflow'
        """
    )
    # older workflow versions are dropped, cascading their steps, domains and files
    op.execute(
        """
        DELETE FROM components c USING components newer
        WHERE c.kind = 'workflow' AND newer.kind = 'workflow'
          AND newer.name = c.name AND newer.version > c.version
        """
    )

    op.rename_table('workflows', 'workflows_detail')
    op.execute('ALTER INDEX workflows_pkey RENAME TO workflows_detail_pkey')
    op.drop_index('ix_workflows_draft_id', table_name='workflows_detail')
    op.create_table(
        'workflows',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(length=2000), nullable=True),
        sa.Column('created_by_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('cwl_content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending_validation'),
        sa.Column('source', sa.String(), nullable=False, server_default='manual_upload'),
        sa.Column(
            'draft_id',
            sa.Uuid(),
            sa.ForeignKey('workflow_drafts.id', ondelete='SET NULL', name='fk_workflows_draft_id_workflow_drafts_old'),
            nullable=True,
        ),
        sa.UniqueConstraint('name', name='uq_workflows_name'),
    )
    op.create_index('ix_workflows_draft_id', 'workflows', ['draft_id'])
    op.execute(
        """
        INSERT INTO workflows (id, name, description, created_by_id, cwl_content, created_at, updated_at,
                               status, source, draft_id)
        SELECT c.id, c.name, c.description, c.created_by_id, c.cwl_content, c.created_at, c.updated_at,
               CASE c.status WHEN 'published' THEN 'validated' ELSE 'pending_validation' END,
               c.source, d.draft_id
        FROM components c JOIN workflows_detail d ON d.component_id = c.id
        """
    )

    op.create_table(
        'workflow_domains',
        sa.Column('workflow_id', sa.Uuid(), sa.ForeignKey('workflows.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('domain', sa.String(), primary_key=True),
    )
    op.create_table(
        'workflow_files',
        sa.Column('workflow_id', sa.Uuid(), sa.ForeignKey('workflows.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('path', sa.String(), primary_key=True),
        sa.Column('content', sa.Text(), nullable=False),
    )
    op.execute(
        """
        INSERT INTO workflow_domains (workflow_id, domain)
        SELECT d.component_id, d.domain FROM component_domains d JOIN workflows w ON w.id = d.component_id
        """
    )
    op.execute(
        """
        INSERT INTO workflow_files (workflow_id, path, content)
        SELECT f.component_id, f.path, f.content FROM component_files f JOIN workflows w ON w.id = f.component_id
        """
    )

    op.drop_constraint('workflow_steps_workflow_id_fkey', 'workflow_steps', type_='foreignkey')
    op.create_foreign_key(
        'workflow_steps_workflow_id_fkey', 'workflow_steps', 'workflows', ['workflow_id'], ['id'], ondelete='CASCADE'
    )
    op.drop_table('workflows_detail')
    # cascades the workflows' domains, files and parameters off the base table
    op.execute("DELETE FROM components WHERE kind = 'workflow'")
    op.execute(
        """
        ALTER TABLE workflows
        RENAME CONSTRAINT fk_workflows_draft_id_workflow_drafts_old TO fk_workflows_draft_id_workflow_drafts
        """
    )

    op.add_column('components', sa.Column('cwl_type', sa.String(), nullable=True))
    op.add_column('components', sa.Column('dockerfile_content', sa.Text(), nullable=True))
    op.add_column('components', sa.Column('docker_pull_reference', sa.String(), nullable=True))
    op.execute(
        """
        UPDATE components c
        SET cwl_type = t.cwl_type, dockerfile_content = t.dockerfile_content,
            docker_pull_reference = t.docker_pull_reference
        FROM tools t WHERE t.component_id = c.id
        """
    )
    op.drop_table('tools')
    op.drop_column('components', 'kind')
