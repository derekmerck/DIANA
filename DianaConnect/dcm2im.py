#! python
"""
dcm2im.py
Derek Merck, Spring 2018

Convert pixels from a DICOM format image or directory into a standard
PIL format (png, jpg).

> dcm2py.py -i im000001.dcm
"""

import os, glob, logging
from argparse import ArgumentParser
from dicom import read_file
from PIL.Image import fromarray

def parse_args():

    p = ArgumentParser()
    p.add_argument("--infile", "-i",  required=False)
    p.add_argument("--outfile", "-o", required=False)
    p.add_argument("--indir", "-I",   required=False)
    p.add_argument("--outdir", "-O",  required=False)
    p.add_argument("--format", "-f",  default="png", choices=['png', 'jpg'])
    opts = p.parse_args()
    return opts

def convert_file(infile, outfile):

    ds = read_file(infile)
    pixels = ds.pixel_array
    if ds[0x0028,0x0004].value == "RGB":
        pixels = pixels.reshape([pixels.shape[1], pixels.shape[2], 3])
    im = fromarray(pixels)
    im.save(outfile)

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

        print "Must provide either an input file (-i) or an input directory (-I)"



