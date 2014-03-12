class artifice::server(
    $version
) {
    # $path_to_package = $::package_path + "/artifice" + $version + ".deb"
    
    # package {"python2.7":
    #     ensure => present
    # }
    
    package {"artifice":
        name    => "openstack-artifice",
        ensure  => present,
        require => Package["python2.7"]
    }

    package {"libpq-dev":
        ensure => present
    }
    package {"python2.7": ensure         => present}
    package {"python-pip": ensure        => present}
    package {"python-dev": ensure        => present}
    package {"python-virtualenv": ensure => present}

    Package["python-virtualenv"] -> Package["artifice"]
    # We don't try to ensure running here.
    #
}
