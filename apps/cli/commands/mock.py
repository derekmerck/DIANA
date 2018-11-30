import random, logging, time
from datetime import datetime
import click
import attr
from diana.apis import Orthanc
from diana.mock import MockStudy

@attr.s
class MockScanner(object):
    seed = attr.ib( default=None )
    name = attr.ib( type=str, default="Mock Scanner" )
    modality = attr.ib( type=str, default="CT" )
    rate = attr.ib( type=float, default=10, converter=float )

    @seed.validator
    def set_seed(self, attribute, value):
        if value:
            random.seed(value)

    def gen_study(self):
        s = MockStudy(seed=self.seed,
                      study_datetime=datetime.now(),
                      station_name = self.name,
                      modality=self.modality )
        return s

    def run(self, dest: Orthanc):

        while True:

            logging.info("Generating mock study")
            s = self.gen_study()

            for d in s.dixels():
                # logging.debug(d)
                d.gen_file()
                dest.put( d )

            ave_delay  = 60*60/self.rate
            this_delay = random.gauss(ave_delay, ave_delay*0.3)
            if this_delay < 0.1:
                this_delay = 0.1
            logging.info("Waiting {} secs".format(this_delay))
            time.sleep( this_delay )


@click.command()
@click.argument('destination')
@click.argument('rate')
@click.pass_context
def mock(ctx, destination, rate):
    """Generate mock studies at RATE per hour and submit to DESTINATION"""
    click.echo(mock.__doc__)
    services = ctx.obj['SERVICES']

    D = Orthanc(**services.get(destination))
    M = MockScanner(name = "Diana Mock", rate = rate)
    M.run(dest=D)