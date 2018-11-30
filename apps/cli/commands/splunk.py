import click
from diana.apis import Splunk
from diana.utils import DatetimeInterval2 as DatetimeInterval


@click.command()
@click.argument('query')
@click.argument('source')
@click.option("-e", "--earliest", default="-1d")
@click.option("-l", "--latest",   default="now")
@click.pass_context
def sfind(ctx, query, source, earliest, latest):
    """Find items matching Splunk QUERY in SOURCE Splunk service"""
    click.echo(sfind.__doc__)
    services = ctx.obj['SERVICES']

    S = Splunk(**services.get(source))
    click.echo(S.find_items(query, DatetimeInterval( earliest, latest )))

