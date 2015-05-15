import tkinter as tk

import pytest


@pytest.fixture(scope='session')
def tk_main_win():
    return tk.Tk()
