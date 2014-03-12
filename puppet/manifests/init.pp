class artifice (
    $keystone_password,
    $region,
    $version,
    $database_password,
    $database_provider    = "postgres",
    $database_host        = "localhost",
    $database_port        = 5432,
    $database_name        = "artifice",
    $database_user        = "artifice",
    $csv_output_directory = '/var/lib/artifice/csv',
    $ceilometer_uri       = "http://localhost:8777",
    $keystone_uri         = "http://localhost:35357/v2.0",
    $keystone_tenant      = "demo",
    $keystone_username    = "admin"
) {
    
    
    # Materialises the class
    # I think.. this is better served as part of the package install
    $config_file = "/etc/artifice/conf.yaml"
    $install_path = "/opt/stack/artifice"

    class {"artifice::server":
        # region   => $region,
        version  => $version,
        # require  => Class["artifice::dependencies"]
    }

    $database_uri = "$database_provider://${database_user}:${database_password}@${database_host}:${database_port}/${database_name}"

    class {"artifice::config":
        keystone_uri      => $keystone_uri,
        keystone_tenant   => $keystone_tenant,
        keystone_username => $keystone_username,
        keystone_password => $keystone_password,
        database_uri      => $database_uri,
        ceilometer_uri    => $ceilometer_uri,
        require           => Class["artifice::server"],
        notify            => Service["artifice"],
        region            => $region
    }

    class {"artifice::database":
        provider      => $database_provider,
        host          => $database_host,
        port          => $database_port,
        user          => $database_user,
        password      => $database_password,
        database_name => $database_name,
        require       => Class["artifice::server"]
    }

    service {"artifice":
        ensure  => running,
        require => [
            Class["artifice::server"], 
            Class["artifice::config"]
        ]
    }
}
