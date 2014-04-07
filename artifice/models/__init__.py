from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Text, DateTime, Numeric, ForeignKey, String
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

from sqlalchemy import event, DDL

from sqlalchemy.orm import relationship
from sqlalchemy.schema import ForeignKeyConstraint

# Version digit.
__VERSION__ = 1.0


Base = declarative_base()


class _Version(Base):
    """
    A model that knows what version we are, stored in the DB.
    """
    __tablename__ = "artifice_database_version"
    id = Column(String(10), primary_key=True)


class Resource(Base):
    """Database model for storing metadata associated with a resource."""
    __tablename__ = 'resources'
    id = Column(String(100), primary_key=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id"), primary_key=True)
    info = Column(Text)
    created = Column(DateTime, nullable=False)


class UsageEntry(Base):
    """Simplified data store of usage information for a given service,
       in a resource, in a tenant. Similar to ceilometer datastore,
       but stores local transformed data."""
    __tablename__ = 'usage'

    # Service is things like incoming vs. outgoing, as well as instance
    # flavour
    service = Column(String(100), primary_key=True)
    volume = Column(Numeric(precision=20, scale=2), nullable=False)
    resource_id = Column(String(100), primary_key=True)
    tenant_id = Column(String(100), primary_key=True)
    start = Column(DateTime, nullable=False, primary_key=True)
    end = Column(DateTime, nullable=False, primary_key=True)
    created = Column(DateTime, nullable=False)

    resource = relationship(Resource,
                            primaryjoin=(resource_id == Resource.id))
    tenant = relationship(Resource,
                          primaryjoin=(tenant_id == Resource.tenant_id))

    __table_args__ = (ForeignKeyConstraint(
        ["resource_id", "tenant_id"],
        ["resources.id", "resources.tenant_id"],
        name="fk_resource_constraint"
    ),
    )

    @hybrid_property
    def length(self):
        return self.end - self.start

    @hybrid_method
    def intersects(self, other):
        return (self.start <= other.end and other.start <= self.end)


class Tenant(Base):
    """Model for storage of metadata related to a tenant."""
    __tablename__ = 'tenants'
    # ID is a uuid
    id = Column(String(100), primary_key=True, nullable=False)
    name = Column(Text, nullable=False)
    info = Column(Text)
    created = Column(DateTime, nullable=False)

    resources = relationship(Resource, backref="tenant")


class SalesOrder(Base):
    """Historic billing periods so that tenants
       cannot be rebilled accidentally."""
    __tablename__ = 'sales_orders'
    tenant_id = Column(
        String(100),
        ForeignKey("tenants.id"),
        primary_key=True)
    start = Column(DateTime, nullable=False, primary_key=True)
    end = Column(DateTime, nullable=False, primary_key=True)

    tenant = relationship("Tenant")

    @hybrid_property
    def length(self):
        return self.end - self.start

    @hybrid_method
    def intersects(self, other):
        return (self.start <= other.end and other.start <= self.end)

# Create a trigger in MySQL that enforces our range overlap constraints,
# since MySQL lacks a native range overlap type.

# Mysql trigger:

mysql_table_triggers = {
    UsageEntry.__table__: """
            CREATE TRIGGER %(table)s_%(funcname)s_range_constraint
               BEFORE %(type)s ON `%(table)s`
               FOR EACH ROW
               BEGIN
                DECLARE existing INT;
                SET existing = ( SELECT COUNT(*) FROM `%(table)s` t
                         WHERE ( NEW.start <= t.end
                                 AND t.start <= NEW.end )
                           AND service = NEW.service
                           AND tenant_id = NEW.tenant_id
                           AND resource_id = NEW.resource_id );
                IF existing > 0 THEN
                    SET NEW.start = NULL;
                    SET NEW.end = NULL;
                END IF;
               END;""",
    SalesOrder.__table__: """
            CREATE TRIGGER %(table)s_%(funcname)s_range_constraint
               BEFORE %(type)s ON `%(table)s`
               FOR EACH ROW
               BEGIN
                DECLARE existing INT;
                SET existing = ( SELECT COUNT(*) FROM `%(table)s` t
                         WHERE ( NEW.start <= t.end
                                 AND t.start <= NEW.end )
                           AND tenant_id = NEW.tenant_id );
                IF existing > 0 THEN
                    SET NEW.start = NULL;
                    SET NEW.end = NULL;
                END IF;
               END;
"""
}

# before insert

funcmaps = {"INSERT": "entry", "UPDATE": "change"}
for table in (SalesOrder.__table__, UsageEntry.__table__):
    for type_ in ("INSERT", "UPDATE"):
        event.listen(
            table,
            "after_create",
            DDL(mysql_table_triggers[table] % {
                "table": table,
                "type": type_,
                "funcname": funcmaps[type_]}).
            execute_if(dialect="mysql"))


# And the postgres constraints
# Ideally this would use Postgres' exclusion constraints and a TSRange type.
# This is currently not feasible because I can't find a way to emit different
# DDL for MySQL and Postgres to support the varying concepts
# (single vs. dual columns).

pgsql_trigger_funcs = {
    UsageEntry.__table__: """
CREATE FUNCTION %(table)s_exclusion_constraint_trigger() RETURNS trigger AS $trigger$
    DECLARE
        existing INTEGER = 0;
    BEGIN
        SELECT count(*) INTO existing FROM %(table)s t
         WHERE t.service = NEW.service
           AND t.tenant_id = NEW.tenant_id
           AND t.resource_id = NEW.resource_id
           AND ( NEW.start <= t."end"
                 AND t.start <= NEW."end" );
        IF existing > 0 THEN
            RAISE SQLSTATE '23P01';
            RETURN NULL;
        END IF;
        RETURN NEW;
    END;
$trigger$ LANGUAGE PLPGSQL;""",
    SalesOrder.__table__: """
CREATE FUNCTION %(table)s_exclusion_constraint_trigger() RETURNS trigger AS $trigger$
    DECLARE
        existing INTEGER = 0;
    BEGIN
        SELECT count(*) INTO existing FROM %(table)s t
         WHERE t.tenant_id = NEW.tenant_id
           AND ( NEW.start <= t."end"
                 AND t.start <= NEW."end" );
        IF existing > 0 THEN
            RAISE SQLSTATE '23P01';
            RETURN NULL;
        END IF;
        RETURN NEW;
    END;
$trigger$ LANGUAGE PLPGSQL;"""
}

pgsql_trigger = """
CREATE TRIGGER %(table)s_exclusion_trigger BEFORE INSERT OR UPDATE ON %(table)s
    FOR EACH ROW EXECUTE PROCEDURE %(table)s_exclusion_constraint_trigger();
"""

for table in (UsageEntry.__table__, SalesOrder.__table__):
    event.listen(
        table,
        "after_create",
        DDL(pgsql_trigger_funcs[table] % {
            "table": table
            }).execute_if(dialect="postgresql")
    )
    event.listen(
        table,
        "after_create",
        DDL(pgsql_trigger % {
            "table": table
            }
            ).execute_if(dialect="postgresql")
    )

# Create the PGSQL secondary trigger for sales order overlaps, for
# the usage entry


pgsql_secondary_trigger = """
CREATE TRIGGER %(table)s_secondary_exclusion_trigger BEFORE INSERT OR UPDATE ON %(table)s
    FOR EACH ROW EXECUTE PROCEDURE %(secondary_table)s_exclusion_constraint_trigger();
"""

event.listen(
    UsageEntry.__table__,
    "after_create",
    DDL(pgsql_secondary_trigger % {
        "table": UsageEntry.__table__,
        "secondary_table": SalesOrder.__table__
        }).execute_if(dialect="postgresql")
)


event.listen(
    UsageEntry.__table__,
    "before_drop",
    DDL("""DROP TRIGGER %(table)s_secondary_exclusion_trigger ON %(table)s""" %
        {"table": UsageEntry.__table__,
         "secondary_table": SalesOrder.__table__
         }).execute_if(dialect="postgresql")
)

event.listen(
    UsageEntry.__table__,
    "before_drop",
    DDL("DROP TRIGGER %(table)s_exclusion_trigger ON %(table)s" %
        {"table": UsageEntry.__tablename__}).execute_if(dialect="postgresql")
)

event.listen(
    UsageEntry.__table__,
    "before_drop",
    DDL("DROP FUNCTION %s_exclusion_constraint_trigger()" %
        UsageEntry.__tablename__).execute_if(dialect="postgresql")
)

event.listen(
    UsageEntry.__table__,
    "before_drop",
    DDL("DROP TRIGGER %(table)s_exclusion_trigger ON %(table)s" % {
        "table": SalesOrder.__tablename__}).execute_if(dialect="postgresql")
)

event.listen(
    UsageEntry.__table__,
    "before_drop",
    DDL("DROP FUNCTION %s_exclusion_constraint_trigger()" %
        SalesOrder.__tablename__).execute_if(dialect="postgresql")
)


def insert_into_version(target, connection, **kw):
    connection.execute("INSERT INTO %s (id) VALUES (%s)" %
                            (target.name, __VERSION__))

event.listen(
    _Version.__table__,
    "after_create",
    insert_into_version
)
