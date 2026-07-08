def test_core_package_imports():
    import lunalink
    import lunalink.config
    import lunalink.constants
    import lunalink.environment
    import lunalink.frames
    import lunalink.orbit

    assert lunalink.__version__ == "0.1.0"
