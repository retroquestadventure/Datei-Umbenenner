"""
Datei-Umbenenner
- Dateien per Drag & Drop in das Fenster ziehen
- Doppelklick auf "Neuer Name", um den Namen zu ändern
- Ein Klick auf "Umbenennen" führt die Änderungen durch

Installation (einmalig):
    pip install tkinterdnd2

Starten mit:
    python datei_umbenenner.py
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


"Prüfen ob tkinterdnd2 installiert wurde"
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    import sys
    print("Bitte zuerst tkinterdnd2 installieren:  pip install tkinterdnd2")
    sys.exit(1)


"Ungültige Zeichen für das Umbenennen"
UNGUELTIG = '<>:"/\\|?*'


class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Datei-Umbenenner")
        self.geometry("820x480")
        self.minsize(600, 300)

        self.eintraege = {}   # iid -> {"pfad": str, "neu": str}
        self.editor = None

        self._baue_gui()

        # Drop auf Fenster UND auf die Widgets darin erlauben
        for widget in (self, self.hinweis, self.tree):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._beim_drop)

    # ---------- GUI ----------
    def _baue_gui(self):
        self.hinweis = ttk.Label(
            self,
            text="Dateien hierher ziehen  •  Doppelklick auf „Neuer Name“ zum Ändern",
            anchor="center",
        )
        self.hinweis.pack(fill="x", padx=10, pady=(10, 4))

        rahmen = ttk.Frame(self)
        rahmen.pack(fill="both", expand=True, padx=10, pady=4)

        spalten = ("alt", "neu", "ordner")
        self.tree = ttk.Treeview(rahmen, columns=spalten, show="headings", selectmode="extended")
        self.tree.heading("alt", text="Aktueller Name")
        self.tree.heading("neu", text="Neuer Name")
        self.tree.heading("ordner", text="Ordner")
        self.tree.column("alt", width=250)
        self.tree.column("neu", width=250)
        self.tree.column("ordner", width=280)

        scroll = ttk.Scrollbar(rahmen, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self._starte_edit)
        self.tree.bind("<Delete>", lambda e: self._entfernen())

        leiste = ttk.Frame(self)
        leiste.pack(fill="x", padx=10, pady=10)

        ttk.Button(leiste, text="Dateien hinzufügen…", command=self._dialog).pack(side="left")
        ttk.Button(leiste, text="Auswahl entfernen", command=self._entfernen).pack(side="left", padx=6)
        ttk.Button(leiste, text="Liste leeren", command=self._leeren).pack(side="left")

        self.status = ttk.Label(leiste, text="0 Dateien")
        self.status.pack(side="left", padx=15)

        ttk.Button(leiste, text="Umbenennen", command=self._umbenennen).pack(side="right")

    # ---------- Dateien hinzufügen ----------
    def _beim_drop(self, event):
        self._hinzufuegen(self.tk.splitlist(event.data))

    def _dialog(self):
        pfade = filedialog.askopenfilenames(title="Dateien auswählen")
        self._hinzufuegen(pfade)

    def _hinzufuegen(self, pfade):
        vorhanden = {e["pfad"] for e in self.eintraege.values()}
        for p in pfade:
            p = os.path.normpath(p)
            if not os.path.isfile(p) or p in vorhanden:
                continue
            name = os.path.basename(p)
            iid = self.tree.insert("", "end", values=(name, name, os.path.dirname(p)))
            self.eintraege[iid] = {"pfad": p, "neu": name}
            vorhanden.add(p)
        self._status()

    def _entfernen(self):
        for iid in self.tree.selection():
            self.tree.delete(iid)
            self.eintraege.pop(iid, None)
        self._status()

    def _leeren(self):
        self.tree.delete(*self.tree.get_children())
        self.eintraege.clear()
        self._status()

    def _status(self):
        self.status.config(text=f"{len(self.eintraege)} Dateien")

    # ---------- Namen bearbeiten ----------
    def _starte_edit(self, event):
        self._beende_edit(speichern=False)
        if self.tree.identify_region(event.x, event.y) != "cell":
            return
        if self.tree.identify_column(event.x) != "#2":
            return
        iid = self.tree.identify_row(event.y)
        if not iid:
            return

        x, y, b, h = self.tree.bbox(iid, "neu")
        self.editor = ttk.Entry(self.tree)
        self.editor.place(x=x, y=y, width=b, height=h)
        self.editor.insert(0, self.eintraege[iid]["neu"])
        self.editor.focus_set()

        # Name ohne Endung vorauswählen
        text = self.eintraege[iid]["neu"]
        ende = text.rfind(".") if "." in text[1:] else len(text)
        self.editor.selection_range(0, ende)

        self.editor.bind("<Return>", lambda e: self._beende_edit(True, iid))
        self.editor.bind("<Escape>", lambda e: self._beende_edit(False, iid))
        self.editor.bind("<FocusOut>", lambda e: self._beende_edit(True, iid))

    def _beende_edit(self, speichern, iid=None):
        if not self.editor:
            return
        editor, self.editor = self.editor, None
        neu = editor.get().strip()
        editor.destroy()
        if speichern and iid in self.eintraege and neu:
            self.eintraege[iid]["neu"] = neu
            self.tree.set(iid, "neu", neu)

    # ---------- Umbenennen ----------
    def _umbenennen(self):
        self._beende_edit(False)
        aufgaben = []
        for iid, e in self.eintraege.items():
            alt = e["pfad"]
            neu = os.path.join(os.path.dirname(alt), e["neu"])
            if os.path.basename(alt) != e["neu"]:
                aufgaben.append((iid, alt, neu))

        if not aufgaben:
            messagebox.showinfo("Nichts zu tun", "Es wurde kein Name geändert.")
            return

        # Prüfunge vorab
        quellen = {os.path.normcase(a) for _, a, _ in aufgaben}
        ziele = set()
        for _, alt, neu in aufgaben:
            name = os.path.basename(neu)
            if any(c in UNGUELTIG for c in name):
                messagebox.showerror("Ungültiger Name", f"„{name}“ enthält ungültige Zeichen:\n{UNGUELTIG}")
                return
            key = os.path.normcase(neu)
            if key in ziele:
                messagebox.showerror("Doppelter Name", f"„{name}“ würde mehrfach vergeben.")
                return
            ziele.add(key)
            if os.path.exists(neu) and key not in quellen:
                messagebox.showerror("Existiert bereits", f"„{name}“ gibt es im Ordner schon.")
                return

        if not messagebox.askyesno("Bestätigen", f"{len(aufgaben)} Datei(en) umbenennen?"):
            return

        # Zweistufiges umbenennen über einen temporären Dateinamen, damit z. B. Tauschen von Namen klappt
        zwischen = []
        fehler = []
        for iid, alt, neu in aufgaben:
            temp = alt + ".__umbenenner_tmp__"
            try:
                os.rename(alt, temp)
                zwischen.append((iid, alt, temp, neu))
            except OSError as ex:
                fehler.append(f"{os.path.basename(alt)}: {ex}")

        for iid, alt, temp, neu in zwischen:
            try:
                os.rename(temp, neu)
                self.eintraege[iid]["pfad"] = neu
                self.tree.item(iid, values=(os.path.basename(neu), os.path.basename(neu), os.path.dirname(neu)))
            except OSError as ex:
                fehler.append(f"{os.path.basename(alt)}: {ex}")
                try:
                    os.rename(temp, alt)  # zurücksetzen
                except OSError:
                    pass

        if fehler:
            messagebox.showwarning("Teilweise fehlgeschlagen", "\n".join(fehler))
        else:
            messagebox.showinfo("Fertig", f"{len(zwischen)} Datei(en) umbenannt.")


if __name__ == "__main__":
    App().mainloop()
