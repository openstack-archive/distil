class artifice::plugins::csv (
    $delimiter,
    $output_path,
    $output_pattern
) {
   
    # This should cause a runtime error if another plugin is loaded
    yaml_setting {"artifice.billing.plugin":
        target => $artifice::config_file,
        key    => "main/invoice:object",
        value  => "billing.csv_plugin:Csv"
    }
    yaml_setting {"artifice.csv.config.delimiter":
        target => $artifice::config_file,
        key    => "invoice_object/delimiter",
        value  => $delimiter
    }
    yaml_setting {"artifice.csv.config.output_path":
        target => $artifice::config_file,
        key    => "invoice_object/output_path",
        value  => $output_path
    }
    yaml_setting {"artifice.csv.config.output_file":
        target => $artifice::config_file,
        key    => "invoice_object/output_file",
        value  => $output_pattern
    }
    # Rates information is pulled from the rates-file plugin
}
