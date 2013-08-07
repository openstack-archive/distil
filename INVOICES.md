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

