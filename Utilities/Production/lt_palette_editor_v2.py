import sys, os
import glob
from PyQt4 import QtGui, QtCore

from palette_editor_code import PaletteList
from palette_editor_code import ImageMap
from palette_editor_code import Animation

class MainView(QtGui.QGraphicsView):
    min_scale = 1
    max_scale = 5

    def __init__(self, window=None):
        QtGui.QGraphicsView.__init__(self)
        self.window = window
        self.scene = QtGui.QGraphicsScene(self)
        self.setScene(self.scene)

        self.setMouseTracking(True)

        self.image = None
        self.screen_scale = 1

    def set_image(self, image_map, palette_frame):
        colors = [QtGui.QColor(c).rgb() for c in palette_frame.get_colors()]
        width, height = image_map.width, image_map.height
        image = QtGui.QImage(width, height, QtGui.QImage.Format_ARGB32)
        for x in range(width):
            for y in range(height):
                idx = image_map.get(x, y)
                image.setPixel(x, y, colors[idx])
        self.image = QtGui.QImage(image)
        # self.image = self.image.convertToFormat(QtGui.QImage.Format_ARGB32)
        self.setSceneRect(0, 0, self.image.width(), self.image.height())

    def clear_scene(self):
        self.scene.clear()

    def show_image(self):
        if self.image:
            self.clear_scene()
            self.scene.addPixmap(QtGui.QPixmap.fromImage(self.image))

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        pixmap = self.scene.itemAt(scene_pos)
        if not pixmap:
            return
        image = pixmap.pixmap().toImage()
        pos = int(scene_pos.x()), int(scene_pos.y())

        if event.button() == QtCore.Qt.LeftButton:
            dlg = QtGui.QColorDialog()
            dlg.setCurrentColor(QtGui.QColor(image.pixel(pos[0], pos[1])))
            if dlg.exec_():
                self.window.change_current_palette(pos, dlg.currentColor())

    def wheelEvent(self, event):
        if event.delta() > 0 and self.screen_scale < self.max_scale:
            self.screen_scale += 1
            self.scale(2, 2)
        elif event.delta() < 0 and self.screen_scale > self.min_scale:
            self.screen_scale -= 1
            self.scale(0.5, 0.5)

class MainEditor(QtGui.QWidget):
    def __init__(self):
        super(MainEditor, self).__init__()
        self.setWindowTitle('Lex Talionis Palette Editor v5.9.0')
        self.setMinimumSize(640, 480)

        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)

        self.main_view = MainView(self)
        self.menu_bar = QtGui.QMenuBar(self)
        self.palette_list = PaletteList.PaletteList(self)
        self.image_map_list = ImageMap.ImageMapList()
        self.scripts = []

        self.create_menu_bar()

        self.grid.setMenuBar(self.menu_bar)
        self.grid.addWidget(self.main_view, 0, 0)
        self.grid.addWidget(self.palette_list, 0, 1, 2, 1)
        self.info_form = QtGui.QFormLayout()
        self.grid.addLayout(self.info_form, 1, 0)

        self.create_info_bars()
        self.clear_info()

    def create_menu_bar(self):
        load_class_anim = QtGui.QAction("Load Class Animation...", self, triggered=self.load_class)
        load_single_anim = QtGui.QAction("Load Single Animation...", self, triggered=self.load_single)
        load_image = QtGui.QAction("Load Image...", self, triggered=self.load_image)
        save = QtGui.QAction("&Save...", self, shortcut="Ctrl+S", triggered=self.save)
        exit = QtGui.QAction("E&xit...", self, shortcut="Ctrl+Q", triggered=self.close)

        file_menu = QtGui.QMenu("&File", self)
        file_menu.addAction(load_class_anim)
        file_menu.addAction(load_single_anim)
        file_menu.addAction(load_image)
        file_menu.addAction(save)
        file_menu.addAction(exit)

        self.menu_bar.addMenu(file_menu)

    def create_info_bars(self):
        self.class_text = QtGui.QLineEdit()
        self.class_text.textChanged.connect(self.class_text_change)
        self.weapon_box = QtGui.QComboBox()
        self.weapon_box.uniformItemSizes = True
        self.weapon_box.activated.connect(self.weapon_changed)
        self.palette_text = QtGui.QLineEdit()
        self.palette_text.textChanged.connect(self.palette_text_change)

        self.play_button = QtGui.QPushButton("View Animation")
        self.play_button.clicked.connect(self.view_animation)
        self.play_button.setEnabled(False)

        self.info_form.addRow("Class", self.class_text)
        self.info_form.addRow("Weapon", self.weapon_box)
        self.info_form.addRow("Palette", self.palette_text)
        self.info_form.addRow(self.play_button)

    def change_current_palette(self, position, color):
        palette_frame = self.palette_list.get_current_palette()
        image_map = self.image_map_list.get_current_map()
        color_idx = image_map.get(position[0], position[1])
        palette_frame.set_color(color_idx, color)

    def view_animation(self):
        image = self.main_view.image
        index = self.image_map_list.get_current_map().get_index()
        script = self.image_map_list.get_current_map().get_script()
        ok = Animation.Animator.get_dialog(image, index, script)

    def clear_info(self):
        self.class_text.setEnabled(True)
        self.class_text.setText('')
        self.weapon_box.clear()
        self.palette_text.setText('')
        self.play_button.setEnabled(False)
        self.image_map_list.clear()
        self.palette_list.clear()
        self.scripts = []

    def class_text_change(self):
        pass

    def palette_text_change(self):
        self.palette_list.get_current_palette().set_name(self.palette_text.text())

    def weapon_changed(self, idx):
        self.image_map_list.set_current_idx(idx)
        self.update_view()

    def update_view(self):
        cur_image_map = self.image_map_list.get_current_map()
        cur_palette = self.palette_list.get_current_palette()
        self.main_view.set_image(cur_image_map, cur_palette)
        self.main_view.show_image()

    def get_script_from_index(self, fn):
        script = fn[:-10] + '-Script.txt'
        if os.path.exists(script):
            return script
        return None

    def get_images_from_index(self, fn):
        image_header = fn[:-10]
        images = glob.glob(str(image_header + "-*.png"))
        return images

    def get_all_index_files(self, index_file):
        head, tail = os.path.split(index_file)
        class_name = tail.split('-')[0]
        index_files = glob.glob(head + '/' + class_name + "*-Index.txt")
        return index_files

    def handle_duplicates(self, palette, image_map):
        for existing_palette in self.palette_list.list[:-1]:
            # TODO palette != existing_palette
            print(palette.name, existing_palette.name)
            if existing_palette.name == palette.name and palette.get_colors() != existing_palette.get_colors():
                image_map.reorder(palette, existing_palette)
                return True
        return False

    def auto_load(self):
        starting_path = QtCore.QDir.currentPath()
        check_here = str(QtCore.QDir.currentPath() + '/pe_config.txt')
        if os.path.exists(check_here):
            with open(check_here) as fp:
                directory = fp.readline().strip()
            if os.path.exists(directory):
                starting_path = directory
        return starting_path

    def load_class(self):
        # starting_path = QtCore.QDir.currentPath() + '/../Data'
        index_file = QtGui.QFileDialog.getOpenFileName(self, "Choose Class", QtCore.QDir.currentPath(),
                                                       "Index Files (*-Index.txt);;All Files (*)")
        if index_file:
            self.clear_info()
            weapon_index_files = self.get_all_index_files(str(index_file))
            for index_file in weapon_index_files:  # One for each weapon
                script_file = self.get_script_from_index(index_file)
                image_files = [str(i) for i in self.get_images_from_index(index_file)]
                if image_files:
                    image_map = self.image_map_list.add_map_from_image(image_files[0])
                    image_map.load_script(script_file)
                    image_map.set_index(index_file)
                    self.play_button.setEnabled(True)
                    for image_filename in image_files:
                        self.palette_list.add_palette_from_image(image_filename)
                        dup = self.handle_duplicates(self.palette_list.get_current_palette(), image_map)
                        if dup:
                            self.palette_list.remove_last_palette()
            for weapon in self.image_map_list.get_available_weapons():
                self.weapon_box.addItem(weapon)
            klass_name = os.path.split(image_files[0][:-4])[-1].split('-')[0]  # Klass
            self.class_text.setText(klass_name)
            self.palette_list.set_current_palette(0)

    def load_single(self):
        starting_path = self.auto_load()
        print(starting_path)
        index_file = QtGui.QFileDialog.getOpenFileName(self, "Choose Animation", starting_path,
                                                       "Index Files (*-Index.txt);;All Files (*)")
        auto_load = str(QtCore.QDir.currentPath() + '/pe_config.txt')
        with open(auto_load, 'w') as fp:
            print(os.path.relpath(str(index_file)))
            fp.write(os.path.relpath(str(index_file)))
        if index_file:
            script_file = self.get_script_from_index(index_file)
            image_files = [str(i) for i in self.get_images_from_index(index_file)]
            if image_files:
                self.clear_info()
                image_map = self.image_map_list.add_map_from_image(image_files[0])
                image_map.load_script(script_file)
                image_map.set_index(index_file)
                self.play_button.setEnabled(True)
                for image_filename in image_files:
                    self.palette_list.add_palette_from_image(image_filename)
                self.weapon_box.addItem(self.image_map_list.get_current_map().weapon_name)
                klass_name = os.path.split(image_files[0][:-4])[-1].split('-')[0]  # Klass
                self.class_text.setText(klass_name)
                self.palette_list.set_current_palette(0)

    def load_image(self):
        image_filename = QtGui.QFileDialog.getOpenFileName(self, "Choose Image PNG", QtCore.QDir.currentPath(),
                                                           "PNG Files (*.png);;All Files (*)")
        if image_filename:
            self.clear_info()
            self.image_map_list.add_map_from_image(str(image_filename))
            self.palette_list.add_palette_from_image(str(image_filename))
            self.class_text.setEnabled(False)
            self.palette_list.set_current_palette(0)

    def save(self):
        pass

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    main_editor = MainEditor()
    main_editor.show()
    app.exec_()