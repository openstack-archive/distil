# Openstack-Artifice

## What

Artifice is a layer sitting on top of Ceilometer to provide easy interactions with ERP systems, by exposing a configurable interface for turning Ceilometer data into a single billable line item.

Artifice provides hooks to integrate with arbitrary ERP systems, by not imposing logic beyond the concept of a dated invoice that covers a given range.

What the ranges are, and how Ceilometer data is aggregated is intended to be configurable.

Artifice enforces its own rigid postgresql-backed data store, used to store what data has been billed, and for what time range. This is used by Artifice to add prevention of repeated billing of a range of data.

The Artifice data store will prevent overlapping bills for a given tenant and resource ever being stored, while still allowing for regeneration of a given invoice statement.

## Requirements:

Artifice requires:
 * Postgresql 9.1 or greater.
 * Python >=2.7.5, <3.0
 * Python modules:
   * pyaml
   * mock
   * no
   * TODO
 * OpenStack Grizzly or greater
 * Openstack-Keystone
 * Openstack-Ceilometer

## Installation

Installing Artifice is as simple as:
    dpkg -i openstack-artifice-<version>.deb

The library will be installed to /opt/stack/artifice, and the command-line tool 'artifice' will be added to the path.

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
    # Configuration passed to the invoice system. This is arbitrary and may be
    # anything that the invoice object may require.
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

## Setup of Openstack environment

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

    # Enable Quantum
    disable_service n-net
    enable_service q-svc
    enable_service q-agt
    enable_service q-dhcp
    enable_service q-l3
    enable_service q-meta
    enable_service quantum

    # Enable Swift
    enable_service swift

    # Enable ceilometer!
    enable_service ceilometer-acompute,ceilometer-acentral,ceilometer-collector,ceilometer-api

A localrc file can be found at **devstack/localrc**

Create your VM and install DevStack into it. A Vagrant-compatible bootstrap script that will install most of the necessary components is included in this distribution, at **devstack/bootstrap.sh**

Install Artifice and the packages it depends on from the Debian repositories.

Artifices' post-intallation hooks will have set up the Postgres database as expected, and Artifice will be ready to run.

### Production OpenStack

TODO: Fill this out

## Using Artifice

As mentioned, Artifice comes with a command-line tool to provide some simple commands.

Actions one can perform with Artifice are:

 * Bill; Given a date range, generates the current usage bill for a tenant. This will result in a CSV file.


### Future things

Eventually we also want Artifice to:

 * List current usage numbers
 * List historic usage numbers
 * Re-generate billing information

Things we may eventually want include:

 * Listing this months' total usage of a given resource
 * Listing total usage by datacentre
 * Listing all usage ever
 * Etc