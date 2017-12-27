from re import match


def test_version():
    from mongotime import __version__

    assert __version__
    assert isinstance(__version__, str)
    assert match(r'\d+\.\d+\.\d+$', __version__)
