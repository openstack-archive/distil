class artifice::database (
    $provider,
    $host,
    $port,
    $user,
    $password,
    $database_name
) {
    # I think the install path should 
    #
    if $provider != "postgres" and $provider != "mysql" {
       fail("Provider must be postgres or mysql") 
    }
    $install_path = "/opt/stack/artifice"
    
    # Create is handled by the Galera setup earlier.
    # exec {"create.database":
    #     command => $create_command,
    #     cwd     => $pwd,
    #     onlyif  => $unless_command
    # }
    exec {"sqlalchemy.create":
        command     => "/usr/bin/python $install_path/initdb.py",
        environment => "DATABASE_URI=$provider://$user:$password@$host/$database_name",
        onlyif      => "/usr/bin/python $install_path/is_provisioned.py",
    }
}
