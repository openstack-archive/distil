# Invoice API

This document details how to add a new Invoice adapter to Artifice, enabling connection with arbitrary ERP systems.

## What Does Artifice Do

Artifice manages the connection from OpenStack Ceilometer to the ERP/billing system, managing data from Ceilometer in terms of a block (usually a month) of "billed time."

Artifice maintains its own storage to handle time that has been billed.

Artifice does not hold opinions on which ERP system should be used; OpenERP acts only as a reference implementation, detailing how an invoice could be billed.

Artifice makes the following assumptions:

* An invoice must be creatable
* An invoice must allow Sections to be declared
* An invoice must allow line items to be added
* An invoice must respond to cost(datacenter, name), returning a cost value
* An invoice must be commitable, saving it to the underlying ERP storage


## Implementation

Implementing an Artifice invoice object is intended to be simple:

    from artifice.invoice import Invoice
    class MyInvoice(Invoice):
        def __init__(self, tenant, config):
            pass

        def add_line(self, item):
            """item is a triple of datacenter, name, value"""
        def add_section(self, name):

            """Expected to create a subsection in the Invoice. Used for datacenter locations.
            """
        def commit(self):
            """Closes this invoice. Expects to save to the underlying ERP storage system.
            """

        def cost(self, datacenter, name):
            """
            Taking a datacenter and a meter name, expected to return a fixed value for the given month.
            :param datacenter
            :param name
            :returns float
            """

## Configuration

Configuration of the Invoice object is passed from the main Artifice configuration during Invoice initiation.

Configuration will be passed as-is from the main configuration to the Invoice system, allowing for arbitrary items to be passed through.

For example:

    [invoice:object]
    database_name="somedb"

or

    [invoice:object]
    url = "https://localhost:4567"

or

    [invoice:object]
    csv_directory = "/path/to/my/file"

## Usage and Declaration

Usage of the custom Invoice is controlled via the Artifice configuration file.

Under
    [main]

add the line:

    [main]
    invoice:object="path.to.my.object:MyInvoice"

similar to *paste*-style configuration items.


## Rates

Rate information is currently consumed from CSV files, dictated by the
configuration file in the [invoice_object] section.

This rates information applies solely (at present) to the CSV output module
for Artifice.

### Rate and Names Mapping files

#### Name mapping file

First, names must be mapped from the internal Ceilometer naming to a
user-friendly format.
This allows for a much simpler user interface, allowing for people to easily
determine what services they are taking advantage of on the Catalyst cloud
without needing to interpret internal names.

The naming file format is a |-delimited CSV file, consisting of:

    ceilometer name | user-facing name

An example file would be:

    m1.nano                        | VM instance, size nano
    network.incoming.bytes         | Incoming Network Usage
    network.outgoing.bytes         | Outgoing Network Usage
    storage.objects.size           | Object Storage Usage
    volume.size                    | Disk Volume, Size

Excess whitespace will be trimmed.

#### Rates Mapping File

The other half of the Rates system is the Rates mapping file.

This mapping describes, for a given region, the price multiplier per
unit per time that should be applied.

The default time range is a 10 minute time slice.

The rates mapping file is in the structure of:

    region | VM instance, size nano  | duration       | 100
    region | Incoming Network Usage  | bytes          | 120
    region | Outgoing Network Usage  | bytes          | 240
    region | Object Storage Usage    | bytes per hour | 300
    region | Disk Volume, Size       | bytes per hour | 320

The first column is the name of the region this rate should be used for.
This is **NOT CURRENTLY IMPLEMENTED.**

The second column is the name of the item being rated.
This is always the prettified name from the Names mapping file.

The third column is what is being measured, per time slice.

The fourth column is an integer or decimal value denoting the cost per time
slice.

The time slice width will be set in the config file. This is not currently
implemented.