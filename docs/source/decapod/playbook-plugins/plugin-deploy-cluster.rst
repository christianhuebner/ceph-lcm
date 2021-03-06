.. _plugins_deploy_ceph_cluster:

===================
Deploy Ceph cluster
===================

The *Deploy Ceph cluster* playbook plugin allows you to deploy an initial Ceph
cluster. The plugin supports all the capabilities and roles of
``ceph-ansible``.

.. note::

   The majority of configuration options described in this section match the
   ``ceph-ansible`` settings. For a list of supported parameters, see
   `official list <https://github.com/ceph/ceph-ansible/blob/master/group_vars/all.yml.sample>`_.

.. toctree::
   :maxdepth: 1

   deploy-cluster/overview.rst
   deploy-cluster/parameters-and-roles.rst
   deploy-cluster/example-config.rst
