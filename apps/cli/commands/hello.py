import click


@click.command()
@click.option('--count', default=1, help='Number of greetings.')
@click.option('--name', prompt='Your name', help='The person to greet.')
def hello(count, name):
    """Greets NAME for a total of COUNT times."""
    click.echo(hello.__doc__)

    for x in range(count):
        click.echo('Hello %s!' % name)