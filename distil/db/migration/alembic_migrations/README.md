<!--
Copyright 2012 New Dream Network, LLC (DreamHost)

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
-->

The migrations in `alembic_migrations/versions` contain the changes needed to migrate
between Distil database revisions. A migration occurs by executing a script that
details the changes needed to upgrade or downgrade the database. The migration scripts
are ordered so that multiple scripts can run sequentially. The scripts are executed by
Distil's migration wrapper which uses the Alembic library to manage the migration. Distil
supports migration from Icehouse or later.

You can upgrade to the latest database version via:
```
$ distil-db-manage --config-file /path/to/distil.conf upgrade head
```

To check the current database version:
```
$ distil-db-manage --config-file /path/to/distil.conf current
```

To create a script to run the migration offline:
```
$ distil-db-manage --config-file /path/to/distil.conf upgrade head --sql
```

To run the offline migration between specific migration versions:
```
$ distil-db-manage --config-file /path/to/distil.conf upgrade <start version>:<end version> --sql
```

Upgrade the database incrementally:
```
$ distil-db-manage --config-file /path/to/distil.conf upgrade --delta <# of revs>
```

Downgrade the database by a certain number of revisions:
```
$ distil-db-manage --config-file /path/to/distil.conf downgrade --delta <# of revs>
```

Create new revision:
```
$ distil-db-manage --config-file /path/to/distil.conf revision -m "description of revision" --autogenerate
```

Create a blank file:
```
$ distil-db-manage --config-file /path/to/distil.conf revision -m "description of revision"
```

This command does not perform any migrations, it only sets the revision.
Revision may be any existing revision. Use this command carefully.
```
$ distil-db-manage --config-file /path/to/distil.conf stamp <revision>
```

To verify that the timeline does branch, you can run this command:
```
$ distil-db-manage --config-file /path/to/distil.conf check_migration
```

If the migration path does branch, you can find the branch point via:
```
$ distil-db-manage --config-file /path/to/distil.conf history
```
