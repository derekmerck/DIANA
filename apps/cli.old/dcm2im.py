#! python3
"""
dcm2im.py
Derek Merck, Spring 2018

Wrapper command-line tool to convert pixels from a DICOM format file or directory
into a standard image format (png, jpg).

$ python dcm2py.py -i im000001.dcm

"""

import os, glob, logging
from argparse import ArgumentParser
from diana.apis import DicomFile, ImageFile


def parse_args():

    p = ArgumentParser("dcm2im")
    p.add_argument("-i", "--infile",  required=False)
    p.add_argument("-o", "--outfile", required=False)
    p.add_argument("-I", "--indir",   required=False)
    p.add_argument("-O", "--outdir",  required=False)
    p.add_argument("-f", "--format",  default="png", choices=['png', 'jpg'])
    opts = p.parse_args()
    return opts


def convert_file(infile, outfile):

    dixel = DicomFile().get(infile)
    ImageFile().put(dixel, outfile)


def convert_dir(indir, outdir, format):
    infiles = glob.glob(os.path.join(indir, "*.dcm"))
    for infile in infiles:
        infile_name = os.path.basename(infile)
        outfile = os.path.join( outdir, "{}.{}".format(infile_name, format))
        convert_file(infile, outfile)


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    opts = parse_args()

    if opts.infile:

        if not opts.outfile:
            # set default
            opts.outfile = "{}.{}".format( os.path.splitext(opts.infile)[0], opts.format)
        convert_file(opts.infile, opts.outfile)

    elif opts.indir:

        if not opts.outdir:
            # set default
            opts.outdir = opts.indir
        convert_dir(opts.indir, opts.outdir, opts.format)

    else:

        print("Must provide either an input file (-i) or an input directory (-I)")



