..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

====================================
Welcome to the Distil Documentation!
====================================


Project scope
=============

Distil is a service to provide easy interactions with ERP systems, by exposing
a configurable set of collection tools and transformers to make usable billing
data out of Ceilometer entries.

Distil provides a rest api to integrate with arbitrary ERP systems, and returns
quotations/invoices as json. What the ranges are, and how Ceilometer data is
aggregated is intended to be configurable, and defined in the configuration
file.

The Distil data store will prevent overlapping bills for a given tenant and
resource ever being stored, while still allowing for regeneration of a given
invoices.

Design principles
=================

Distil, as with all OpenStack projects, is designed with the following
guidelines in mind:

* **Component-based architecture.** Quickly add new behaviors
* **Highly available and scalable.** Scale to very serious workloads
* **Fault tolerant.** Isolated processes avoid cascading failures
* **Recoverable.** Failures should be easy to diagnose, debug, and rectify
* **Open standards.** Be a reference implementation for a community-driven

Concepts
========

.. toctree::
   :maxdepth: 1

   glossary

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
