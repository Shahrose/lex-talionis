#! usr/bin/env python2.7
import pygame, sys
from pygame.locals import *

import configuration

import logging
logger = logging.getLogger(__name__)

engine_constants = {'current_time': 0,
                    'last_time': 0,
                    'last_fps': 0}

def create_surface(size, transparent=False, convert=False):
    if transparent:
        surf = pygame.Surface(size, pygame.SRCALPHA, 32)
        if convert:
            surf = surf.convert_alpha()
        return surf
    else:
        surf = pygame.Surface(size)
        if convert:
            surf = surf.convert()
        return surf

def copy_surface(surf):
    return surf.copy()

def update_time():
    engine_constants['last_time'] = engine_constants['current_time']
    engine_constants['current_time'] = pygame.time.get_ticks()
    engine_constants['last_fps'] = engine_constants['current_time'] - engine_constants['last_time']
    if engine_constants['last_fps'] > 32:
        print('Frame took too long! %s', engine_constants['last_fps'])
        logger.debug('Frame took too long! %s', engine_constants['last_fps'])
    
def get_time():
    return engine_constants['current_time']

def get_last_time():
    return engine_constants['last_time']

def get_true_time():
    return pygame.time.get_ticks()

# assumes pygame surface
def subsurface(surf, (x, y, width, height)):
    #print(x, y, width, height)
    return surf.subsurface(x, y, width, height)

def flip_horiz(surf):
    return pygame.transform.flip(surf, 1, 0)

def flip_vert(surf):
    return pygame.transform.flip(surf, 0, 1)

def image_load(fp, convert=False, convert_alpha=False):
    try:
        image = pygame.image.load(fp)
    except pygame.error:
        print("ERROR! If you cloned this from source,\nYou didn't use Git LFS to bring down the sprites!\nGo install Git LFS!\n\n \
               If this is just an executable, then you are missing files. Sorry!")
        terminate()
    if convert:
        image = image.convert()
    elif convert_alpha:
        image = image.convert_alpha()
    return image

def fill(surf, color, blend):
    if blend == 'RGBA_MULT':
        blend_mode = pygame.BLEND_RGBA_MULT
    elif blend == 'RGB_ADD':
        blend_mode = pygame.BLEND_RGB_ADD
    else:
        blend_mode = 0
    surf.fill(color, None, blend_mode)

def set_colorkey(surf, color, rleaccel=True):
    if rleaccel:
        surf.set_colorkey(color, pygame.RLEACCEL)
    else:
        surf.set_colorkey(color)

class BaseSound():
    def play(self, loops=0, maxtime=0, fade_ms=0):
        pass
    def stop():
        pass
    def fadeout(time):
        pass
    def set_volume(value):
        pass
    def get_volume():
        pass

def create_sound(fp):
    return pygame.mixer.Sound(fp)

def get_key_name(key_code):
    return pygame.key.name(key_code)

def transform_scale(surf, scale):
    return pygame.transform.scale(surf, scale)

def transform_rotate(surf, degrees):
    return pygame.transform.rotate(surf, degrees)

def terminate():
    configuration.write_config_file() # Write last saved options to config file
    pygame.mixer.music.stop()
    pygame.mixer.quit()
    pygame.quit()
    sys.exit()

def build_event_list():
    # Get events
    eventList = [] # Clear event list
    # Only gets escape events!
    for event in pygame.event.get():
        if event.type == QUIT:
            terminate()
        if event.type == KEYUP and configuration.OPTIONS['debug']:
            if event.key == K_ESCAPE:
                terminate()
        eventList.append(event)
    return eventList

### === MUSIC STUFF =====================================================
class Song(object):
    def __init__(self, song, num_plays=-1, time=0):
        self.song = song
        self.num_plays = num_plays
        self.current_time = time

        if self.song.endswith('- Start.ogg'):
            self.loop = self.song[:-11] + '- Loop.ogg'
        else:
            self.loop = None

    def swap(self):
        self.song = self.loop[:]
        self.loop = None

class MusicThread(object):
    def __init__(self):
        self.song_stack = []
        self.volume = 1.0

        self.fade_out_time = 200
        self.fade_out_update = 0

        self.state = 'normal'

        self.end_song = pygame.USEREVENT + 1
        pygame.mixer.music.set_endevent(self.end_song)

        self.current = None
        self.next = None

        self.debug = 0

    def clear(self):
        self.song_stack = []
        self.state = "normal"

    def pause(self):
        pygame.mixer.music.pause()

    def resume(self):
        pygame.mixer.music.unpause()

    def set_volume(self, volume):
        self.volume = volume
        pygame.mixer.music.set_volume(self.volume)
    
    def fade_to_normal(self, gameStateObj, metaDataObj):
        logger.info('Music: Fade to Normal')
        phase_name = gameStateObj.statedict['phases'][gameStateObj.statedict['current_phase']].name
        if phase_name == 'player':
            self.fade_in(metaDataObj['playerPhaseMusic'])
        elif phase_name.startswith('enemy'):
            self.fade_in(metaDataObj['enemyPhaseMusic'])
        elif phase_name == 'other':
            self.fade_in(metaDataObj['otherPhaseMusic'])
        else:
            logging.error('Unsupported phase name: %s', phase_name)
        #self.music_stack = [] # Clear the stack

    def fade_in(self, next, num_plays=-1, time=0):
        logger.info('Music: Fade in')
        # Confirm thats its not already at the top of the stack
        if self.song_stack and self.song_stack[-1].song == next:
            logger.info('Music: Already Present')
            return
        # Determine if song is in stack
        for song in self.song_stack:
            # If so, move to top of stack
            if song.song == next:
                logger.info('Music: Pull Up')
                self.song_stack.remove(song)
                self.song_stack.append(song)
                break
        else:
            logger.info('Music: New')
            new_song = Song(next, num_plays, time)
            self.song_stack.append(new_song)

        # Update the current one -- so we know where to head back to
        if self.current:
            self.current.current_time += pygame.mixer.music.get_pos()/1000

        # This is where we are going to
        self.next = self.song_stack[-1]

        # Start fade out process
        self.state = 'fade' # Now we know to fade to next index
        pygame.mixer.music.fadeout(self.fade_out_time)
        self.fade_out_update = get_time()

    def fade_back(self):
        logger.info('Music: Fade back')
        # Confirm that there is something to pop
        if not self.song_stack:
            return
        self.song_stack.pop()

        self.next = self.song_stack[-1]

        # Start fade out process
        self.state = 'fade' # Now we know to fade to next index
        pygame.mixer.music.fadeout(self.fade_out_time)
        self.fade_out_update = get_time()

    def fade_out(self, time=400):
        pygame.mixer.music.fadeout(time)

    def stop(self):
        pygame.mixer.music.stop()

    def update(self, eventList):
        current_time = get_time()
        """
        if not pygame.mixer.music.get_busy():
            if self.debug:
                print(current_time - self.debug)
            print('Music not playing!')
            self.debug = 0
        elif not self.debug:
            print('--')
            self.debug = current_time
        """
        #logger.debug(current_time)

        ### Take Input
        for event in eventList:
            if event.type == self.end_song:
                if self.state == 'normal':
                    logger.debug('Music: Normal Event')
                    if self.current.loop:
                        self.current.swap()
                        pygame.mixer.music.load(self.current.song)
                        pygame.mixer.music.play(0)
                    elif self.current.num_plays == -1:
                        pygame.mixer.music.play(0)
                    self.current.current_time = 0
                elif self.state == 'fade':
                    logger.debug('Music: Fade Event')
                    self.state = 'normal' # catches the stop from fade

        ### Update
        if self.state == 'normal':
            pass

        elif self.state == 'fade':
            if current_time - self.fade_out_update > self.fade_out_time:
                logger.debug('Music: Actual Fade in!')
                self.current = self.next
                if pygame.mixer.music.get_busy():
                    self.fade_out_update = current_time
                #self.next = None
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.stop()
                pygame.mixer.music.load(self.current.song)
                pygame.mixer.music.play(0, self.current.current_time)
                #self.fade_out_update = current_time
                #self.state = 'normal'

music_thread = MusicThread()
