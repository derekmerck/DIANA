import logging
from hashlib import md5
import click
import yaml
from diana.apis import Orthanc, DicomFile
from diana.utils.dicom import DicomLevel


# TODO: Query should always include StudyDate, StudyTime, AccessionNumber
# Without StudyDate/StudyTime it fails on readback

@click.command()
@click.argument('query')
@click.argument('source')
@click.option('--domain', help="Domain for proxied query")
@click.option('-r', '--retrieve', default=False)
@click.pass_context
def ofind(ctx, query, source, domain, retrieve):
    """Find items matching json QUERY in SOURCE Orthanc service {optionally with proxy DOMAIN}"""
    click.echo(ofind.__doc__)
    services = ctx.obj['SERVICES']

    S = Orthanc(**services.get(source))
    if isinstance(query, str):
        query = yaml.safe_load(query)
    click.echo(S.find(query, DicomLevel.STUDIES, domain, retrieve=retrieve))


@click.command()
@click.option("--accession_number", required=False)
@click.option("--worklist", type=click.File(), required=False)
@click.argument('source')
@click.argument('domain')
@click.argument('destination', type=click.Path(), required=False)
@click.option('-a', '--anonymize', default=False, is_flag=True)
@click.pass_context
def pull(ctx, accession_number, worklist, source, domain, destination, anonymize):
    """Pull items matching QUERY from SOURCE Orthanc service with proxy DOMAIN"""
    click.echo(pull.__doc__)
    services = ctx.obj['SERVICES']

    S = Orthanc(**services.get(source))
    # ep.clear()
    click.echo(S)

    D = None
    if destination:
        D = DicomFile(location=destination)

    def get_by_accession_num(accession_num):

        # Only if it's a file destination...
        if destination:
            # If dest is DicomFile
            if D.check("{}.zip".format(md5(accession_num.encode('UTF8')).hexdigest())):
                click.echo("Skipping {}".format(accession_num))
                return

        q = {
             "AccessionNumber": accession_num,
             "StudyDate": "",
             "StudyTime": "",
             "PatientName": "",
             "PatientBirthDate": "",
             "PatientSex": ""
             }
        dixels = S.find(q, DicomLevel.STUDIES, domain, retrieve=True)
        click.echo(dixels)

        for dixel in dixels:
            if anonymize:
                dixel = S.anonymize(dixel, remove=True)
                click.echo(dixel)

            if destination:
                # If dest is DicomFile
                dixel = S.get(dixel, view='archive')
                logging.debug(dixel.meta['AccessionNumber'])
                D.put(dixel, fn_from="AccessionNumber")
                S.remove(dixel)

                # If dest is peer or modality node
                # ep.send(dixel, peer_dest=destination)
                # ep.remove(dixel)

    if not worklist and not accession_number:
        logging.warning("No --accession_number or --worklist option provided. Nothing to do.")

    if accession_number:
        get_by_accession_num(accession_number)
        return

    if worklist:
        for accession_num in worklist.readlines():
            # Get rid of trailing return
            get_by_accession_num(accession_num.rstrip())

