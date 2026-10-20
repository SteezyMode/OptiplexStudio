"""Small GTK widget fakes shared by local workflow regression tests."""

class Widget:
    def __init__(self):
        self.sensitive = True
        self.text = ''
    def set_sensitive(self, sensitive): self.sensitive = sensitive
    def set_text(self, text): self.text = text

class Combo:
    def __init__(self): self.selected = 'old-game'
    def get_active_id(self): return self.selected
    def remove_all(self): self.selected = None
