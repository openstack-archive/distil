.. _basic-configuration:

Basic Configuration
===================

The ``distil.conf`` configuration file is an
`INI file format <https://en.wikipedia.org/wiki/INI_file>`_.

This file is located in ``/etc/distil``. If there is a file ``distil.conf`` in
``~/.distil`` directory, it is used instead of the one in ``/etc/distil``
directory. When you manually install the Rating service, you must generate
the distil.conf file using the config samples generator located inside distil
installation directory and customize it according to your preferences.

To generate the sample configuration file ``distil/etc/distil.conf.sample``:

.. code-block:: console

   # pip install tox
   $ cd distil
   $ tox -e genconfig

Where :samp:`{distil}` is your Rating service installation directory.

Then copy Rating service configuration sample to the directory ``/etc/distil``:

.. code-block:: console

   # cp etc/distil.conf.sample /etc/distil/distil.conf

For a list of configuration options, see the tables in this guide.

.. important::

   Do not specify quotes around configuration options.

