from queue import Queue
from threading import Thread
import os
import sys

from tkinter import *
from tkinter import filedialog

from soar.main import client
from soar.main.messages import *
from soar.geometry import *
from soar.gui.canvas import SoarCanvas
from soar.gui.output import OutputField
from soar.world.base import World

def polygon():

    # Building the 8-sided shape of the sonar faces
    s = [Point(0, 0) for i in range(9)]
    s[1].add((1, 0))
    s[2].add((2, 0))
    s[2].rotate(s[1], 2 * pi / 14.0)
    for i in range(3, 9):
        s[i].add(s[i - 1])
        s[i].scale(2.0, s[i - 2])
        s[i].rotate(s[i - 1], 2 * pi / 14.0)
    s = PointCollection(s, fill='red', tags='poly')
    return s


class SoarUI(Tk):
    image_dir = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), 'media/')

    def __init__(self, parent=None, brain_path=None, world_path=None, title='SoaR v0.5.0'):
        Tk.__init__(self, parent)
        #self.parent = parent
        self.title(title)
        self.play_image = PhotoImage(file=os.path.join(self.image_dir, 'play.gif'))
        self.pause_image = PhotoImage(file=os.path.join(self.image_dir, 'pause.gif'))
        self.step_image = PhotoImage(file=os.path.join(self.image_dir, 'step.gif'))
        self.stop_image = PhotoImage(file=os.path.join(self.image_dir, 'stop.gif'))
        self.play = Button(self)
        self.step = Button(self)
        self.stop = Button(self)
        self.reload = Button(self)
        self.brain_but = Button(self)
        self.world_but = Button(self)
        self.sim_but = Button(self)
        self.real = Button(self)
        self.output = OutputField(self)
        self.initialize()
        self.brain_path = brain_path
        self.world_path = world_path
        if self.brain_path is not None:
            self.load_brain()
        if self.world_path is not None:
            self.load_world()
        self.sim_window = None
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.file_opt = {
            'defaultextension': '.py',
            'filetypes': [('all files', '.*'), ('python files',' .py')],
            'parent': parent,
            'title': "Find your file",
        }
        self.draw_queue = Queue(maxsize=1000)
        self.print_queue = Queue(maxsize=1000)

    def initialize(self):
        self.grid()
        self.reset()
        self.play.grid(column=0, row=0, pady=5)
        self.step.grid(column=1, row=0, pady=5)
        self.stop.grid(column=2, row=0, pady=5)
        self.reload.grid(column=3, row=0, pady=5)
        self.brain_but.grid(column=4, row=0)
        self.world_but.grid(column=5, row=0)
        self.sim_but.grid(column=6, row=0)
        self.real.grid(column=7, row=0)
        self.output.grid(column=0, row=2, columnspan=8, sticky='EW')
        self.resizable(False, False)  # TODO: Can only be resized horizontally

    def reset(self):
        self.play.config(state=DISABLED, image=self.play_image, command=self.play_cmd)
        self.step.config(state=DISABLED, image=self.step_image, command=self.step_cmd)
        self.stop.config(state=DISABLED, image=self.stop_image, command=self.stop_cmd)
        self.reload.config(state=DISABLED, text='RELOAD', command=self.reload_cmd)
        self.brain_but.config(state=NORMAL, text='BRAIN', command=self.brain_cmd)
        self.world_but.config(state=NORMAL, text='WORLD', command=self.world_cmd)
        self.sim_but.config(state=DISABLED, text='SIMULATOR', command=self.sim_cmd)
        self.real.config(state=DISABLED, text='REAL ROBOT', command=self.real_cmd)

    def mainloop(self, n=0):
        t = Thread(target=client.mainloop, daemon=True)
        t.start()
        self.after(0, self.tick)
        Tk.mainloop(self, n)
        t.join()

    def tick(self):
        while not self.print_queue.empty():
            text = self.print_queue.get()
            self.output.output(text)
            self.print_queue.task_done()
        while not self.draw_queue.empty():
            obj = self.draw_queue.get()
            if isinstance(obj, World) and self.sim_window is None:
                self.sim_window = self.canvas_from_world(obj)
                self.sim_window.grid(row=1, columnspan=8)
                obj.draw(self.sim_window)
            elif obj == 'DESTROY':
                self.sim_window.destroy()
                self.sim_window = None
            else:
                obj.delete(self.sim_window)
                obj.draw(self.sim_window)
            self.draw_queue.task_done()
        self.after(10, self.tick)

    def close(self):
        self.destroy()
        client.message(CLOSE)  # HACK
        client.message(CLOSE)

    def play_cmd(self):
        self.play.config(image=self.pause_image, command=self.pause_cmd)
        self.stop.config(state=NORMAL)
        client.message(START_SIM)

    def pause_cmd(self):
        self.play.config(image=self.play_image, command=self.play_cmd)
        client.message(PAUSE_SIM)

    def step_cmd(self):
        self.stop.config(state=NORMAL)
        client.message(STEP_SIM)

    def stop_cmd(self):
        self.play.config(image=self.play_image, command=self.play_cmd, state=DISABLED)
        self.step.config(state=DISABLED)
        self.stop.config(state=DISABLED)
        client.message(STOP_SIM)

    def reload_cmd(self):
        # Reload consists of killing the brain, and simulator (or real robot process),
        # followed by opening them up again. We ignore brain death once when doing this.
        #
        client.message(CLOSE_SIM)
        client.message(LOAD_BRAIN, self.brain_path)
        client.message(LOAD_WORLD, self.world_path)
        self.reset()
        self.load_brain()
        self.load_world()

    def load_brain(self):
        self.real.config(state=NORMAL)
        if self.world_path is not None:
            self.sim_but.config(state=NORMAL)

    def load_world(self):
        if self.brain_path is not None:
            self.sim_but.config(state=NORMAL)


    def brain_cmd(self):
        new_brain = filedialog.askopenfilename(**self.file_opt)
        if new_brain:
            if self.brain_path is not None and self.world_path is not None:
                self.brain_path = new_brain
                self.reload_cmd()
            else:
                self.brain_path = new_brain
                client.message(LOAD_BRAIN, new_brain)
                self.load_brain()

    def world_cmd(self):
        new_world = filedialog.askopenfilename(**self.file_opt)
        if new_world:
            if self.brain_path is not None and self.world_path is not None:
                self.world_path = new_world
                self.reload_cmd()
            else:
                self.world_path = new_world
                client.message(LOAD_WORLD, new_world)
                self.load_world()

    def canvas_from_world(self, world):
        dim_x, dim_y = world.dimensions
        max_dim = max(dim_x, dim_y)
        options = {'width': int(dim_x/max_dim*500), 'height': int(dim_y/max_dim*500), 'pixels_per_meter': 500/max_dim,
                   'bg': 'white'}
        return SoarCanvas(self, **options)

    def sim_cmd(self):
        client.message(MAKE_SIM)
        self.draw_queue.join()
        self.play.config(image=self.play_image, state=NORMAL)
        self.step.config(state=NORMAL)
        self.stop.config(state=DISABLED)
        self.reload.config(state=NORMAL)
        self.sim_but.config(text='CLOSE', command=self.close_sim_cmd)


    def close_sim_cmd(self):
        client.message(CLOSE_SIM)
        self.draw_queue.join()
        self.sim_but.config(text='SIMULATOR', command=self.sim_cmd)


    def real_cmd(self):
        self.real_set = True