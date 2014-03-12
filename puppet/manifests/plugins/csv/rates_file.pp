class artifice::plugins::csv::rates_file (
    $path
) {
    # Sets the path to the rates information, if any
    yaml_setting {"artifice.plugins.rates":
        target  => $artifice::config_file,
        key     => "invoice_object/rates/file",
        value   => $path,
        require => File[$path]
    }
}
