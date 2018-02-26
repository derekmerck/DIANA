import logging

def readme2rst():
    import subprocess

    readmes = [
        '.',
        'DianaConnect',
        'DianaFE',
        'DixelKit',
        'GUIDMint',
        'SplunkApps/rad_rx'
        ]

    for r in readmes:
        logging.debug('/usr/local/bin/pandoc')
        subprocess.call(['/usr/local/bin/pandoc',
                         '--from=markdown',
                         '--to=rst',
                         '--output=./{}/_README.rst'.format(r),
                         './{}/README.MD'.format(r)])

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    readme2rst()