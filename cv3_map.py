from PIL import Image

PRG_SIZE = 256 * 1024
CHR_SIZE = 128 * 1024

GREYSCALE_PAL = [0,0,0,85,85,85,170,170,170,255,255,255]
NES_PAL = [0x62,0x62,0x62,0x00,0x1F,0xB2,0x24,0x04,0xC8,0x52,0x00,0xB2,0x73,0x00,0x76,0x80,0x00,0x24,0x73,0x0B,0x00,0x52,0x28,0x00,0x24,0x44,0x00,0x00,0x57,0x00,0x00,0x5C,0x00,0x00,0x53,0x24,0x00,0x3C,0x76,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0xAB,0xAB,0xAB,0x0D,0x57,0xFF,0x4B,0x30,0xFF,0x8A,0x13,0xFF,0xBC,0x08,0xD6,0xD2,0x12,0x69,0xC7,0x2E,0x00,0x9D,0x54,0x00,0x60,0x7B,0x00,0x20,0x98,0x00,0x00,0xA3,0x00,0x00,0x99,0x42,0x00,0x7D,0xB4,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0xFF,0xFF,0xFF,0x53,0xAE,0xFF,0x90,0x85,0xFF,0xD3,0x65,0xFF,0xFF,0x57,0xFF,0xFF,0x5D,0xCF,0xFF,0x77,0x57,0xFA,0x9E,0x00,0xBD,0xC7,0x00,0x7A,0xE7,0x00,0x43,0xF6,0x11,0x26,0xEF,0x7E,0x2C,0xD5,0xF6,0x4E,0x4E,0x4E,0x00,0x00,0x00,0x00,0x00,0x00,0xFF,0xFF,0xFF,0xB6,0xE1,0xFF,0xCE,0xD1,0xFF,0xE9,0xC3,0xFF,0xFF,0xBC,0xFF,0xFF,0xBD,0xF4,0xFF,0xC6,0xC3,0xFF,0xD5,0x9A,0xE9,0xE6,0x81,0xCE,0xF4,0x81,0xB6,0xFB,0x9A,0xA9,0xFA,0xC3,0xA9,0xF0,0xF4,0xB8,0xB8,0xB8,0x00,0x00,0x00,0x00,0x00,0x00]

# "bank" is the bank of the pointer read, not the bank of the address
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

def load_tile(addr, pal, img, bx, by):
    for y in range(8):
        lo = chrrom[addr+y]
        hi = chrrom[addr+y+8]
        for x in range(8):
            lb = (lo >> (7-x)) & 1
            hb = (hi >> (7-x)) & 1
            b = (hb << 1) | lb
            c = pal[b]
            img.putpixel((bx+x,by+y), c)
    return img

def get_palette(pal_id):
    BASE = 0x06DF
    addr = BASE + pal_id*9

    # TODO: Don't hardcode the default palette
    pals = [[0x0F, 0x16, 0x26, 0x20]]
    for i in range(3):
        pal = [0x0F]
        for j in range(3):
            pal.append(prgrom[addr+i*3+j])
        pals.append(pal)
    return pals

def get_room_chr(stage, block, room):
    # All pointers are in the first ROM bank
    stage_ptr = 0x005F
    block_ptr = read_ptr(stage_ptr+stage*2, 0)
    room_ptr = read_ptr(block_ptr+block*4, 0)
    chr_5 = prgrom[room_ptr+room*2]
    chr_6 = prgrom[room_ptr+room*2+1]
    return (chr_5,chr_6)

def get_room_pal(stage, block, room):
    stage_ptr = read_ptr(0x0541+stage*2, 0x0)
    block_ptr = read_ptr(stage_ptr+block*4, 0x0)
    index = prgrom[block_ptr+room]
    return index

def get_tsa_def(stage):
    def_addr = read_ptr(0x3D917 + stage*2, 0x10)
    pal_addr = read_ptr(0x3D935 + stage*2, 0x10)
    return (def_addr, pal_addr)

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

def render_tsa(tsa_id, tsa_def, tsa_attr, chr_5, chr_6, pal, img, bx, by):
    attr = prgrom[tsa_attr+tsa_id]
    attrs = [[(attr>>0)&3, (attr>>2)&3], [(attr>>4)&3, (attr>>6)&3]]
    for y in range(4):
        for x in range(4):
            index = attrs[y//2][x//2]
            tile_id = prgrom[tsa_def+tsa_id*16+y*4+x]
            tile_addr = get_tile_addr(tile_id, chr_5, chr_6)
            load_tile(tile_addr, pal[index], img, bx+x*8, by+y*8)

def render_screen(addr, tsa_def, tsa_attr, chr_5, chr_6, pal, img, bx, by):
    for y in range(6):
        for x in range(8):
            tsa_id = prgrom[addr+x+y*8]
            render_tsa(tsa_id, tsa_def, tsa_attr, chr_5, chr_6, pal, img, bx+x*8*4, by+y*8*4)

def render_room(stage, block, room):
    SCREEN_X = 8*8*4
    SCREEN_Y = 6*8*4
    (tsa_def, tsa_attr) = get_tsa_def(stage)
    (room_size, tsa_map) = get_tsa_map(stage, block, room)
    (chr_5, chr_6) = get_room_chr(stage, block, room)
    pal = get_palette(get_room_pal(stage, block, room))
    
    img = Image.new('P', (room_size*SCREEN_X,SCREEN_Y))
    img.putpalette(NES_PAL)
    for x in range(room_size):
        render_screen(tsa_map+48*x, tsa_def, tsa_attr, chr_5, chr_6, pal, img, x*SCREEN_X, 0)
    img.show()

(prgrom, chrrom) = load_rom('Akumajou Densetsu (Japan).nes')
render_room(0,0,0)
#print(get_palette(get_room_pal(0,0,0)))
