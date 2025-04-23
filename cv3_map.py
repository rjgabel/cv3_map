from PIL import Image

PRG_SIZE = 256 * 1024
CHR_SIZE = 128 * 1024

GREYSCALE_PAL = [0,0,0,85,85,85,170,170,170,255,255,255]

def read_ptr(addr, bank):
    lo = prgrom[addr]
    hi = prgrom[addr+1]
    ptr = (hi << 8)|lo
    return (ptr&0x1FFF)|(bank *0x2000)

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

def get_room_chr(stage, block, room):
    # All pointers are in the first ROM bank
    stage_ptr = 0x005F
    block_ptr = read_ptr(stage_ptr+stage*2, 0)
    room_ptr = read_ptr(block_ptr+block*4, 0)
    chr_5 = prgrom[room_ptr+room*2]
    chr_6 = prgrom[room_ptr+room*2+1]
    return (chr_5,chr_6)

def get_tsa_def(stage):
    # TODO: Fix this later
    return 0x20441 # For stage 1

def get_tsa_map(stage, block, room):
    stage_ptr = read_ptr(0x3D8F9+stage*2, 0x10)
    block_ptr = read_ptr(stage_ptr+block*2, 0x10)
    room_ptr = read_ptr(block_ptr+room*2+1, 0x10)
    return (prgrom[room_ptr]+1, room_ptr+1)

def get_tile_addr(tile, chr_5, chr_6):
    assert tile < 0x100
    sets = [0x40, chr_5, chr_6, 0x43]
    bank = sets[tile >> 6]
    tile &= 0x3F
    addr = bank * 0x400 + tile * 0x10
    return addr

def render_tsa(tsa_id, tsa_def, chr_5, chr_6, img, bx, by):
    for y in range(4):
        for x in range(4):
            tile_id = prgrom[tsa_def+tsa_id*16+y*4+x]
            tile_addr = get_tile_addr(tile_id, chr_5, chr_6)
            load_tile(tile_addr, img, bx+x*8, by+y*8)

def render_screen(addr, tsa_def, chr_5, chr_6, img, bx, by):
    for y in range(6):
        for x in range(8):
            tsa_id = prgrom[addr+x+y*8]
            render_tsa(tsa_id, tsa_def, chr_5, chr_6, img, bx+x*8*4, by+y*8*4)
            

def render_room(stage, block, room):
    SCREEN_X = 8*8*4
    SCREEN_Y = 6*8*4
    tsa_def = get_tsa_def(stage)
    (room_size, tsa_map) = get_tsa_map(stage, block, room)
    (chr_5,chr_6) = get_room_chr(stage, block, room)
    
    img = Image.new('P', (room_size*SCREEN_X,SCREEN_Y))
    img.putpalette(GREYSCALE_PAL)
    for x in range(room_size):
        render_screen(tsa_map+48*x, tsa_def, chr_5, chr_6, img, x*SCREEN_X, 0)
    img.show()

(prgrom, chrrom) = load_rom('Akumajou Densetsu (Japan).nes')
render_room(0,2,0)
