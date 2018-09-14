import logging
import click

import command
from redistrib import __version__


def _parse_host_port(addr):
    host, port = addr.split(':')
    return host, int(port)


@click.group(help='Note: each `--xxxx-addr` argument in the following commands'
                  ' is in the form of HOST:PORT')
def cli():
    pass


@cli.command(help='Create a cluster with several Redis nodes')
@click.option(
    '--max-slots', type=int, default=1024,
    help='maxium number of slots in a single CLUSTER ADDSLOTS command')
@click.option('--password', help='Password for all nodes the cluster')
@click.argument('addrs', nargs=-1, required=True)
def create(addrs, password=None, max_slots=1024):
    command.create([_parse_host_port(hp) for hp in addrs], password, max_slots)


@cli.command(help='Add a new Redis node to a cluster')
@click.option('--existing-addr', required=True,
              help='Address of any node in the cluster')
@click.option('--new-addr', required=True, help='Address of the new node')
@click.option('--password', help='Password for all nodes the cluster')
def add_node(existing_addr, new_addr, password=None):
    cluster_host, cluster_port = _parse_host_port(existing_addr)
    newin_host, newin_port = _parse_host_port(new_addr)
    command.add_node(cluster_host, cluster_port, newin_host, newin_port, password)


@cli.command(help='Add a slave node to a master')
@click.option('--master-addr', required=True, help='Address of the master')
@click.option('--slave-addr', required=True, help='Address of the slave')
@click.option('--password', help='Password for all nodes the cluster')
def replicate(master_addr, slave_addr, password=None):
    master_host, master_port = _parse_host_port(master_addr)
    slave_host, slave_port = _parse_host_port(slave_addr)
    command.replicate(master_host, master_port, slave_host, slave_port, password)


@cli.command(help='Remove a Redis node from a cluster')
@click.option('--addr', required=True, help='Address of the node')
@click.option('--password', help='Password for all nodes the cluster')
def del_node(addr, password=None):
    command.del_node(*_parse_host_port(addr), password=password)


@cli.command(help='Shutdown a cluster. The cluster should not contain more'
                  ' than one Redis node and there is no key in that Redis')
@click.option('--addr', required=True, help='Address of the node')
@click.option('--password', help='Password for all nodes the cluster')
def shutdown(addr, password=None):
    command.shutdown_cluster(*_parse_host_port(addr), password=password)


@cli.command(help='Fix migrating status')
@click.option('--addr', required=True, help='Address of the node')
@click.option('--password', help='Password for all nodes the cluster')
def fix(addr, password=None):
    command.fix_migrating(*_parse_host_port(addr), password=password)


@cli.command(help='Add a Redis node to a broken cluster to undertake missing'
                  ' slots and recover the cluster status')
@click.option('--existing-addr', required=True,
              help='Address of any node in the cluster')
@click.option('--new-addr', required=True, help='Address of the new node')
@click.option('--password', help='Password for all nodes the cluster')
def rescue(existing_addr, new_addr, password=None):
    host, port = _parse_host_port(existing_addr)
    command.rescue_cluster(host, port, *_parse_host_port(new_addr), password=password)


@cli.command(help='Migrate slots from one Redis node to another')
@click.option('--src-addr', required=True,
              help='Address of the migrating source')
@click.option('--dst-addr', required=True,
              help='Address of the migrating destination')
@click.argument('slots_ranges', nargs=-1, required=True)
@click.option('--password', help='Password for all nodes the cluster')
def migrate(src_addr, dst_addr, slots_ranges, password=None):
    src_host, src_port = _parse_host_port(src_addr)
    dst_host, dst_port = _parse_host_port(dst_addr)

    slots = []
    for rg in slots_ranges:
        if '-' in rg:
            begin, end = rg.split('-')
            slots.extend(xrange(int(begin), int(end) + 1))
        else:
            slots.append(int(rg))

    command.migrate_slots(src_host, src_port, dst_host, dst_port, slots, password)


def _format_master(node):
    s = 'M  %s %s %d' % (node.addr(), ','.join(node.flags),
                         len(node.assigned_slots))
    if node.slots_migrating:
        s += ' [migrating]'
    return s


def _format_slave(node, master):
    return ' S %s %s %s' % (node.addr(), ','.join(node.flags), master.addr())


@cli.command(help='List Redis nodes in a cluster')
@click.option('--addr', required=True,
              help='Address of any node in the cluster')
@click.option('--password', help='Password for all nodes the cluster')
def list(addr, password=None):
    host, port = _parse_host_port(addr)
    id_map = {}
    nodes = sorted(command.list_nodes(host, port, password=password)[0], key=lambda n: n.addr())
    master_count = 0
    fail_count = 0
    for node in nodes:
        node.slaves = []
        id_map[node.node_id] = node
        if node.fail:
            fail_count += 1
    for node in nodes:
        if node.slave:
            if node.master_id:
                id_map[node.master_id].slaves.append(node)
        else:
            master_count += 1
    print('Total %d nodes, %d masters, %d fail' % (
        len(nodes), master_count, fail_count))
    for node in nodes:
        if node.master:
            print(_format_master(node))
            for slave in node.slaves:
                print(_format_slave(slave, node))


@cli.command(help='Send a command to all nodes in the cluster')
@click.option('--master-only', is_flag=True,
              help='Only send to masters, and ignore --slave flag')
@click.option('--slave-only', is_flag=True, help='Only send to slaves')
@click.option('--addr', required=True,
              help='Address of any node in the cluster')
@click.option('--password', help='Password for all nodes the cluster')
@click.argument('commands', nargs=-1, required=True)
def execute(master_only, slave_only, addr, commands, password=None):
    host, port = _parse_host_port(addr)
    for r in command.execute(host, port, master_only, slave_only, commands, password):
        if r['result'] is None:
            print('%s -%s' % (r['node'].addr(), r['exception']))
        else:
            print('%s +%s' % (r['node'].addr(), r['result']))


def main():
    logging.basicConfig(level=logging.INFO)
    click.echo('Redis-trib 0.5.0 Copyright (c) HunanTV Platform developers')
    click.echo('Redis-trib %s by Negash' %
               __version__)
    cli()


if __name__ == "__main__":
    main()
