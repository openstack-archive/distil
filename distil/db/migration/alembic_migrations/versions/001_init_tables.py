# Copyright 2014 OpenStack Foundation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Juno release

Revision ID: 001
Revises: None
Create Date: 2014-04-01 20:46:25.783444

"""

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None

from alembic import op
import sqlalchemy as sa
from distil.db.sqlalchemy import model_base

MYSQL_ENGINE = 'InnoDB'
MYSQL_CHARSET = 'utf8'


def upgrade():
    op.create_table('tenants',
                    sa.Column('id', sa.String(length=100), nullable=False),
                    sa.Column('name', sa.String(length=100), nullable=False),
                    sa.Column('info', model_base.JSONEncodedDict(),
                              nullable=True),
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('last_collected', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    mysql_engine=MYSQL_ENGINE,
                    mysql_charset=MYSQL_CHARSET)

    op.create_table('resources',
                    sa.Column('id', sa.String(length=100)),
                    sa.Column('tenant_id', sa.String(length=100),
                              nullable=False),
                    sa.Column('info', model_base.JSONEncodedDict(),
                              nullable=True),
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('id', 'tenant_id'),
                    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
                    mysql_engine=MYSQL_ENGINE,
                    mysql_charset=MYSQL_CHARSET)

    op.create_table('usage_entry',
                    sa.Column('service', sa.String(length=100),
                              primary_key=True),
                    sa.Column('unit', sa.String(length=100),
                              nullable=False),
                    sa.Column('volume', sa.Numeric(precision=20, scale=2),
                              nullable=True),
                    sa.Column('tenant_id', sa.String(length=100),
                              primary_key=True, nullable=False),
                    sa.Column('resource_id', sa.String(length=100),
                              primary_key=True, nullable=False),
                    sa.Column('start_at', sa.DateTime(), primary_key=True,
                              nullable=True),
                    sa.Column('end_at', sa.DateTime(), primary_key=True,
                              nullable=True),
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
                    sa.ForeignKeyConstraint(['resource_id'],
                                            ['resources.id'], ),
                    mysql_engine=MYSQL_ENGINE,
                    mysql_charset=MYSQL_CHARSET)

    op.create_table('sales_orders',
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('tenant_id', sa.String(length=64),
                              nullable=False, primary_key=True),
                    sa.Column('start_at', sa.DateTime(), primary_key=True,
                              nullable=True),
                    sa.Column('end_at', sa.DateTime(), primary_key=True,
                              nullable=True),
                    sa.PrimaryKeyConstraint('id', 'tenant_id', 'start_at',
                                            'end_at'),
                    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
                    mysql_engine=MYSQL_ENGINE,
                    mysql_charset=MYSQL_CHARSET)

    op.create_table('distil_last_run',
                    sa.Column('id', sa.Integer,
                              sa.Sequence("last_run_id_seq"),
                              primary_key=True,),
                    sa.Column('last_run', sa.DateTime(), nullable=True),
                    mysql_engine=MYSQL_ENGINE,
                    mysql_charset=MYSQL_CHARSET)


def downgrade():
    op.drop_table('tenants')
    op.drop_table('usage_entry')
    op.drop_table('resources')
    op.drop_table('distil_last_run')
    op.drop_table('sales_orders')