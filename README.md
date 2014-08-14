# Distil

## What

Distil is a web app to provide easy interactions with ERP systems, by exposing a configurable set of collection tools and transformers to make usable billing data out of Ceilometer entries.

Distil provides a rest api to integrate with arbitrary ERP systems, and returns sales orders as json.
What the ranges are, and how Ceilometer data is aggregated is intended to be configurable, and defined in the configuration file.

The Distil data store will prevent overlapping bills for a given tenant and resource ever being stored, while still allowing for regeneration of a given sales order.

## Requirements:

See: requirements.txt

## Configuration

Configuring Distil is handled through its primary configuration file, which defaults to /etc/distil/conf.yaml.
This is a yaml-format config file, in the format of:
  ---
  main:
    region: nz_wlg_2
    # timezone is unused at this time
    timezone: Pacific/Auckland 
    database_uri: postgres://admin:password@localhost:5432/billing
    trust_sources: 
      - openstack
    log_file: logs/billing.log
    ignore_tenants:
      - test
  rates_config:
    file: test_rates.csv
  # Keystone auth user details
  auth:
    end_point: https://api.cloud.catalyst.net.nz:5000/v2.0
    default_tenant: demo
    username: admin
    password: openstack
    insecure: True
  # configuration for defining usage collection
  collection:
    # defines which meter is mapped to which transformer
    meter_mappings:
      # meter name as seen in ceilometer
      state: 
        # type of resource it maps to (seen on sales order)
        type: Virtual Machine
        # which transformer to use
        transformer: Uptime
        # what unit type is coming in via the meter
        unit: second 
      ip.floating:
        type: Floating IP
        transformer: GaugeMax
        unit: hour
      volume.size:
        type: Volume
        transformer: GaugeMax
        unit: gigabyte
      instance:
        type: Volume
        transformer: FromImage
        unit: gigabyte
        # if true allows id pattern, and metadata patterns
        transform_info: True
        # allows us to put the id into a pattern,
        # only if transform_info is true,
        # such as to append something to it
        res_id_template: "%s-root_disk"
      image.size:
        type: Image
        transformer: GaugeMax
        unit: byte
      bandwidth:
        type: Traffic
        transformer: GaugeSum
        unit: byte
      network.services.vpn:
        type: VPN
        transformer: GaugeNetworkService
        unit: hour
    # metadata definition for resources (seen on invoice)
    metadata_def:
      # resource type (must match above definition)
      Virtual Machine:
        # name the field will have on the sales order
        name:
          sources:
            # which keys to search for in the ceilometer entry metadata
            # this can be more than one as metadata is inconsistent between source types
            - display_name
        availability zone:
          sources:
            - OS-EXT-AZ:availability_zone
      Volume:
        name:
          sources:
            - display_name
          # template is only used if 'transform_info' in meter mappings is true.
          template: "%s - root disk"
        availability zone:
          sources:
            - availability_zone
      Floating IP:
        ip address:
          sources:
            - floating_ip_address
      Image:
        name:
          sources:
            - name
            - properties.image_name
      Traffic:
        name:
          sources:
            - name
      VPN:
        name:
          sources:
            - name
        subnet:
          sources:
            - subnet_id
  # transformer configs
  transformers:
    uptime:
      # states marked as "billable" for VMs. 
      tracked_states:
        - active
        - paused
        - rescued
        - resized
    from_image:
      service: volume.size
      # What metadata values to check
      md_keys:
        - image_ref
        - image_meta.base_image_ref
      none_values:
        - None
        - ""
      # where to get volume size from
      size_keys:
        - root_gb

A sample configuration is included, but must be modified appropriately.

### Collection

Under collection > meter_mappings in the configs is how we define the transformers being used, and the meters mapped to them. This is the main functionality of Distil, and works as a way to make usable piece of usage data out of ceilometer samples.

We are also able to configure metadata fetching from the samples via collection > metadata_def, with the ability to pull from multiple metadata fields as the same data can be in different field names based on sample origin.

### Transformers

Active transformers are currently hard coded as a dict of names to classes, but adding additional transformers is a straightforward process assuming new transformers follow the same input/output conventions of the existing ones. Once listed under the active transformers dict, they can be used and referenced in the config.


## Setup 

Provided all the requirements are met, a database must be created, and then setup with artifice/initdb.py

The web app itself consists of running bin/web.py with specified config, at which point you will have the app running locally at: http://0.0.0.0:8000/

### Setup with Openstack environment
As mentioned, Distil relies entirely on the Ceilometer project for its metering and measurement collection.

It needs to be given admin access, and provided with the keystone endpoint in the config.

Currently it also relies on the "state" metric existing in Ceilometer, but that will be patched out later. As well as a few other pollster we've made for it.

### Setup in Production

Puppet install to setup as mod_wsgi app.
More details to come.

## Using Distil

Distil comes with a command-line tool to provide some simple commands. These are mainly commands as accessible via the web api, and they can be used from command-line, or by importing the client module and using it in python.

IMPORTANT: Distil assumes all incoming datetimes are in UTC, conversion from local timezone must occur before passing to the api.

### Web Api

The web app is a rest style api for starting usage collection, and for 

#### Commands

/collect_usage
runs usage collection on all tenants present in Keystone

/sales_order
generate a sales order for a given tenant from the last generated sales order, or the first ever usage entry.
tenant - tenant id for a given tenant, required.
end - end date for the sales order (yyyy-mm-dd), defaults to 00:00:00 UTC for the current date.

/collect_draft
same as generating a sales order, but does not create the sales order in the database.
tenant - tenant id for a given tenant, required.
end - end date for the sales order (yyyy-mm-dd or yyyy-mm-ddThh-mm-ss), defaults to now in UTC.

/collect_historic
regenerate a sales order for a tenant that intersects with the given date
tenant - tenant id for a given tenant, required.
date - target date (yyyy-mm-dd).

/collect_range
get all sales orders that intersect with the given range
tenant - tenant id for a given tenant, required.
start - start of the range (yyyy-mm-dd).
end - end of the range (yyyy-mm-dd), defaults to now in UTC.

### Client/Command-line

The client is a simple object that once given a target endpoint for the web api, provides functions that match the web api.

The command-line tool is the same, and has relatively comprehensive help text from the command-line.


## Running Tests

The tests are currently expected to run with Nosetests, against a pre-provisioned database.

## Future things

Eventually we also want Distil to:

  * Authenticate via Keystone
  * Have a public endpoint on keystone, with commands limited by user role and tenant.
  * Have separate usage collection from the web app layer and a scheduler to handle it.

Things we may eventually want include:

  * Alarms built on top of our hourly usage collection.
  * Horizon page that builds graphs based on billing data, both past(sales order), and present (sales draft).
