class artifice::config (
    $keystone_uri,
    $keystone_tenant,
    $keystone_password,
    $keystone_username,
    $database_uri,
    $ceilometer_uri,
    $region
) {
    # target => '/tmp/example1.yaml',
    # key    => 'value/subkey/final',
    # value  => ['one', 'two', 'three'],
    #
    
    $artifice_config_file = "/etc/artifice/conf.yaml" 

    # OPENSTACK SETTINGS
    #
   yaml_setting {"artifice.config.ceilometer.uri":
        target => $artifice_config_file,
        key    => "ceilometer/host",
        value  => $ceilometer_uri
    } 

    yaml_setting {"artifice.config.keystone.uri":
        target => $artifice_config_file,
        key    => "openstack/authentication_url",
        value  => $keystone_uri
    }
    yaml_setting {"artifice.config.keystone.username":
        target => $artifice_config_file,
        key    => "openstack/username",
        value  => $keystone_user
    }
    yaml_setting {"artifice.config.keystone.tenant":
        target => $artifice_config_file,
        key    => "openstack/default_tenant",
        value  => $keystone_tenant
    }
    yaml_setting {"artifice.config.keystone.password":
        target => $artifice_config_file,
        key    => "openstack/password",
        value  => $keystone_password
    }
    
    # DATABASE SETTINGS

    yaml_setting {"artifice.config.database.uri":
        target => $artifice_config_file,
        key    => "database/uri",
        value  => $database_uri
    }

    # Config settings for plugins are stored in the plugins directory

    # file {"/etc/artifice/conf.yaml":
    #     ensure  => present,
    #     content => template("artifice/etc/artifice/conf.yaml")
    # }

    # Region
    #
    yaml_setting {"artifice.config.region":
        target => $artifice_config_file,
        key    => "region",
        value  => $region
    }
}
