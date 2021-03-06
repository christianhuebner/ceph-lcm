# -*- coding: utf-8 -*-
# Copyright (c) 2016 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Different utils, related to networking."""


import ipaddress
import operator


def get_networks(server):
    networks = {}

    for ifname in server.facts["ansible_interfaces"]:
        ifname = "ansible_{0}".format(ifname.replace("-", "_"))
        interface = server.facts.get(ifname)

        if not interface:
            continue
        if not interface.get("ipv4"):
            continue

        hw_ifname = get_hw_ifname(ifname, server.facts)
        if not hw_ifname:
            continue

        hw_interface = server.facts[hw_ifname]
        if not hw_interface["active"] or hw_interface["type"] == "loopback":
            continue

        network = "{0}/{1}".format(
            interface["ipv4"]["network"],
            interface["ipv4"]["netmask"]
        )
        networks[interface["ipv4"]["address"]] = ipaddress.ip_network(
            network, strict=False)

    return networks


def get_cluster_network(servers):
    networks = {}
    public_network = get_public_network(servers)

    for srv in servers:
        server_ip = get_default_ip_address(srv)
        networks[server_ip] = get_networks(srv)
        networks[server_ip].pop(server_ip, None)

    first_network = networks.pop(get_default_ip_address(servers[0]))
    if not first_network:
        return public_network

    _, first_network = first_network.popitem()
    other_similar_networks = []

    for other_networks in networks.values():
        for ip_addr, other_network in other_networks.items():
            if ip_addr in first_network:
                other_similar_networks.append(other_network)
                break
        else:
            return public_network

    other_similar_networks.append(first_network)

    return spanning_network(other_similar_networks)


def get_public_network(servers):
    networks = [
        get_networks(srv)[get_default_ip_address(srv)] for srv in servers]

    if not networks:
        raise ValueError(
            "List of servers should contain at least 1 element.")

    return spanning_network(networks)


def get_public_network_if(server, all_servers):
    public_network = get_public_network(all_servers)

    for name in server.facts["ansible_interfaces"]:
        name = name.replace("-", "_")
        interface = server.facts["ansible_{0}".format(name)]
        if not interface.get("ipv4") or "device" not in interface:
            continue

        addr = interface["ipv4"]["address"]
        addr = ipaddress.ip_address(addr)
        if addr in public_network:
            return interface["device"]

    raise ValueError(
        "Cannot find suitable interface for server {0}".format(
            server.model_id))


def get_public_network_ip(server, all_servers):
    public_network = get_public_network(all_servers)

    for server_ip in server.facts["ansible_all_ipv4_addresses"]:
        addr = ipaddress.ip_address(server_ip)
        if addr in public_network:
            return str(addr)

    raise ValueError(
        "Cannot find suitable public address for server {0}".format(
            server.model_id))


def spanning_network(networks):
    if not networks:
        raise ValueError("List of networks is empty")
    if len(networks) == 1:
        return networks[0]

    sorter = operator.attrgetter("num_addresses")
    while True:
        networks = sorted(
            ipaddress.collapse_addresses(networks), key=sorter, reverse=True)

        if len(networks) == 1:
            return networks[0]

        networks[-1] = networks[-1].supernet()


def get_default_ip_address(server):
    if server.ip in server.facts["ansible_all_ipv4_addresses"]:
        return server.ip

    # If server IP is floating one, detected by metadata server, it is
    # not placed here, in Ansbile facts. It is managed by external
    # network server (e.g Neutron) and in most cases it is managed by NAT.
    #
    # If such situation (IP fetched from Metadata API) has happened, then
    # only valid solution is to select default ipv4 address from facts.
    #
    # Hint: Ansible detect such IP address literally by parsing
    # `ip route get 8.8.8.8` output. We follow the same logic on server
    # discovery.
    return server.facts["ansible_default_ipv4"]["address"]


def get_hw_ifname(ifname, facts):
    # Ansible has a mess in facts about NICs and aliases. The solution is
    # understandable but not convenient. The most irritating part is that
    # it is impossible to recognize if interface is alias and if it is
    # an alias, then to get a device of HW NIC. This drives nuts.
    #
    # https://github.com/ansible/ansible/issues/842
    #
    # Here is the heuristics we are using: if interface has "device"
    # field then hooray, this is HW NIC. Otherwise (NIC alias), logic
    # is following: we cut ifname till it can detect some HW NIC and it
    # means that we've found our desired NIC.
    while len(ifname) > len("ansible_"):
        if "device" in facts.get(ifname, {}):
            return ifname

        # if ifname == "ansible_eth0_1", search for "ansible_eth0"
        ifname = ifname[:-1]
