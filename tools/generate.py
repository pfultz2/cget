import os
__dir__ = os.path.dirname(os.path.realpath(__file__))

preamble = open(os.path.join(__dir__, 'preamble.cmake')).read()

for p in os.listdir(os.path.join(__dir__, 'cmake')):
    inf = os.path.join(__dir__, 'cmake', p)
    outf = os.path.join(__dir__, '..', 'cget', 'cmake', p)
    s = open(inf).read()
    s = s.replace('@PREAMBLE@', preamble)
    open(outf, 'w').write(s)
