from PIL import Image

# "bank" is the bank of the pointer read, not the bank of the address
def read_ptr(addr, bank):
    lo = prgrom[addr]
    hi = prgrom[addr+1]
    ptr = (hi << 8)|lo
    return (ptr&0x3FFF)|(bank * 0x2000)

def load_rom(filename):
    PRG_SIZE = 256 * 1024
    CHR_SIZE = 128 * 1024
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

def get_tile_addr(tile, chr_5, chr_6):
    assert tile < 0x100
    sets = [0x40, chr_5, chr_6, 0x43]
    bank = sets[tile >> 6]
    tile &= 0x3F
    addr = bank * 0x400 + tile * 0x10
    return addr

def render_tsa(room, tsa_id, img, bx, by):
    attr = prgrom[room.tsa_attr+tsa_id]
    attrs = [[(attr>>0)&3, (attr>>2)&3], [(attr>>4)&3, (attr>>6)&3]]
    for y in range(4):
        for x in range(4):
            index = attrs[y//2][x//2]
            tile_id = prgrom[room.tsa_def+tsa_id*16+y*4+x]
            tile_addr = get_tile_addr(tile_id, room.chr_5, room.chr_6)
            load_tile(tile_addr, room.pal[index], img, bx+x*8, by+y*8)

def render_screen(room, addr, img, bx, by, y_size):
    for y in range(y_size):
        for x in range(8):
            tsa_id = prgrom[addr+x+y*8]
            render_tsa(room, tsa_id, img, bx+x*8*4, by+y*8*4)

class Room:    
    def __init__(self, stage, block, subroom):
        self.stage = int(stage)
        self.block = int(block)
        self.subroom = int(subroom)

        stage_ptr = 0x005F
        block_ptr = read_ptr(stage_ptr+self.stage*2, 0)
        room_ptr = read_ptr(block_ptr+self.block*4, 0)
        self.chr_5 = prgrom[room_ptr+self.subroom*2]
        self.chr_6 = prgrom[room_ptr+self.subroom*2+1]

        stage_ptr = read_ptr(0x0541+self.stage*2, 0x0)
        block_ptr = read_ptr(stage_ptr+self.block*4, 0x0)
        self.pal = get_palette(prgrom[block_ptr+self.subroom])

        stage_ptr = read_ptr(0x3D953 + self.stage*2, 0x1E)
        block_ptr = read_ptr(stage_ptr + self.block*2, 0x1E)
        self.type = prgrom[block_ptr+self.subroom]
        
        rom_bank = prgrom[0x3C94B + self.stage] * 2
        self.tsa_def = read_ptr(0x3D917 + self.stage*2, rom_bank)
        self.tsa_attr = read_ptr(0x3D935 + self.stage*2, rom_bank)

        stage_ptr = read_ptr(0x3D8F9+self.stage*2, rom_bank)
        block_ptr = read_ptr(stage_ptr+self.block*2, rom_bank)
        room_ptr = read_ptr(block_ptr+self.subroom*2+1, rom_bank)
        self.size = prgrom[room_ptr]+1
        self.tsa_map = room_ptr+1

        if self.type & 0x80:
            # Vertical room
            self.h = self.size*240
            self.w = 256
        else:
            # Horizontal room
            self.h = 192
            self.w = self.size*256

def render_room(room):
    if room.type & 0x80:
        # Vertical rooms are weird because there's a 16-pixel row (half a metatile)
        # at the bottom of each screen that doesn't actually show up
        SCREEN_X = 256
        SCREEN_Y = 240
        img = Image.new('P', (SCREEN_X, room.size*SCREEN_Y+16))
        img.putpalette(NES_PAL)
        for y in range(room.size):
            render_screen(room, room.tsa_map+64*y, img, 0, y*SCREEN_Y, 8)
        img = img.crop((0, 0, SCREEN_X, room.size*SCREEN_Y))
    else:
        SCREEN_X = 256
        SCREEN_Y = 192
        img = Image.new('P', (room.size*SCREEN_X, SCREEN_Y))
        img.putpalette(NES_PAL)
        for x in range(room.size):
            render_screen(room, room.tsa_map+48*x, img, x*SCREEN_X, 0, 6)
    return img

def create_world(filename):
    with open('worlds/' + filename + '.txt', 'r') as f:
        lines = f.readlines()
    lines = [line.rstrip() for line in lines]

    # Handle first room specially
    l0 = lines[0].split(' ')
    room = Room(*l0)
    room.x = 0
    room.y = 0
    rooms = [room]
    lines = lines[1:]

    for line in lines:
        l = line.split(' ')
        new_room = Room(*l[0:3])
        attach_side = l[3]
        
        if len(l) > 4:
            offset = int(l[4])*16
        else:
            offset = 0

        if len(l) > 5:
            old_room = rooms[int(l[5])]
        else:
            old_room = rooms[-1]

        if attach_side == 'U':
            new_room.x = old_room.x + offset
            new_room.y = old_room.y - new_room.h
        elif attach_side == 'D':
            new_room.x = old_room.x + offset
            new_room.y = old_room.y + old_room.h
        elif attach_side == 'L':
            new_room.x = old_room.x - new_room.w
            new_room.y = old_room.y + offset
        elif attach_side == 'R':
            new_room.x = old_room.x + old_room.w
            new_room.y = old_room.y + offset
        else:
            assert 1==0
        rooms.append(new_room)

    # Figure out bounds
    min_x = 0
    min_y = 0
    max_x = 0
    max_y = 0
    for room in rooms:
        min_x = min(room.x, min_x)
        min_y = min(room.y, min_y)
        max_x = max(room.x+room.w, max_x)
        max_y = max(room.y+room.h, max_y)

    # Adjust coordinates so they're all positive
    for room in rooms:
        room.x -= min_x
        room.y -= min_y

    w = max_x - min_x
    h = max_y - min_y
    return (rooms, w, h)

def render_world(world, w, h):
    img = Image.new('RGBA', (w, h))
    for room in world:
        room_img = render_room(room)
        img.paste(room_img, (room.x, room.y, room.x+room.w, room.y+room.h))
    img.show()

with open('nes.pal', 'rb') as f:
    NES_PAL = f.read()
(prgrom, chrrom) = load_rom('Akumajou Densetsu (Japan).nes')
#render_stage()
#print(get_palette(get_room_pal(0,0,0)))

render_world(*create_world('07'))
