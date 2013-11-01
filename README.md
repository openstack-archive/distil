# Openstack-Artifice

## What

Artifice is a prototype of a data aggregation and billing generation layer, intended to tightly couple with the Openstack-Ceilometer 
project.

The Artifice layer is intended to store computed values for a known date range, and provide an easy, consistent API for injecting
billing information into arbitrary ERP systems; from CSV through OpenERP.
Time-series data for a given time period, a month, is compressed into a single billable item for that month, based on datacenter-based
rates information.

By not imposing logic beyond the concept of a dated invoice that covers a given range, Artifice tries to be unopinionated on how ERP 
must be handled.

What the ranges are, and how Ceilometer data is aggregated is intended to be configurable.

Artifice enforces its own rigid Postgresql-backed data store, used to store what data has been billed, and for what time range. This is used to prevent repeated billing of a range of data.

The Artifice data store will prevent overlapping bills for a given tenant and resource ever being stored, while still allowing for regeneration of a given invoice statement.

## Requirements:

Artifice requires:
  * Postgresql >= 9.1.
  * Python >=2.7.5, <3.0
  * Python modules:
    * pyaml
    * mock
    * requests
    *
  * OpenStack Grizzly. *currently untested with Havana*
  * Openstack-Keystone
  * Openstack-Ceilometer

## Configuration

Configuring Artifice is handled through its primary configuration file, stored in `/etc/openstack/artifice.conf`.

This is a yaml-format config file, in the format of:

    # Defines the database connection logic. This will be converted to a standard
    # database connection string.
    database:
      database: artifice
      host: localhost
      password: aurynn
      port: '5433'
      username: aurynn
    # Configuration passed to the invoice system. This is an arbitrary dictionary 
    # and may be anything that the invoice object may require.
    # This example is intended for the CSV module
    invoice:config:
      delimiter: ','
      output_file: '%(tenant)s-%(start)s-%(end)s.csv'
      output_path: /opt/openstack/artifice/invoices
      row_layout:
      - location
      - type
      - start
      - end
      - amount
      - cost
    main:
      # What invoice object we should be using
      invoice:object: billing.csv_invoice:Csv
    # Configuration for OpenStack
    openstack:
      # Location of the Keystone host
      authentication_url: http://foo
      # Location of the Ceilometer host
      ceilometer_url: http://localhost:8777
      # Default tenant to connect to. As this
      default_tenant: demo
      # Username to use
      username: foo
      # Password
      password: bar

A sample configuration is included, but **must** be modified appropriately.

## Setup of an Openstack environment

As mentioned, Artifice relies entirely on the Ceilometer project for its metering and measurement collection.

All development has (so far) occurred using a DevStack installation, but a production Ceilometer installation should work as expected.

### DevStack

Installation on DevStack is relatively easy.
First, prep the VM with DevStack.
Since we need Ceilometer installed, we recommend a DevStack localrc similar to:

    ADMIN_PASSWORD=openstack
    MYSQL_PASSWORD=openstack
    RABBIT_PASSWORD=openstack
    SERVICE_PASSWORD=openstack

    # Enable Quantum, on Grizzly
    disable_service n-net
    enable_service q-svc
    enable_service q-agt
    enable_service q-dhcp
    enable_service q-l3
    enable_service q-meta
    enable_service quantum

    # Enable Neutron

    # Enable Swift
    enable_service swift

    # Enable ceilometer!
    enable_service ceilometer-acompute,ceilometer-acentral,ceilometer-collector,ceilometer-api

A localrc file can be found at **devstack/localrc**

Create your VM and install DevStack into it. A Vagrant-compatible bootstrap script that will install most of the necessary components is included in this distribution, at **devstack/bootstrap.sh**

Install Artifice and the packages it depends on from the Debian repositories.

Artifices' post-intallation hooks will have set up the Postgres database as expected, and Artifice will be ready to run.

### Production OpenStack

FIXME :)

## Using Artifice

As mentioned, Artifice comes with a command-line tool to provide some simple commands.

Actions one can perform with Artifice are:

 * *Bill*; Given a date range, generates the current usage bill for a tenant. This will result in a CSV file.
 * *usage*


### Future things

Eventually we also want Artifice to:

 * List current usage numbers
 * List historic usage numbers
 * Re-generate billing information

Things we may eventually want include:

 * Listing this months' total usage of a given resource
 * Listing total usage by datacentre
 * Listing all usage ever
 * A web API for everything
 * A web API for rates information
