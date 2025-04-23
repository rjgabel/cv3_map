from PIL import Image

PRG_SIZE = 256 * 1024
CHR_SIZE = 128 * 1024

GREYSCALE_PAL = [0,0,0,85,85,85,170,170,170,255,255,255]

def load_rom(filename):
    with open(filename, 'rb') as f:
        romfile = f.read()
    assert len(romfile) == 16 + PRG_SIZE + CHR_SIZE
    prgrom = romfile[16:16+PRG_SIZE]
    chrrom = romfile[16+PRG_SIZE:]
    return (prgrom, chrrom)

def load_tile(addr, img, bx, by):
    for y in range(8):
        lo = chrrom[addr+y]
        hi = chrrom[addr+y+8]
        for x in range(8):
            lb = (lo >> (7-x)) & 1
            hb = (hi >> (7-x)) & 1
            b = (hb << 1) | lb
            img.putpixel((bx+x,by+y), b)
    return img

def load_chr():
    img=Image.new('P', (8*16,128*8*4))
    img.putpalette(GREYSCALE_PAL)
    for y in range(128*4):
        for x in range(16):
            load_tile((y*16+x)*16, img, x*8, y*8)
    return img
            

(prgrom, chrrom) = load_rom('Akumajou Densetsu (Japan).nes')
img=load_chr()
