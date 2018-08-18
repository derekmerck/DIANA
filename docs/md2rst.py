from pypandoc import convert_file
import os

tlds = [
    '/Users/derek/dev/DIANA/apps',
    '/Users/derek/dev/DIANA/examples',
    '/Users/derek/dev/DIANA/packages',
    '/Users/derek/dev/ansible',
    '/Users/derek/dev/docker'
]

for d in tlds:

    for root, dirs, files in os.walk(d, topdown=False):
        for name in files:
            if name.endswith('.md'):
                input = os.path.join(root, name)
                output =  "source/" + os.path.split( os.path.dirname( os.path.join(root, name) ))[-1] + ".rst"
                print("{}:{}".format(input, output))

                convert_file(input, "rst", outputfile=output)

convert_file("/Users/derek/dev/DIANA/README.md", "rst", outputfile="source/diana-overview.rst")
