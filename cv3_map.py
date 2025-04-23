from PIL import Image

PRG_SIZE = 256 * 1024
CHR_SIZE = 128 * 1024

#3C94B has the stage banks?

with open('nes.pal', 'rb') as f:
    NES_PAL = f.read()

# "bank" is the bank of the pointer read, not the bank of the address
def read_ptr(addr, bank):
    lo = prgrom[addr]
    hi = prgrom[addr+1]
    ptr = (hi << 8)|lo
    return (ptr&0x3FFF)|(bank * 0x2000)

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

def get_room_type(stage, block, room):
    stage_ptr = read_ptr(0x3D953 + stage*2, 0x1E)
    block_ptr = read_ptr(stage_ptr + block*2, 0x1E)
    return prgrom[block_ptr+room]

def get_tsa_def(stage):
    rom_bank = prgrom[0x3C94B + stage] * 2
    def_addr = read_ptr(0x3D917 + stage*2, rom_bank)
    pal_addr = read_ptr(0x3D935 + stage*2, rom_bank)
    return (def_addr, pal_addr)

def get_tsa_map(stage, block, room):
    rom_bank = prgrom[0x3C94B + stage] * 2
    stage_ptr = read_ptr(0x3D8F9+stage*2, rom_bank)
    block_ptr = read_ptr(stage_ptr+block*2, rom_bank)
    room_ptr = read_ptr(block_ptr+room*2+1, rom_bank)
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

def render_screen(addr, tsa_def, tsa_attr, chr_5, chr_6, pal, img, bx, by, y_size):
    for y in range(y_size):
        for x in range(8):
            tsa_id = prgrom[addr+x+y*8]
            render_tsa(tsa_id, tsa_def, tsa_attr, chr_5, chr_6, pal, img, bx+x*8*4, by+y*8*4)

def render_room(stage, block, room):    
    (tsa_def, tsa_attr) = get_tsa_def(stage)
    (room_size, tsa_map) = get_tsa_map(stage, block, room)
    (chr_5, chr_6) = get_room_chr(stage, block, room)
    pal = get_palette(get_room_pal(stage, block, room))

    room_type = get_room_type(stage, block, room)
    if room_type & 0x80:
        # Vertical rooms are weird because there's a 16-pixel row (half a metatile)
        # at the bottom of each screen that doesn't actually show up
        SCREEN_X = 256
        SCREEN_Y = 240
        img = Image.new('P', (SCREEN_X,room_size*SCREEN_Y+16))
        img.putpalette(NES_PAL)
        for y in range(room_size):
            render_screen(tsa_map+64*y, tsa_def, tsa_attr, chr_5, chr_6, pal, img, 0, y*SCREEN_Y, 8)
        img = img.crop((0, 0, SCREEN_X, room_size*SCREEN_Y))
    else:
        SCREEN_X = 256
        SCREEN_Y = 192
        img = Image.new('P', (room_size*SCREEN_X,SCREEN_Y))
        img.putpalette(NES_PAL)
        for x in range(room_size):
            render_screen(tsa_map+48*x, tsa_def, tsa_attr, chr_5, chr_6, pal, img, x*SCREEN_X, 0, 6)
    img.show()

(prgrom, chrrom) = load_rom('Akumajou Densetsu (Japan).nes')
for i in range(15):
    render_room(i,0,0)
#print(get_palette(get_room_pal(0,0,0)))
