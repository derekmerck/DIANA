import logging
import click_log
import click
from diana.apis import *
from utils.merge_yaml_sources import merge_yaml_sources
from commands.orthanc import ofind, pull
from commands.splunk import sfind
from commands.watch import watch
from commands.mock import mock
from commands.hello import hello

@click.group()
@click.option('-s', '--services',
              help='Services description (DIANA_SERVICES)',
              required=False)
@click.option('-S', '--services_path',
              help='Path to services file or directory (DIANA_SERVICES_PATH)',
              type=click.Path(exists=True),
              required=False)
@click_log.simple_verbosity_option()
# @click.option('-v', '--verbose', help='Verbose logging', is_flag=True, multiple=True)
@click.pass_context
def cli(ctx, services, services_path):

    # Create services context
    all_services = merge_yaml_sources(services, services_path)
    ctx.ensure_object(dict)
    ctx.obj['SERVICES'] = all_services

    # print(len(verbose))
    #
    # if len(verbose) >= 3:
    #     logging.basicConfig(level=logging.DEBUG)
    #     logging.info("Setting super-verbose")
    # elif len(verbose) == 2:
    #     logging.basicConfig(level=logging.DEBUG)
    #     # Reduce junk output
    #     logging.getLogger("requests").setLevel(logging.WARNING)
    #     logging.getLogger("urllib3").setLevel(logging.WARNING)
    #     logging.getLogger("diana.utils.gateway.requester").setLevel(logging.WARNING)
    # elif len(verbose) == 1:
    #     logging.basicConfig(level=logging.WARN)
    #     logging.getLogger("requests").setLevel(logging.WARNING)
    #     logging.getLogger("urllib3").setLevel(logging.WARNING)
    #     logging.getLogger("diana.utils.gateway.requester").setLevel(logging.WARNING)
    # else:
    #     logging.basicConfig(level=logging.ERROR)
    #     logging.getLogger("requests").setLevel(logging.ERROR)
    #     logging.getLogger("urllib3").setLevel(logging.ERROR)
    #     logging.getLogger("diana.utils.gateway.requester").setLevel(logging.ERROR)



@click.command()
@click.argument('endpoints', nargs=-1)
@click.pass_context
def status(ctx, endpoints):
    """Report status of ENDPOINTS"""
    services = ctx.obj['SERVICES']
    click.echo('Reporting endpoint status')

    if len(endpoints) == 0:
        endpoints = services.keys()

    click.echo(endpoints)

    for key in endpoints:
        ep = Orthanc(**services[key])
        click.echo(ep)
        click.echo(ep.info())


@click.command()
@click.argument('oid')
@click.argument('source')
@click.argument('path', type=click.File())
@click.pass_context
def get(ctx, oid, source, path):
    """Get a dixel by OID from SOURCE Orthanc service and save to PATH"""
    click.echo(get.__doc__)
    services = ctx.obj['SERVICES']

    S = Orthanc(**services.get(source))
    dixel = S.get(oid)
    D = DicomFile()
    D.put(dixel, path=path)


@click.command()
@click.argument('path', type=click.Path(exists=True))
@click.argument('destination')
@click.pass_context
def put(ctx, path, destination):
    """Put dixels at PATH in DESTINATION Orthanc service"""
    click.echo(__doc__)
    services = ctx.obj['SERVICES']

    S = DicomFile()
    dixel = S.get(path)
    D = Orthanc(**services.get(destination))
    destination.put(dixel)


@click.command()
@click.argument('dixel')
@click.argument('handler')
@click.argument('source')
@click.argument('destination')
@click.pass_context
def handle(ctx, dixel, handler, source, destination):
    """Retrieve a DIXEL from SOURCE, process it with HANDLER, and submit the result to DESTINATION"""
    click.echo(handle.__doc__)
    services = ctx.obj['SERVICES']


cli.add_command(status)
cli.add_command(get)
cli.add_command(ofind)
cli.add_command(pull)
cli.add_command(sfind)
cli.add_command(put)
cli.add_command(handle)
cli.add_command(watch)
cli.add_command(mock)
cli.add_command(hello)


if __name__ == '__main__':
    cli(auto_envvar_prefix='DIANA')