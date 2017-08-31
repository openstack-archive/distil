========================
Team and repository tags
========================

.. image:: https://governance.openstack.org/badges/distil.svg
    :target: https://governance.openstack.org/tc/reference/tags/index.html

.. Change things from this point on

======
Distil
======

Distil is a service to provide easy interactions with ERP systems, by exposing
a configurable set of collection tools and transformers to make usable billing
data out of Ceilometer entries.

Distil provides a rest api to integrate with arbitrary ERP systems, and returns
quotations/invoices as json. What the ranges are, and how Ceilometer data is
aggregated is intended to be configurable, and defined in the configuration
file.

The Distil data store will prevent overlapping bills for a given tenant and
resource ever being stored, while still allowing for regeneration of a given
invoices.
