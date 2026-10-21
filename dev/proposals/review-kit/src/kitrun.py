"""Kit wrapper, run as: kitrun.py script <script.py> [args...]      (runs the probe as __main__, as `python script.py args` would)
                       or: kitrun.py module <module> <Case.test>... (imports the probe, so a __main__ block in the middle of it
                                                                      does not run; the probe sees sys.argv == [module, $KIT_CK])
Before the probe starts, a helper that later branches removed (test_report_exports.tiny_png) is put back in memory,
only when the probe uses it. Nothing in the checkout is edited."""
import os, sys, runpy, unittest, importlib

mode = sys.argv[1]
ck = os.environ["KIT_CK"]


def shim(src_text):
    if "tiny_png" not in src_text:
        return
    sys.path.insert(0, os.path.join(ck, "dev", "tests"))
    sys.path.insert(0, os.path.join(ck, "system", "scripts"))
    try:
        import test_report_exports as T
        if not hasattr(T, "tiny_png"):
            import kitshim
            T.tiny_png = kitshim.tiny_png
            print("### kit: shimmed test_report_exports.tiny_png", flush=True)
    except Exception as e:  # the probe will report its own import error
        print("### kit: tiny_png shim not applied:", repr(e)[:120], flush=True)


if mode == "script":
    script = sys.argv[2]
    shim(open(script, encoding="utf-8").read())
    sys.argv = [script] + sys.argv[3:]
    runpy.run_path(script, run_name="__main__")
else:
    name = sys.argv[2]
    cases = sys.argv[3:]
    sys.path.insert(0, os.getcwd())
    shim(open(name + ".py", encoding="utf-8").read())
    sys.argv = [name, ck]
    m = importlib.import_module(name)
    unittest.main(module=m, argv=["kitrun"] + cases, verbosity=2)
