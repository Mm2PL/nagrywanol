import os
import queue
import sys
import mimetypes
from concurrent.futures import ThreadPoolExecutor, Future

import pydub
from PyQt5 import QtWidgets
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from interfejs import Ui_MainWindow
from obr import podziel
from obr.util import safe_name


class UserInterface(Ui_MainWindow):
    def __init__(self):
        self.file_picker_dialog = QFileDialog()
        self.mimetypes = mimetypes.MimeTypes()
        self.model_split_file_list = QStandardItemModel()
        self.model_split_channels_file_list = QStandardItemModel()
        self.model_listview_log = QStandardItemModel()
        self.executor = ThreadPoolExecutor()
        self.split_queue = queue.Queue()
        self.pre_processing_tab = 0

    def _set_processing(self, value):
        if value:
            current = self.action_picker.currentIndex()
            if current != 4:
                self.pre_processing_tab = current  # "doing things" tab shouldn't be considered here.
            print(repr(self.pre_processing_tab), repr(current))

        self.action_picker.setTabEnabled(4, value)
        self.action_picker.setCurrentIndex(4 if value else self.pre_processing_tab)
        print(repr(4 if value else self.pre_processing_tab))

        for i in range(0, 4):
            self.action_picker.setTabEnabled(i, not value)

    def setupUi(self, main_win):
        super().setupUi(main_win)
        self.button_from_file.clicked.connect(
            lambda *a: self.action_picker.setCurrentIndex(1)
        )

        self.button_next_step.clicked.connect(
            lambda *a: self.action_picker.setCurrentIndex(3)
        )

        self.button_next_step2.clicked.connect(
            lambda *a: self.action_picker.setCurrentIndex(2)
        )
        self._set_processing(False)

        self.button_autovolume_pick_file.clicked.connect(self.on_autovolume_pick_file)
        self.button_autovolume_pick_file.dropEvent = self.on_autovolume_drop
        self.button_autovolume_pick_file.setAcceptDrops(True)
        self.button_autovolume_pick_file.dragEnterEvent = self.on_drag_accepts_wave()

        self.button_split_pick_file.dragEnterEvent = self.on_drag_accepts_wave(True)
        self.button_split_pick_file.clicked.connect(self.on_split_pick_file)
        self.button_split_pick_file.dropEvent = self.on_button_split_drop
        self.button_split_pick_file.setAcceptDrops(True)

        self.listview_split_files.setModel(self.model_split_file_list)
        self.listview_split_files.dragEnterEvent = self.on_drag_accepts_wave(True)
        self.listview_split_files.dropEvent = self.on_button_split_drop
        self.listview_split_files.setAcceptDrops(True)

        self.listview_log.setModel(self.model_listview_log)

        self.button_delete_picked_file.clicked.connect(self.split_list_delete_item)

        self.slider_silence_length.valueChanged.connect(self.slider_silence_length_value_changed)

        self.button_check_volume_run.clicked.connect(self.check_volume_run)

        self.button_update_split_volume.clicked.connect(
            self.button_update_split_volume_on_click
        )

        self.button_split_accept.clicked.connect(self.split)

        self.button_back.clicked.connect(lambda: self._set_processing(False))

        # region split channels
        self.listview_split_channels_files.setModel(self.model_split_channels_file_list)
        self.listview_split_channels_files.dragEnterEvent = self.on_drag_accepts_wave(True)
        self.listview_split_channels_files.dropEvent = self.on_button_split_drop
        self.listview_split_channels_files.setAcceptDrops(True)

        self.button_split_channels_pick_file.dragEnterEvent = self.on_drag_accepts_wave(True)
        self.button_split_channels_pick_file.clicked.connect(self.on_split_channels_pick_file)
        self.button_split_channels_pick_file.dropEvent = self.on_button_channels_split_drop
        self.button_split_channels_pick_file.setAcceptDrops(True)

        self.button_split_channels_delete_picked_file.clicked.connect(self.split_channels_list_delete_item)

        self.button_split_channels_accept.clicked.connect(self.split_channels)
        # endregion

    def button_update_split_volume_on_click(self):
        self.spin_silence.setValue(self.spin_volume_output.value())
        self.action_picker.setCurrentIndex(3)

    def on_drag_accepts_wave(self, allow_multiple=False):
        def func(a0: QDragEnterEvent):
            mimedata = a0.mimeData()
            if mimedata.hasUrls():
                urls = mimedata.urls()
                if len(urls) == 1 or allow_multiple:
                    allow = True
                    for url in urls:
                        mimetype, _ = self.mimetypes.guess_type(url.toLocalFile())
                        if mimetype != 'audio/x-wav':
                            allow = False
                    a0.setAccepted(allow)
                    return

            a0.setAccepted(False)

        return func

    # region defs autovolume
    def on_autovolume_drop(self, a0: QDropEvent):
        mimedata = a0.mimeData()
        self.edit_autovolume_file_name.setText(mimedata.urls()[0].toLocalFile())

    def on_autovolume_pick_file(self):
        opts = self.file_picker_dialog.Options()
        fname, _ = (self.file_picker_dialog.getOpenFileName(None, 'Wybierz plik', '', 'Pliki audio wave (*.wav)',
                                                            options=opts))
        self.edit_autovolume_file_name.setText(fname)

    def _update_volume_output(self, fut: Future):
        print('update volume output', fut)
        res: int = fut.result()
        self.spin_volume_output.setValue(res)
        self.button_update_split_volume.setDisabled(False)

    def check_volume_run(self):
        path = self.edit_autovolume_file_name.text()
        if not os.path.exists(path):
            QMessageBox.information(main_window,
                                    app.translate('file_not_found', 'Plik nie istnieje'),
                                    app.translate('file_not_found', 'Plik {path!r} nie istnieje').format(path=path),
                                    buttons=QMessageBox.StandardButton(0))
            return

        task = self.executor.submit(self._really_check_volume, path)
        task.add_done_callback(self._update_volume_output)

    # endregion

    def on_button_split_drop(self, a0: QDropEvent):
        mimedata = a0.mimeData()
        for url in mimedata.urls():
            self.model_split_file_list.appendRow(QStandardItem(url.toLocalFile()))

    def on_button_channels_split_drop(self, a0: QDropEvent):
        mimedata = a0.mimeData()
        for url in mimedata.urls():
            self.model_split_channels_file_list.appendRow(QStandardItem(url.toLocalFile()))

    def on_split_pick_file(self):
        opts = self.file_picker_dialog.Options()
        fnames, _ = (self.file_picker_dialog.getOpenFileNames(None, 'Wybierz plik', '', 'Pliki audio wave (*.wav)',
                                                              options=opts))
        for fname in fnames:
            self.model_split_file_list.appendRow(QStandardItem(fname))

    def on_split_channels_pick_file(self):
        opts = self.file_picker_dialog.Options()
        fnames, _ = (self.file_picker_dialog.getOpenFileNames(None, 'Wybierz plik', '', 'Pliki audio wave (*.wav)',
                                                              options=opts))
        for fname in fnames:
            self.model_split_channels_file_list.appendRow(QStandardItem(fname))

    def split_list_delete_item(self, *args):
        for index in self.listview_split_files.selectedIndexes():
            self.model_split_file_list.removeRow(
                index.row(),
                index.parent()
            )

    def split_channels_list_delete_item(self, *args):
        for index in self.listview_split_channels_files.selectedIndexes():
            self.model_split_channels_file_list.removeRow(
                index.row(),
                index.parent()
            )

    def slider_silence_length_value_changed(self, e):
        if e % 100 != 0:
            self.slider_silence_length.setValue(e - e % 100)

    # region actions
    def _really_check_volume(self, path: str):
        print('really check volume')
        inp = pydub.AudioSegment.from_wav(path)
        return round(inp.dBFS, 3)

    def _move_files_from_list_view(self, model):
        for _ in range(model.rowCount()):
            row = model.takeRow(0)
            self.split_queue.put(row[0].text())

    def split(self):
        self._set_processing(True)
        self._move_files_from_list_view(self.model_split_file_list)
        try:
            path = self.split_queue.get_nowait()
        except queue.Empty:
            self.model_listview_log.appendRow(QStandardItem(
                app.translate('log', 'Wszystko zrobione!')
            ))
            self.button_back.setEnabled(True)
            return
        dest_dir = os.path.join(os.path.dirname(path), os.path.splitext(path)[0] + '_split')
        self.model_listview_log.appendRow(QStandardItem(
            app.translate('log', 'Dzielenie pliku {file!r} do katalogu {output!r}').format(
                file=path,
                output=dest_dir
            )
        ))
        min_silence_length = self.spin_silence_length.value()
        silence_thresh = self.spin_silence.value()
        task = self.executor.submit(self._really_split, path, min_silence_length, silence_thresh, dest_dir)
        task.add_done_callback(self._split_done)

    def split_channels(self):
        self._set_processing(True)
        self._move_files_from_list_view(self.model_split_channels_file_list)
        try:
            path = self.split_queue.get_nowait()
        except queue.Empty:
            self.model_listview_log.appendRow(QStandardItem(
                app.translate('log', 'Wszystko zrobione!')
            ))
            self.button_back.setEnabled(True)
            return
        dest_dir = os.path.join(os.path.dirname(path), os.path.splitext(path)[0] + '_split_channels')
        self.model_listview_log.appendRow(QStandardItem(
            app.translate('log', 'Rozdzielanie kanałów z pliku {file!r} do katalogu {output!r}').format(
                file=path,
                output=dest_dir
            )
        ))
        task = self.executor.submit(self._really_split_channels, path, dest_dir)
        task.add_done_callback(self._split_channels_done)

    def _split_done(self, fut: Future):
        try:
            fut.result()
        except Exception as e:
            self.model_listview_log.appendRow(QStandardItem(
                app.translate('log', 'Problem z dzieleniem. Błąd: {e!r}').format(
                    e=e
                )
            ))
        else:
            self.model_listview_log.appendRow(QStandardItem(
                app.translate('log', 'Podzielono :)')
            ))
        self.split()

    def _split_channels_done(self, fut: Future):
        try:
            fut.result()
        except Exception as e:
            self.model_listview_log.appendRow(QStandardItem(
                app.translate('log', 'Problem z dzieleniem. Błąd: {e!r}').format(
                    e=e
                )
            ))
        else:
            self.model_listview_log.appendRow(QStandardItem(
                app.translate('log', 'Podzielono :)')
            ))
        self.split_channels()

    def _really_split(self, path: str, min_silence_length: int, silence_thresh: float, dest_dir: str):
        os.mkdir(dest_dir)
        inp = pydub.AudioSegment.from_wav(path)
        podziel.split(
            inp,
            dest_dir,
            min_silence_length,
            silence_thresh,
            path
        )
        self.split_queue.task_done()

    def _really_split_channels(self, path: str, dest_dir: str):
        os.mkdir(dest_dir)
        inp = pydub.AudioSegment.from_wav(path)
        channels = inp.split_to_mono()
        n = safe_name(path)
        for i, ch in enumerate(channels):
            e_path = os.path.join(dest_dir, f'{n}_{i}.wav')
            print(f"Eksportownie dźwięku do {e_path}")
            ch.export(
                e_path,
                format="wav"
            )
        self.split_queue.task_done()
    # endregion


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    ui = UserInterface()
    ui.setupUi(main_window)
    main_window.show()
    sys.exit(app.exec_())
