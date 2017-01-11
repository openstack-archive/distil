# Copyright 2017 OpenStack Foundation.
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

"""add-project-lock-table

Revision ID: 002
Revises: 001
Create Date: 2017-01-11 11:45:05.107888

"""

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'project_locks',
        sa.Column('created', sa.DateTime(), nullable=False),
        sa.Column('project_id', sa.String(length=100), nullable=False),
        sa.Column('owner', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('project_id'),
    )
